"""Runtime configuration, read from environment variables / a local .env file."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# The only models this project is allowed to call (competition rule, guide section 3).
ALLOWED_MODELS = {
    "google": {"gemini-3.5-flash-lite", "gemini-3.1-flash-lite"},
}


@dataclass(frozen=True)
class Config:
    provider: str
    model: str
    api_key: str
    # Second model used as an independent cross-check and as a fallback on API errors.
    verifier_model: str
    # Minimum seconds between API calls (free tier is 15 requests/min).
    min_interval: float = 4.2
    max_retries: int = 5
    cache_dir: Path = field(default_factory=lambda: Path(".cache"))

    @staticmethod
    def from_env() -> "Config":
        load_dotenv()
        provider = os.getenv("MODEL_PROVIDER", "google").strip().lower()
        model = os.getenv("MODEL_NAME", "gemini-3.5-flash-lite").strip()
        verifier = os.getenv("VERIFIER_MODEL_NAME", "gemini-3.1-flash-lite").strip()
        api_key = os.getenv("API_KEY", "").strip()
        if provider not in ALLOWED_MODELS:
            raise SystemExit(f"MODEL_PROVIDER={provider!r} is not supported (use 'google').")
        for name in (model, verifier):
            if name not in ALLOWED_MODELS[provider]:
                raise SystemExit(f"Model {name!r} is not on the competition's allowed list.")
        if not api_key:
            raise SystemExit("API_KEY is empty. Copy .env.example to .env and fill it in.")
        return Config(
            provider=provider,
            model=model,
            api_key=api_key,
            verifier_model=verifier,
            min_interval=float(os.getenv("MIN_INTERVAL_SECONDS", "4.2")),
            max_retries=int(os.getenv("MAX_RETRIES", "5")),
            cache_dir=Path(os.getenv("CACHE_DIR", ".cache")),
        )
