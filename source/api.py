"""HTTP API for a web front end (e.g. a Lovable/React UI).

    uvicorn api:app --port 8000

Stateless: every call carries the bill image, so the front end only has to hold state in the browser.
Interactive docs: http://localhost:8000/docs
"""
from __future__ import annotations

import hashlib
import io
import json
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from PIL import Image

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
SAMPLE_DIR = ROOT.parent / "data" / "train" / "train" / "bills"

app = FastAPI(title="Utility Bill Decoder API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_cfg = Config.from_env()
_llm = LLMClient(_cfg)
_cache = Cache(_cfg.cache_dir, True)
_facts: dict[str, dict] = {}


async def _save_upload(upload: UploadFile) -> tuple[Path, str]:
    """Persist an upload (needed for cache hashing) and return (path, bill_id). Rejects non-images."""
    data = await upload.read()
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(413, "Image larger than 15 MB")
    try:
        Image.open(io.BytesIO(data)).verify()
    except Exception:
        raise HTTPException(400, "File is not a valid image")
    suffix = Path(upload.filename or "bill.png").suffix or ".png"
    digest = hashlib.sha1(data).hexdigest()[:12]
    path = Path(tempfile.gettempdir()) / f"upload_{digest}{suffix}"
    path.write_bytes(data)
    return path, Path(upload.filename or "bill").stem


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "model": _cfg.model, "verifier_model": _cfg.verifier_model}


@app.get("/api/samples")
def samples() -> list[str]:
    """Names of the bundled sample bills (training set), if present."""
    return sorted(p.name for p in SAMPLE_DIR.glob("*") if p.suffix.lower() in {".png", ".jpg", ".jpeg"})


@app.get("/api/samples/{name}")
def sample_image(name: str):
    path = SAMPLE_DIR / Path(name).name
    if not path.exists():
        raise HTTPException(404, "Unknown sample")
    return FileResponse(path)


@app.post("/api/decode")
async def decode(image: UploadFile = File(...)) -> dict:
    """Level 1: returns {bill_id, bill, issues}. `issues` lists failed consistency checks (empty = all pass)."""
    path, bill_id = await _save_upload(image)
    bill = _cache.get(bill_id, "l1", path)
    if bill is None:
        try:
            bill = extract_bill(_llm, load_image(path), bill_id)
        except Exception as exc:
            raise HTTPException(502, f"Model call failed: {exc}")
        _cache.put(bill_id, "l1", path, bill)
    return {"bill_id": bill_id, "bill": bill, "issues": check(bill)}


@app.post("/api/second-opinion")
async def second_opinion(image: UploadFile = File(...), bill: str = Form(...)) -> dict:
    """Re-read with the other allowed model and report fields where the two readings disagree."""
    path, bill_id = await _save_upload(image)
    primary = json.loads(bill)
    try:
        other = read_once(_llm, load_image(path), provider_hint(bill_id), _cfg.verifier_model)
    except Exception as exc:
        raise HTTPException(502, f"Model call failed: {exc}")
    diffs = differences(primary, other)
    return {"agrees": not diffs, "differences": [{"field": d, "primary": primary.get(d), "second": other.get(d)} for d in diffs]}


@app.post("/api/ask")
async def ask(image: UploadFile = File(...), bill: str = Form(...), question: str = Form(...)) -> dict:
    """Level 2: returns {answer, calculations:[{name, expression, result}]}."""
    if not question.strip():
        raise HTTPException(400, "Question is empty")
    path, bill_id = await _save_upload(image)
    img = load_image(path)
    key = hashlib.sha1(path.read_bytes()).hexdigest()
    if key not in _facts:
        _facts[key] = _cache.get(bill_id, "facts", path) or extract_facts(_llm, img)
        _cache.put(bill_id, "facts", path, _facts[key])
    answers, calcs = answer_with_trace(_llm, img, json.loads(bill), _facts[key], [("Q1", question.strip())])
    return {"answer": answers["Q1"], "calculations": calcs.get("Q1", [])}


@app.get("/api/expected/{bill_id}")
def expected(bill_id: str) -> dict:
    path = GOLD_DIR / f"{Path(bill_id).stem}.json"
    if not path.exists():
        raise HTTPException(404, "No answer key for this bill")
    return json.loads(path.read_text("utf-8"))


@app.post("/api/compare")
def compare_endpoint(payload: dict) -> dict:
    """Body: {"bill": {...}, "expected": {...}} -> per-field results and accuracy."""
    rows = compare(payload["bill"], payload["expected"])
    ok = sum(r["ok"] for r in rows)
    return {"correct": ok, "total": len(rows), "accuracy": ok / len(rows) if rows else None, "fields": rows}
