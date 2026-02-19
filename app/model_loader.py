from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from peft import PeftModel
import torch
from pathlib import Path
import json
import os


DEFAULT_MODEL_DIR = Path(__file__).resolve().parents[1] / "model"
REQUIRED_MODEL_FILES = {
    "config.json",
    "model.safetensors",
    "tokenizer_config.json",
    "spiece.model",
}


def resolve_model_dir() -> Path:
    env_path = os.environ.get("MODEL_DIR")
    model_dir = Path(env_path) if env_path else DEFAULT_MODEL_DIR
    if not model_dir.exists():
        raise RuntimeError(
            f"Model directory not found: {model_dir}. "
            "Set MODEL_DIR explicitly or provide ./model/"
        )
    missing = [name for name in sorted(REQUIRED_MODEL_FILES) if not (model_dir / name).is_file()]
    if missing:
        raise RuntimeError(
            f"Model directory missing required files: {', '.join(missing)}"
        )
    return model_dir


def get_model_dir() -> Path:
    return resolve_model_dir()


class ModelLoader:
    def __init__(self, adapter_dir: str, base_model_name: str = None):
        self.adapter_dir = resolve_model_dir()
        self.base_model_name = base_model_name or self._resolve_base_model_name()

    def _resolve_base_model_name(self):
        adapter_config = self.adapter_dir / "adapter_config.json"
        if adapter_config.exists():
            try:
                cfg = json.loads(adapter_config.read_text(encoding="utf-8"))
                base = cfg.get("base_model_name_or_path")
                if isinstance(base, str) and base.strip():
                    return base
            except Exception:
                pass
        local_config = self.adapter_dir / "config.json"
        if local_config.exists():
            return str(self.adapter_dir)
        raise RuntimeError(
            "Model configuration missing from model directory. "
            "Ensure config.json is present."
        )

    def load(self):
        # 1. Load base model
        base_model = AutoModelForSeq2SeqLM.from_pretrained(
            self.base_model_name,
            local_files_only=True,
        )

        # 2. Attach LoRA adapter only when adapter artifacts exist.
        adapter_config = self.adapter_dir / "adapter_config.json"
        adapter_weights = self.adapter_dir / "adapter_model.safetensors"
        adapter_weights_bin = self.adapter_dir / "adapter_model.bin"
        has_adapter = adapter_config.is_file() and (adapter_weights.is_file() or adapter_weights_bin.is_file())
        if has_adapter:
            model = PeftModel.from_pretrained(
                base_model,
                str(self.adapter_dir),
                local_files_only=True,
            )
        else:
            model = base_model

        # 3. Load tokenizer from adapter dir (important).
        # Prefer slow tokenizer for T5-family models.
        tokenizer_source = self.adapter_dir
        if not (self.adapter_dir / "tokenizer.json").exists() and not (self.adapter_dir / "spiece.model").exists():
            tokenizer_source = self.base_model_name
        try:
            tokenizer = AutoTokenizer.from_pretrained(
                str(tokenizer_source),
                use_fast=False,
                legacy=True,
                local_files_only=True,
            )
        except TypeError:
            tokenizer = AutoTokenizer.from_pretrained(
                str(tokenizer_source),
                use_fast=False,
                local_files_only=True,
            )

        device = "cuda" if torch.cuda.is_available() else "cpu"
        model.to(device)
        model.eval()

        return model, tokenizer
