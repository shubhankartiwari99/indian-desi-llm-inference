def get_response_scaffold(intent: str, lang: str) -> str:
    """
    Returns a short, human-like prefix based on intent and language.
    """

    if intent == "emotional":
        return {
            "en": "I hear you. You're not alone. ",
            "hi": "मैं समझ सकता हूँ कि आप क्या महसूस कर रहे हैं। ",
            "pa": "ਮੈਂ ਤੁਹਾਡੀ ਗੱਲ ਸਮਝਦਾ ਹਾਂ। ",
            "bn": "আমি বুঝতে পারছি আপনি কী অনুভব করছেন। ",
            "ta": "நான் உங்களைப் புரிந்துகொள்கிறேன். ",
            "te": "మీ భావన నాకు అర్థమవుతోంది. ",
            "kn": "ನಾನು ನಿಮ್ಮ ಭಾವನೆಗಳನ್ನು ಅರ್ಥಮಾಡಿಕೊಳ್ಳುತ್ತೇನೆ. ",
        }.get(lang, "I hear you. ")

    if intent == "factual":
        return {
            "en": "Here's a clear and factual answer: ",
            "hi": "यह एक संक्षिप्त और तथ्यात्मक उत्तर है: ",
            "pa": "ਇਹ ਇੱਕ ਤੱਥਾਂ ਅਧਾਰਤ ਜਵਾਬ ਹੈ: ",
            "bn": "এটি একটি তথ্যভিত্তিক উত্তর: ",
            "ta": "இதோ ஒரு உண்மை அடிப்படையிலான பதில்: ",
            "te": "ఇది ఒక వాస్తవ ఆధారిత సమాధానం: ",
            "kn": "ಇದು ಒಂದು ತಥ್ಯಾಧಾರಿತ ಉತ್ತರ: ",
        }.get(lang, "Here's a factual answer: ")

    if intent == "explanatory":
        return {
            "en": "Let me explain this simply: ",
            "hi": "इसे सरल शब्दों में समझते हैं: ",
            "pa": "ਇਸਨੂੰ ਸੌਖੇ ਸ਼ਬਦਾਂ ਵਿੱਚ ਸਮਝੀਏ: ",
            "bn": "সহজ ভাষায় ব্যাখ্যা করি: ",
            "ta": "இதை எளிய வார்த்தைகளில் விளக்கலாம்: ",
            "te": "దీన్ని సరళంగా వివరిద్దాం: ",
            "kn": "ಇದನ್ನು ಸರಳವಾಗಿ ವಿವರಿಸೋಣ: ",
        }.get(lang, "Let me explain: ")

    # conversational default
    return {
        "en": "Here's what I think: ",
        "hi": "मेरे हिसाब से: ",
        "pa": "ਮੇਰੇ ਖ਼ਿਆਲ ਵਿੱਚ: ",
        "bn": "আমার মতে: ",
        "ta": "எனக்கு தோன்றுவது: ",
        "te": "నా అభిప్రాయం ప్రకారం: ",
        "kn": "ನನ್ನ ಅಭಿಪ್ರಾಯದಲ್ಲಿ: ",
    }.get(lang, "Here's what I think: ")