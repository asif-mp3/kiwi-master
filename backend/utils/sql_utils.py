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
        >>> quote_identifier("Profit_Margin_%")
        '"Profit_Margin_%"'
    """
    # Never quote the SQL wildcard - it should remain unquoted
    if name == "*":
        return "*"

    # Special characters that require quoting in SQL identifiers
    # Note: '*' removed from this list as it's handled above
    special_chars = [' ', '-', '.', '(', ')', '%', '#', '@', '/', '\\', '+', '&', '$']
    if any(char in name for char in special_chars) or (name and name[0].isdigit()):
        return f'"{name}"'
    return name
