"""Field-by-field comparison of an extraction against expected values (competition scoring rules:
text/dates exact, numbers within +/-1, charge/tax lists entry by entry in order)."""
from __future__ import annotations

from typing import Any


def same(a: Any, b: Any) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        return abs(a - b) <= 1
    return a == b


def field_ok(pred: Any, gold: Any) -> bool:
    if isinstance(gold, list):
        return isinstance(pred, list) and len(pred) == len(gold) and all(
            p.get("type") == g.get("type") and same(p.get("amount"), g.get("amount")) for p, g in zip(pred, gold)
        )
    return same(pred, gold)


def compare(pred: dict[str, Any], gold: dict[str, Any]) -> list[dict[str, Any]]:
    """One row per expected field: {field, predicted, expected, ok}."""
    return [{"field": k, "predicted": pred.get(k), "expected": v, "ok": field_ok(pred.get(k), v)} for k, v in gold.items()]
