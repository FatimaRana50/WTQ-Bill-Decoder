"""End-to-end run: bills folder + CSV templates -> completed level1.csv and level2.csv."""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from . import csv_io
from .config import Config
from .extract import extract_bill
from .llm import LLMClient
from .preprocess import find_bill, load_image
from .qa import answer_questions, extract_facts
from .schema import empty_result

log = logging.getLogger(__name__)
CACHE_VERSION = "v1"  # bump when prompts change so stale cache entries are ignored


class Cache:
    """Per-bill JSON cache so a crash or re-run never repeats finished (paid) work."""

    def __init__(self, root: Path, enabled: bool = True):
        self.root, self.enabled = root, enabled
        if enabled:
            root.mkdir(parents=True, exist_ok=True)

    def _path(self, bill_id: str, kind: str, image_path: Path) -> Path:
        digest = hashlib.sha1(image_path.read_bytes()).hexdigest()[:10]
        return self.root / f"{bill_id}.{kind}.{CACHE_VERSION}.{digest}.json"

    def get(self, bill_id: str, kind: str, image_path: Path) -> Any | None:
        path = self._path(bill_id, kind, image_path)
        if self.enabled and path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return None

    def put(self, bill_id: str, kind: str, image_path: Path, value: Any) -> None:
        if self.enabled:
            self._path(bill_id, kind, image_path).write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def run(bills_dir: Path, csv_dir: Path, out_dir: Path, cfg: Config, *, use_cache: bool = True) -> None:
    llm = LLMClient(cfg)
    cache = Cache(cfg.cache_dir, use_cache)
    l1_rows = csv_io.read_rows(csv_dir / "level1.csv")
    l2_rows = csv_io.read_rows(csv_dir / "level2.csv")

    level1: dict[str, dict] = {}
    for row in l1_rows:
        bill_id = row["bill_id"]
        log.info("Level 1: %s", bill_id)
        try:
            path = find_bill(bills_dir, bill_id)
            result = cache.get(bill_id, "l1", path)
            if result is None:
                result = extract_bill(llm, load_image(path), bill_id)
                cache.put(bill_id, "l1", path, result)
        except Exception:
            log.exception("Level 1 failed for %s; writing an all-null object", bill_id)
            result = empty_result()
        level1[bill_id] = result
        row["json"] = csv_io.dumps_one_line(result)
    csv_io.write_rows(out_dir / "level1.csv", ["bill_id", "json"], [{"bill_id": r["bill_id"], "json": r["json"]} for r in l1_rows])
    log.info("Wrote %s", out_dir / "level1.csv")

    questions_by_bill: dict[str, list[tuple[str, str]]] = {}
    for row in l2_rows:
        questions_by_bill.setdefault(row["bill_id"], []).append((row["question_id"], row["question"]))

    answers: dict[str, dict[str, str]] = {}
    for bill_id, questions in questions_by_bill.items():
        log.info("Level 2: %s (%d questions)", bill_id, len(questions))
        try:
            path = find_bill(bills_dir, bill_id)
            cached = cache.get(bill_id, "l2", path)
            if cached is not None and all(qid in cached for qid, _ in questions):
                answers[bill_id] = cached
                continue
            image = load_image(path)
            facts = cache.get(bill_id, "facts", path)
            if facts is None:
                facts = extract_facts(llm, image)
                cache.put(bill_id, "facts", path, facts)
            answers[bill_id] = answer_questions(llm, image, level1.get(bill_id) or empty_result(), facts, questions)
            cache.put(bill_id, "l2", path, answers[bill_id])
        except Exception:
            log.exception("Level 2 failed for %s", bill_id)
            answers[bill_id] = {}
    fallback = "I could not read this bill reliably enough to answer, so I am not guessing."
    for row in l2_rows:
        row["answer"] = answers.get(row["bill_id"], {}).get(row["question_id"]) or fallback
    csv_io.write_rows(out_dir / "level2.csv", ["bill_id", "question_id", "question", "answer"], l2_rows)
    log.info("Wrote %s", out_dir / "level2.csv")
