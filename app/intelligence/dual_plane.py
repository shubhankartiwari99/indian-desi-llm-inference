from app.intelligence.embedding_engine import EmbeddingEngine

embedding_engine = EmbeddingEngine()

def ambiguity_score(text: str) -> float:
    hedges = [
        "maybe", "might", "could", "perhaps",
        "i think", "possibly", "it seems"
    ]
    count = 0
    lower = text.lower()
    for h in hedges:
        count += lower.count(h)
    return min(count / 5.0, 1.0)  # normalized cap

def evaluate_dual_plane(det_output: str, ent_outputs: list[str], det_tokens: int, ent_tokens: list[int]):

    # 1. Token and Length Analysis (average delta across all entropy samples)
    length_deltas = [abs(len(det_output) - len(ent)) for ent in ent_outputs]
    token_deltas = [abs(det_tokens - ent_tok) for ent_tok in ent_tokens]
    
    avg_length_delta = sum(length_deltas) / len(length_deltas) if length_deltas else 0
    avg_token_delta = sum(token_deltas) / len(token_deltas) if token_deltas else 0

    normalized_length = min(avg_length_delta / 500.0, 1.0)
    normalized_token = min(avg_token_delta / 150.0, 1.0)

    # 2. Ambiguity Analysis (average ambiguity across all entropy samples)
    ambiguities = [ambiguity_score(ent) for ent in ent_outputs]
    avg_ambiguity = sum(ambiguities) / len(ambiguities) if ambiguities else 0

    # 3. Monte Carlo Semantic Stability
    # a. Consistency among the entropy samples themselves
    entropy_consistency = embedding_engine.similarity_matrix(ent_outputs)
    
    # b. Similarity between the deterministic run and each entropy sample
    det_similarities = embedding_engine.reference_similarities(det_output, ent_outputs)
    det_entropy_similarity = sum(det_similarities) / len(det_similarities) if det_similarities else 1.0

    # Entropy variance (1 - consistency among entropy samples)
    entropy_variance = 1.0 - entropy_consistency
    semantic_dispersion = embedding_engine.semantic_dispersion(ent_outputs)
    pairwise_entropy = embedding_engine.pairwise_disagreement_entropy(ent_outputs)

    # 4. Final Confidence Metric Calculation
    # Research-grade confidence: High if entropy samples agree with each other AND they agree with deterministic
    confidence = entropy_consistency * det_entropy_similarity

    # Legacy instability calculation (shifted to rely on the new confidence metric)
    instability = 1.0 - confidence
    
    # Soften instability with length/token/ambiguity factors to maintain backwards compatibility 
    # with the UI's visual thresholds
    adjusted_instability = (
        0.45 * instability
        + 0.15 * normalized_length
        + 0.10 * normalized_token
        + 0.15 * avg_ambiguity
        + 0.15 * semantic_dispersion
    )
    adjusted_instability = min(adjusted_instability, 1.0)

    # Pairwise disagreement entropy captures divergence structure beyond centroid spread.
    uncertainty = min((0.5 * adjusted_instability) + (0.5 * pairwise_entropy), 1.0)
    
    # 4. Semantic Clustering
    cluster_stats = embedding_engine.cluster_responses(ent_outputs)

    if uncertainty > 0.65:
        uncertainty_level = "critical"
    elif uncertainty > 0.50:
        uncertainty_level = "high"
    elif uncertainty > 0.35:
        uncertainty_level = "moderate"
    else:
        uncertainty_level = "low"

    escalate = uncertainty > 0.40 or cluster_stats.get("self_consistency", 1.0) < 0.50

    return {
        "instability": round(adjusted_instability, 3),
        "entropy": round(pairwise_entropy, 3),
        "uncertainty": round(uncertainty, 3),
        "confidence": round(confidence, 3),
        "escalate": escalate,
        "uncertainty_level": uncertainty_level,
        "embedding_similarity": round(det_entropy_similarity, 3), # back-compat mappings
        "det_entropy_similarity": round(det_entropy_similarity, 3),
        "entropy_consistency": round(entropy_consistency, 3),
        "entropy_variance": round(entropy_variance, 3),
        "semantic_dispersion": round(semantic_dispersion, 3),
        "pairwise_disagreement_entropy": round(pairwise_entropy, 3),
        "sample_count": len(ent_outputs),
        "ambiguity": round(avg_ambiguity, 3),
        "length_delta": round(avg_length_delta, 3),
        "token_delta": round(avg_token_delta, 3),
        "ambiguities": [round(a, 3) for a in ambiguities],
        "cluster_count": cluster_stats["cluster_count"],
        "cluster_entropy": round(cluster_stats["cluster_entropy"], 3),
        "dominant_cluster_ratio": round(cluster_stats["dominant_cluster_ratio"], 3),
        "self_consistency": round(cluster_stats["self_consistency"], 3),
        "cluster_labels": cluster_stats["labels"]
    }
