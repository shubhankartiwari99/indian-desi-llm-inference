from app.knowledge_base import KNOWLEDGE_BASE

FACT_TRIGGERS = {
    "indian_prime_minister": [
        "prime minister of india",
        "pm of india",
        "प्रधानमंत्री",
        "प्रधान मंत्री",
        "प्रਧਾਨ ਮੰਤਰੀ",
    ],
    "india_capital": [
        "capital of india",
        "राजधानी",
        "ਰਾਜਧਾਨੀ",
    ]
}

def resolve_fact(prompt: str, lang: str):
    p = prompt.lower()

    for fact_key, triggers in FACT_TRIGGERS.items():
        for t in triggers:
            if t in p:
                fact_text = (
                    KNOWLEDGE_BASE.get(lang, {}).get(fact_key)
                    or KNOWLEDGE_BASE["en"].get(fact_key)
                )

                if not fact_text:
                    return None

                return {
                    "answer": fact_text,
                    "confidence": "high",
                    "topic": fact_key,
                }

    return None