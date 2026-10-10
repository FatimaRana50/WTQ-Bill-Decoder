"""Validate output CSVs against the templates before packaging.
Usage: python dev/check_submission.py <template_csv_dir> <output_dir>"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bill_decoder import csv_io  # noqa: E402
from bill_decoder.schema import CHARGE_TYPES, FIELD_ORDER, PROVIDERS, TAX_TYPES  # noqa: E402


def main(template_dir: Path, out_dir: Path) -> int:
    errors: list[str] = []

    t1, o1 = csv_io.read_rows(template_dir / "level1.csv"), csv_io.read_rows(out_dir / "level1.csv")
    if [r["bill_id"] for r in t1] != [r["bill_id"] for r in o1]:
        errors.append("level1.csv: bill_ids / order differ from template")
    for row in o1:
        raw = row.get("json", "")
        if "\n" in raw:
            errors.append(f"level1 {row['bill_id']}: JSON spans several lines")
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            errors.append(f"level1 {row['bill_id']}: invalid JSON")
            continue
        if list(obj) != FIELD_ORDER:
            errors.append(f"level1 {row['bill_id']}: keys differ from the schema")
        if obj.get("provider") not in PROVIDERS:
            errors.append(f"level1 {row['bill_id']}: provider is {obj.get('provider')!r}")
        for key, allowed in (("charges", CHARGE_TYPES), ("taxes", TAX_TYPES)):
            for item in obj.get(key) or []:
                if item.get("type") not in allowed or not isinstance(item.get("amount"), (int, float)):
                    errors.append(f"level1 {row['bill_id']}: bad {key} entry {item}")
        nulls = [k for k, v in obj.items() if v is None]
        print(f"level1 {row['bill_id']}: ok, null fields: {nulls}")

    t2, o2 = csv_io.read_rows(template_dir / "level2.csv"), csv_io.read_rows(out_dir / "level2.csv")
    if len(t2) != len(o2):
        errors.append(f"level2.csv: {len(o2)} rows, template has {len(t2)}")
    for a, b in zip(t2, o2):
        for col in ("bill_id", "question_id", "question"):
            if a[col] != b[col]:
                errors.append(f"level2 {a['bill_id']} {a['question_id']}: column {col} was modified")
        if not b["answer"].strip():
            errors.append(f"level2 {b['bill_id']} {b['question_id']}: empty answer")
        elif "could not" in b["answer"].lower() and "not guessing" in b["answer"].lower():
            errors.append(f"level2 {b['bill_id']} {b['question_id']}: fallback answer used (generation failed)")

    print(f"level1 rows: {len(o1)}, level2 rows: {len(o2)}")
    for e in errors:
        print("ERROR:", e)
    print("PASS" if not errors else f"FAIL ({len(errors)} problems)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]), Path(sys.argv[2])))
