from collections import deque

class ConversationMemory:
    """
    Short-term conversational memory.
    Stores the last N user/assistant turns.
    """

    def __init__(self, max_turns: int = 4):
        self.history = deque(maxlen=max_turns * 2)

    def add_user(self, text: str):
        self.history.append(("User", text))

    def add_assistant(self, text: str):
        self.history.append(("Assistant", text))

    def is_empty(self) -> bool:
        return len(self.history) == 0

    def render(self) -> str:
        """
        Render memory as a conversation block.
        """
        lines = []
        for role, text in self.history:
            lines.append(f"{role}: {text}")
        return "\n".join(lines)

    def clear(self):
        self.history.clear()