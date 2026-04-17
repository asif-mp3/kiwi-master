"""
Centralized formatting utilities for Thara AI.
Consolidates number formatting, currency formatting, and date formatting logic.
"""

from typing import Union


def format_indian_number(value: Union[int, float], use_words: bool = True,
                        currency: bool = False, round_for_speech: bool = True) -> str:
    """
    Format numbers in Indian numbering system (crores, lakhs, thousands).

    Args:
        value: The number to format
        use_words: If True, use words (crores, lakhs). If False, use abbreviations (Cr, L)
        currency: If True, add ₹ symbol
        round_for_speech: If True, round to 1-2 significant digits for natural speech

    Returns:
        Formatted string like "12.5 lakhs" or "₹1.2 Cr"

    Examples:
        >>> format_indian_number(1250000)
        "12.5 lakhs"
        >>> format_indian_number(1250000, use_words=False, currency=True)
        "₹12.50 L"
        >>> format_indian_number(10500000)
        "about 1.1 crores"
    """
    if value is None:
        return "0"

    # Handle negative numbers
    sign = ""
    if value < 0:
        sign = "-"
        value = abs(value)

    # Thresholds for Indian numbering
    CRORE = 10000000  # 1,00,00,000
    LAKH = 100000     # 1,00,000
    THOUSAND = 1000   # 1,000

    # Add currency symbol if requested
    currency_symbol = "₹" if currency else ""

    # Format based on magnitude
    if value >= CRORE:
        crores = value / CRORE
        if round_for_speech:
            # Round for natural speech
            if crores >= 10:
                formatted = f"{crores:.0f}"
            else:
                formatted = f"{crores:.1f}"
            word = "crores" if use_words else "Cr"
            prefix = "about " if use_words else ""
            return f"{sign}{currency_symbol}{prefix}{formatted} {word}"
        else:
            formatted = f"{crores:.2f}"
            word = "crores" if use_words else "Cr"
            return f"{sign}{currency_symbol}{formatted} {word}"

    elif value >= LAKH:
        lakhs = value / LAKH
        if round_for_speech:
            # Round for natural speech
            if lakhs >= 10:
                formatted = f"{lakhs:.0f}"
            else:
                formatted = f"{lakhs:.1f}"
            word = "lakhs" if use_words else "L"
            prefix = "about " if use_words else ""
            return f"{sign}{currency_symbol}{prefix}{formatted} {word}"
        else:
            formatted = f"{lakhs:.2f}"
            word = "lakhs" if use_words else "L"
            return f"{sign}{currency_symbol}{formatted} {word}"

    elif value >= THOUSAND:
        thousands = value / THOUSAND
        if round_for_speech:
            # Round for natural speech
            formatted = f"{thousands:.0f}" if thousands >= 10 else f"{thousands:.1f}"
            word = "thousand" if use_words else "K"
            prefix = "around " if use_words else ""
            return f"{sign}{currency_symbol}{prefix}{formatted} {word}"
        else:
            formatted = f"{thousands:.2f}"
            word = "thousand" if use_words else "K"
            return f"{sign}{currency_symbol}{formatted} {word}"
    else:
        # Less than 1000 - show as-is
        if isinstance(value, float) and value != int(value):
            return f"{sign}{currency_symbol}{value:.2f}"
        else:
            return f"{sign}{currency_symbol}{int(value)}"



def format_percentage(value: Union[int, float], decimal_places: int = 1) -> str:
    """
    Format a value as a percentage.

    Args:
        value: The percentage value (e.g., 12.5 for 12.5%)
        decimal_places: Number of decimal places (default 1)

    Returns:
        Formatted percentage string

    Example:
        >>> format_percentage(12.47)
        "12.5%"
    """
    if value is None:
        return "0%"

    if decimal_places == 0:
        return f"{int(round(value))}%"
    else:
        return f"{value:.{decimal_places}f}%"


def humanize_metric_name(metric: str) -> str:
    """
    Convert metric/column names to human-readable format.

    Args:
        metric: Raw metric name (e.g., "total_sales_amount")

    Returns:
        Human-readable name (e.g., "Total Sales Amount")

    Example:
        >>> humanize_metric_name("total_sales_amount")
        "Total Sales Amount"
    """
    if not metric:
        return ""

    # Replace underscores and hyphens with spaces
    readable = metric.replace("_", " ").replace("-", " ")

    # Capitalize each word
    readable = " ".join(word.capitalize() for word in readable.split())

    return readable


