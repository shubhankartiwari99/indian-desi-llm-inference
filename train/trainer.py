from transformers import TrainingArguments

def get_training_args():
    return TrainingArguments(
        output_dir="checkpoints/desi-align",
        overwrite_output_dir=True,

        # Core training
        num_train_epochs=3,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=16,

        # Optimization
        learning_rate=2e-4,
        warmup_steps=100,
        lr_scheduler_type="cosine",

        # Stability
        fp16=False,             
        bf16=False,              
        gradient_checkpointing=True,

        # Logging & saving
        logging_steps=20,
        save_steps=500,
        save_total_limit=2,

        # Misc
        report_to="none",
        remove_unused_columns=False,
        dataloader_pin_memory=False,
    )