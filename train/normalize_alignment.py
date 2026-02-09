import json

SRC = "data/alignment_gold.jsonl"
DST = "data/alignment_gold_normalized.jsonl"

with open(SRC) as fin, open(DST, "w") as fout:
    for line in fin:
        ex = json.loads(line)

        input_text = f"{ex['instruction']}\n{ex['input']}"
        target_text = ex["output"]

        fout.write(
            json.dumps({
                "input_text": input_text,
                "target_text": target_text
            }) + "\n"
        )

print("Normalized dataset written to", DST)