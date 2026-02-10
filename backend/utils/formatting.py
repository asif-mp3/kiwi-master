"""
Centralized formatting utilities for Thara AI.
Consolidates number formatting, currency formatting, and date formatting logic.
"""

from typing import Union, Optional


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


def format_indian_commas(value: Union[int, float]) -> str:
    """
    Add Indian-style comma separators to numbers.
    Indian format: 1,23,45,678 (groups of 2 after first 3 digits)

    Args:
        value: Number to format

    Returns:
        String with Indian comma separators

    Example:
        >>> format_indian_commas(12345678)
        "1,23,45,678"
    """
    if value is None:
        return "0"

    # Handle negative numbers
    sign = ""
    if value < 0:
        sign = "-"
        value = abs(value)

    # Convert to string and split integer/decimal
    if isinstance(value, float):
        str_value = f"{value:.2f}"
        if "." in str_value:
            integer_part, decimal_part = str_value.split(".")
            decimal_suffix = f".{decimal_part}"
        else:
            integer_part = str_value
            decimal_suffix = ""
    else:
        integer_part = str(int(value))
        decimal_suffix = ""

    # Apply Indian comma formatting
    if len(integer_part) <= 3:
        result = integer_part
    else:
        # Last 3 digits
        result = integer_part[-3:]
        remaining = integer_part[:-3]

        # Add remaining digits in groups of 2 from right to left
        while remaining:
            if len(remaining) <= 2:
                result = remaining + "," + result
                remaining = ""
            else:
                result = remaining[-2:] + "," + result
                remaining = remaining[:-2]

    return f"{sign}{result}{decimal_suffix}"


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


def format_number_smart(value: Union[int, float], metric_type: Optional[str] = None) -> str:
    """
    Smart number formatting based on metric type.
    Chooses appropriate formatting based on context.

    Args:
        value: Number to format
        metric_type: Type hint ('currency', 'percentage', 'count', 'ratio')

    Returns:
        Appropriately formatted string
    """
    if value is None:
        return "N/A"

    # Auto-detect metric type if not provided
    if metric_type is None:
        if isinstance(value, float) and 0 < value < 1:
            metric_type = 'ratio'
        elif abs(value) >= 1000:
            metric_type = 'currency'  # Assume large numbers are currency
        else:
            metric_type = 'count'

    # Format based on type
    if metric_type == 'percentage':
        return format_percentage(value)
    elif metric_type == 'currency':
        return format_indian_number(value, use_words=True, currency=True)
    elif metric_type == 'ratio':
        return format_percentage(value * 100)
    else:  # count or default
        if abs(value) >= 1000:
            return format_indian_number(value, use_words=True, currency=False)
        else:
            return str(int(value)) if value == int(value) else f"{value:.2f}"
