from transformers import AutoModelForSeq2SeqLM
from peft import get_peft_model
from train.lora_config import LORA_CONFIG
from typing import Callable, cast

MODEL_NAME = "google/mt5-small"

def load_lora_model():
    model = AutoModelForSeq2SeqLM.from_pretrained(
        MODEL_NAME,
        device_map="auto",
    )

    # Enable gradient checkpointing (memory-safe)
    model.gradient_checkpointing_enable()

    # Apply LoRA
    model = get_peft_model(model, LORA_CONFIG)

    if hasattr(model, "enable_input_require_grads"):
        enable_fn = cast(Callable[[], None], model.enable_input_require_grads)
        enable_fn()

    model.train()

    # Disable cache (Trainer + checkpointing safe)
    if hasattr(model.config, "use_cache"):
        model.config.use_cache = False  # type: ignore[attr-defined]

    model.print_trainable_parameters()

    return model