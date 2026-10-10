"""Level 1: image -> validated JSON.

Flow: read with the primary model -> validate. If checks pass, done. Otherwise read again with a
second allowed model, keep the reading with fewer failed checks, and ask the model to re-inspect
the flagged values. Values are never recomputed in code; the image stays the source of truth.
"""
from __future__ import annotations

import logging
from typing import Any

from . import prompts
from .llm import LLMClient
from .schema import normalise
from .validate import check, differences

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


def extract_bill(llm: LLMClient, image: tuple[bytes, str], bill_id: str) -> dict[str, Any]:
    cfg = llm.cfg
    hint = provider_hint(bill_id)

    first = read_once(llm, image, hint, cfg.model)
    issues = check(first)
    if not issues:
        return first
    log.info("%s: primary reading failed checks: %s", bill_id, issues)

    # Independent second opinion from the other allowed model.
    second: dict[str, Any] | None
    try:
        second = read_once(llm, image, hint, cfg.verifier_model)
    except Exception as exc:
        log.warning("%s: verifier reading failed (%s)", bill_id, exc)
        second = None

    best, best_issues = first, issues
    if second is not None:
        second_issues = check(second)
        if not second_issues:
            return second
        if len(second_issues) < len(issues):
            best, best_issues = second, second_issues
    other = second if best is first else first
    diffs = differences(best, other) if other is not None else []

    try:
        refined = apply_layout_rules(normalise(
            llm.generate_json(
                prompts.l1_refine_prompt(best, best_issues, other, diffs),
                images=[image],
                system=prompts.L1_SYSTEM,
                model=cfg.model,
            )
        ))
        if len(check(refined)) <= len(best_issues):
            best = refined
    except Exception as exc:
        log.warning("%s: refinement failed (%s); keeping best reading", bill_id, exc)

    remaining = check(best)
    if remaining:
        log.warning("%s: unresolved checks (kept as printed): %s", bill_id, remaining)
    return best

