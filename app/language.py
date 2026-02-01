def detect_language(text: str) -> str:
    text = text.strip()

    # Devanagari (Hindi, Marathi)
    if any('\u0900' <= ch <= '\u097F' for ch in text):
        return "hi"

    # Gurmukhi (Punjabi)
    if any('\u0A00' <= ch <= '\u0A7F' for ch in text):
        return "pa"

    # Bengali
    if any('\u0980' <= ch <= '\u09FF' for ch in text):
        return "bn"

    # Tamil
    if any('\u0B80' <= ch <= '\u0BFF' for ch in text):
        return "ta"

    # Telugu
    if any('\u0C00' <= ch <= '\u0C7F' for ch in text):
        return "te"

    # Kannada
    if any('\u0C80' <= ch <= '\u0CFF' for ch in text):
        return "kn"

    # Default
    return "en"