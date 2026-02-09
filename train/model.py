from transformers import AutoModelForSeq2SeqLM
from peft import get_peft_model
from train.lora_config import LORA_CONFIG

MODEL_NAME = "t5-base"

def load_lora_model():
    model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)

    # model.gradient_checkpointing_enable()

    # ✅ Required for Trainer + seq2seq
    model.config.use_cache = False

    # ✅ Apply LoRA
    model = get_peft_model(model, LORA_CONFIG)

    # ✅ REQUIRED: forces inputs to carry gradients
    model.enable_input_require_grads()

    # ✅ Training mode
    model.train()

    # Sanity check (keep this)
    model.print_trainable_parameters()

    return model