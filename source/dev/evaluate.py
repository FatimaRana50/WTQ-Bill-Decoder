"""Score an output level1.csv against gold JSON files (tests/gold/<bill_id>.json).
Usage: python dev/evaluate.py <level1.csv> [gold_dir]"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bill_decoder import csv_io  # noqa: E402
from bill_decoder.compare import compare  # noqa: E402


def main(csv_path: Path, gold_dir: Path) -> None:
    total = correct = 0
    for row in csv_io.read_rows(csv_path):
        gold_path = gold_dir / f"{row['bill_id']}.json"
        if not gold_path.exists():
            continue
        results = compare(json.loads(row["json"]), json.loads(gold_path.read_text("utf-8")))
        wrong = [r for r in results if not r["ok"]]
        total += len(results)
        correct += len(results) - len(wrong)
        print(f"{row['bill_id']}: {len(results) - len(wrong)}/{len(results)} fields correct")
        for r in wrong:
            print(f"   {r['field']}: predicted {r['predicted']!r} expected {r['expected']!r}")
    if total:
        print(f"TOTAL {correct}/{total} = {correct / total:.1%}")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parent.parent / "tests" / "gold")
