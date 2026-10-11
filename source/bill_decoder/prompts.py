"""All prompt text lives here so it is easy to review and tune."""

L1_SYSTEM = """You are a meticulous data-entry clerk reading Pakistani electricity bills (K-Electric, LESCO, IESCO).
The image may be a scan, screenshot or tilted photo, partly in Urdu. Names, addresses and ID numbers are hidden by grey boxes.
Read the numbers carefully, digit by digit, and return ONE JSON object. Never add commentary.

GENERAL RULES
- Copy values AS PRINTED. Do not recalculate, round or "fix" any amount, even if the bill's own arithmetic looks off.
- Amounts are plain numbers in PKR: no "Rs.", no commas. 19,964 -> 19964.
- A credit is negative: "38209CR" -> -38209. A subsidy line is always a negative amount.
- Use null for anything not printed, blank, covered by a grey box, unreadable, or not a number (e.g. the words "NOT TO BE PAID"). Never guess. Use [] for an empty list.
- Dates are YYYY-MM-DD ("17 JUL 26" -> 2026-07-17). bill_month is YYYY-MM ("JUL 2026" -> 2026-07).
- NEVER output names, addresses, CNIC, account/reference/consumer/contract/invoice numbers or meter numbers.

FIELDS
- provider: "KE" for K-Electric, "LESCO", or "IESCO".
- tariff: the tariff code exactly as printed (e.g. "A1-R", "A-1a(01)").
- sanctioned_load_kw: the number next to Sanc Load / S.Load / San Load.
- reading_date, issue_date: printed dates. due_date: the last date to pay without a late payment surcharge.
- previous_reading, current_reading, units_consumed: from the meter section, units billed this month as printed.
  If several meter rows are shown (e.g. net metering, peak/off-peak), use the FIRST / main row.
- charges: one entry per line of the charges section; keep separate entries when a type repeats; skip blank or 0 lines.
  type is one of:
    energy (cost of units: "Variable Upto ... Units", "Cost of Electricity", "Energy Charges", "Total Electricity Charges" when it is the gross cost of electricity),
    fixed (fixed charges), fpa (fuel price adjustment; use for both FPA and FCA),
    quarterly_adjustment (QTA / Uniform Quarterly Adjustment), surcharge (e.g. Additional Surcharge (PHL), F.C Surcharge),
    meter_rent (meter or service rent), subsidy (government subsidy/relief, NEGATIVE amount), other.
- total_charges: the printed charges subtotal (e.g. "Electricity Charges" subtotal, or "Net Electricity Charges"); null if none printed.
- taxes: one entry per line of the tax / government-duty section. Classify by SECTION, not line name.
  type is one of: gst (sales tax/GST, incl. GST on FPA), electricity_duty (ED), income_tax, municipal_tax (e.g. KE MUCT (KMC)), other_tax (extra/further tax, TV fee ...).
  If only ONE combined tax amount is printed (a single "Taxes" line, as on LESCO and IESCO bills), return [] and put it in total_taxes.
- total_taxes: the printed tax subtotal ("Taxes and Duties", "Taxes"); null if none printed.
- current_bill: the printed amount for THIS month's bill (before arrears), e.g. "Current Bill" or "Electricity charges for current month".
- arrears: previous dues carried forward, keep the printed sign (a credit is negative); null if blank.
- payable_within_due_date: the amount payable by the due date (the grand total).
- payable_after_due_date: the amount payable after the due date. If several late-payment amounts are printed, return the HIGHEST.

Return exactly these keys: provider, tariff, sanctioned_load_kw, bill_month, reading_date, issue_date, due_date,
previous_reading, current_reading, units_consumed, charges, total_charges, taxes, total_taxes, current_bill,
arrears, payable_within_due_date, payable_after_due_date.
"""

L1_EXAMPLE = """EXAMPLE (K-Electric bill, for format only; your values must come from the image you are given):
{"provider":"KE","tariff":"A1-R","sanctioned_load_kw":3,"bill_month":"2026-04","reading_date":"2026-04-03","issue_date":"2026-04-07","due_date":"2026-04-21",
"previous_reading":8819,"current_reading":8970,"units_consumed":151,
"charges":[{"type":"fixed","amount":900},{"type":"energy","amount":1054},{"type":"energy","amount":663.51},{"type":"quarterly_adjustment","amount":52.91},{"type":"fpa","amount":125.27},{"type":"surcharge","amount":64.93}],
"total_charges":2860.62,
"taxes":[{"type":"electricity_duty","amount":29.41},{"type":"gst","amount":520.21},{"type":"municipal_tax","amount":20}],
"total_taxes":569.62,"current_bill":3430.24,"arrears":-0.53,"payable_within_due_date":3430,"payable_after_due_date":3716}
(The bill showed two late-payment amounts, 3574 and 3716; the highest was used.)
"""

PROVIDER_HINTS = {
    "KE": "This is a K-Electric (KE) bill. Charges and taxes are itemised in the 'Bill Calculation' table: lines from 'Fixed Charges' down to the 'Electricity Charges' subtotal are charges; lines under 'Taxes and Duties' (up to its subtotal) are taxes. 'Previous Dues' is arrears. Late-payment amounts (5% / 10% LPS) appear in boxes and in the table; use the highest. units_consumed is the figure in the header box 'Current Month ... N units =' (the total billed units, which already adds Peak and Off-Peak registers when the meter table has several rows); previous_reading / current_reading come from the FIRST row of the 'Electricity You Have Used' meter table.",
    "LESCO": "This is a LESCO bill. Look at the 'BILL CHARGES BREAKDOWN' block (Total Electricity Charges, Subsidies, Net Electricity Charges, Taxes, Current Bill, Arrears, Grand Total), the meter table, and the header boxes for dates and payable amounts. A grand total printed with 'CR' is a credit, so negative.",
    "IESCO": "This is an IESCO bill. Look at the 'BILL CHARGES BREAKDOWN' block (Total Electricity Charges, Subsidies, Net Electricity Charges, Taxes, Current Bill, Arrears, Total FPA, Grand Total), the meter table, and the header boxes for dates and payable amounts (late-payment surcharge boxes list amounts up to / after a date; use the highest).",
}

# Row-order guidance shared by the LESCO and IESCO breakdown blocks (their numbers can sit slightly off their labels in tilted photos).
BREAKDOWN_HINT = (
    " The breakdown is a vertical list of labels with one number per label, in this order: Total Electricity Charges, Subsidies, "
    "Net Electricity Charges (its share % is printed beside it), Taxes (its share % is printed beside it), Current Bill, Grand Total; "
    "Arrears / Installment / Adjustments / Total FPA sit in a second column. In tilted photos a number can sit slightly above or below "
    "its label, so match numbers to labels in order and never skip one: Taxes has its own number, between Net Electricity Charges and "
    "Current Bill. Sanity-check what you read against the printed % split and totals "
    "(Net = Total - Subsidies; Current Bill is about Net + Taxes; Grand Total is about Current Bill + Arrears + Total FPA when FPA is printed separately), "
    "but write down what is PRINTED, never a recomputed value. "
    "If a non-zero 'Total FPA' (or FPA / FCA) amount is printed in this block, include it as one 'fpa' entry in charges."
)
PROVIDER_HINTS["LESCO"] += BREAKDOWN_HINT
PROVIDER_HINTS["IESCO"] += BREAKDOWN_HINT

GENERIC_HINT = "Identify which company issued the bill (K-Electric = KE, LESCO or IESCO) from the logo and layout."


def l1_user_prompt(hint: str) -> str:
    return f"{hint}\n\n{L1_EXAMPLE}\nNow read the attached bill image and return the JSON object."


FACTS_SYSTEM = """You transcribe electricity bills (K-Electric, LESCO, IESCO) into a complete fact sheet for answering customer questions.
Names, addresses and ID numbers are hidden or must be omitted. Copy numbers exactly as printed, as plain numbers (credits negative).
Return ONE JSON object with these keys (use null / [] when absent):
- usage_history: list of {"month": "YYYY-MM", "units": number|null, "bill_amount": number|null, "payment": number|null} from the usage / billing history tables or chart (include every month shown; read bar-chart labels if that is the only source).
  Units are NEVER negative: on net-metering bills a '-' printed beside a number in the BILL / PAYMENT columns is a credit on that amount, not on the units. Keep the sign on money columns.
- line_items: list of {"label": exact printed label, "units": number|null, "rate": number|null, "amount": number} for every line of the bill calculation / charges breakdown, including taxes, subtotals and totals, in printed order.
- late_payment: list of {"label": printed label, "amount": number} for every late-payment surcharge or amount-after-due-date figure.
- printed_percentages: list of {"label": ..., "percent": number} for any printed split (e.g. energy 83.39%, taxes 16.61%).
- payment_history: list of {"month": ..., "billed": number|null, "paid": number|null, "pay_date": "YYYY-MM-DD"|null}.
- messages: list of strings with any message board / notice text, translated to English.
- other_notes: list of strings for anything else a customer might ask about (installments, adjustments, net metering rows, meter readings per row, security deposit, etc.).
"""

PLAN_SYSTEM = """You prepare calculations for answering customer questions about one electricity bill.
You get the bill image, a verified extraction (JSON), a fact sheet and numbered questions. For each question list every arithmetic
calculation needed (sums, averages, differences, counts, percentages, projections). Write each as a Python-style expression with the numbers
typed in literally, using only + - * / ** %, parentheses, lists, and the functions sum, avg, min, max, abs, round, len, sqrt,
count_gt/count_ge/count_lt/count_le(list, threshold), filter_gt/filter_lt(list, threshold), index_of_max(list), index_of_min(list).
For counting or filtering, pass the COMPLETE list of values from the history and let the function decide, e.g. count_gt([141, 138, 197, 239, 203], 200).
Never decide by eye which values qualify. Provide separate calculations with and without the current month when it matters.
Use only numbers that appear on the bill. If a question needs no arithmetic, or needs data the bill does not show, use an empty list.
Consider both readings of ambiguous questions (e.g. history with and without the current month).
For estimate / projection / "roughly" questions always plan at least one estimate calculation from bill figures (e.g. current bill / units * units asked about, average of the monthly bill amounts, average or trend of monthly units).
Reply with ONLY JSON: {"Q1": [{"name": "what it computes", "expression": "..."}], "Q2": [], ...} covering every question id."""

QA_SYSTEM = """You are a helpful, precise assistant explaining one electricity bill to a customer in plain English.
You are given the bill image, a verified extraction (JSON), a fact sheet transcribed from the bill, and pre-computed calculation results. Answer every question using ONLY this bill.

RULES
- Numbers must be right. Use the pre-computed calculation results for all arithmetic; do not compute in your head. If something needed was not computed, only use figures printed on the bill.
- Never use outside tariff, rate or regulatory knowledge. If the bill does not show something needed, say clearly that the bill does not show it, and explain what it does show instead of guessing.
- If a value is an estimate or projection, say it is an estimate and show how you calculated it (inputs and method).
- When a question asks for an estimate, projection or "roughly" ("what would my bill be", "how much should I set aside", "how many units should I expect"), ALWAYS give a clearly labelled estimate built only from bill figures, with the method and its limits stated. Examples: this month's average cost per unit (current bill / units) x the units in question; the average of the monthly bill amounts the bill shows, or this month's bill x 12 / 12; the average or trend of the monthly units shown. Mention what the estimate ignores (e.g. fixed charges, slab rates, taxes). Say the bill does not show the information only when NO bill figure can support even a rough estimate.
- Answer the question that was asked first, in one sentence, then give supporting figures.
- If a question can be read more than one way, state the interpretation you used, or answer both (e.g. history with or without the current month).
- Be specific: lead with the direct answer and the exact figures (PKR, units, month names), then briefly explain. Mention the relevant bill lines. Keep each answer to a few sentences.
- Never include names, addresses, ID/reference/consumer/meter numbers.
- Write in English only, even if the bill has Urdu.
- Round money to 2 decimals (or whole rupees when the bill does) and percentages to 1 decimal.
"""


def _context(bill: dict, facts: dict, questions: list[tuple[str, str]]) -> str:
    import json

    qs = "\n".join(f"{qid}: {text}" for qid, text in questions)
    return (
        "Verified extraction (Level 1):\n" + json.dumps(bill) + "\n\n"
        "Fact sheet:\n" + json.dumps(facts) + "\n\n"
        "Questions:\n" + qs + "\n\n"
    )


def plan_user_prompt(bill: dict, facts: dict, questions: list[tuple[str, str]]) -> str:
    return _context(bill, facts, questions) + "List the calculations needed for each question as instructed."


def qa_user_prompt(bill: dict, facts: dict, questions: list[tuple[str, str]], calcs: dict) -> str:
    import json

    return (
        _context(bill, facts, questions)
        + "Pre-computed calculation results (exact, from code), by question id:\n" + json.dumps(calcs) + "\n\n"
        'Reply with ONLY a JSON array like [{"question_id":"Q1","answer":"..."}, ...] covering every question id.'
    )

