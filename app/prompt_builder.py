from typing import Optional


def build_prompt(
    prompt: str,
    lang: str,
    intent: str,
    facts: Optional[str] = None
) -> str:
    """
    Build an intent-aware, language-aware, retrieval-aware prompt
    with OPTIONAL, bounded fact injection.
    """

    # --- Instruction block ---
    if intent == "factual":
        instruction = {
            "en": "Answer factually and briefly.",
            "hi": "तथ्यात्मक और संक्षिप्त उत्तर दें।",
            "pa": "ਤੱਥਾਂ ਅਨੁਸਾਰ ਸੰਖੇਪ ਜਵਾਬ ਦਿਓ।",
            "bn": "তথ্যভিত্তিক ও সংক্ষিপ্ত উত্তর দিন।",
            "ta": "உண்மை அடிப்படையில் சுருக்கமாக பதிலளிக்கவும்।",
            "te": "వాస్తవాల ఆధారంగా సంక్షిప్తంగా సమాధానం ఇవ్వండి।",
            "kn": "ತಥ್ಯಾಧಾರಿತವಾಗಿ ಸಂಕ್ಷಿಪ್ತ ಉತ್ತರ ನೀಡಿ।",
        }.get(lang, "Answer factually and briefly.")

    elif intent == "explanatory":
        instruction = {
            "en": "Explain clearly in simple words.",
            "hi": "सरल शब्दों में स्पष्ट रूप से समझाएँ।",
            "pa": "ਸੌਖੇ ਸ਼ਬਦਾਂ ਵਿੱਚ ਸਮਝਾਓ।",
            "bn": "সহজ ভাষায় ব্যাখ্যা করুন।",
            "ta": "எளிய சொற்களில் விளக்குங்கள்।",
            "te": "సరళమైన పదాల్లో వివరించండి।",
            "kn": "ಸರಳ ಪದಗಳಲ್ಲಿ ವಿವರಿಸಿ।",
        }.get(lang, "Explain clearly in simple words.")

    elif intent == "emotional":
        instruction = {
            "en": "Respond with empathy and emotional support.",
            "hi": "सहानुभूति और समझ के साथ उत्तर दें।",
            "pa": "ਸਹਾਨੁਭੂਤੀ ਅਤੇ ਸਮਝ ਨਾਲ ਜਵਾਬ ਦਿਓ।",
            "bn": "সহানুভূতির সঙ্গে উত্তর দিন।",
            "ta": "புரிதலுடனும் அக்கறையுடனும் பதிலளிக்கவும்।",
            "te": "సానుభూతితో స్పందించండి。",
            "kn": "ಸಹಾನುಭೂತಿಯೊಂದಿಗೆ ಉತ್ತರಿಸಿ।",
        }.get(lang, "Respond with empathy and emotional support.")

    else:  # conversational
        instruction = {
            "en": "Reply in a friendly and conversational tone.",
            "hi": "दोस्ताना और बातचीत के अंदाज़ में जवाब दें।",
            "pa": "ਦੋਸਤਾਨਾ ਅੰਦਾਜ਼ ਵਿੱਚ ਜਵਾਬ ਦਿਓ।",
            "bn": "বন্ধুত্বপূর্ণ ভঙ্গিতে উত্তর দিন।",
            "ta": "நண்பனான முறையில் பதிலளிக்கவும்।",
            "te": "స్నేహపూర్వకంగా స్పందించండి।",
            "kn": "ಸ್ನೇಹಪೂರ್ಣವಾಗಿ ಉತ್ತರಿಸಿ।",
        }.get(lang, "Reply in a friendly and conversational tone.")

    # Emotional responses must never receive factual injection
    if intent == "emotional":
        facts = None

    fact_block = ""
    if facts:
        fact_block = (
            "\n\n[FACTS — USE ONLY IF RELEVANT]\n"
            f"{facts}\n"
            "[END FACTS]\n"
        )

    return (
        f"{instruction}"
        f"{fact_block}\n"
        f"Question: {prompt}\n"
        f"Answer:"
    )