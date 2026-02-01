from transformers import AutoTokenizer

MODEL_NAME = "google/mt5-small"

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

def tokenize_fn(example, max_input_length=256, max_target_length=128):
    # Support both schema variants
    if "prompt" in example and "response" in example:
        input_text = example["prompt"]
        target_text = example["response"]
    elif "input_text" in example and "target_text" in example:
        input_text = example["input_text"]
        target_text = example["target_text"]
    else:
        raise KeyError(
            "Expected example to contain either "
            "('prompt', 'response') or ('input_text', 'target_text')"
        )

    model_inputs = tokenizer(
        input_text,
        truncation=True,
        padding="max_length",
        max_length=max_input_length,
    )

    with tokenizer.as_target_tokenizer():
        labels = tokenizer(
            target_text,
            truncation=True,
            padding="max_length",
            max_length=max_target_length,
        )

    model_inputs["labels"] = labels["input_ids"]
    return model_inputs