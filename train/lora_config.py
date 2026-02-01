from peft import LoraConfig, TaskType

LORA_CONFIG = LoraConfig(
    task_type=TaskType.SEQ_2_SEQ_LM,
    r=8,                     
    lora_alpha=16,
    lora_dropout=0.05,
    bias="none",
    target_modules=[
        "q",
        "v"
    ],
)