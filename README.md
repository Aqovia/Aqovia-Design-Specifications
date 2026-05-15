# Aqovia Design Specifications

Public, LLM-friendly rendering of the Aqovia brand and design specifications.
GitHub Pages serves `index.html` from the `master` branch — point an LLM (or a
human) at the published URL and they get colours, logo guidance, fonts, social
post examples and reference imagery in a single page.

## Repository layout

```
.
├── index.html                 # Built output — committed, served by GitHub Pages
├── src/
│   └── index.html             # Editable template (relative paths to assets)
├── Design Specifications/
│   ├── README.md              # Original markdown spec (source of truth for wording)
│   ├── 2026_Brand_Guidelines.pdf
│   └── *.png                  # Logos, icons, reference imagery
└── build.py                   # Inlines every local image into index.html
```

The published `index.html` is **self-contained for images**: every `<img>` is a
base64 `data:` URI, so a single URL fetch gives an LLM the full page including
visuals. The PDF stays as a relative link (`./Design%20Specifications/2026_Brand_Guidelines.pdf`)
because embedding it would push the file past most LLM URL-fetch size limits.

## Updating the spec

1. **Edit the wording / layout**: open `src/index.html` and change the markup.
2. **Add or replace imagery**: drop the file into `Design Specifications/` and
   reference it from `src/index.html` as
   `./Design%20Specifications/your-file.png` (spaces in the folder name must be
   URL-encoded as `%20`).
3. **Rebuild**:
   ```bash
   python3 build.py
   ```
4. Commit `index.html`, `src/index.html` and any new assets, then push to
   `master`. GitHub Pages rebuilds automatically.

If you also want to keep the markdown spec in sync, update
`Design Specifications/README.md` alongside the template.

## What `build.py` does

For every `src="./..."` / `href="./..."` it finds in `src/index.html`:

- **Images** (`.png .jpg .jpeg .gif .webp .bmp`) are
  - downscaled to a maximum of `MAX_DIM` (1280 px) on the longest edge,
  - re-encoded as **PNG** when they have real alpha transparency, otherwise as
    progressive **JPEG** at quality `JPEG_QUALITY` (82) — both formats are
    universally understood by vision-capable LLMs,
  - embedded inline as a base64 `data:` URI.
- **Everything else** (currently just the PDF) is left as the original relative
  link so the browser fetches it normally.

The script prints a per-asset before/after size table and the final
`index.html` size at the end.

### Tuning

Two constants near the top of `build.py`:

| Constant       | Default | Effect                                                |
| -------------- | ------- | ----------------------------------------------------- |
| `MAX_DIM`      | `1280`  | Cap on the longest image edge in pixels.              |
| `JPEG_QUALITY` | `82`    | JPEG encoder quality for photo-like images (0–95).    |

Raise `MAX_DIM` if you need sharper imagery on retina displays (at the cost of
a larger `index.html`); lower `JPEG_QUALITY` if you want a smaller file.

## Requirements

- Python 3.10+
- [Pillow](https://pillow.readthedocs.io/) — install with
  `pip install Pillow` if it isn't already available.
