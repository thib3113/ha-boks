import secrets
import re

# Valid characters for Boks PIN codes
BOKS_CHAR_MAP = "0123456789AB"

# Regex to extract code from task summary
# Matches "   123456 - Description", "123456: Description", "123456 Description", "123456...Description"
# Group 1 is the code, Group 2 is the description
# Logic: Start of string -> Optional spaces -> 6 Hex chars -> Optional non-word chars (separators) -> Description
PARCEL_REGEX = re.compile(r"^\s*([0-9A-B]{6})(?:[\W_]+)?(.*)", re.IGNORECASE)


def parse_parcel_string(text: str) -> tuple[str | None, str]:
    """
    Parse a todo item string to extract potential code and description.

    Returns:
        (code, description)
        - code: The 6-char code if found, else None
        - description: The rest of the string (cleaned). If empty, returns ""

    """
    if not text:
        return None, ""

    text_stripped = text.strip()  # Keep original case for description
    match = PARCEL_REGEX.match(text_stripped)

    if match:
        code = match.group(1).upper()  # Codes should be uppercase for consistency
        description = match.group(2).strip()
        # If the code was the entire string, and no description was provided, description will be empty.
        # This is desired behavior.
        return code, description

    # No code found, return None and the original text as description
    return None, text_stripped  # Return original case for description if no code parsed


def generate_random_code() -> str:
    """Generate a random valid 6-character Boks code."""
    return "".join(secrets.choice(BOKS_CHAR_MAP) for _ in range(6))


def format_parcel_item(code: str | None, description: str) -> str:
    """
    Format the todo item string.
    If code is None, returns just the description.
    """
    clean_desc = description.strip()

    if code:
        # If the description already starts with the code (after parsing), don't duplicate it
        # (Edge case handling - though improved parsing should reduce this need)
        if clean_desc.upper().startswith(code.upper()):
            return clean_desc

        if not clean_desc:
            return code

        return f"{code} - {clean_desc}"

    return clean_desc  # If no code, just return the description
