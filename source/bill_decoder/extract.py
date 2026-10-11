"""Level 1: image -> validated JSON.

Flow: read with the primary model and validate (arithmetic checks). If every check passes, done.
If not, take several more independent readings (alternating the two allowed models) and majority-vote
each field. Values are never recomputed in code; the image stays the source of truth.
"""
from __future__ import annotations

import json
import logging
from collections import Counter
from typing import Any

from . import prompts
from .llm import LLMClient
from .schema import normalise
from .validate import check

log = logging.getLogger(__name__)


def provider_hint(bill_id: str) -> str:
    prefix = bill_id.split("_")[0].upper()
    key = {"KESC": "KE", "KE": "KE", "LESCO": "LESCO", "IESCO": "IESCO"}.get(prefix)
    return prompts.PROVIDER_HINTS.get(key, prompts.GENERIC_HINT)


def read_once(llm: LLMClient, image: tuple[bytes, str], hint: str, model: str) -> dict[str, Any]:
    raw = llm.generate_json(prompts.l1_user_prompt(hint), images=[image], system=prompts.L1_SYSTEM, model=model)
    if isinstance(raw, list) and raw:
        raw = raw[0]
    return apply_layout_rules(normalise(raw if isinstance(raw, dict) else {}))


def apply_layout_rules(bill: dict[str, Any]) -> dict[str, Any]:
    """LESCO/IESCO print a single combined 'Taxes' amount; the guide wants [] + total_taxes then."""
    taxes = bill.get("taxes") or []
    if bill.get("provider") in ("LESCO", "IESCO") and len(taxes) == 1:
        if bill.get("total_taxes") is None or abs(taxes[0]["amount"] - bill["total_taxes"]) <= 1:
            bill["total_taxes"] = bill["total_taxes"] if bill["total_taxes"] is not None else taxes[0]["amount"]
            bill["taxes"] = []
    return bill


EXTRA_READINGS = 4  # additional independent readings (alternating models) when the first one fails checks


def vote(readings: list[dict[str, Any]]) -> dict[str, Any]:
    """Field-by-field majority vote. Ties go to the reading with the fewest failed checks, then the earliest.

    Voting is per field, so one misread digit in a single reading is outvoted by the others, while the
    values themselves are always ones the model actually read (nothing is recomputed)."""
    ranked = sorted(range(len(readings)), key=lambda i: (len(check(readings[i])), i))
    result: dict[str, Any] = {}
    for field in readings[0]:
        counts: Counter[str] = Counter(json.dumps(r.get(field), sort_keys=True) for r in readings)
        top = max(counts.values())
        winner = next(json.dumps(readings[i].get(field), sort_keys=True) for i in ranked
                      if counts[json.dumps(readings[i].get(field), sort_keys=True)] == top)
        result[field] = json.loads(winner)
    return result


def extract_bill(llm: LLMClient, image: tuple[bytes, str], bill_id: str) -> dict[str, Any]:
    """One reading when it passes the consistency checks; otherwise several readings are voted on."""
    cfg = llm.cfg
    hint = provider_hint(bill_id)

    first = read_once(llm, image, hint, cfg.model)
    issues = check(first)
    if not issues:
        return first
    log.info("%s: primary reading failed checks: %s", bill_id, issues)

    readings = [first]
    for i in range(EXTRA_READINGS):
        model = cfg.verifier_model if i % 2 == 0 else cfg.model
        try:
            readings.append(read_once(llm, image, hint, model))
        except Exception as exc:
            log.warning("%s: extra reading %d failed (%s)", bill_id, i + 1, exc)

    best = vote(readings)
    remaining = check(best)
    if remaining:
        log.warning("%s: unresolved checks after voting (values kept as read): %s", bill_id, remaining)
    return best


