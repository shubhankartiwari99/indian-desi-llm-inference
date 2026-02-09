from pathlib import Path
import os

DATA_PATH = "data/alignment_gold_mt5.jsonl"
LOCAL_TOKENIZER_PATH = Path("artifacts/alignment_lora/final")
TOKENIZER_PATH = str(LOCAL_TOKENIZER_PATH) if LOCAL_TOKENIZER_PATH.exists() else "google/mt5-small"

datasets_cache = Path("artifacts/.hf_datasets_cache")
datasets_cache.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("HF_DATASETS_CACHE", str(datasets_cache.resolve()))

from datasets import load_dataset
from transformers import AutoTokenizer

try:
    tokenizer = AutoTokenizer.from_pretrained(
        TOKENIZER_PATH,
        use_fast=False,
        legacy=True,
    )
except TypeError:
    tokenizer = AutoTokenizer.from_pretrained(
        TOKENIZER_PATH,
        use_fast=False,
    )
ds = load_dataset("json", data_files=DATA_PATH)["train"]

# Build set of sentinel token ids whose token contains "<extra_id_"
sentinel_ids = {i for i in range(tokenizer.vocab_size) if "<extra_id_" in tokenizer.convert_ids_to_tokens(i)}
print("sentinel ids (sample):", list(sentinel_ids)[:10])

count = 0
examples = []
for i, ex in enumerate(ds):
    ids = tokenizer(ex["target_text"], truncation=True, max_length=512)["input_ids"]
    if any(tid in sentinel_ids for tid in ids):
        count += 1
        examples.append((i, ex["target_text"], ids[:40], [tokenizer.convert_ids_to_tokens(t) for t in ids[:40]]))
    if i >= 200 and count > 10:
        break

print("Examples with sentinel tokens in target_text:", count)
for e in examples[:10]:
    print("--- example", e[0])
    print(e[1])
    print(e[2])
    print(e[3])
