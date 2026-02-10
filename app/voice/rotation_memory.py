class RotationMemory:
    def __init__(self):
        self.pools = {}

    def read_window(self, key):
        return []

    def record_usage(self, key, variant_id, turn_index):
        # Phase 0: no-op
        pass

    def reset(self):
        self.pools.clear()

    def to_dict(self):
        return {"pools": {}}
