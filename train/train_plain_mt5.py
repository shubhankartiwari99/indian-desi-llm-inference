if __name__ == "__main__" and __package__ is None:
    from pathlib import Path
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[1]))

import torch
import re
from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    Trainer,
    TrainingArguments,
    DataCollatorForSeq2Seq,
)
from app.intent import detect_intent

BASE_MODEL = "google/flan-t5-small"
DATA_PATH = "data/alignment_gold_mt5_expanded.jsonl"
OUTPUT_DIR = "artifacts/plain_mt5"

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
PREFIX_RE = re.compile(r"^\s*(empathy|fact|explain|uncertain|refusal)\s*:\s*(.*)$", re.IGNORECASE)


def canonicalize_input_text(text: str) -> str:
    raw = str(text).strip()
    match = PREFIX_RE.match(raw)
    if match:
        prefix = match.group(1).lower()
        body = match.group(2).strip()
        return f"{prefix}: {body}"

    intent = detect_intent(raw)
    prefix = {
        "emotional": "empathy",
        "factual": "fact",
        "explanatory": "explain",
        "uncertain": "uncertain",
        "refusal": "refusal",
        "conversational": "empathy",
    }.get(intent, "empathy")
    return f"{prefix}: {raw}"


def tokenize_fn(batch):
    inputs_text = [canonicalize_input_text(x) for x in batch["input_text"]]
    inputs = tokenizer(
        inputs_text,
        truncation=True,
        padding="max_length",
        max_length=128,
    )

    with tokenizer.as_target_tokenizer():
        labels = tokenizer(
            batch["target_text"],
            truncation=True,
            padding="max_length",
            max_length=128,
        )

    labels_ids = labels["input_ids"]
    labels_ids = [
        [(token if token != tokenizer.pad_token_id else -100) for token in seq]
        for seq in labels_ids
    ]

    inputs["labels"] = labels_ids
    return inputs


def main():
    global tokenizer

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    model = AutoModelForSeq2SeqLM.from_pretrained(BASE_MODEL)
    
    model.config.decoder_start_token_id = tokenizer.pad_token_id
    model.to(DEVICE)

    dataset = load_dataset("json", data_files=DATA_PATH)["train"]
    dataset = dataset.map(
        tokenize_fn,
        batched=True,
        remove_columns=dataset.column_names,
    )

    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        overwrite_output_dir=True,
        num_train_epochs=8,
        per_device_train_batch_size=2,
        learning_rate=3e-4,
        logging_steps=5,
        save_strategy="epoch",
        report_to="none",
    )

    data_collator = DataCollatorForSeq2Seq(
        tokenizer=tokenizer,
        model=model,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        data_collator=data_collator,
    )

    trainer.train()

    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)

    print(f"\n Plain FLAN-T5 model saved to {OUTPUT_DIR}\n")


if __name__ == "__main__":
    main()
