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
        # Default for new training runs.
        return "google/flan-t5-small"

    def load(self):
        # 1. Load base model
        base_model = AutoModelForSeq2SeqLM.from_pretrained(self.base_model_name)

        # 2. Attach LoRA adapter
        model = PeftModel.from_pretrained(
            base_model,
            str(self.adapter_dir),
        )

        # 3. Load tokenizer from adapter dir (important).
        # Prefer slow tokenizer for T5-family models.
        try:
            tokenizer = AutoTokenizer.from_pretrained(
                str(self.adapter_dir),
                use_fast=False,
                legacy=True,
            )
        except TypeError:
            tokenizer = AutoTokenizer.from_pretrained(
                str(self.adapter_dir),
                use_fast=False,
            )

        device = "cuda" if torch.cuda.is_available() else "cpu"
        model.to(device)
        model.eval()

        return model, tokenizer
