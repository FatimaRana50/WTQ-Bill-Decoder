# Prompt to paste into Lovable

Build a polished, professional single-page web app called **"Bill Decoder"** (React + TypeScript + Tailwind + shadcn/ui, Vite). It is the front end for a Pakistani electricity-bill reader: the user uploads a photo or scan of a K-Electric, LESCO or IESCO bill, and the app shows every extracted detail, lets them verify it, and answers questions about the bill in plain English.

**Frontend only. Do NOT use Supabase, auth, or any database, and do not invent data or mock the AI.** All logic is behind an existing REST API. Read its base URL from `import.meta.env.VITE_API_URL` (default `http://localhost:8000`). Show a small "API connected / API offline" indicator in the header using `GET /api/health`, and a friendly error state with a Retry button whenever a call fails.

## Visual style
Calm, trustworthy fintech/utility look. Light theme by default with a dark-mode toggle. Primary colour deep teal (#0F766E) with amber (#F59E0B) as the accent for taxes and late fees. Inter font, generous whitespace, rounded-2xl cards with soft shadows, subtle fade/slide transitions, skeleton loaders while waiting (calls take 5-40 seconds, so show a stepper such as "Reading the bill -> Checking the numbers -> Done"). Fully responsive; on mobile stack the image above the results. Accessible contrast, visible focus rings.

## Layout
**Header:** logo (lightning-bolt icon) + "Bill Decoder", API status pill, dark-mode toggle.

**Hero / upload zone** (shown until a bill is chosen): large drag-and-drop area for PNG/JPG (max 15 MB), plus a row of "Try a sample bill" chips populated from `GET /api/samples` (clicking one fetches `GET /api/samples/{name}` as a Blob and uses it as the uploaded file).

**After a bill is chosen:** two-column workspace. Left (sticky): the bill image with a zoom-on-click lightbox, the file name, and a "Use a different bill" button. Right: tabs **Summary | Verify | Ask | JSON**. Start decoding automatically on upload and show progress.

### Tab 1: Summary
- Badge row: provider (K-Electric / LESCO / IESCO), tariff, bill month, and a green "All checks passed" or red "N checks flagged" badge (from `issues`).
- Three big KPI cards: **Payable by due date** (with the due date), **Payable after due date** (amber, label "highest late amount"), **Units consumed** (with "previous -> current reading").
- A horizontal stacked bar "Where your money goes": charges vs taxes (use `total_charges` and `total_taxes`), with amounts and percentages.
- Two tables side by side: **Charges** and **Taxes** (type prettified e.g. `quarterly_adjustment` -> "Quarterly adjustment", amount right-aligned in PKR with thousands separators, negatives in green as credits/subsidies). If `taxes` is empty but `total_taxes` is set, show "Single combined tax amount printed: PKR X".
- Small stat row: Current bill, Arrears (negative = credit, explain with a tooltip), Sanctioned load (kW), Issue date, Reading date.
- A `null` value must render as a muted "Not on bill" (never as 0 or blank).

### Tab 2: Verify (how the user can trust the result)
1. **Consistency checks:** list from `issues`; green check card when empty ("Charges and taxes add up, readings match units, dates are valid"), red cards otherwise.
2. **Compare to image:** a table of every field and its extracted value next to the zoomable image.
3. **Second opinion:** button -> `POST /api/second-opinion`; show "The second model read exactly the same values" (green) or a table of Field / Primary / Second for each disagreement (amber).
4. **Compare with expected values:** if `GET /api/expected/{bill_id}` returns 200 load it automatically; also provide a textarea to paste expected JSON. Call `POST /api/compare` and show an accuracy ring (e.g. 18/18 = 100%) and a table with a check/cross per field (Field / Extracted / Expected).

### Tab 3: Ask
- Suggested question chips: "How much of my bill is taxes?", "How many months in my history went above 200 units?", "What is my average monthly consumption?", "How much extra would I pay if I pay after the due date?", "What is the average price I paid per unit this month?", "If I use 20% more units next month, roughly what would my bill be?", "What does the fuel price adjustment mean?"
- Free-text input + Send. Render the conversation as chat bubbles (question right, answer left in a card with a teal left border). Keep history in React state.
- Under each answer a collapsible "How this was calculated (N steps)" showing a small table: What / Expression (monospace) / Result.
- Typing indicator while waiting.

### Tab 4: JSON
Syntax-highlighted, collapsible JSON of the bill, a Copy button and a Download .json button.

## API contract (already implemented; base `VITE_API_URL`)
All requests are `multipart/form-data` where noted. The backend is stateless, so the frontend must keep the original image File and the decoded `bill` object in state and resend them.

- `GET /api/health` -> `{"status":"ok","model":"...","verifier_model":"..."}`
- `GET /api/samples` -> `["IESCO_0004.jpg","KESC_0004.png", ...]`
- `GET /api/samples/{name}` -> the image file
- `POST /api/decode` form field `image` (file) -> `{"bill_id":"KESC_0008","bill":{...},"issues":["..."]}`
- `POST /api/second-opinion` fields `image` (file), `bill` (JSON string of the decoded bill) -> `{"agrees":false,"differences":[{"field":"arrears","primary":-0.53,"second":0}]}`
- `POST /api/ask` fields `image` (file), `bill` (JSON string), `question` (string) -> `{"answer":"...","calculations":[{"name":"Tax share %","expression":"569.62 / 3430.24 * 100","result":"16.606"}]}`
- `GET /api/expected/{bill_id}` -> expected bill JSON, or 404 when none exists (treat 404 as "no answer key", not an error)
- `POST /api/compare` JSON body `{"bill":{...},"expected":{...}}` -> `{"correct":18,"total":18,"accuracy":1.0,"fields":[{"field":"tariff","predicted":"A1-R","expected":"A1-R","ok":true}]}`

The `bill` object always has exactly these keys (any scalar may be `null`; amounts are numbers in PKR, credits negative):
```json
{
  "provider": "KE", "tariff": "A1-R", "sanctioned_load_kw": 3,
  "bill_month": "2026-04", "reading_date": "2026-04-03", "issue_date": "2026-04-07", "due_date": "2026-04-21",
  "previous_reading": 8819, "current_reading": 8970, "units_consumed": 151,
  "charges": [{"type": "fixed", "amount": 900}, {"type": "energy", "amount": 1054}],
  "total_charges": 2860.62,
  "taxes": [{"type": "gst", "amount": 520.21}],
  "total_taxes": 569.62, "current_bill": 3430.24, "arrears": -0.53,
  "payable_within_due_date": 3430, "payable_after_due_date": 3716
}
```
`provider` is `"KE" | "LESCO" | "IESCO"`. Charge types: energy, fixed, fpa, quarterly_adjustment, surcharge, meter_rent, subsidy, other. Tax types: gst, electricity_duty, income_tax, municipal_tax, other_tax.

## Quality bar
Typed API client in `src/lib/api.ts`, one component per tab, no hard-coded demo data, loading/empty/error states everywhere, currency formatted as `PKR 3,430.24` (drop `.00`), dates shown like "21 Apr 2026". Add a footer: "Answers use only the information printed on your bill."
