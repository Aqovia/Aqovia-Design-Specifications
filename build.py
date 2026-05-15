#!/usr/bin/env python3
"""
Build a single self-contained index.html.

For every relative asset referenced from src/index.html:
  - Images (.png/.jpg/.jpeg/.gif/.webp/.bmp) are downscaled to MAX_DIM on the
    longest edge and re-encoded:
      * images with real transparency  → optimized PNG
      * everything else                → progressive JPEG (quality JPEG_QUALITY)
    The result is embedded as a base64 data: URI. JPEG and PNG are the two
    formats every vision-capable LLM supports, so the page stays consumable
    via a single URL fetch.
  - Non-image assets (e.g. the PDF) are left as relative hrefs so they resolve
    against the page's served path.

Usage:
    python3 build.py

Reads:   src/index.html
Writes:  index.html

Requires: Pillow.
"""

import base64
import io
import re
import sys
from pathlib import Path
from urllib.parse import unquote

from PIL import Image

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src" / "index.html"
OUT = ROOT / "index.html"

ATTR = re.compile(r'(\b(?:src|href)=")(\.\/[^"]+)(")')

MAX_DIM = 1280
JPEG_QUALITY = 82
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}


def has_alpha(img: Image.Image) -> bool:
    if img.mode == "P" and "transparency" in img.info:
        return True
    if img.mode in ("RGBA", "LA"):
        return img.getchannel("A").getextrema()[0] < 255
    return False


def compress_image(asset: Path) -> tuple[bytes, str]:
    with Image.open(asset) as im:
        im.load()
        w, h = im.size
        if max(w, h) > MAX_DIM:
            scale = MAX_DIM / max(w, h)
            im = im.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)

        buf = io.BytesIO()
        if has_alpha(im):
            if im.mode == "P":
                im = im.convert("RGBA")
            im.save(buf, format="PNG", optimize=True)
            return buf.getvalue(), "image/png"
        if im.mode != "RGB":
            im = im.convert("RGB")
        im.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
        return buf.getvalue(), "image/jpeg"


def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def build() -> int:
    if not SRC.is_file():
        print(f"error: template not found: {SRC}", file=sys.stderr)
        return 1

    html = SRC.read_text(encoding="utf-8")
    inlined: list[tuple[str, int, int]] = []
    linked: list[str] = []
    missing: list[str] = []

    def replace(m: re.Match) -> str:
        prefix, path, suffix = m.group(1), m.group(2), m.group(3)
        rel = unquote(path[2:])
        asset = ROOT / rel

        if not asset.is_file():
            missing.append(rel)
            return m.group(0)

        if asset.suffix.lower() not in IMAGE_EXTS:
            linked.append(rel)
            return m.group(0)

        original_size = asset.stat().st_size
        try:
            data, mime = compress_image(asset)
        except (OSError, Image.UnidentifiedImageError) as e:
            print(f"  ! could not compress {rel}: {e}", file=sys.stderr)
            linked.append(rel)
            return m.group(0)

        b64 = base64.b64encode(data).decode("ascii")
        inlined.append((rel, original_size, len(b64)))
        return f"{prefix}data:{mime};base64,{b64}{suffix}"

    out_html = ATTR.sub(replace, html)
    OUT.write_text(out_html, encoding="utf-8")

    if inlined:
        total_orig = sum(o for _, o, _ in inlined)
        total_enc = sum(e for _, _, e in inlined)
        ratio = total_enc / total_orig if total_orig else 0
        print(f"Inlined {len(inlined)} image(s) — {human(total_orig)} on disk → {human(total_enc)} base64 ({ratio:.1%}):")
        for name, orig, enc in sorted(inlined, key=lambda x: -x[2]):
            print(f"  {human(orig):>10} → {human(enc):>10}  {name}")
    if linked:
        print(f"\nLeft as relative links ({len(linked)}):")
        for name in sorted(set(linked)):
            print(f"  - {name}")
    if missing:
        print(f"\nMissing on disk ({len(missing)}):", file=sys.stderr)
        for name in missing:
            print(f"  ! {name}", file=sys.stderr)

    print(f"\nWrote {OUT.name} ({human(OUT.stat().st_size)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
