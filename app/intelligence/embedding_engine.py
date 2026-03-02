from sentence_transformers import SentenceTransformer
import numpy as np

class EmbeddingEngine:
    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def similarity(self, text_a: str, text_b: str) -> float:
        embeddings = self.model.encode([text_a, text_b], normalize_embeddings=True)
        sim = np.dot(embeddings[0], embeddings[1])
        return float(sim)
