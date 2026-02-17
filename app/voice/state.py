from dataclasses import dataclass
from typing import Optional


@dataclass
class SessionVoiceState:
    rotation_memory: "RotationMemory"
    escalation_state: str = "none"  # none | escalating | latched
    latched_theme: Optional[str] = None  # family | resignation | None
    emotional_turn_index: int = 0
    selector_invocation_count: int = 0
    last_skeleton: Optional[str] = None  # A | B | C | D | None
    last_intent: Optional[str] = None
    last_emotional_lang: Optional[str] = None

    def reset(self):
        self.rotation_memory.reset()
        self.escalation_state = "none"
        self.latched_theme = None
        self.emotional_turn_index = 0
        self.selector_invocation_count = 0
        self.last_skeleton = None
        self.last_intent = None
        self.last_emotional_lang = None

    def to_dict(self):
        return {
            "rotation_memory": self.rotation_memory.to_dict(),
            "escalation_state": self.escalation_state,
            "latched_theme": self.latched_theme,
            "emotional_turn_index": self.emotional_turn_index,
            "selector_invocation_count": self.selector_invocation_count,
            "last_skeleton": self.last_skeleton,
            "last_intent": self.last_intent,
            "last_emotional_lang": self.last_emotional_lang,
        }
