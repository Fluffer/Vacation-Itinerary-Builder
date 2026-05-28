"""Fact-validate trip data via Ollama models w/ timeout + cascade fallback.

Models tried in order: deepseek-pro → deepseek-flash → glm → minimax.
Per-call timeout 60s. On all-fail, log to unvalidated.md and continue.

This module is invoked from run_all.py with the parsed trip data. It does NOT
import any MCP libraries — those are only available inside Claude. When running
standalone, this script flags claims as unvalidated.

When Claude is driving the skill, Claude itself should call the MCP
second_opinion tools and write validated facts back into data.json. This script
just lists what needs validation.
"""
import sys, os, argparse, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.common import load_data, save_data, log_unvalidated, trip_dir

# Facts to always validate
CHECKS = [
    ('visa', 'Visa rule for {passport} passport to {destination}: number of days visa-free, e-visa needed?'),
    ('weather', 'Weather profile in {destination} during {dates_start} to {dates_end}: typical conditions, storm risk?'),
    ('plug', 'Power plug standard in {destination_country}; does {origin_plug} fit?'),
    ('fx_rate', 'Current FX rate {currency_code} per 1 SGD as of today?'),
    ('airport_buffer', 'Recommended international check-in window for {airline} departing {destination_airport}?'),
]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--slug', required=True)
    ap.add_argument('--write-prompts', action='store_true',
                    help='Write per-fact prompts to validate_prompts.md for Claude to consume')
    args = ap.parse_args()

    data = load_data(args.slug)
    meta = data.get('metadata', {})

    prompts_path = os.path.join(trip_dir(args.slug), 'validate_prompts.md')
    with open(prompts_path, 'w', encoding='utf-8') as f:
        f.write(f'# Validation Prompts — {args.slug}\n\n')
        f.write('Send each block to an Ollama second_opinion tool. '
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
            except Exception as e:
                question = f'(template error: {e})'
            f.write(f'## {key}\n\n{question}\n\n')

    print(f'Wrote validation checklist to: {prompts_path}')
    print('Run validation interactively via Claude (uses MCP second_opinion tools).')
    print('Write results back to data.json under "visa", "validated_facts" etc.')

if __name__ == '__main__':
    main()
