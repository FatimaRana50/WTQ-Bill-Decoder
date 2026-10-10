"""Arithmetic / consistency checks on an extracted bill.

These never change values (the guide says to keep amounts as printed). A failed check only
tells the pipeline that something was probably misread, so it can look at the image again.
"""
from __future__ import annotations

import re
from typing import Any

TOL = 1.5  # bills round to whole rupees in places, so allow a little slack


def _close(a: float | None, b: float | None, tol: float = TOL) -> bool:
    return a is None or b is None or abs(a - b) <= tol


def check(bill: dict[str, Any]) -> list[str]:
    """Return human-readable descriptions of every failed check (empty list = all good)."""
    issues: list[str] = []
    charges, taxes = bill.get("charges") or [], bill.get("taxes") or []

    if charges and bill.get("total_charges") is not None:
        total = sum(c["amount"] for c in charges)
        without_fpa = sum(c["amount"] for c in charges if c["type"] != "fpa")
        if not (_close(total, bill["total_charges"]) or _close(without_fpa, bill["total_charges"])):
            issues.append(f"charges sum to {total:.2f} but total_charges is {bill['total_charges']}")

    if taxes and bill.get("total_taxes") is not None:
        total = sum(t["amount"] for t in taxes)
        if not _close(total, bill["total_taxes"]):
            issues.append(f"taxes sum to {total:.2f} but total_taxes is {bill['total_taxes']}")

    prev, cur, units = bill.get("previous_reading"), bill.get("current_reading"), bill.get("units_consumed")
    if None not in (prev, cur, units) and not _close(cur - prev, units, 0.5):
        issues.append(f"current_reading - previous_reading = {cur - prev} but units_consumed is {units}")

    tc, tt, cb = bill.get("total_charges"), bill.get("total_taxes"), bill.get("current_bill")
    if None not in (tc, tt, cb) and not _close(tc + tt, cb, 3.0):
        issues.append(f"total_charges + total_taxes = {tc + tt:.2f} but current_bill is {cb}")

    within, after = bill.get("payable_within_due_date"), bill.get("payable_after_due_date")
    if None not in (within, after) and after < within:
        issues.append(f"payable_after_due_date ({after}) is lower than payable_within_due_date ({within})")

    for key in ("reading_date", "issue_date", "due_date"):
        if bill.get(key) is None:
            issues.append(f"{key} missing or not a valid date")
    if bill.get("bill_month") is None:
        issues.append("bill_month missing")
    if bill.get("issue_date") and bill.get("due_date") and bill["due_date"] < bill["issue_date"]:
        issues.append("due_date is before issue_date")
    if bill.get("provider") is None:
        issues.append("provider missing")
    if not re.fullmatch(r"\d{4}-\d{2}", bill.get("bill_month") or "0000-00"):
        issues.append("bill_month malformed")
    return issues


def differences(a: dict[str, Any], b: dict[str, Any], tol: float = 1.0) -> list[str]:
    """Fields on which two extractions disagree (numbers within tol count as equal)."""
    diffs = []
    for key in a:
        va, vb = a[key], b.get(key)
        if isinstance(va, (int, float)) and isinstance(vb, (int, float)) and not isinstance(va, bool):
            if abs(va - vb) > tol:
                diffs.append(key)
        elif va != vb:
            diffs.append(key)
    return diffs
