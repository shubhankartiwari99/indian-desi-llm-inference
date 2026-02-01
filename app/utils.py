import re


EXTRA_ID_PATTERN = re.compile(r"<extra_id_\d+>")


def normalize_output(text: str) -> str:
    """
    Cleans model output for user-facing consumption.

    - Removes mT5 sentinel tokens (<extra_id_*>)
    - Normalizes whitespace
    - Strips leading/trailing junk
    """

    if not text:
        return ""

    # Remove sentinel tokens
    cleaned = EXTRA_ID_PATTERN.sub("", text)

    # Normalize whitespace
    cleaned = " ".join(cleaned.split())

    return cleaned.strip()