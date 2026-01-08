"""
Shared SQL utility functions.
Consolidates common SQL helpers used across the codebase.
"""


def quote_identifier(name: str) -> str:
    """
    Quote SQL identifiers that contain spaces, special characters, or start with a digit.

    Args:
        name: Column or table name to potentially quote

    Returns:
        Quoted identifier if needed, otherwise original name

    Examples:
        >>> quote_identifier("Sales Amount")
        '"Sales Amount"'
        >>> quote_identifier("simple_col")
        'simple_col'
    """
    if ' ' in name or any(char in name for char in ['-', '.', '(', ')']) or (name and name[0].isdigit()):
        return f'"{name}"'
    return name
