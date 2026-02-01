from datasets import load_dataset

def load_alignment_dataset(path: str):
    """
    Loads alignment JSONL into a HuggingFace Dataset.
    """
    dataset = load_dataset(
        "json",
        data_files=path,
        split="train"
    )
    return dataset