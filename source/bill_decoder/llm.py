"""Thin Gemini client: rate limiting, retries with backoff, model fallback, JSON parsing."""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Callable, Sequence

from google import genai
from google.genai import types

from .config import Config

log = logging.getLogger(__name__)


class LLMError(RuntimeError):
    pass


def parse_json(text: str) -> Any:
    """Parse JSON from a model reply, tolerating code fences and surrounding prose."""
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Last resort: take the outermost {...} or [...] span.
    for open_c, close_c in (("{", "}"), ("[", "]")):
        start, end = text.find(open_c), text.rfind(close_c)
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    raise LLMError(f"Model did not return valid JSON: {text[:200]!r}")


class LLMClient:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._client = genai.Client(api_key=cfg.api_key)
        self._last_call = 0.0

    def _pace(self) -> None:
        wait = self.cfg.min_interval - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()

    def generate(
        self,
        prompt: str,
        *,
        images: Sequence[tuple[bytes, str]] = (),
        system: str | None = None,
        model: str | None = None,
        json_mode: bool = True,
        tools: Sequence[Callable] | None = None,
    ) -> str:
        """Return the model's text. Retries on transient errors, then falls back to the other model."""
        primary = model or self.cfg.model
        order = [primary] + [m for m in (self.cfg.model, self.cfg.verifier_model) if m != primary]
        parts: list[Any] = [types.Part.from_bytes(data=d, mime_type=m) for d, m in images]
        parts.append(prompt)
        config = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json" if json_mode and not tools else None,
            tools=list(tools) if tools else None,
        )
        last_err: Exception | None = None
        for name in order:
            for attempt in range(self.cfg.max_retries):
                self._pace()
                try:
                    resp = self._client.models.generate_content(model=name, contents=parts, config=config)
                    text = resp.text
                    if not text:
                        raise LLMError("empty response")
                    return text
                except Exception as exc:  # network, quota, safety, empty reply...
                    last_err = exc
                    delay = min(2**attempt * 3, 40)
                    log.warning("%s attempt %d failed (%s); retrying in %ds", name, attempt + 1, str(exc)[:120], delay)
                    time.sleep(delay)
            log.error("Model %s exhausted retries, trying fallback", name)
        raise LLMError(f"All models failed: {last_err}")

    def generate_json(self, prompt: str, **kwargs: Any) -> Any:
        """Generate and parse JSON, with one repair retry if the reply is malformed."""
        text = self.generate(prompt, **kwargs)
        try:
            return parse_json(text)
        except LLMError:
            log.warning("Malformed JSON, asking again")
            text = self.generate(prompt + "\n\nReturn ONLY valid JSON, nothing else.", **kwargs)
            return parse_json(text)
