from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app import api as api_module
from app.inference import InferenceEngine
from app.intelligence.dual_plane import evaluate_dual_plane

class _StubEngine:
    def __init__(self, instability_values: list[float]):
        self.instability_values = instability_values
        self.calls = []

    def generate(self, prompt: str, max_new_tokens: int = 64, return_meta: bool = False, **kwargs):
        self.calls.append({"prompt": prompt, "max_new_tokens": max_new_tokens, "return_meta": return_meta})
        
        # Simulate different outputs for each sample
        response_text = f"response_{len(self.calls)}"
        
        if return_meta:
            return response_text, {}
        return response_text

def _client_with_engine(monkeypatch, engine) -> TestClient:
    monkeypatch.setattr(api_module, "_get_engine", lambda: engine)
    return TestClient(api_module.app)

def _mock_evaluate_dual_plane(instability_values):
    call_count = 0
    def mock_function(*args, **kwargs):
        nonlocal call_count
        instability = instability_values[call_count]
        call_count += 1
        return {
            "instability": instability,
            "confidence": 0.5,
            "entropy": 0.5,
            "uncertainty": 0.5,
            "escalate": False,
            "sample_count": 0,
            "semantic_dispersion": 0,
            "cluster_count": 0,
            "cluster_entropy": 0,
            "dominant_cluster_ratio": 0,
            "self_consistency": 0,
            "det_entropy_similarity": 0,
            "entropy_consistency": 0,
            "entropy_variance": 0,
            "pairwise_disagreement_entropy": 0,
            "uncertainty_level": "low",
        }
    return mock_function

def test_adaptive_sampling_stops_early(monkeypatch):
    # Instability stabilizes after the 4th sample
    instability_values = [0.5, 0.4, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3]
    engine = _StubEngine(instability_values)
    
    monkeypatch.setattr("app.api.evaluate_dual_plane", _mock_evaluate_dual_plane(instability_values))
    
    client = _client_with_engine(monkeypatch, engine)
    
    response = client.post("/generate", json={"prompt": "test", "monte_carlo_samples": 10})
    
    assert response.status_code == 200
    body = response.json()
    assert body["samples_used"] == 4

def test_adaptive_sampling_runs_min_samples(monkeypatch):
    # Instability stabilizes immediately
    instability_values = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1]
    engine = _StubEngine(instability_values)
    
    monkeypatch.setattr("app.api.evaluate_dual_plane", _mock_evaluate_dual_plane(instability_values))
    
    client = _client_with_engine(monkeypatch, engine)
    
    response = client.post("/generate", json={"prompt": "test", "monte_carlo_samples": 10})
    
    assert response.status_code == 200
    body = response.json()
    assert body["samples_used"] == 4

def test_adaptive_sampling_runs_max_samples(monkeypatch):
    # Instability never stabilizes
    instability_values = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    engine = _StubEngine(instability_values)
    
    monkeypatch.setattr("app.api.evaluate_dual_plane", _mock_evaluate_dual_plane(instability_values))
    
    client = _client_with_engine(monkeypatch, engine)
    
    response = client.post("/generate", json={"prompt": "test", "monte_carlo_samples": 10})
    
    assert response.status_code == 200
    body = response.json()
    assert body["samples_used"] == 10
