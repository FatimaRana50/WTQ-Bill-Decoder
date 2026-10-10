# Utility Bill Decoder (WTQ Build Track)

Reads a K-Electric, LESCO or IESCO electricity bill image and
1. **Level 1**: extracts the billing details into the required JSON schema, and
2. **Level 2**: answers customer questions about the bill in plain English, with calculations done in code.

Runtime: **Python 3.13** (works on 3.11+).

## Setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate      macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # then put your Google AI Studio key in API_KEY
```

## Run (generates both CSV files)

```bash
python main.py --bills test/bills --csv test/csv --out output
```

- `--bills` folder of images named `<bill_id>.png|jpg`
- `--csv` folder containing the `level1.csv` and `level2.csv` templates
- `--out` where the completed `level1.csv` and `level2.csv` are written (row order and the
  `bill_id`, `question_id`, `question` columns are kept untouched)

Finished work is cached per bill in `.cache/` so a re-run after a crash only redoes unfinished bills (`--no-cache` to disable).
Check the result before submitting: `python dev/check_submission.py test/csv output`.

## Testing and UIs

- Unit tests: `pytest -q tests`
- Score Level 1 against answer keys in `tests/gold/`: `python dev/evaluate.py output/level1.csv`
- Validate the CSVs before submitting: `python dev/check_submission.py test/csv output`
- Demo / verification UI (Streamlit): `streamlit run app.py` → http://localhost:8501
- HTTP API for a web front end: `uvicorn api:app --port 8000` → docs at http://localhost:8000/docs

## How it works

```
image -> preprocess (EXIF fix, size cap)
      -> Level 1: Gemini vision read (provider-specific hints, schema + rules prompt)
                  -> deterministic normalisation (numbers, CR -> negative, dates, enums, zero lines)
                  -> arithmetic validation (charges/taxes sums, readings vs units, totals, dates)
                  -> if a check fails: second allowed model reads independently, best reading is kept,
                     then a focused re-inspection of the flagged values (printed values are never "corrected" by code)
      -> Level 2: fact sheet transcription (usage history, line items, late-payment amounts, notes)
                  -> planner lists the calculations each question needs
                  -> expressions are evaluated by a safe calculator in Python (sums, averages, counts, projections)
                  -> answer writer uses the exact results, states interpretations, labels estimates,
                     and says so when the bill does not show something
```

Design choices: the model is used where it adds the most value (reading messy, tilted, bilingual
images and explaining in plain language); code is used where it is more reliable (number parsing,
validation, arithmetic, CSV writing). Every API call has pacing for the free-tier rate limit, retries
with backoff, and a fallback to the other allowed model. A failure on one bill never stops the run.

## Configuration (`.env`)

| Variable | Purpose |
|---|---|
| `MODEL_PROVIDER` | `google` |
| `MODEL_NAME` | primary model, `gemini-3.5-flash-lite` |
| `VERIFIER_MODEL_NAME` | cross-check / fallback model, `gemini-3.1-flash-lite` |
| `API_KEY` | Google AI Studio key (placeholder in `.env.example`) |
| `MIN_INTERVAL_SECONDS`, `MAX_RETRIES`, `CACHE_DIR` | optional tuning |

## AI usage

- **Models called by the solution (only these two):** Google `gemini-3.5-flash-lite` (primary) and
  Google `gemini-3.1-flash-lite` (second reading / fallback), via the Google AI Studio API (`google-genai` SDK).
- **Other APIs / services:** none. No OCR library and no invoice-extraction service is used.
- **AI tools used to write the code:** Claude Code (Anthropic) was used as a coding assistant.
