"""Build level1.csv / level2.csv templates for the training bills (sample questions only; the real
test questions are released at 12:30). Usage: python dev/make_dev_templates.py <bills_dir> <out_dir>"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bill_decoder import csv_io  # noqa: E402

QUESTIONS = [
    "How much of my bill is taxes?",
    "How many months in my history went above 200 units?",
    "What is my average monthly consumption based on the usage history shown on the bill?",
    "Which month had the highest bill and how much was it?",
    "How much extra would I pay if I paid after the due date?",
    "What is the average price I paid per unit this month, all charges and taxes included?",
    "If my consumption next month is 20% higher than this month, roughly what would my bill be?",
    "What does the fuel price adjustment (FPA/FCA) on my bill mean and how much was I charged?",
    "How does this month's units compare with the previous month in my history?",
    "What was my previous balance or arrears and what does it mean for what I owe?",
    "What is my sanctioned load and my tariff?",
    "Summarise this bill in plain language in three sentences.",
]


def main(bills_dir: Path, out_dir: Path) -> None:
    ids = sorted(p.stem for p in bills_dir.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg"})
    csv_io.write_rows(out_dir / "level1.csv", ["bill_id", "json"], [{"bill_id": i, "json": ""} for i in ids])
    rows = [{"bill_id": i, "question_id": f"Q{n}", "question": q, "answer": ""} for i in ids for n, q in enumerate(QUESTIONS, 1)]
    csv_io.write_rows(out_dir / "level2.csv", ["bill_id", "question_id", "question", "answer"], rows)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
