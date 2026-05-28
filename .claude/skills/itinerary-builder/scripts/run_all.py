"""Orchestrator — run the full pipeline end-to-end.

Assumes trips/<slug>/data.json already exists. Use Claude or manual workflow
to populate it from a source draft document.

Usage:
    python scripts/run_all.py --slug da-nang

Steps:
    1. validate_facts.py    — writes validate_prompts.md
    2. fetch_images.py      — downloads photos
    3. normalize_images.py  — fixes JPEG markers
    4. build_map.py         — renders maps
    5. build_workbook.py    — Excel
    6. build_docx.py        — Word
    7. copy outputs to user Downloads
"""
import sys, os, argparse, subprocess, shutil, json
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.common import load_data, out_xlsx, out_docx, trip_dir

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

class PipelineError(RuntimeError):
    pass

def run(script, slug, *extra, required=True):
    cmd = [sys.executable, os.path.join(SCRIPT_DIR, script), '--slug', slug, *extra]
    print(f'\n=== {script} ===')
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        msg = f'{script} failed with exit code {result.returncode}'
        if required:
            raise PipelineError(msg)
        print(f'⚠️ {msg} — continuing (non-required step)')

def validate_metadata(data):
    """Fail fast on malformed dates / missing required fields."""
    meta = data.get('metadata', {})
    required = ['destination', 'dates_start', 'dates_end', 'passport']
    missing = [k for k in required if not meta.get(k)]
    if missing:
        raise PipelineError(f'metadata missing required fields: {missing}')
    for date_field in ('dates_start', 'dates_end'):
        try:
            datetime.strptime(meta[date_field], '%Y-%m-%d')
        except ValueError:
            raise PipelineError(
                f'metadata.{date_field}="{meta[date_field]}" not ISO YYYY-MM-DD')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--slug', required=True)
    ap.add_argument('--skip-images', action='store_true')
    ap.add_argument('--skip-maps', action='store_true')
    ap.add_argument('--skip-validate', action='store_true',
                    help='Skip Ollama fact validation step')
    ap.add_argument('--downloads-copy', action='store_true',
                    help='Copy final xlsx + docx to user Downloads folder')
    args = ap.parse_args()

    # Verify data.json + metadata
    try:
        data = load_data(args.slug)
    except FileNotFoundError as e:
        print(f'ERROR: {e}')
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f'ERROR: data.json is not valid JSON — {e}')
        sys.exit(1)

    try:
        validate_metadata(data)
    except PipelineError as e:
        print(f'ERROR: {e}')
        sys.exit(1)

    try:
        if not args.skip_validate:
            run('validate_facts.py', args.slug, required=False)
        if not args.skip_images:
            run('fetch_images.py', args.slug, required=False)
            run('normalize_images.py', args.slug, required=False)
        if not args.skip_maps:
            run('build_map.py', args.slug, required=False)
        run('build_workbook.py', args.slug, required=True)
        run('build_docx.py', args.slug, required=True)
    except PipelineError as e:
        print(f'\nERROR: pipeline aborted — {e}')
        sys.exit(2)

    xlsx = out_xlsx(args.slug)
    docx = out_docx(args.slug)
    print(f'\n=== DONE ===')
    print(f'Excel:  {xlsx}  ({os.path.getsize(xlsx) if os.path.exists(xlsx) else "?"} bytes)')
    print(f'Word:   {docx}  ({os.path.getsize(docx) if os.path.exists(docx) else "?"} bytes)')

    if args.downloads_copy:
        dl = os.path.expanduser('~/Downloads')
        for src in (xlsx, docx):
            if os.path.exists(src):
                dst = os.path.join(dl, os.path.basename(src))
                shutil.copy2(src, dst)
                print(f'Copied → {dst}')

    # Print unvalidated items
    uv = os.path.join(trip_dir(args.slug), 'unvalidated.md')
    if os.path.exists(uv):
        print('\n⚠️ Unvalidated items (manual review):')
        print(open(uv, encoding='utf-8').read())

if __name__ == '__main__':
    main()
