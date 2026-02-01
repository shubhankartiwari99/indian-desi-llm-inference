def detect_intent(prompt: str) -> str:
    """
    Lightweight heuristic-based intent detection.
    Returns one of:
    - factual
    - explanatory
    - conversational
    - emotional
    """

    p = prompt.lower().strip()

    emotional_triggers = [
        "feeling", "stress", "sad", "lonely", "anxious", "tired",
        "breakup", "depressed", "overwhelmed"
    ]

    explanatory_triggers = [
        "explain", "samjhao", "samjha", "kaise", "kyon",
        "why", "how", "meaning", "difference between"
    ]

    factual_triggers = [
        "who is", "what is", "when did", "capital of",
        "प्रधानमंत्री", "राजधानी", "कौन है", "क्या है"
    ]

    for t in emotional_triggers:
        if t in p:
            return "emotional"

    for t in explanatory_triggers:
        if t in p:
            return "explanatory"

    for t in factual_triggers:
        if t in p:
            return "factual"

    return "conversational"