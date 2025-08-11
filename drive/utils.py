import re
import unicodedata

def is_safe_filename(name: str, max_length: int = 255) -> bool:
    """
    Checks if a filename is safe for storage/serving.
    Returns True if safe, False if not.
    - No path traversal chars
    - No null bytes
    - Reasonable length
    - Has a valid base name
    """

    if not name:
        return False

    # Normalize Unicode
    name = unicodedata.normalize("NFC", name)

    # Check length
    if len(name) > max_length:
        return False

    # Disallow path separators and null bytes
    if any(char in name for char in ('/', '\\', '\x00')):
        return False

    # Must have a visible base name (no empty before extension)
    base, ext = re.match(r"^(.*?)(\.[^.]+)?$", name).groups()
    if not base.strip():
        return False

    # Optional: only allow safe characters
    safe_pattern = r'^[\w\-. ()\u00C0-\u017F]+$'  # letters, numbers, dash, dot, space, some Unicode
    if not re.match(safe_pattern, name):
        return False

    return True

def is_safe_foldername(name: str, max_length: int = 255) -> bool:
    """
    Checks if a folder name is safe for storage/serving.
    Returns True if safe, False if not.
    """

    if not name:
        return False

    # Normalize Unicode
    name = unicodedata.normalize("NFC", name)

    # Check length
    if len(name) > max_length:
        return False

    # Disallow path separators and null bytes
    if any(char in name for char in ('/', '\\', '\x00')):
        return False

    # Disallow names that are just dots or spaces
    if name.strip(" .") == "":
        return False

    # Disallow reserved Windows device names (case-insensitive)
    reserved_names = {
        ".", "..", "CON", "PRN", "AUX", "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }
    if name.upper() in reserved_names:
        return False

    # Only allow safe characters: letters, numbers, dash, underscore, space, some Unicode
    safe_pattern = r'^[\w\- .()\u00C0-\u017F]+$'
    if not re.match(safe_pattern, name):
        return False

    return True
