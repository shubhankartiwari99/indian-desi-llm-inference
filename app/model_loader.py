import torch
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from peft import PeftModel


class ModelLoader:
    def __init__(self, model_dir=None, device=None, lora_dir=None):
        if model_dir is None:
            # DEFAULT MODEL LOCATION (repo-local)
            self.model_dir = Path("model")
        else:
            self.model_dir = Path(model_dir)

        if not self.model_dir.exists():
            raise FileNotFoundError(
                f"Model directory not found: {self.model_dir.resolve()}"
            )

        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.lora_dir = Path(lora_dir) if lora_dir else None

    def load(self):
        tokenizer = AutoTokenizer.from_pretrained(
            self.model_dir,
            use_fast=False
        )

        model = AutoModelForSeq2SeqLM.from_pretrained(
            self.model_dir
        ).to(self.device)

        if self.lora_dir and self.lora_dir.exists():
            model = PeftModel.from_pretrained(model, self.lora_dir)

        model.eval()
        return model, tokenizer, self.device