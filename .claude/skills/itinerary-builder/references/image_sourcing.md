# Image Sourcing — Royalty-Free Photos

Use only permissively-licensed images. Wikipedia/Wikimedia Commons content (CC-BY-SA / CC0 / PD) is safe for personal use; for redistribution attribution helps.

## Primary source — Wikipedia REST summary endpoint

For any named POI (must match a Wikipedia article title):

```text
GET https://en.wikipedia.org/api/rest_v1/page/summary/{Title}
```

Returns JSON. Two image URLs of interest:
- `thumbnail.source` — ~300px wide, always a raster format (JPEG/PNG)
- `originalimage.source` — full resolution, **may be SVG or PDF**

Prefer `thumbnail` (guaranteed raster) and fall back to `originalimage` only if
its media type is an accepted raster (`fetch_images.py` rejects non-image
responses). SVG/PDF originals must be skipped so PIL and python-docx don't fail.

### Title encoding

- URL-encode spaces as `_` or `%20`
- For Vietnamese names: try the diacritic form first (`H%C3%A0_V%C3%A2n_Pass`); if 404, fall back to ASCII (`Hai_Van_Pass`).
- Some POIs need slight rewording: "Linh Ứng Pagoda, Sơn Trà" → use "Linh Ung Pagoda" or commons search

## Fallback — Wikimedia Commons search

When Wikipedia REST returns no image, search Commons directly:

```text
GET https://commons.wikimedia.org/w/api.php
    ?action=query
    &list=search
    &srsearch=<query>
    &srnamespace=6      # 6 = File namespace
    &format=json
    &srlimit=1
```

The first hit's `title` is "File:Something.jpg". Then fetch its URL via `imageinfo`:

```text
GET https://commons.wikimedia.org/w/api.php
    ?action=query
    &titles=<File:Something.jpg>
    &prop=imageinfo
    &iiprop=url
    &format=json
```

## User-Agent header — required

Wikimedia REST/API endpoints **require** a descriptive `User-Agent` header:

```python
HEADERS = {'User-Agent': 'ItineraryBuilder/1.0 (trip-planner)'}
```

Without this, you get 403 / rate-limited.

## Download with stdlib

```python
import urllib.request
req = urllib.request.Request(url, headers=HEADERS)
with urllib.request.urlopen(req, timeout=30) as r:
    open(dest_path, 'wb').write(r.read())
```

No need for `requests` package.

## Image normalisation — REQUIRED before python-docx embed

`python-docx` strict-parses JPEG markers. Some Wikipedia images use unusual marker order (e.g. FFD8FFDB instead of FFD8FFE0). Always re-save through PIL:

```python
from PIL import Image
im = Image.open(src)
im.load()
if im.mode in ('RGBA', 'P'):
    im = im.convert('RGB')
if im.width > 1600:
    ratio = 1600 / im.width
    im = im.resize((1600, int(im.height * ratio)), Image.LANCZOS)
im.save(dest, 'JPEG', quality=85, optimize=True)
```

Always re-save to `.jpg` extension even if source was `.png` — keeps embed format consistent.

## Image inventory per trip

Build a list in `trips/<slug>/data.json` under `images`:

```json
{
  "places": [
    {"key": "dragon_bridge", "wiki_title": "Dragon Bridge (Vietnam)", "alt_search_query": "Dragon Bridge Da Nang"},
    {"key": "ba_na_hills",   "wiki_title": "Bà Nà Hills", "alt_search_query": "Golden Bridge Da Nang"},
    ...
  ]
}
```

`fetch_images.py` iterates this list, tries Wiki first, then Commons search, then logs failures.

## When no image is available

- Leave a placeholder paragraph in the Word doc: `[Image placeholder: <key>]` in light grey italic
- Continue building; do not block on missing images
- Log to `trips/<slug>/unvalidated.md` for the user to manually source

## Attribution

Wikimedia images vary in licence (CC-BY-SA most common). For personal travel docs, attribution in a footer is good practice:

> All photos from Wikimedia Commons under permissive licences (CC-BY-SA / public domain). Map data © OpenStreetMap contributors.

Add this footer to the Word doc.

## DO NOT

- Hot-link to non-Wikimedia images (copyright + may break)
- Use random Google Image results
- Scrape Instagram / TikTok / travel blogs
- Use stock-photo sites without verifying licence

## Map images

See [`map_rendering.md`](map_rendering.md) — maps are rendered locally from OSM tiles, not fetched as images.
