# Bill Decoder

Frontend for the existing Pakistani electricity-bill REST service. Built with React 19, TypeScript, TanStack Start, Vite, Tailwind v4, and shadcn/ui. No database, authentication, sample bill data, or AI simulation is included.

## Run locally

1. Install dependencies: `bun install` (or `npm install`).
2. Copy `.env.example` to `.env.local` and set `VITE_API_URL` to your REST service URL. The default is `http://localhost:8000`.
3. Start your existing API separately.
4. Run `bun run dev` (or `npm run dev`).

The REST API must allow CORS from your frontend origin. A hosted frontend needs a publicly reachable **HTTPS** API URL; localhost refers to each visitor's computer and cannot connect to your local Python service. Rebuild/redeploy after changing `VITE_API_URL`.

## Features

- PNG/JPG upload, drag-and-drop, 15 MB limit, samples fetched only from the API.
- Automatic decoding with loading states, original image preview and enlarged image.
- Summary of charges, taxes, payments, dates, readings, and credits.
- Consistency checks, second-model verification, automatic answer-key lookup and expected JSON comparison.
- Questions with session-only history and calculation traces returned by the API.
- Highlighted JSON with copy and download; light/dark themes.
- Retry states for failed calls. Answer-key 404 is treated as unavailable, not an error.

## Files

- `src/lib/api.ts`: typed API requests and decoded-bill validation.
- `src/lib/bill-format.ts`: file validation and display formatting.
- `src/components/bill-decoder/`: one component per tab and shared controls.
- `src/routes/index.tsx`: upload page and workspace; `src/styles.css`: semantic theme tokens.

## Tests

Run `bun run test`. Tests cover upload types/size, null handling, PKR/date formatting, routing, and API contracts. Actual extraction, verification, and Q&A require the real running API and are not mocked.

The supplied `app.py` is a Streamlit reference application, not the REST server. Keep your existing REST implementation; this frontend uses exactly the endpoints in the attached prompt.