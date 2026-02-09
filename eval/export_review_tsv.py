import argparse
import csv
import json
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Export eval results for human review.")
    parser.add_argument("--results-file", required=True, help="Path to eval result JSON.")
    parser.add_argument("--output-file", required=True, help="Path to TSV output.")
    return parser.parse_args()


def main():
    args = parse_args()
    items = json.loads(Path(args.results_file).read_text(encoding="utf-8"))

    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["prompt", "response", "category", "expected_behavior", "ok?", "notes"])
        for item in items:
            writer.writerow(
                [
                    item.get("prompt", ""),
                    item.get("response", ""),
                    item.get("category", ""),
                    item.get("expected_behavior", ""),
                    "",
                    "",
                ]
            )

    print(f"Wrote review TSV: {output_path}")


if __name__ == "__main__":
    main()
