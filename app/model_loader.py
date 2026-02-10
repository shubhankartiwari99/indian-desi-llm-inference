from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from peft import PeftModel
import torch
from pathlib import Path
import json


class ModelLoader:
    def __init__(self, adapter_dir: str, base_model_name: str = None):
        self.adapter_dir = Path(adapter_dir)
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
        # Default for new training runs.
        return "google/flan-t5-small"

    def load(self):
        # 1. Load base model
        base_model = AutoModelForSeq2SeqLM.from_pretrained(self.base_model_name)

        # 2. Attach LoRA adapter only when adapter artifacts exist.
        adapter_config = self.adapter_dir / "adapter_config.json"
        adapter_weights = self.adapter_dir / "adapter_model.safetensors"
        adapter_weights_bin = self.adapter_dir / "adapter_model.bin"
        has_adapter = adapter_config.is_file() and (adapter_weights.is_file() or adapter_weights_bin.is_file())
        if has_adapter:
            model = PeftModel.from_pretrained(
                base_model,
                str(self.adapter_dir),
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
            )
        except TypeError:
            tokenizer = AutoTokenizer.from_pretrained(
                str(tokenizer_source),
                use_fast=False,
            )

        device = "cuda" if torch.cuda.is_available() else "cpu"
        model.to(device)
        model.eval()

        return model, tokenizer
