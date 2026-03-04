from sentence_transformers import SentenceTransformer
import numpy as np

class EmbeddingEngine:
    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def similarity(self, text_a: str, text_b: str) -> float:
        embeddings = self.model.encode([text_a, text_b], normalize_embeddings=True)
        sim = np.dot(embeddings[0], embeddings[1])
        return float(sim)

    def similarity_matrix(self, texts: list[str]) -> float:
        if not texts or len(texts) < 2:
            return 1.0
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        # Compute pairwise dot products (cosine similarities since normalized)
        sim_matrix = np.dot(embeddings, embeddings.T)
        # We want the average of the upper triangle, excluding the diagonal (self-similarity)
        n = len(texts)
        i_upper = np.triu_indices(n, 1)
        avg_sim = np.mean(sim_matrix[i_upper])
        return float(avg_sim)
