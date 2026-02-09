if __name__ == "__main__" and __package__ is None:
    from pathlib import Path
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[1]))

import json
import math
import argparse
from datetime import datetime
from pathlib import Path
import re
import torch

from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    Trainer,
    TrainingArguments,
    DataCollatorForSeq2Seq,
)

from peft import LoraConfig, TaskType, get_peft_model
import os
from datasets import load_dataset
from app.intent import detect_intent
os.environ["TORCH_DISABLE_DYNAMO"] = "1"


# ============================================================
# 1. HARD-CONSTANTS (DO NOT CHANGE)
# ============================================================

BASE_MODEL = "google/flan-t5-small"
DATA_PATH = "data/alignment_gold_mt5_expanded.jsonl"
RUNS_DIR = Path("artifacts/alignment_lora/runs")
DEFAULT_EXPORT_DIR = Path("artifacts/alignment_lora/final")

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
PREFIX_RE = re.compile(r"^\s*(empathy|fact|explain|uncertain|refusal)\s*:\s*(.*)$", re.IGNORECASE)


# ============================================================
# 2. LoRA CONFIG — MATCHES T5-BASE (hidden_size = 768)
# ============================================================

LORA_CONFIG = LoraConfig(
    r=8,
    lora_alpha=16,
    lora_dropout=0.05,
    target_modules=["q", "v"],   # T5 attention projections
    bias="none",
    task_type=TaskType.SEQ_2_SEQ_LM,
)


# ============================================================
# 3. DATA LOADING (JSONL SAFE)
# ============================================================

def clean_target(text: str) -> str:
    bad_prefixes = [
        "answer the following:",
        "the following:",
        "response:",
        "instruction:",
        ":",
    ]
    t = text.strip()
    for p in bad_prefixes:
        if t.lower().startswith(p):
            t = t[len(p):].strip()
    return t

def load_alignment_dataset(path):
    dataset = load_dataset("json", data_files=path)["train"]

    # Dataset is ALREADY normalized
    required_keys = {"input_text", "target_text"}
    sample_keys = set(dataset[0].keys())

    if not required_keys.issubset(sample_keys):
        raise ValueError(
            f"Dataset schema mismatch. Expected {required_keys}, got {sample_keys}"
        )

    return dataset


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


# ============================================================
# 4. TOKENIZATION
# ============================================================

def tokenize_fn(batch):
    inputs_text = [canonicalize_input_text(x) for x in batch["input_text"]]
    model_inputs = tokenizer(
        inputs_text,
        truncation=True,
        padding="max_length",
        max_length=128,
    )

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

    model_inputs["labels"] = labels_ids
    return model_inputs


# ============================================================
# 5. MAIN
# ============================================================

def parse_args():
    parser = argparse.ArgumentParser(description="Train LoRA adapter for alignment.")
    parser.add_argument("--base-model", default=BASE_MODEL)
    parser.add_argument("--data-path", default=DATA_PATH)
    parser.add_argument("--run-dir", default=None, help="Checkpoint/output dir for this run.")
    parser.add_argument(
        "--export-dir",
        default=str(DEFAULT_EXPORT_DIR),
        help="Final adapter/tokenizer export directory.",
    )
    return parser.parse_args()


def build_run_dir(run_dir_arg: str):
    if run_dir_arg:
        return Path(run_dir_arg)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return RUNS_DIR / f"run_{ts}"


def main():
    args = parse_args()

    run_dir = build_run_dir(args.run_dir)
    export_dir = Path(args.export_dir)

    run_dir.mkdir(parents=True, exist_ok=True)
    export_dir.mkdir(parents=True, exist_ok=True)

    # --- tokenizer ---
    global tokenizer
    tokenizer = AutoTokenizer.from_pretrained(args.base_model)
    

    # --- base model ---
    base_model = AutoModelForSeq2SeqLM.from_pretrained(args.base_model)
    base_model.config.decoder_start_token_id = tokenizer.pad_token_id

    # --- apply LoRA ---
    model = get_peft_model(base_model, LORA_CONFIG)
    model.print_trainable_parameters()

    # IMPORTANT: Trainer safety
    model.config.use_cache = False
    model.train()

    # --- dataset ---
    dataset = load_alignment_dataset(args.data_path)
    split = dataset.train_test_split(test_size=0.1, seed=42, shuffle=True)
    train_raw = split["train"]
    eval_raw = split["test"]

    train_dataset = train_raw.map(
        tokenize_fn,
        batched=True,
        remove_columns=train_raw.column_names,
    )
    eval_dataset = eval_raw.map(
        tokenize_fn,
        batched=True,
        remove_columns=eval_raw.column_names,
    )

    # --- training args ---
    training_args = TrainingArguments(
        output_dir=str(run_dir),
        overwrite_output_dir=True,
        
        # Conservative defaults for expanded dataset to avoid catastrophic drift.
        num_train_epochs=4,
        per_device_train_batch_size=2,
        per_device_eval_batch_size=4,
        gradient_accumulation_steps=4,
        
        learning_rate=2e-5,
        warmup_ratio=0.05,
        weight_decay=0.01,
        max_grad_norm=1.0,

        logging_steps=25,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,

        remove_unused_columns=False,
        report_to="none",
        )

    updates_per_epoch = math.ceil(
        len(train_dataset) / (
            training_args.per_device_train_batch_size
            * training_args.gradient_accumulation_steps
        )
    )
    print(
        f"Train examples: {len(train_dataset)} | Eval examples: {len(eval_dataset)} | "
        f"updates/epoch: {updates_per_epoch} | "
        f"total updates: {updates_per_epoch * int(training_args.num_train_epochs)}"
    )
    print(f"Run dir: {run_dir.resolve()}")
    print(f"Export dir: {export_dir.resolve()}")

    data_collator = DataCollatorForSeq2Seq(
        tokenizer=tokenizer,
        model=model,
    )

    # --- trainer ---
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=data_collator,
    )

    trainer.train()

    # ========================================================
    # 6. EXPORT FINAL ADAPTER (CRITICAL)
    # ========================================================

    export_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(export_dir)
    tokenizer.save_pretrained(export_dir)

    print(f"\n Final LoRA adapter saved to: {export_dir.resolve()}\n")


if __name__ == "__main__":
    main()
