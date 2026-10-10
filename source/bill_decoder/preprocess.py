"""Image loading: fix EXIF rotation, cap the size, return bytes the model can read."""
from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageOps

MAX_SIDE = 2400  # large enough for small print, small enough to keep requests fast


def find_bill(bills_dir: Path, bill_id: str) -> Path:
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        path = bills_dir / f"{bill_id}{ext}"
        if path.exists():
            return path
    raise FileNotFoundError(f"No image for {bill_id} in {bills_dir}")


def load_image(path: Path) -> tuple[bytes, str]:
    """Return (PNG bytes, mime type). Handles photos with EXIF rotation and odd modes."""
    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img).convert("RGB")
        if max(img.size) > MAX_SIDE:
            img.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
    return buf.getvalue(), "image/png"
