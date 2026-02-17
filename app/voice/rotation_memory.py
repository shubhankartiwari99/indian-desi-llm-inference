class RotationMemory:
    def __init__(self):
        self.pools = {}

    @staticmethod
    def _normalize_key(key):
        if isinstance(key, (tuple, list)):
            return "|".join(str(part) for part in key)
        return str(key)

    def read_window(self, key, window_size=None, current_turn_index=None):
        pool_key = self._normalize_key(key)
        history = list(self.pools.get(pool_key, []))

        if current_turn_index is not None:
            history = [item for item in history if item["turn_index"] <= current_turn_index]

        if window_size is not None and window_size > 0:
            history = history[-window_size:]

        return [dict(item) for item in history]

    def record_usage(self, key, variant_id, turn_index):
        pool_key = self._normalize_key(key)
        self.pools.setdefault(pool_key, []).append(
            {
                "variant_id": int(variant_id),
                "turn_index": int(turn_index),
            }
        )

    def reset(self):
        self.pools.clear()

    def to_dict(self):
        return {
            "pools": {
                key: [dict(item) for item in items]
                for key, items in self.pools.items()
            }
        }
