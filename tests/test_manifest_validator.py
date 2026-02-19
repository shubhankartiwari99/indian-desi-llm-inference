"""Tests for the manifest validator."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest


def _run_snapshot(tmp_path: Path) -> None:
    subprocess.run(
        [
            sys.executable,
            "scripts/ci_release_snapshot.py",
            "--artifact-dir",
            str(tmp_path),
        ],
        check=True,
        cwd=Path.cwd(),
        env={"PYTHONPATH": str(Path.cwd())},
    )


def _run_validator(tmp_path: Path, mode: str = "soft", env_override: dict | None = None) -> subprocess.CompletedProcess:
    env = {"PYTHONPATH": str(Path.cwd())}
    if env_override:
        env.update(env_override)
    return subprocess.run(
        [
            sys.executable,
            "scripts/ci_manifest_validator.py",
            "--artifact-dir",
            str(tmp_path),
            "--mode",
            mode,
        ],
        cwd=Path.cwd(),
        env=env,
        capture_output=True,
        text=True,
    )


def _load_report(result: subprocess.CompletedProcess) -> dict:
    return json.loads(result.stdout.strip())


def test_manifest_validator_pass(tmp_path: Path):
    _run_snapshot(tmp_path)
    result = _run_validator(tmp_path)
    report = _load_report(result)

    assert result.returncode == 0
    assert report["status"] == "PASS"
    assert report["errors"] == []
    assert report["artifact_count"] == 3
    assert report["bundle_digest"].startswith("sha256:")


def test_manifest_validator_tampered_contract(tmp_path: Path):
    _run_snapshot(tmp_path)
    contract_path = tmp_path / "contract_snapshot.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["contract_raw_canonical"] = contract["contract_raw_canonical"] + " "
    contract_path.write_text(json.dumps(contract), encoding="utf-8")

    result = _run_validator(tmp_path)
    report = _load_report(result)

    assert result.returncode != 0
    assert report["status"] == "FAIL"
    assert "contract_raw_not_canonical" in report["errors"]


def test_manifest_validator_tampered_selector(tmp_path: Path):
    _run_snapshot(tmp_path)
    selector_path = tmp_path / "selector_snapshot.json"
    selector = json.loads(selector_path.read_text(encoding="utf-8"))
    selector["turns"][0]["response_digest"] = "0" * 64
    selector_path.write_text(json.dumps(selector), encoding="utf-8")

    result = _run_validator(tmp_path)
    report = _load_report(result)

    assert result.returncode != 0
    assert report["status"] == "FAIL"
    assert "selector_snapshot_digest_mismatch" in report["errors"]


def test_manifest_validator_missing_artifact(tmp_path: Path):
    _run_snapshot(tmp_path)
    (tmp_path / "selector_snapshot.json").unlink()

    result = _run_validator(tmp_path)
    report = _load_report(result)

    assert result.returncode != 0
    assert report["status"] == "FAIL"
    assert "missing_artifact:selector_snapshot.json" in report["errors"]


def test_manifest_validator_modified_manifest(tmp_path: Path):
    _run_snapshot(tmp_path)
    manifest_path = tmp_path / "release_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["selector_snapshot_digest"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = _run_validator(tmp_path)
    report = _load_report(result)

    assert result.returncode != 0
    assert report["status"] == "FAIL"
    assert "manifest_not_canonical" in report["errors"]


def test_manifest_validator_deterministic_bytes(tmp_path: Path):
    _run_snapshot(tmp_path)
    result1 = _run_validator(tmp_path)
    result2 = _run_validator(tmp_path)

    assert result1.returncode == 0
    assert result2.returncode == 0
    assert result1.stdout == result2.stdout


def test_manifest_validator_missing_model_fingerprint(tmp_path: Path):
    _run_snapshot(tmp_path)
    manifest_path = tmp_path / "release_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.pop("model_fingerprint", None)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = _run_validator(tmp_path)
    report = _load_report(result)

    assert result.returncode != 0
    assert report["status"] == "FAIL"
    assert "model_fingerprint_missing_in_manifest" in report["errors"]


def test_manifest_validator_model_fingerprint_mismatch(tmp_path: Path):
    _run_snapshot(tmp_path)
    selector_path = tmp_path / "selector_snapshot.json"
    selector = json.loads(selector_path.read_text(encoding="utf-8"))
    selector["model_fingerprint"] = "sha256:" + "0" * 64
    selector_path.write_text(json.dumps(selector), encoding="utf-8")

    result = _run_validator(tmp_path)
    report = _load_report(result)

    assert result.returncode != 0
    assert report["status"] == "FAIL"
    assert "model_fingerprint_mismatch_across_artifacts" in report["errors"]


def test_manifest_validator_runtime_model_mismatch(tmp_path: Path, tmp_path_factory: pytest.TempPathFactory):
    _run_snapshot(tmp_path)
    dummy_dir = tmp_path_factory.mktemp("dummy_model")
    for name in [
        "config.json",
        "model.safetensors",
        "tokenizer_config.json",
        "spiece.model",
    ]:
        (dummy_dir / name).write_bytes(f"{name}-dummy".encode("utf-8"))

    result = _run_validator(tmp_path, mode="hard", env_override={"MODEL_DIR": str(dummy_dir)})
    report = _load_report(result)

    assert result.returncode != 0
    assert report["status"] == "FAIL"
    assert "model_fingerprint_runtime_mismatch" in report["errors"]
