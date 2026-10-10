"""Level 1 output schema and deterministic normalisation of model output."""
from __future__ import annotations

import re
from datetime import date
from typing import Any

CHARGE_TYPES = {"energy", "fixed", "fpa", "quarterly_adjustment", "surcharge", "meter_rent", "subsidy", "other"}
TAX_TYPES = {"gst", "electricity_duty", "income_tax", "municipal_tax", "other_tax"}
PROVIDERS = {"KE", "LESCO", "IESCO"}

SCALAR_FIELDS = [
    "provider", "tariff", "sanctioned_load_kw", "bill_month", "reading_date", "issue_date", "due_date",
    "previous_reading", "current_reading", "units_consumed",
]
NUMERIC_FIELDS = [
    "sanctioned_load_kw", "previous_reading", "current_reading", "units_consumed",
    "total_charges", "total_taxes", "current_bill", "arrears",
    "payable_within_due_date", "payable_after_due_date",
]
DATE_FIELDS = ["reading_date", "issue_date", "due_date"]
FIELD_ORDER = [
    "provider", "tariff", "sanctioned_load_kw", "bill_month", "reading_date", "issue_date", "due_date",
    "previous_reading", "current_reading", "units_consumed", "charges", "total_charges",
    "taxes", "total_taxes", "current_bill", "arrears", "payable_within_due_date", "payable_after_due_date",
]

_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


def to_number(value: Any) -> float | int | None:
    """'Rs. 19,964' -> 19964; '38209CR' -> -38209; blanks / '-' / 'N/A' -> None."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        num = value
    else:
        text = str(value).strip()
        if not text or text.lower() in {"null", "none", "n/a", "na", "-", "--"}:
            return None
        negative = bool(re.search(r"\bCR\b|CR$|^\(.*\)$", text, re.IGNORECASE)) or text.startswith("-")
        match = re.search(r"\d[\d,]*(?:\.\d+)?|\.\d+", text)
        if not match:
            return None
        try:
            num = float(match.group(0).replace(",", ""))
        except ValueError:
            return None
        if negative:
            num = -abs(num)
    if isinstance(num, float) and num.is_integer():
        return int(num)
    return round(num, 2) if isinstance(num, float) else num


def normalise_date(value: Any) -> str | None:
    """Accepts ISO dates and common printed forms ('22nd Sep 2026', '17 JUL 26', '08-Oct-26')."""
    if value is None:
        return None
    text = str(value).strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        try:
            date.fromisoformat(text)
            return text
        except ValueError:
            return None
    m = re.search(r"(\d{1,2})(?:st|nd|rd|th)?[\s\-/.]*([A-Za-z]{3})[A-Za-z]*[\s\-/.,]*(\d{2,4})", text)
    if not m or m.group(2).lower() not in _MONTHS:
        return None
    year = int(m.group(3))
    year += 2000 if year < 100 else 0
    try:
        return date(year, _MONTHS[m.group(2).lower()], int(m.group(1))).isoformat()
    except ValueError:
        return None


def normalise_month(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if re.fullmatch(r"\d{4}-\d{2}", text):
        return text
    m = re.search(r"([A-Za-z]{3})[A-Za-z]*[\s\-/.,]*(\d{2,4})", text)
    if m and m.group(1).lower() in _MONTHS:
        year = int(m.group(2))
        year += 2000 if year < 100 else 0
        return f"{year:04d}-{_MONTHS[m.group(1).lower()]:02d}"
    return None


def _normalise_lines(raw: Any, allowed: set[str], fallback: str) -> list[dict]:
    lines = []
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        amount = to_number(item.get("amount"))
        if amount is None or amount == 0:  # guide: skip blank lines and lines printed as 0
            continue
        kind = str(item.get("type", "")).strip().lower()
        lines.append({"type": kind if kind in allowed else fallback, "amount": amount})
    return lines


def normalise(raw: dict[str, Any]) -> dict[str, Any]:
    """Coerce a raw model reply into the exact Level 1 schema (every key present)."""
    out: dict[str, Any] = {}
    provider = str(raw.get("provider") or "").strip().upper()
    provider = {"KESC": "KE", "K-ELECTRIC": "KE", "KELECTRIC": "KE"}.get(provider, provider)
    out["provider"] = provider if provider in PROVIDERS else None
    tariff = raw.get("tariff")
    out["tariff"] = str(tariff).strip() if tariff not in (None, "") else None
    out["bill_month"] = normalise_month(raw.get("bill_month"))
    for key in DATE_FIELDS:
        out[key] = normalise_date(raw.get(key))
    for key in NUMERIC_FIELDS:
        out[key] = to_number(raw.get(key))
    out["charges"] = _normalise_lines(raw.get("charges"), CHARGE_TYPES, "other")
    out["taxes"] = _normalise_lines(raw.get("taxes"), TAX_TYPES, "other_tax")
    return {key: out.get(key) for key in FIELD_ORDER}


def empty_result() -> dict[str, Any]:
    """Valid all-null object, used only if a bill cannot be processed at all."""
    base = {key: None for key in FIELD_ORDER}
    base["charges"], base["taxes"] = [], []
    return base
