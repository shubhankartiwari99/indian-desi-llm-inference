from typing import Optional, Dict


class KnowledgeRetriever:
    def __init__(self):
        self.facts = [
            {
                "keys": [
                    "prime minister of india",
                    "indian prime minister",
                    "भारत के प्रधानमंत्री",
                ],
                "topic": "government",
                "answers": {
                    "en": "Narendra Modi is the Prime Minister of India.",
                    "hi": "नरेंद्र मोदी भारत के प्रधानमंत्री हैं।",
                },
                "confidence": "high",
            },
            {
                "keys": ["ai", "artificial intelligence"],
                "topic": "ai",
                "answers": {
                    "en": "Artificial Intelligence is the ability of machines to simulate human intelligence.",
                    "hi": "कृत्रिम बुद्धिमत्ता मशीनों की मानव जैसी सोचने की क्षमता है।",
                },
                "confidence": "medium",
            },
        ]

    def retrieve(self, prompt: str, lang: str) -> Optional[Dict[str, str]]:
        p = prompt.lower()

        for entry in self.facts:
            for key in entry["keys"]:
                if key in p:
                    answer = entry["answers"].get(
                        lang,
                        entry["answers"].get("en")
                    )

                    return {
                        "fact": answer,
                        "confidence": entry["confidence"],
                        "topic": entry["topic"],
                    }

        return None