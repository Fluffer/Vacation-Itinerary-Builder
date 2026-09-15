"""Write the fact-validation checklist for a trip.

This script does NOT call a model itself — MCP libraries are only available
inside Claude. It writes:
  - trips/<slug>/validate_prompts.md — one prompt per high-stakes fact
  - trips/<slug>/unvalidated.md       — the pending list (also what run_all prints)

Claude then sends each prompt to the MCP `second_opinion` tools (per-call
timeout 60s, cascade deepseek-pro → deepseek-flash → glm → minimax) and writes
the confirmed values back into data.json.

Usage:
    python validate_facts.py --slug <slug>
    python validate_facts.py --slug-dir <path-to-trip-directory>
"""
import sys
import os
import argparse
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.common import trip_dir

# Facts to always validate
CHECKS = [
    ('visa', 'Visa rule for {passport} passport to {destination}: number of days visa-free, e-visa needed?'),
    ('weather', 'Weather profile in {destination} during {dates_start} to {dates_end}: typical conditions, storm risk?'),
    ('plug', 'Power plug standard in {destination_country}; does {origin_plug} fit?'),
    ('fx_rate', 'Current FX rate {currency_code} per 1 SGD as of today?'),
    ('airport_buffer', 'Recommended international check-in window for {airline} departing {destination_airport}?'),
]


def resolve_trip_path(slug, slug_dir):
    """Return (slug, absolute trip directory) from --slug or --slug-dir.

    When --slug-dir is given it is used verbatim, so a trip outside the resolved
    ITINERARY_TRIPS_ROOT works.
    """
    if slug_dir:
        trip_path = os.path.abspath(slug_dir)
        return os.path.basename(os.path.normpath(trip_path)), trip_path
    return slug, trip_dir(slug)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--slug', help='Trip slug (folder name under trips/)')
    ap.add_argument('--slug-dir', help='Direct path to the trip folder (alternative to --slug)')
    args = ap.parse_args()

    if not args.slug and not args.slug_dir:
        ap.error('one of --slug or --slug-dir is required')

    slug, trip_path = resolve_trip_path(args.slug, args.slug_dir)
    data_path = os.path.join(trip_path, 'data.json')
    if not os.path.exists(data_path):
        print(f'ERROR: no data.json at {data_path}', file=sys.stderr)
        return 1
    with open(data_path, encoding='utf-8') as f:
        data = json.load(f)
    meta = data.get('metadata', {})

    prompts_path = os.path.join(trip_path, 'validate_prompts.md')
    with open(prompts_path, 'w', encoding='utf-8') as f:
        f.write(f'# Validation Prompts — {slug}\n\n')
        f.write('Send each block to an MCP second_opinion tool. '
                'Write the validated value back into data.json.\n\n')
        for key, tmpl in CHECKS:
            try:
                question = tmpl.format(
                    passport=meta.get('passport', '?'),
                    destination=meta.get('destination', '?'),
                    dates_start=meta.get('dates_start', '?'),
                    dates_end=meta.get('dates_end', '?'),
                    destination_country=meta.get('destination', '?'),
                    origin_plug=meta.get('origin_plug', 'Type G (SG/UK)'),
                    currency_code=meta.get('currency_code', '?'),
                    airline=meta.get('airline', '?'),
                    destination_airport=meta.get('destination_airport', '?'),
                )
            except (KeyError, IndexError, ValueError) as e:
                question = f'(template error: {e})'
            f.write(f'## {key}\n\n{question}\n\n')

    # This script cannot validate on its own (MCP tools are only available inside
    # Claude), so record the still-unvalidated facts for review/flagging. This is
    # what run_all.py prints and what the docs call unvalidated.md.
    uv_path = os.path.join(trip_path, 'unvalidated.md')
    with open(uv_path, 'w', encoding='utf-8') as f:
        f.write(f'# Unvalidated facts — {slug}\n\n')
        f.write('Validate these via the MCP second_opinion tools (Ollama cascade: '
                'deepseek-pro → deepseek-flash → glm → minimax), then write the '
                'results back into data.json. Flag anything unconfirmed in the output.\n\n')
        for key, _ in CHECKS:
            f.write(f'- **{key}**\n')

    print(f'Wrote validation checklist to: {prompts_path}')
    print(f'Wrote pending-fact list to:   {uv_path}')
    print('Run validation interactively via Claude (uses MCP second_opinion tools).')
    print('Write results back to data.json under "visa", "validated_facts" etc.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
