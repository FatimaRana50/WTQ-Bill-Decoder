"""Utility Bill Decoder: demo and verification UI.

    streamlit run app.py

Decode a bill, verify the extraction (consistency checks, second-model opinion, comparison with
expected values), and ask plain-language questions with the calculations shown.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from bill_decoder import csv_io
from bill_decoder.compare import compare
from bill_decoder.config import Config
from bill_decoder.extract import extract_bill, provider_hint, read_once
from bill_decoder.llm import LLMClient
from bill_decoder.pipeline import Cache
from bill_decoder.preprocess import load_image
from bill_decoder.qa import answer_with_trace, extract_facts
from bill_decoder.validate import check, differences

ROOT = Path(__file__).resolve().parent
GOLD_DIR = ROOT / "tests" / "gold"
SUGGESTED = [
    "How much of my bill is taxes?",
    "How many months in my history went above 200 units?",
    "What is my average monthly consumption?",
    "How much extra would I pay if I pay after the due date?",
    "What is the average price I paid per unit this month?",
    "If I use 20% more units next month, roughly what would my bill be?",
    "What does the fuel price adjustment on my bill mean?",
]
LABELS = {
    "provider": "Provider", "tariff": "Tariff", "sanctioned_load_kw": "Sanctioned load (kW)", "bill_month": "Bill month",
    "reading_date": "Reading date", "issue_date": "Issue date", "due_date": "Due date",
    "previous_reading": "Previous reading", "current_reading": "Current reading", "units_consumed": "Units consumed",
    "total_charges": "Total charges", "total_taxes": "Total taxes", "current_bill": "Current bill", "arrears": "Arrears",
    "payable_within_due_date": "Payable by due date", "payable_after_due_date": "Payable after due date",
    "charges": "Charges", "taxes": "Taxes",
}
PROVIDER_NAMES = {"KE": "K-Electric", "LESCO": "LESCO", "IESCO": "IESCO"}

st.set_page_config(page_title="Utility Bill Decoder", page_icon="⚡", layout="wide")

st.markdown(
    """
<style>
 .block-container {padding-top: 1.6rem; max-width: 1280px;}
 h1, h2, h3 {letter-spacing: -0.01em;}
 .hero {background: linear-gradient(135deg, #0F766E 0%, #115E59 55%, #134E4A 100%); color: #fff; padding: 22px 28px;
        border-radius: 16px; margin-bottom: 18px;}
 .hero h1 {color: #fff; margin: 0; font-size: 1.75rem;}
 .hero p {color: #CCFBF1; margin: 4px 0 0 0; font-size: 0.95rem;}
 .kpi {background: #fff; border: 1px solid #E2E8F0; border-radius: 14px; padding: 14px 16px; box-shadow: 0 1px 2px rgba(15,23,42,.04);}
 .kpi .lbl {font-size: .72rem; text-transform: uppercase; letter-spacing: .06em; color: #64748B; font-weight: 600;}
 .kpi .val {font-size: 1.55rem; font-weight: 700; color: #0F172A; margin-top: 2px;}
 .kpi .sub {font-size: .78rem; color: #64748B;}
 .kpi.accent {border-left: 4px solid #0F766E;}
 .kpi.warn {border-left: 4px solid #D97706;}
 .badge {display: inline-block; padding: 3px 10px; border-radius: 999px; font-size: .78rem; font-weight: 600; margin-right: 6px;}
 .badge.ok {background: #DCFCE7; color: #166534;} .badge.bad {background: #FEE2E2; color: #991B1B;}
 .badge.info {background: #E0F2FE; color: #075985;} .badge.mute {background: #F1F5F9; color: #475569;}
 .check {padding: 9px 14px; border-radius: 10px; margin-bottom: 6px; font-size: .9rem;}
 .check.ok {background: #F0FDF4; border: 1px solid #BBF7D0;} .check.bad {background: #FEF2F2; border: 1px solid #FECACA;}
 .answer {background: #fff; border: 1px solid #E2E8F0; border-left: 4px solid #0F766E; border-radius: 12px; padding: 16px 18px; font-size: 1rem; line-height: 1.55;}
 .split {height: 14px; border-radius: 8px; overflow: hidden; display: flex; background: #E2E8F0; margin: 6px 0 4px;}
 .split div {height: 100%;}
 section[data-testid="stSidebar"] {background: #fff; border-right: 1px solid #E2E8F0;}
 button[kind="primary"] {border-radius: 10px; font-weight: 600;}
 .stTabs [data-baseweb="tab"] {font-weight: 600;}
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------------------- helpers
@st.cache_resource
def get_llm() -> LLMClient:
    return LLMClient(Config.from_env())


def pkr(value, signed: bool = False) -> str:
    if value is None:
        return "N/A"
    text = f"{abs(value):,.2f}".rstrip("0").rstrip(".") if abs(value) % 1 else f"{abs(value):,.0f}"
    return f"{'-' if value < 0 else ''}PKR {text}"


def kpi(label: str, value: str, sub: str = "", css: str = "") -> str:
    return f'<div class="kpi {css}"><div class="lbl">{label}</div><div class="val">{value}</div><div class="sub">{sub}</div></div>'


def lines_table(lines: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(
        [{"Type": item["type"].replace("_", " ").title(), "Amount (PKR)": item["amount"]} for item in lines]
    )


def load_expected(bill_id: str) -> dict | None:
    path = GOLD_DIR / f"{bill_id}.json"
    return json.loads(path.read_text("utf-8")) if path.exists() else None


# ---------------------------------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown("### ⚡ Bill Decoder")
    st.caption("Reads a K-Electric, LESCO or IESCO bill and explains it in plain English.")
    bills_dir = Path(st.text_input("Bills folder", str(ROOT.parent / "data" / "train" / "train" / "bills")))
    files = sorted(p for p in bills_dir.glob("*") if p.suffix.lower() in {".png", ".jpg", ".jpeg"}) if bills_dir.is_dir() else []
    picked = st.selectbox("Select a bill", files, format_func=lambda p: p.name) if files else None
    upload = st.file_uploader("…or upload a bill image", type=["png", "jpg", "jpeg"])
    st.divider()
    try:
        cfg = Config.from_env()
        st.markdown(f'<span class="badge info">Primary: {cfg.model}</span><span class="badge mute">Check: {cfg.verifier_model}</span>', unsafe_allow_html=True)
    except SystemExit as exc:
        st.error(str(exc))
        st.stop()
    use_cache = st.toggle("Reuse cached results", value=True, help="Instant for bills already processed; turn off to force a fresh read.")

if upload is not None:
    path = Path(tempfile.gettempdir()) / upload.name
    path.write_bytes(upload.getvalue())
elif picked is not None:
    path = picked
else:
    path = None

st.markdown(
    '<div class="hero"><h1>Utility Bill Decoder</h1>'
    "<p>Upload an electricity bill → get every charge, tax and payable amount → verify it → ask questions in plain English.</p></div>",
    unsafe_allow_html=True,
)
if path is None:
    st.info("Select a bill in the sidebar or upload an image to begin.")
    tab_batch_only = st.tabs(["Batch results"])[0]
else:
    tab_batch_only = None

bill_id = path.stem if path else ""
key = f"bill::{path.name}" if path else ""

# ---------------------------------------------------------------------------------------- tabs
tabs = st.tabs(["📄 Decode", "✅ Verify", "💬 Ask", "{ } JSON", "📦 Batch results"]) if path else [None] * 4 + [tab_batch_only]
t_decode, t_verify, t_ask, t_json, t_batch = tabs

if path:
    with t_decode:
        left, right = st.columns([5, 7], gap="large")
        with left:
            st.image(str(path), caption=path.name, width="stretch")
        with right:
            if st.button("Decode this bill", type="primary", width="stretch"):
                with st.status("Reading the bill…", expanded=True) as status:
                    cache = Cache(get_llm().cfg.cache_dir, use_cache)
                    result = cache.get(bill_id, "l1", path)
                    if result is None:
                        st.write("Reading with the primary model and running consistency checks…")
                        result = extract_bill(get_llm(), load_image(path), bill_id)
                        cache.put(bill_id, "l1", path, result)
                    else:
                        st.write("Loaded from cache.")
                    st.session_state[key] = result
                    status.update(label="Bill decoded", state="complete", expanded=False)
            bill = st.session_state.get(key)
            if not bill:
                st.caption("Press **Decode this bill** to extract the details.")
            else:
                issues = check(bill)
                name = PROVIDER_NAMES.get(bill["provider"], "Unknown provider")
                st.markdown(
                    f'<span class="badge info">{name}</span><span class="badge mute">Tariff {bill["tariff"] or "N/A"}</span>'
                    f'<span class="badge mute">{bill["bill_month"] or "N/A"}</span>'
                    + ('<span class="badge ok">All checks pass</span>' if not issues else f'<span class="badge bad">{len(issues)} check(s) flagged</span>'),
                    unsafe_allow_html=True,
                )
                c1, c2, c3 = st.columns(3)
                c1.markdown(kpi("Payable by due date", pkr(bill["payable_within_due_date"]), f"Due {bill['due_date'] or 'N/A'}", "accent"), unsafe_allow_html=True)
                c2.markdown(kpi("After due date", pkr(bill["payable_after_due_date"]), "Highest late amount", "warn"), unsafe_allow_html=True)
                c3.markdown(kpi("Units consumed", f"{bill['units_consumed']:,}" if bill["units_consumed"] is not None else "N/A",
                                f"{bill['previous_reading']} → {bill['current_reading']}"), unsafe_allow_html=True)
                st.write("")
                tc, tt = bill["total_charges"], bill["total_taxes"]
                if tc is not None and tt is not None and (tc + tt) > 0:
                    share = tt / (tc + tt) * 100
                    st.markdown(
                        f'**Where your money goes**<div class="split"><div style="width:{100 - share:.1f}%;background:#0F766E"></div>'
                        f'<div style="width:{share:.1f}%;background:#F59E0B"></div></div>'
                        f'<span class="badge info">Charges {pkr(tc)} ({100 - share:.1f}%)</span><span class="badge mute">Taxes {pkr(tt)} ({share:.1f}%)</span>',
                        unsafe_allow_html=True,
                    )
                st.write("")
                d1, d2 = st.columns(2)
                with d1:
                    st.markdown("**Charges**")
                    if bill["charges"]:
                        st.dataframe(lines_table(bill["charges"]), hide_index=True, width="stretch")
                    else:
                        st.caption("None itemised")
                with d2:
                    st.markdown("**Taxes**")
                    if bill["taxes"]:
                        st.dataframe(lines_table(bill["taxes"]), hide_index=True, width="stretch")
                    else:
                        st.caption(f"Single combined tax amount printed: {pkr(tt)}")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Current bill", pkr(bill["current_bill"]))
                m2.metric("Arrears", pkr(bill["arrears"]))
                m3.metric("Sanctioned load", f"{bill['sanctioned_load_kw']} kW" if bill["sanctioned_load_kw"] is not None else "N/A")
                m4.metric("Issued", bill["issue_date"] or "N/A")

    bill = st.session_state.get(key)

    # ---------------------------------------------------------------------------- verify
    with t_verify:
        if not bill:
            st.info("Decode the bill first (Decode tab).")
        else:
            st.markdown("#### 1 · Consistency checks")
            st.caption("Arithmetic that every bill must satisfy. A failure means a value was probably misread, or the bill itself is inconsistent.")
            issues = check(bill)
            if not issues:
                st.markdown('<div class="check ok">✅ Charges and taxes add up to their printed totals, readings match units, totals match the current bill, dates are valid.</div>', unsafe_allow_html=True)
            for issue in issues:
                st.markdown(f'<div class="check bad">⚠️ {issue}</div>', unsafe_allow_html=True)

            st.markdown("#### 2 · Compare with the bill image")
            vl, vr = st.columns([5, 7], gap="large")
            vl.image(str(path), width="stretch", caption="Click the image's expand icon to zoom in")
            with vr:
                rows = []
                for field, label in LABELS.items():
                    value = bill.get(field)
                    if isinstance(value, list):
                        value = ", ".join(f"{i['type']}: {i['amount']}" for i in value) or "[]"
                    rows.append({"Field": label, "Extracted": "null" if value is None else str(value)})
                st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", height=620)

            st.markdown("#### 3 · Independent second opinion")
            st.caption("Reads the bill again with the other allowed model and lists any disagreement.")
            if st.button("Run second opinion"):
                with st.spinner("Second model is reading the bill…"):
                    second = read_once(get_llm(), load_image(path), provider_hint(bill_id), get_llm().cfg.verifier_model)
                diffs = differences(bill, second)
                if not diffs:
                    st.success("The second model read exactly the same values.")
                else:
                    st.warning(f"Models disagree on: {', '.join(LABELS.get(d, d) for d in diffs)}")
                    st.dataframe(pd.DataFrame([{"Field": LABELS.get(d, d), "Primary": str(bill[d]), "Second": str(second[d])} for d in diffs]),
                                 hide_index=True, width="stretch")

            st.markdown("#### 4 · Compare with expected values")
            expected = load_expected(bill_id)
            if expected:
                st.caption(f"Loaded tests/gold/{bill_id}.json")
            pasted = st.text_area("Expected JSON (paste your own answer key, or leave blank)", value="", height=100,
                                  placeholder="Paste the correct JSON for this bill to score the extraction")
            if pasted.strip():
                try:
                    expected = json.loads(pasted)
                except json.JSONDecodeError:
                    st.error("That is not valid JSON.")
            if expected:
                results = compare(bill, expected)
                ok = sum(r["ok"] for r in results)
                st.markdown(f'<span class="badge {"ok" if ok == len(results) else "bad"}">{ok}/{len(results)} fields correct ({ok / len(results):.0%})</span>', unsafe_allow_html=True)
                st.dataframe(
                    pd.DataFrame([{"": "✅" if r["ok"] else "❌", "Field": LABELS.get(r["field"], r["field"]),
                                   "Extracted": json.dumps(r["predicted"]), "Expected": json.dumps(r["expected"])} for r in results]),
                    hide_index=True, width="stretch",
                )
            else:
                st.caption("No answer key available for this bill. Use sections 1–3, or paste one above.")

    # ---------------------------------------------------------------------------- ask
    with t_ask:
        if not bill:
            st.info("Decode the bill first (Decode tab).")
        else:
            st.caption("Answers use only this bill. Arithmetic is performed by code and shown under 'How this was calculated'.")
            chosen = st.pills("Try a question", SUGGESTED, key=f"pill::{key}")
            question = st.text_input("Or ask your own", value=chosen or "", placeholder="e.g. How much will I pay if I pay late?")
            if st.button("Get answer", type="primary") and question.strip():
                with st.spinner("Reading the bill and working it out…"):
                    image = load_image(path)
                    fkey = f"facts::{path.name}"
                    cache = Cache(get_llm().cfg.cache_dir, use_cache)
                    if fkey not in st.session_state:
                        st.session_state[fkey] = cache.get(bill_id, "facts", path) or extract_facts(get_llm(), image)
                        cache.put(bill_id, "facts", path, st.session_state[fkey])
                    answers, calcs = answer_with_trace(get_llm(), image, bill, st.session_state[fkey], [("Q1", question.strip())])
                st.markdown(f'<div class="answer">{answers["Q1"]}</div>', unsafe_allow_html=True)
                steps = calcs.get("Q1") or []
                with st.expander(f"How this was calculated ({len(steps)} step{'s' if len(steps) != 1 else ''})"):
                    if steps:
                        st.dataframe(pd.DataFrame(steps).rename(columns={"name": "What", "expression": "Expression", "result": "Result"}),
                                     hide_index=True, width="stretch")
                    else:
                        st.caption("No arithmetic was needed; the answer comes straight from printed values.")
                with st.expander("Facts read from the bill"):
                    st.json(st.session_state[fkey], expanded=False)

    # ---------------------------------------------------------------------------- json
    with t_json:
        if not bill:
            st.info("Decode the bill first (Decode tab).")
        else:
            st.json(bill)
            st.download_button("Download JSON", json.dumps(bill, indent=2), file_name=f"{bill_id}.json", mime="application/json")

# ---------------------------------------------------------------------------------------- batch
with t_batch:
    st.caption("Inspect the CSV files produced by `python main.py` (what gets submitted).")
    out_dir = Path(st.text_input("Output folder", str(ROOT.parent / "data" / "dev_out")))
    l1, l2 = out_dir / "level1.csv", out_dir / "level2.csv"
    if l1.exists() and l2.exists():
        rows1, rows2 = csv_io.read_rows(l1), csv_io.read_rows(l2)
        a, b, c = st.columns(3)
        a.metric("Level 1 rows", len(rows1))
        b.metric("Level 2 rows", len(rows2))
        c.metric("Empty answers", sum(1 for r in rows2 if not r["answer"].strip()))
        sel = st.selectbox("Bill", [r["bill_id"] for r in rows1])
        row = next(r for r in rows1 if r["bill_id"] == sel)
        with st.expander("Level 1 JSON", expanded=True):
            st.json(json.loads(row["json"]))
        st.markdown("**Level 2 answers**")
        for r in (r for r in rows2 if r["bill_id"] == sel):
            with st.expander(f"{r['question_id']} · {r['question']}"):
                st.write(r["answer"])
    else:
        st.info("No level1.csv / level2.csv found in that folder yet.")

