def format_example(example, tokenizer):
    prompt = example["input_text"].strip()
    response = example["target_text"].strip()

    # Build full text
    full_text = prompt + "\nResponse: " + response

    # Tokenize full sequence
    tokenized = tokenizer(
        full_text,
        truncation=True,
        max_length=512,
    )

    # Tokenize prompt only (for masking)
    prompt_ids = tokenizer(
        prompt + "\nResponse:",
        truncation=True,
        max_length=512,
    )["input_ids"]

    labels = tokenized["input_ids"].copy()
    labels[: len(prompt_ids)] = [-100] * len(prompt_ids)

    tokenized["labels"] = labels
    return tokenized