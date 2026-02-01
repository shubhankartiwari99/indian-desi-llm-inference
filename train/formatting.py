def format_example(example):
    """
    Converts instruction + input into a single mT5 prompt.
    """

    instruction = example["instruction"].strip()
    user_input = example["input"].strip()
    output = example["output"].strip()

    prompt = (
        f"Instruction: {instruction}\n"
        f"User: {user_input}\n"
        f"Assistant:"
    )

    return {
        "input_text": prompt,
        "target_text": output
    }