from transformers import Trainer
from train.model import load_lora_model
from train.load_dataset import load_alignment_dataset
from train.formatting import format_example
from train.tokenization import tokenize_fn
from train.trainer import get_training_args

def main():
    model = load_lora_model()

    dataset = load_alignment_dataset("data/alignment_gold.jsonl")
    dataset = dataset.map(format_example)
    dataset = dataset.map(
        tokenize_fn,
        remove_columns=dataset.column_names
    )

    training_args = get_training_args()

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
    )

    trainer.train()

    trainer.save_model("artifacts/lora_adapter")

if __name__ == "__main__":
    main()