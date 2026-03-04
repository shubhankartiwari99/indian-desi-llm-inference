from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.cluster import AgglomerativeClustering
from collections import Counter
import math

class EmbeddingEngine:
    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def _encode(self, texts: list[str]) -> np.ndarray:
        return self.model.encode(texts, normalize_embeddings=True)

    def similarity(self, text_a: str, text_b: str) -> float:
        embeddings = self._encode([text_a, text_b])
        sim = np.dot(embeddings[0], embeddings[1])
        return float(sim)

    def reference_similarities(self, reference_text: str, texts: list[str]) -> list[float]:
        if not texts:
            return []
        embeddings = self._encode([reference_text, *texts])
        ref = embeddings[0]
        targets = embeddings[1:]
        sims = np.dot(targets, ref)
        return [float(val) for val in sims]

    def similarity_matrix(self, texts: list[str]) -> float:
        if not texts or len(texts) < 2:
            return 1.0
        embeddings = self._encode(texts)
        # Compute pairwise dot products (cosine similarities since normalized)
        sim_matrix = np.dot(embeddings, embeddings.T)
        # We want the average of the upper triangle, excluding the diagonal (self-similarity)
        n = len(texts)
        i_upper = np.triu_indices(n, 1)
        avg_sim = np.mean(sim_matrix[i_upper])
        return float(avg_sim)

    def semantic_dispersion(self, texts: list[str]) -> float:
        if not texts or len(texts) < 2:
            return 0.0
        embeddings = self._encode(texts)
        centroid = np.mean(embeddings, axis=0)
        distances = np.linalg.norm(embeddings - centroid, axis=1)
        # Distances on normalized vectors are bounded by ~[0, 2], normalize to [0, 1].
        normalized = float(np.mean(distances) / 2.0)
        return max(0.0, min(normalized, 1.0))

    def pairwise_disagreement_entropy(self, texts: list[str]) -> float:
        if not texts or len(texts) < 3:
            return 0.0

        embeddings = self._encode(texts)
        sim_matrix = np.dot(embeddings, embeddings.T)
        n = len(texts)
        i_upper = np.triu_indices(n, 1)
        pairwise_similarities = sim_matrix[i_upper]

        # Disagreement mass grows as similarity drops.
        disagreement = np.clip(1.0 - pairwise_similarities, 0.0, 2.0)
        total = float(np.sum(disagreement))
        if total <= 1e-12:
            return 0.0

        probs = disagreement / total
        entropy = float(-np.sum(probs * np.log(probs + 1e-10)))

        # Normalize entropy to [0, 1] for easy thresholding.
        max_entropy = float(np.log(len(probs))) if len(probs) > 1 else 1.0
        normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0.0
        return max(0.0, min(normalized_entropy, 1.0))

    def cluster_responses(self, texts: list[str], threshold: float = 0.75) -> dict:
        if not texts:
            return {
                "cluster_count": 0,
                "cluster_entropy": 0.0,
                "dominant_cluster_ratio": 0.0,
                "self_consistency": 0.0,
                "labels": []
            }
        
        if len(texts) == 1:
            return {
                "cluster_count": 1,
                "cluster_entropy": 0.0,
                "dominant_cluster_ratio": 1.0,
                "self_consistency": 1.0,
                "labels": [0]
            }

        embeddings = self._encode(texts)
        
        # Agglomerative clustering expects distance matrix or handles cosine directly
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=1.0 - threshold,
            metric="cosine",
            linkage="average"
        )
        
        # Fit and predict labels
        labels = clustering.fit_predict(embeddings)
        
        # Compute cluster statistics
        counts = Counter(labels)
        total = sum(counts.values())
        
        cluster_probs = [c / total for c in counts.values()]
        entropy = -sum(p * math.log(p) for p in cluster_probs)
        dominant_ratio = max(cluster_probs)
        
        # Normalize entropy
        max_entropy = math.log(len(counts)) if len(counts) > 1 else 1.0
        normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0.0
        
        return {
            "cluster_count": len(counts),
            "cluster_entropy": max(0.0, min(normalized_entropy, 1.0)),
            "dominant_cluster_ratio": float(dominant_ratio),
            "self_consistency": float(dominant_ratio),
            "labels": labels.tolist()
        }
