"""Reading the CSV templates and writing completed files (always through the csv module)."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def dumps_one_line(obj: dict[str, Any]) -> str:
    """Compact single-line JSON (csv module doubles the quotes when it quotes the cell)."""
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
