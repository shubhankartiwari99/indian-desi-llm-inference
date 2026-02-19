"""Tests for model fingerprint utility."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.model_fingerprint import compute_model_fingerprint, REQUIRED_FILES_ORDER


def _build_minimal_model_dir(tmp_path: Path, include_optional: bool = True) -> Path:
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    required_files = [
        "config.json",
        "model.safetensors",
        "tokenizer_config.json",
        "spiece.model",
    ]
    for name in required_files:
        (model_dir / name).write_bytes(f"{name}-content".encode("utf-8"))

    if include_optional:
        (model_dir / "generation_config.json").write_bytes(b"gen-config")
        (model_dir / "special_tokens_map.json").write_bytes(b"special-tokens")

    return model_dir


def test_fingerprint_deterministic(tmp_path: Path):
    model_dir = _build_minimal_model_dir(tmp_path)
    first = compute_model_fingerprint(model_dir)
    second = compute_model_fingerprint(model_dir)
    assert first == second


def test_fingerprint_changes_on_mutation(tmp_path: Path):
    model_dir = _build_minimal_model_dir(tmp_path)
    initial = compute_model_fingerprint(model_dir)
    (model_dir / "config.json").write_bytes(b"mutated")
    updated = compute_model_fingerprint(model_dir)
    assert initial != updated


def test_missing_required_file_raises(tmp_path: Path):
    model_dir = _build_minimal_model_dir(tmp_path)
    (model_dir / "model.safetensors").unlink()
    with pytest.raises(RuntimeError, match="Missing required model file"):
        compute_model_fingerprint(model_dir)


def test_missing_optional_files_allowed(tmp_path: Path):
    model_dir = _build_minimal_model_dir(tmp_path, include_optional=False)
    fingerprint = compute_model_fingerprint(model_dir)
    assert fingerprint.startswith("sha256:")


def test_required_order_constant():
    assert REQUIRED_FILES_ORDER[0] == "config.json"
    assert REQUIRED_FILES_ORDER[2] == "model.safetensors"
