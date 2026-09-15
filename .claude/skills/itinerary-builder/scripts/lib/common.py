"""Shared utilities for itinerary-builder scripts.

Layout:
- SKILL_ROOT  : where this skill lives (scripts/lib/.. /..)
- TRIPS_ROOT  : where trip data + outputs live. Defaults to {CWD}/trips
                so the skill is portable across projects. Override via
                env var ITINERARY_TRIPS_ROOT.

Run scripts from a project root that has (or will have) a `trips/` dir.
"""
import sys
import io
import os
import json

# Ensure UTF-8 stdout on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SKILL_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

def _resolve_trips_root():
    env = os.environ.get('ITINERARY_TRIPS_ROOT')
    if env:
        return os.path.abspath(env)
    cwd_trips = os.path.abspath(os.path.join(os.getcwd(), 'trips'))
    legacy = os.path.join(SKILL_ROOT, 'trips')
    if os.path.isdir(cwd_trips) or not os.path.isdir(legacy):
        return cwd_trips
    return legacy

TRIPS_ROOT = _resolve_trips_root()

def trip_dir(slug):
    return os.path.join(TRIPS_ROOT, slug)

def img_dir(slug):
    p = os.path.join(trip_dir(slug), 'images')
    os.makedirs(p, exist_ok=True)
    return p

def out_xlsx(slug):
    return os.path.join(trip_dir(slug), f'{slug}_Booking_Strategy.xlsx')

def out_docx(slug):
    return os.path.join(trip_dir(slug), f'{slug}_Trip_Guide.docx')

def load_data(slug):
    path = os.path.join(trip_dir(slug), 'data.json')
    if not os.path.exists(path):
        raise FileNotFoundError(f'No data.json at {path}. Run the orchestrator first or copy from templates/.')
    with open(path, encoding='utf-8') as f:
        return json.load(f)

def save_data(slug, data):
    os.makedirs(trip_dir(slug), exist_ok=True)
    path = os.path.join(trip_dir(slug), 'data.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path

def log_unvalidated(slug, fact, reason):
    path = os.path.join(trip_dir(slug), 'unvalidated.md')
    with open(path, 'a', encoding='utf-8') as f:
        f.write(f'- **{fact}** — {reason}\n')

def derive_distance_matrix(data):
    """Augment distance_matrix with base→place rows derived from places[].

    Explicit rows always win. Shared by stage_runner (stage 6) and
    build_workbook so both agree on the derived rows. De-duplication is exact
    (case-insensitive) — a substring match wrongly collapsed distinct places
    (e.g. "Beach" vs "My Khe Beach") and broke on empty `to` values.
    """
    base = data.get('metadata', {}).get('base_hotel_area', 'Base hotel')
    dm = list(data.get('distance_matrix', []))
    existing_to = {(row.get('to') or '').strip().casefold() for row in dm}
    for p in data.get('places', []):
        name = (p.get('name') or '').strip()
        if not name or p.get('distance_km_from_base') is None:
            continue
        if name.casefold() in existing_to:
            continue
        dm.append({
            'from': base,
            'to': name,
            'km': p['distance_km_from_base'],
            'min': p.get('travel_min_from_base', 0),
            'note': '[derived from places]',
        })
        existing_to.add(name.casefold())
    return dm


def derive_indoor_bank(data):
    """Augment weather_plan_b.indoor_bank with places[] flagged indoor=true.

    Explicit rows win; de-duplication is exact (case-insensitive). Shared by
    stage_runner (stage 6) and build_workbook.
    """
    wb_data = data.get('weather_plan_b', {}) or {}
    bank = list(wb_data.get('indoor_bank', []))
    existing = {(b.get('name') or '').strip().casefold() for b in bank}
    for p in data.get('places', []):
        if not p.get('indoor'):
            continue
        name = (p.get('name') or '').strip()
        if not name or name.casefold() in existing:
            continue
        local_cost = p.get('price_local')
        if local_cost is None:
            local_cost = p.get('price_vnd')
        bank.append({
            'name': name,
            'area': p.get('area', ''),
            'local_cost': local_cost,
            'duration': p.get('duration', ''),
            'notes': (p.get('description') or '')[:120],
        })
        existing.add(name.casefold())
    return bank


def safe_save_xlsx(wb, path):
    """Atomic save with fallback if file locked.

    os.replace is atomic on same fs (POSIX + Windows). Never remove the
    original first — if replace fails, we'd lose data.
    """
    tmp = path + '.tmp'
    wb.save(tmp)
    try:
        os.replace(tmp, path)
        return path
    except (PermissionError, OSError):
        alt = path.replace('.xlsx', '_new.xlsx')
        try:
            os.replace(tmp, alt)
        except (PermissionError, OSError):
            # leave .tmp in place rather than silently delete user work
            print(f'⚠️ Both target and _new locked. Output left at {tmp}')
            return tmp
        print(f'⚠️ Original locked, saved to {alt}')
        return alt
