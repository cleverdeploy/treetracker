"""Read a numbered tag from a tree photo using Claude Haiku vision."""

from __future__ import annotations

import base64
import json
import logging
import mimetypes
from dataclasses import dataclass

from anthropic import Anthropic

from app.config import get_settings

log = logging.getLogger(__name__)

MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = (
    "You read small numbered identification tags fixed to trees in photographs. "
    "Tags are typically aluminium or plastic, stamped or printed with digits "
    "(sometimes leading zeros). They may be weathered, partially obscured, or "
    "at an angle. Return ONLY a JSON object matching the schema."
)

USER_PROMPT = (
    "Find the numbered tag on this tree. Respond with strict JSON:\n"
    '{"tag": "<digits as string, preserving leading zeros, or null if none readable>",\n'
    ' "confidence": <number from 0 to 1>}\n'
    "If you can see a tag but cannot read it confidently, return the best guess "
    "with a low confidence (e.g. 0.3). If there is clearly no tag visible, return "
    'tag=null with confidence=1.0. Do not include any commentary.'
)


@dataclass
class OcrResult:
    tag: str | None
    confidence: float | None
    raw: str


def read_tag(image_path: str) -> OcrResult:
    settings = get_settings()
    if not settings.anthropic_api_key:
        log.warning("ANTHROPIC_API_KEY missing — skipping OCR")
        return OcrResult(tag=None, confidence=None, raw="")

    media_type = mimetypes.guess_type(image_path)[0] or "image/jpeg"
    if media_type == "image/heic":
        media_type = "image/jpeg"  # we always convert HEIC before calling
    with open(image_path, "rb") as f:
        b64 = base64.standard_b64encode(f.read()).decode("ascii")

    client = Anthropic(api_key=settings.anthropic_api_key)
    try:
        msg = client.messages.create(
            model=MODEL,
            max_tokens=200,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": b64,
                            },
                        },
                        {"type": "text", "text": USER_PROMPT},
                    ],
                }
            ],
        )
    except Exception as e:
        log.exception("Anthropic API call failed: %s", e)
        return OcrResult(tag=None, confidence=None, raw="")

    text = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text").strip()
    return _parse(text)


def _parse(text: str) -> OcrResult:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        log.warning("OCR response not JSON: %r", text)
        return OcrResult(tag=None, confidence=None, raw=text)

    tag = data.get("tag")
    if tag is not None:
        tag = str(tag).strip() or None
    conf = data.get("confidence")
    try:
        conf = float(conf) if conf is not None else None
    except (TypeError, ValueError):
        conf = None
    return OcrResult(tag=tag, confidence=conf, raw=text)


def normalize_tag(tag: str) -> str:
    """Strip non-digits, preserve leading zeros."""
    return "".join(c for c in tag if c.isdigit())
