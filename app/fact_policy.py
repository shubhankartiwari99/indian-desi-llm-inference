def should_inject_facts(intent: str, confidence: str) -> bool:
    """
    Decide whether facts are allowed to enter the prompt.
    """

    if intent == "factual" and confidence in {"high", "medium"}:
        return True

    if intent == "explanatory" and confidence == "medium":
        return True

    # Never inject facts for emotional or conversational
    return False