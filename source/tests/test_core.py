import csv
import io
import json

from bill_decoder import csv_io
from bill_decoder.qa import calculate
from bill_decoder.schema import normalise, normalise_date, normalise_month, to_number
from bill_decoder.validate import check


def test_to_number():
    assert to_number("Rs. 19,964") == 19964
    assert to_number("38209CR") == -38209
    assert to_number("-0.53") == -0.53
    assert to_number("NOT TO BE PAID") is None
    assert to_number("") is None and to_number(None) is None


def test_dates():
    assert normalise_date("22nd Sep 2026") == "2026-09-22"
    assert normalise_date("17 JUL 26") == "2026-07-17"
    assert normalise_date("2026-04-21") == "2026-04-21"
    assert normalise_date("garbage") is None
    assert normalise_month("MAR 2026") == "2026-03"


def test_normalise_drops_zero_lines_and_bad_types():
    out = normalise({"provider": "KESC", "charges": [{"type": "weird", "amount": "5"}, {"type": "fixed", "amount": 0}],
                     "taxes": [{"type": "gst", "amount": "Rs 10"}]})
    assert out["provider"] == "KE"
    assert out["charges"] == [{"type": "other", "amount": 5}]
    assert out["taxes"] == [{"type": "gst", "amount": 10}]
    assert list(out)[0] == "provider" and "payable_after_due_date" in out


def test_check_flags_inconsistency():
    bill = {"charges": [{"type": "energy", "amount": 100}], "total_charges": 500, "taxes": [], "total_taxes": None,
            "previous_reading": 10, "current_reading": 30, "units_consumed": 20, "bill_month": "2026-01",
            "reading_date": "2026-01-01", "issue_date": "2026-01-02", "due_date": "2026-01-10", "provider": "KE"}
    issues = check(bill)
    assert len(issues) == 1 and "total_charges" in issues[0]
    bill["total_charges"] = 100
    assert check(bill) == []


def test_calculator_is_safe_and_correct():
    assert calculate("avg([239, 203, 187])") == "209.666667"
    assert calculate("569.62 / 3430.24 * 100").startswith("16.6")
    assert calculate("count_gt([141, 239, 203, 151], 200)") == "2"
    assert calculate("__import__('os').system('echo hi')").startswith("error")


def test_csv_roundtrip_one_line_json(tmp_path):
    obj = {"provider": "KE", "charges": [{"type": "fixed", "amount": 900}]}
    path = tmp_path / "level1.csv"
    csv_io.write_rows(path, ["bill_id", "json"], [{"bill_id": "KESC_0008", "json": csv_io.dumps_one_line(obj)}])
    text = path.read_text("utf-8")
    assert text.count("\n") == 2  # header + one row, JSON stays on one line
    assert '""provider"":""KE""' in text
    row = next(csv.DictReader(io.StringIO(text)))
    assert json.loads(row["json"]) == obj
