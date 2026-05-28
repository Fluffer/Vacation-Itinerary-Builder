# Error Handling — Failure Modes & Fallbacks

The pipeline must produce deliverables even when sub-steps fail. Never block on a single validation or image fetch.

## Ollama validation hangs / errors

- Per-call timeout 60 seconds
- Try model order: `deepseek-pro` → `deepseek-flash` → `glm` → `minimax`
- On all-fail: log fact to `trips/<slug>/unvalidated.md` with status "manual verify needed"
- Add ⚠️ flag to corresponding cell in workbook + paragraph in docx
- Continue pipeline

## Wikipedia REST returns 404 / no image

- Try Wikipedia title variants (with/without diacritics, alt spellings)
- Fall back to Wikimedia Commons search via `srsearch`
- Final fallback: skip image, emit `[Image placeholder: <key>]` paragraph in docx
- Log skip to `unvalidated.md`

## python-docx UnrecognizedImageError

Cause: non-standard JPEG marker order or unsupported color profile.

Fix: re-save every image via PIL before embedding (always — not just on error):

```python
im = Image.open(src); im.load()
if im.mode in ('RGBA', 'P'):
    im = im.convert('RGB')
im.save(dst, 'JPEG', quality=85)
```

## staticmap rate-limit (HTTP 429 from OSM tiles)

- Default tile server is shared; heavy iteration triggers rate-limit
- Swap to alternate template: `https://tile.openstreetmap.de/{z}/{x}/{y}.png`
- Add 1-second sleep between map renders
- If persistent: cache rendered map locally, only re-render when POI list changes

## Source docx malformed

- Wrap parse in try/except
- If full parse fails: extract plain text via `python-docx` paragraph iteration only (no table parsing)
- If even that fails: ask user to paste text directly
- Never silently produce empty trip data

## Vietnamese / non-ASCII print on Windows

`charmap` codec errors on Windows when printing UTF-8 to stdout. Always wrap:

```python
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
```

Place at the top of EVERY script.

## Excel file locked (open in Excel during build)

`PermissionError: [Errno 13]` on `wb.save()`.

Options:
1. Detect locked file, prompt user to close OR save with `_v2` suffix
2. Always write to temp file first, then atomic rename

Reference implementation in `scripts/lib/safe_save.py`:

```python
def safe_save_xlsx(wb, path):
    tmp = path + '.tmp'
    wb.save(tmp)
    try:
        os.replace(tmp, path)
    except PermissionError:
        alt = path.replace('.xlsx', '_v2.xlsx')
        os.replace(tmp, alt)
        print(f'Original locked; saved to {alt}')
        return alt
    return path
```

## LibreOffice not installed on Windows

`recalc.py` from the xlsx skill uses Unix sockets (AF_UNIX), unavailable on Windows.

Fallback: don't recalc formulas; rely on Excel to recalc on first open. Verify formula strings via openpyxl load:

```python
from openpyxl import load_workbook
wb = load_workbook(path)
for sn in wb.sheetnames:
    ws = wb[sn]
    for row in ws.iter_rows():
        for c in row:
            if isinstance(c.value, str) and c.value.startswith('='):
                # syntactic check — does range exist?
                ...
```

Bare minimum: count formulas, sample a few for shape.

## Distance / travel-time unknown for a route

If we can't determine km/min between two points:
- Leave cell blank (formulas show "-" via custom number format)
- Annotate "verify on day" in Notes column
- Don't fabricate values

## Currency rate fetch fails

- Fall back to last-known rate hardcoded in `trips/<slug>/data.json`
- Add ⚠️ warning to Budget sheet: "Rate from YYYY-MM-DD — recheck before booking"

## File path with non-ASCII (Vietnamese folder names, emoji)

Always use raw strings + UTF-8:

```python
path = r'C:\Users\peter\Downloads\📅 Booking Strategy.docx'  # this works
```

If invoking subprocess, ensure encoding:

```python
subprocess.run([...], encoding='utf-8', errors='replace')
```

## Final deliverable check

After build, do a sanity check:

```python
assert os.path.getsize(xlsx_path) > 50_000, "xlsx too small — build failure?"
assert os.path.getsize(docx_path) > 500_000, "docx too small — images missing?"
```

50 KB xlsx = no real content. 500 KB docx = no embedded images.

## User-facing report

At end, always print:
1. Output file paths (clickable `file://` URLs on Windows)
2. Count of sheets emitted + formulas verified
3. Count of images embedded + skipped
4. List of `unvalidated.md` items for manual review

This makes pipeline failures visible — better than silent partial outputs.
