"""
Recommendation service - data-grounded business suggestions.

Goal:
- Handle advisory questions like "recommendations to increase sales in Chennai"
- Stay HIGH ACCURACY: recommendations must be grounded in the user's data (DuckDB)
- Use LLM only for phrasing/creativity, not for inventing facts
"""

from __future__ import annotations

from datetime import datetime
import re
from typing import Any, Optional

import pandas as pd

from analytics_engine.duckdb_manager import DuckDBManager
from utils.logger import get_logger

logger = get_logger("recommendation_service")


_ADVISORY_PATTERNS = [
    r"\brecommend\b", r"\brecommendation\b", r"\bsuggest\b", r"\bsuggestion\b",
    r"\bstrategy\b", r"\bstrategies\b", r"\bimprove\b", r"\bincrease\b",
    r"\bgrow\b", r"\bgrowth\b", r"\bboost\b", r"\bdrive\b",
    r"\badvice\b", r"\badvise\b", r"\bplan\b", r"\boptimi[sz]e\b",
    r"\bwhat should i do\b", r"\bhow can i\b",
]


def _is_advisory_question(question: str) -> bool:
    q = (question or "").lower()
    if not any(re.search(p, q) for p in _ADVISORY_PATTERNS):
        return False
    # Keep this data/business-oriented to avoid hijacking generic chit-chat.
    business_terms = [
        "sales", "revenue", "profit", "cost", "margin", "attendance", "hours",
        "stock", "inventory", "category", "branch", "state", "performance", "trend",
    ]
    return any(term in q for term in business_terms)


def _extract_location_fallback(question: str) -> Optional[str]:
    """
    Fallback location extraction for advisory questions.
    Keeps it conservative: only extracts a single trailing token after "in/for/at".
    """
    q = (question or "").strip()
    m = re.search(r"\b(?:in|for|at)\s+([A-Za-z][A-Za-z\s]{2,40})\??$", q, re.IGNORECASE)
    if not m:
        return None
    loc = m.group(1).strip()
    # Avoid catching generic words
    if loc.lower() in {"india", "business", "sales", "revenue"}:
        return None
    return loc


def _pick_best_metric_column(columns: dict[str, dict], question: str) -> Optional[str]:
    q = (question or "").lower()
    metric_cols = [c for c, info in columns.items() if info.get("role") == "metric"]
    if not metric_cols:
        return None
    # Prefer "revenue"/"sales"/"amount" like names depending on the ask
    want_revenue = "revenue" in q
    want_profit = "profit" in q
    preferred_terms = []
    if want_profit:
        preferred_terms = ["profit", "margin"]
    elif want_revenue:
        preferred_terms = ["revenue", "sales", "amount", "value", "net"]
    else:
        preferred_terms = ["sales", "revenue", "amount", "value"]

    for term in preferred_terms:
        for c in metric_cols:
            if term in c.lower():
                return c
    return metric_cols[0]


def _pick_dimension_column(columns: dict[str, dict], keywords: list[str]) -> Optional[str]:
    dim_cols = [c for c, info in columns.items() if info.get("role") == "dimension"]
    if not dim_cols:
        return None
    for kw in keywords:
        for c in dim_cols:
            if kw in c.lower():
                return c
    return dim_cols[0]


def _pick_date_column(columns: dict[str, dict]) -> Optional[str]:
    date_cols = [c for c, info in columns.items() if info.get("role") == "date"]
    return date_cols[0] if date_cols else None


def _escape_like(value: str) -> str:
    # DuckDB supports ESCAPE for LIKE; keep it minimal
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _safe_date_expr(column_name: str) -> str:
    # Handle DATE/TIMESTAMP/VARCHAR uniformly in DuckDB.
    return (
        f'COALESCE('
        f'TRY_CAST("{column_name}" AS DATE), '
        f'CAST(TRY_CAST("{column_name}" AS TIMESTAMP) AS DATE)'
        f')'
    )


def _compute_chennai_like_insights(
    table: str,
    date_col: str,
    metric_col: str,
    category_col: Optional[str],
    location_col: Optional[str],
    location_value: Optional[str],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Returns:
    - df_monthly: month/category aggregated totals (for grounding + optional UI data)
    - facts: dict of computed facts to feed the LLM prompt
    """
    db = DuckDBManager()

    date_expr = _safe_date_expr(date_col)

    # Determine last 3 months window based on actual parsable dates.
    max_date_df = db.query(
        f'SELECT MAX({date_expr}) AS max_date FROM "{table}" WHERE {date_expr} IS NOT NULL'
    )
    max_date_val = max_date_df.iloc[0]["max_date"] if len(max_date_df) else None
    if max_date_val is None or str(max_date_val).lower() in {"nan", "none"}:
        raise ValueError(f"Table '{table}' has no max date in column '{date_col}'")

    # DuckDB returns python datetime sometimes, sometimes string; normalize
    if isinstance(max_date_val, datetime):
        max_date = max_date_val
    else:
        max_date = pd.to_datetime(max_date_val, errors="coerce").to_pydatetime()
    if not max_date:
        raise ValueError(f"Could not parse max date for '{table}.{date_col}'")

    end_date = max_date.date()
    start_date = (pd.Timestamp(end_date) - pd.DateOffset(months=3)).date()

    where = [f"{date_expr} >= DATE '{start_date}'", f"{date_expr} < DATE '{end_date}'"]
    if location_col and location_value:
        # Use a case-insensitive contains match for robustness
        loc = _escape_like(location_value.strip())
        where.append(f'LOWER(CAST("{location_col}" AS VARCHAR)) LIKE \'%{loc.lower()}%\' ESCAPE \'\\\\\'')

    where_sql = " AND ".join(where)

    if category_col:
        sql = f"""
        SELECT
          DATE_TRUNC('month', {date_expr}) AS month,
          CAST("{category_col}" AS VARCHAR) AS category,
          SUM(CAST("{metric_col}" AS DOUBLE)) AS total
        FROM "{table}"
        WHERE {where_sql}
          AND {date_expr} IS NOT NULL
          AND "{category_col}" IS NOT NULL
        GROUP BY 1, 2
        ORDER BY 1 ASC, 3 DESC
        """
    else:
        sql = f"""
        SELECT
          DATE_TRUNC('month', {date_expr}) AS month,
          SUM(CAST("{metric_col}" AS DOUBLE)) AS total
        FROM "{table}"
        WHERE {where_sql}
          AND {date_expr} IS NOT NULL
        GROUP BY 1
        ORDER BY 1 ASC
        """

    df = db.query(sql)
    if df is None or df.empty:
        raise ValueError("No rows found for the requested period/location")

    facts: dict[str, Any] = {
        "table": table,
        "date_column": date_col,
        "metric_column": metric_col,
        "category_column": category_col,
        "location_column": location_col,
        "location_value": location_value,
        "window_start": str(start_date),
        "window_end": str(end_date),
        "rows": int(len(df)),
    }

    # Compute growth / top categories when category available
    if category_col:
        # aggregate last month vs first month in window for each category
        df2 = df.copy()
        df2["month"] = pd.to_datetime(df2["month"], errors="coerce")
        df2 = df2.dropna(subset=["month"])
        if not df2.empty:
            first_m = df2["month"].min()
            last_m = df2["month"].max()
            first = df2[df2["month"] == first_m].groupby("category")["total"].sum()
            last = df2[df2["month"] == last_m].groupby("category")["total"].sum()
            growth = (last - first).fillna(0.0)
            top_last = last.sort_values(ascending=False).head(5)
            top_growth = growth.sort_values(ascending=False).head(5)
            facts["top_categories_last_month"] = [(k, float(v)) for k, v in top_last.items()]
            facts["top_growing_categories"] = [(k, float(v)) for k, v in top_growth.items()]
            facts["first_month"] = str(first_m.date())
            facts["last_month"] = str(last_m.date())

    return df, facts


def _format_recommendations_fallback(facts: dict[str, Any], location: Optional[str]) -> str:
    # Deterministic, crisp recommendations built only from computed facts.
    loc = location or "this location"
    top_growth = facts.get("top_growing_categories") or []
    top_last = facts.get("top_categories_last_month") or []
    first_m = facts.get("first_month")
    last_m = facts.get("last_month")

    def _fmt(v: float) -> str:
        if v >= 100000:
            return f"{v/100000:.2f}L"
        return f"{v:,.0f}"

    lines = [f"Boss, to increase sales in {loc}, focus on a few high-impact moves."]
    if top_growth:
        cat, growth_val = top_growth[0]
        lines.append(
            f"Your strongest momentum is in {cat}, so prioritize campaigns and visibility there first."
        )
    if len(top_growth) > 1:
        cat2, _ = top_growth[1]
        lines.append(
            f"Use bundles and cross-sell offers around {cat2} to convert interest into larger baskets."
        )
    if top_last:
        best_cat, best_val = top_last[0]
        lines.append(
            f"Keep {best_cat} always in stock and prominently promoted, since it is your top revenue driver."
        )
        lines.append(f"As a reference point, {best_cat} delivered roughly {_fmt(float(best_val))} in the latest month.")
    lines.append("Shift budget weekly away from low-converting creatives and channels to the categories that are responding.")
    if first_m and last_m:
        lines.append(f"Review performance each week against the {first_m} to {last_m} trend and quickly stop what is not working.")
    else:
        lines.append("Review performance each week and quickly stop what is not working.")
    return "\n".join(lines[:7])


def _clean_recommendation_text(text: str) -> str:
    # Remove markdown symbols and keep response concise for voice/caption UX.
    t = (text or "").strip()
    t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
    t = re.sub(r"^[\-\*\u2022]\s*", "", t, flags=re.MULTILINE)
    t = t.replace("```", "")
    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    if len(lines) > 7:
        lines = lines[:7]
    return "\n".join(lines)


def maybe_generate_recommendations(
    question: str,
    entities: dict[str, Any],
    profile_store,
) -> Optional[dict[str, Any]]:
    """
    If this is an advisory question, return a ProcessQueryResponse-like dict.
    Otherwise, return None and the normal pipeline continues.
    """
    if not _is_advisory_question(question):
        return None

    location = (entities or {}).get("location") or _extract_location_fallback(question) or None

    profiles = profile_store.get_all_profiles() if profile_store else {}
    if not profiles:
        return None

    # Pick best table that can support time-series + metric + (optional) category/location breakdown
    best_table = None
    best_score = -1
    best_profile = None
    for table, prof in profiles.items():
        cols = prof.get("columns", {}) if isinstance(prof, dict) else {}
        if not cols:
            continue
        has_date = any(info.get("role") == "date" for info in cols.values())
        has_metric = any(info.get("role") == "metric" for info in cols.values())
        if not (has_date and has_metric):
            continue
        # Score: prefer location+category dims if present
        dim_names = [c.lower() for c, info in cols.items() if info.get("role") == "dimension"]
        score = 0
        if any("category" in n or "product" in n or "item" in n for n in dim_names):
            score += 2
        if any("city" in n or "branch" in n or "area" in n or "location" in n or "state" in n for n in dim_names):
            score += 2
        score += int(prof.get("row_count", 0) > 50)  # tiny preference for non-trivial tables
        if score > best_score:
            best_score = score
            best_table = table
            best_profile = prof

    if not best_table or not best_profile:
        return None

    columns = best_profile.get("columns", {})
    date_col = _pick_date_column(columns)
    metric_col = _pick_best_metric_column(columns, question)
    if not date_col or not metric_col:
        return None

    category_col = _pick_dimension_column(columns, ["category", "product", "item", "sku"])
    location_col = _pick_dimension_column(columns, ["city", "branch", "area", "location", "state", "region", "zone"])

    try:
        df_monthly, facts = _compute_chennai_like_insights(
            table=best_table,
            date_col=date_col,
            metric_col=metric_col,
            category_col=category_col,
            location_col=location_col,
            location_value=location,
        )
    except Exception as e:
        logger.warning("Recommendation grounding failed: %s", e)
        return {
            "success": True,
            "explanation": "Boss, I could not compute reliable recommendations from the current date format in this table. Please normalize date values and try again.",
            "data": None,
            "plan": None,
            "table_used": best_table,
            "routing_confidence": 0.8,
            "was_followup": False,
            "entities_extracted": {"location": location, "advisory": True},
            "visualization": None,
            "debug_timings": {"recommendations": -1},
        }

    # Hard guardrail for client accuracy: recommendation text is always deterministic.
    # This avoids hallucinated or generic advisory responses.
    text = _clean_recommendation_text(_format_recommendations_fallback(facts, location))

    # Provide the aggregated data for UI table if needed (kept small)
    df_serializable = df_monthly.copy()
    if "month" in df_serializable.columns:
        df_serializable["month"] = pd.to_datetime(df_serializable["month"], errors="coerce").astype(str)
    data_records = df_serializable.head(200).to_dict(orient="records")
    return {
        "success": True,
        "explanation": text,
        "data": data_records,
        "plan": {
            "query_type": "trend",
            "table": best_table,
            "metrics": [metric_col],
            "group_by": [c for c in [category_col] if c],
        },
        "table_used": best_table,
        "routing_confidence": 1.0,
        "was_followup": False,
        "entities_extracted": {"location": location, "advisory": True},
        "visualization": None,
        "debug_timings": {"recommendations": -1},
    }

