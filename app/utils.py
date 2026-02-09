import re


EXTRA_ID_PATTERN = re.compile(r"<extra_id_\d+>")
TASK_PREFIX_PATTERN = re.compile(
    r"^(?:\s*(?:empathy|fact|explain|uncertain|refusal)\s*:\s*)+",
    re.IGNORECASE,
)


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

    # Remove leaked task prefixes from decoder output.
    cleaned = TASK_PREFIX_PATTERN.sub("", cleaned)

    # Normalize whitespace
    cleaned = " ".join(cleaned.split())

    return cleaned.strip(" -:;")
