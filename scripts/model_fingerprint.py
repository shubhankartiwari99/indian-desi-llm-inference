"""Model fingerprint utility for deterministic model identity locking."""

from __future__ import annotations

from pathlib import Path
import hashlib

REQUIRED_FILES_ORDER = [
    "config.json",
    "generation_config.json",  # optional
    "model.safetensors",
    "tokenizer_config.json",
    "spiece.model",
    "special_tokens_map.json",  # optional
]

OPTIONAL_FILES = {"generation_config.json", "special_tokens_map.json"}


def compute_model_fingerprint(model_dir: Path) -> str:
    model_dir = Path(model_dir)

    if not model_dir.exists():
        raise RuntimeError(f"Model directory does not exist: {model_dir}")

    sha = hashlib.sha256()

    for filename in REQUIRED_FILES_ORDER:
        path = model_dir / filename

        if filename in OPTIONAL_FILES:
            if not path.exists():
                continue
        else:
            if not path.exists():
                raise RuntimeError(f"Missing required model file: {filename}")

        sha.update(filename.encode("utf-8"))
        sha.update(b"\n")

        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(8192), b""):
                sha.update(chunk)

        sha.update(b"\n")

    return f"sha256:{sha.hexdigest()}"
