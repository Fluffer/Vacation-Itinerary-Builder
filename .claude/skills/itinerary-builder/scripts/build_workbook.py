"""Build the multi-sheet Excel workbook from trips/<slug>/data.json.

Emits up to 14 sheets, conditionally on data presence. See
references/sheet_schemas.md.
"""
import sys, os, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.common import load_data, out_xlsx, safe_save_xlsx
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

ARIAL = 'Arial'
HEADER_FILL = PatternFill('solid', start_color='1F4E78')
HEADER_FONT = Font(name=ARIAL, bold=True, color='FFFFFF', size=11)
TITLE_FONT = Font(name=ARIAL, bold=True, color='FFFFFF', size=14)
TITLE_FILL = PatternFill('solid', start_color='2E75B6')
V2_FILL = PatternFill('solid', start_color='7030A0')
V3_FILL = PatternFill('solid', start_color='595959')
ALT_FILL = PatternFill('solid', start_color='F2F2F2')
WARN_FILL = PatternFill('solid', start_color='FFF2CC')
GOOD_FILL = PatternFill('solid', start_color='E2EFDA')
GEM_FILL = PatternFill('solid', start_color='FCE4D6')
PRICING_FILL = PatternFill('solid', start_color='548235')
SECTION_FILL = PatternFill('solid', start_color='305496')
DEFAULT_FONT = Font(name=ARIAL, size=10)
WRAP = Alignment(wrap_text=True, vertical='top')
CENTER = Alignment(horizontal='center', vertical='center', wrap_text=True)
LEFT = Alignment(horizontal='left', vertical='center', indent=1, wrap_text=True)
thin = Side(border_style='thin', color='BFBFBF')
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)

def style_header_row(ws, row, ncols):
    for c in range(1, ncols+1):
        cell = ws.cell(row=row, column=c)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = CENTER
        cell.border = BORDER

def write_section_title(ws, row, text, ncols, fill=TITLE_FILL):
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=ncols)
    c = ws.cell(row=row, column=1, value=text)
    c.font = TITLE_FONT
    c.fill = fill
    c.alignment = LEFT
    ws.row_dimensions[row].height = 24

def write_subsection_band(ws, row, text, ncols, color='305496'):
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=ncols)
    c = ws.cell(row=row, column=1, value=text)
    c.font = Font(name=ARIAL, bold=True, size=11, color='FFFFFF')
    c.fill = PatternFill('solid', start_color=color)
    c.alignment = LEFT
    ws.row_dimensions[row].height = 20

def set_col_widths(ws, widths):
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

def write_itinerary(ws, start_row, day_blocks, header_color):
    ITIN_HEADERS = ['Time', 'Activity', 'From -> To', 'Dist (km)', 'Travel (min)',
                    'Cost (local)', 'Cost (SGD)', 'Notes', '✓']
    r = start_row
    for day in day_blocks:
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=9)
        c = ws.cell(row=r, column=1, value=day['day_label'])
        c.font = Font(name=ARIAL, bold=True, size=12, color='FFFFFF')
        c.fill = PatternFill('solid', start_color=header_color)
        c.alignment = LEFT
        ws.row_dimensions[r].height = 22
        r += 1
        for j, h in enumerate(ITIN_HEADERS, 1):
            ws.cell(row=r, column=j, value=h)
        style_header_row(ws, r, len(ITIN_HEADERS))
        r += 1
        data_start = r
        for i, row in enumerate(day['rows']):
            ws.cell(row=r, column=1, value=row.get('time'))
            ws.cell(row=r, column=2, value=row.get('activity'))
            ws.cell(row=r, column=3, value=row.get('route', ''))
            km = row.get('km'); mn = row.get('min')
            local = row.get('cost_local', row.get('vnd'))  # back-compat
            sgd = row.get('sgd')
            ws.cell(row=r, column=4, value=km if km is not None else None).number_format = '0.0;[Red]0.0;"-"'
            ws.cell(row=r, column=5, value=mn if mn is not None else None).number_format = '0;[Red]0;"-"'
            ws.cell(row=r, column=6, value=local if local is not None else None).number_format = '#,##0;[Red](#,##0);"FREE"'
            ws.cell(row=r, column=7, value=sgd if sgd is not None else None).number_format = '"S$"#,##0;[Red]("S$"#,##0);"-"'
            ws.cell(row=r, column=8, value=row.get('notes', ''))
            ws.cell(row=r, column=9, value='☐')
            for cc in range(1, 10):
                cell = ws.cell(row=r, column=cc)
                cell.font = DEFAULT_FONT
                cell.alignment = WRAP if cc in (2, 3, 8) else CENTER
                cell.border = BORDER
                if i % 2 == 0:
                    cell.fill = ALT_FILL
            ws.row_dimensions[r].height = 26
            r += 1
        ws.cell(row=r, column=1, value='Day total').font = Font(name=ARIAL, bold=True)
        ws.cell(row=r, column=4, value=f'=SUM(D{data_start}:D{r-1})').number_format = '0.0;[Red]0.0;"-"'
        ws.cell(row=r, column=5, value=f'=SUM(E{data_start}:E{r-1})').number_format = '0;[Red]0;"-"'
        ws.cell(row=r, column=6, value=f'=SUM(F{data_start}:F{r-1})').number_format = '#,##0;[Red](#,##0);"-"'
        ws.cell(row=r, column=7, value=f'=SUM(G{data_start}:G{r-1})').number_format = '"S$"#,##0;[Red]("S$"#,##0);"-"'
        for cc in range(1, 10):
            cell = ws.cell(row=r, column=cc)
            cell.fill = GOOD_FILL
            cell.border = BORDER
            cell.font = Font(name=ARIAL, bold=True, size=10)
            cell.alignment = CENTER if cc in (4,5,6,7,9) else LEFT
        r += 2
    set_col_widths(ws, [9, 36, 22, 9, 10, 13, 12, 38, 5])

def write_kv_block(ws, start_row, kv_pairs, ncols=4):
    """Key-value layout: col 1 = key, cols 2-ncols merged = value."""
    r = start_row
    for k, v in kv_pairs:
        if k is None and v is None:
            r += 1
            continue
        if v is None:
            ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=ncols)
            c = ws.cell(row=r, column=1, value=k)
            c.font = Font(name=ARIAL, bold=True, size=11, color='1F4E78')
            c.alignment = LEFT
            ws.row_dimensions[r].height = 22
        else:
            kcell = ws.cell(row=r, column=1, value=k)
            kcell.font = Font(name=ARIAL, size=10, bold=True)
            kcell.fill = ALT_FILL
            kcell.border = BORDER
            kcell.alignment = Alignment(vertical='center', indent=1, wrap_text=True)
            ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=ncols)
            vc = ws.cell(row=r, column=2, value=str(v))
            vc.font = DEFAULT_FONT
            vc.alignment = WRAP
            vc.border = BORDER
            ws.row_dimensions[r].height = 24
        r += 1
    return r

def _pick(d, *keys, default=None):
    """Return first present key — supports schema migration without breaking
    legacy data.json that still uses *_vnd field names."""
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default

def derive_distance_matrix(data):
    """Augment distance_matrix with entries derivable from places[].

    Explicit distance_matrix rows always win. Auto-add base→place rows for
    places that have distance_km_from_base + travel_min_from_base but no
    matching matrix entry.
    """
    base = data.get('metadata', {}).get('base_hotel_area', 'Base hotel')
    dm = list(data.get('distance_matrix', []))
    existing_to = {row.get('to', '').lower() for row in dm}
    for p in data.get('places', []):
        name = p.get('name', '')
        if not name or p.get('distance_km_from_base') is None:
            continue
        # Skip if already present (loose substring match — generous)
        if any(name.lower() in t or t in name.lower() for t in existing_to):
            continue
        dm.append({
            'from': base,
            'to': name,
            'km': p['distance_km_from_base'],
            'min': p.get('travel_min_from_base', 0),
            'fare_local': None,
            'note': '[derived from places]',
        })
    return dm

def derive_indoor_bank(data):
    """Augment weather_plan_b.indoor_bank with places[] flagged indoor=true.

    Explicit indoor_bank rows win. Derived only when no matching name exists.
    """
    wb_data = data.get('weather_plan_b', {})
    bank = list(wb_data.get('indoor_bank', []))
    existing = {b.get('name', '').lower() for b in bank}
    for p in data.get('places', []):
        if not p.get('indoor'):
            continue
        if p.get('name', '').lower() in existing:
            continue
        bank.append({
            'name': p['name'],
            'area': p.get('area', ''),
            'local_cost': _pick(p, 'price_local', 'price_vnd'),
            'duration': p.get('duration', ''),
            'notes': p.get('description', '')[:120],
        })
    return bank

def build(slug):
    data = load_data(slug)
    meta = data.get('metadata', {})
    # Validate critical metadata up front
    for f in ('destination', 'dates_start', 'dates_end'):
        if not meta.get(f):
            raise ValueError(f'metadata.{f} is required')
    from datetime import datetime
    for f in ('dates_start', 'dates_end'):
        try:
            datetime.strptime(meta[f], '%Y-%m-%d')
        except ValueError:
            raise ValueError(f'metadata.{f}="{meta[f]}" must be ISO YYYY-MM-DD')

    wb = Workbook()
    wb.remove(wb.active)
    sheets_emitted = []
    currency = meta.get('currency_code', 'VND')
    rate = meta.get('fx_rate_to_sgd', 18500)

    # ===== Sheet 1: Overview =====
    ws = wb.create_sheet('1. Overview')
    ws.sheet_view.showGridLines = False
    dest = meta.get('destination', 'Trip')
    write_section_title(ws, 1, f'{dest} Trip Overview — {meta.get("dates_start", "")} → {meta.get("dates_end", "")}', 4)
    rows = [
        ('Trip dates', f'{meta.get("dates_start","")} → {meta.get("dates_end","")}'),
        ('Nights / Days', f'{meta.get("nights","?")} nights'),
        ('Origin', f'{meta.get("origin","")} — {meta.get("airline","")}'),
        ('Destination', dest),
        ('Outbound flight', meta.get('outbound_arrive_local', '')),
        ('Return flight', meta.get('return_depart_local', '')),
        ('Passport', meta.get('passport', '')),
        ('Visa', (data.get('visa') or {}).get('rule', 'Verify before travel')),
        ('Base hotel', meta.get('base_hotel_area', '')),
        ('Travelers', f'{meta.get("pax",1)} pax'),
        ('Currency', f'{currency} ~{rate} per 1 SGD'),
        ('Climate', meta.get('climate_summary', '')),
        ('Power', meta.get('power_plug', '')),
        ('Tap water', meta.get('tap_water', 'Verify locally')),
        ('Tipping', meta.get('tipping', '')),
        ('Emergency', meta.get('emergency', '')),
    ]
    next_r = write_kv_block(ws, 3, rows, ncols=4)

    # Risk flags block
    flags = data.get('risk_flags', [])
    if flags:
        next_r += 1
        write_section_title(ws, next_r, '⚠️ Risk Flags & Mitigations', 4, fill=PatternFill('solid', start_color='C00000'))
        next_r += 2
        for label, note in flags:
            kcell = ws.cell(row=next_r, column=1, value=label)
            kcell.font = Font(name=ARIAL, size=10, bold=True)
            kcell.fill = WARN_FILL
            kcell.border = BORDER
            kcell.alignment = Alignment(vertical='center', indent=1, wrap_text=True)
            ws.merge_cells(start_row=next_r, start_column=2, end_row=next_r, end_column=4)
            vc = ws.cell(row=next_r, column=2, value=note)
            vc.font = DEFAULT_FONT
            vc.alignment = WRAP
            vc.border = BORDER
            ws.row_dimensions[next_r].height = 28
            next_r += 1

    # Variant pointer banner
    next_r += 1
    ws.merge_cells(start_row=next_r, start_column=1, end_row=next_r, end_column=4)
    pc = ws.cell(row=next_r, column=1,
                 value='📌 Three itinerary variants — adjacent tabs: Sheet 3 (v1 standard) · Sheet 4 (v2 relaxed) · Sheet 5 (v3 bad-weather) · Sheet 6 (v1 vs v2 compare)')
    pc.font = Font(name=ARIAL, bold=True, color='FFFFFF', size=11)
    pc.fill = V2_FILL
    pc.alignment = LEFT
    ws.row_dimensions[next_r].height = 24

    set_col_widths(ws, [22, 30, 30, 30])
    sheets_emitted.append('1. Overview')

    # ===== Sheet 2: Booking Timeline =====
    timeline = data.get('booking_timeline', [])
    if timeline:
        ws = wb.create_sheet('2. Booking Timeline')
        ws.sheet_view.showGridLines = False
        write_section_title(ws, 1, f'📅 Booking Strategy Timeline (relative to {meta.get("dates_start","trip")})', 4)
        r = 3
        for j, h in enumerate(['Window', 'Lead time', 'Action', 'Why'], 1):
            ws.cell(row=r, column=j, value=h)
        style_header_row(ws, r, 4)
        r += 1
        for i, row in enumerate(timeline):
            ws.cell(row=r, column=1, value=row.get('window', ''))
            ws.cell(row=r, column=2, value=row.get('lead_time', ''))
            ws.cell(row=r, column=3, value=row.get('action', ''))
            ws.cell(row=r, column=4, value=row.get('why', ''))
            for cc in range(1, 5):
                cell = ws.cell(row=r, column=cc)
                cell.font = DEFAULT_FONT
                cell.alignment = WRAP
                cell.border = BORDER
                if i % 2 == 0:
                    cell.fill = ALT_FILL
            ws.row_dimensions[r].height = 30
            r += 1
        set_col_widths(ws, [22, 14, 50, 44])
        sheets_emitted.append('2. Booking Timeline')

    # ===== Sheet 3: Daily Itinerary v1 =====
    itin = data.get('itinerary', {})
    if itin.get('v1_standard'):
        ws = wb.create_sheet('3. v1 Daily Itinerary')
        ws.sheet_view.showGridLines = False
        write_section_title(ws, 1, '🗺️ v1 Standard Pace Itinerary', 9)
        write_itinerary(ws, 3, itin['v1_standard'], '2E75B6')
        sheets_emitted.append('3. Daily Itinerary')

    # ===== Sheet 4: Accommodation =====
    hotels = data.get('hotels', [])
    if hotels:
        ws = wb.create_sheet('7. Accommodation')
        ws.sheet_view.showGridLines = False
        write_section_title(ws, 1, f'🏨 Accommodation Options — {meta.get("base_hotel_area","")}', 6)
        r = 3
        for j, h in enumerate(['Hotel', 'Tier', 'Rating', 'SGD/night (low)', 'SGD/night (high)', 'Notes'], 1):
            ws.cell(row=r, column=j, value=h)
        style_header_row(ws, r, 6)
        r += 1
        for i, h in enumerate(hotels):
            ws.cell(row=r, column=1, value=h.get('name', ''))
            ws.cell(row=r, column=2, value=h.get('tier', ''))
            ws.cell(row=r, column=3, value=h.get('rating', ''))
            ws.cell(row=r, column=4, value=h.get('sgd_low')).number_format = '"S$"#,##0'
            ws.cell(row=r, column=5, value=h.get('sgd_high')).number_format = '"S$"#,##0'
            ws.cell(row=r, column=6, value=h.get('notes', ''))
            for cc in range(1, 7):
                cell = ws.cell(row=r, column=cc)
                cell.font = DEFAULT_FONT
                cell.alignment = WRAP if cc in (1, 6) else CENTER
                cell.border = BORDER
                if i % 2 == 0:
                    cell.fill = ALT_FILL
            ws.row_dimensions[r].height = 32
            r += 1
        r += 1
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
        rec = ws.cell(row=r, column=1,
                      value=data.get('accommodation_recommendation',
                                     f'Recommendation: Single hotel for {meta.get("nights","?")} nights. Free Cancellation rate on Agoda/Booking.'))
        rec.font = Font(name=ARIAL, italic=True, bold=True, size=10)
        rec.fill = GOOD_FILL
        rec.alignment = WRAP
        rec.border = BORDER
        ws.row_dimensions[r].height = 30
        set_col_widths(ws, [32, 11, 8, 18, 18, 50])
        sheets_emitted.append('4. Accommodation')

    # ===== Sheet 5: Food, Spas, Nightlife =====
    places = data.get('places', [])
    foods = [p for p in places if p.get('category') == 'food']
    spas = [p for p in places if p.get('category') == 'spa']
    nightlife = [p for p in places if p.get('category') == 'nightlife']
    if foods or spas or nightlife:
        ws = wb.create_sheet('8. Food, Spas, Nightlife')
        ws.sheet_view.showGridLines = False
        write_section_title(ws, 1, '🍜 Food / 💆 Spa / 🍻 Nightlife', 5)
        r = 3
        def sub(label, items, color):
            nonlocal r
            if not items:
                return
            write_subsection_band(ws, r, label, 5, color=color)
            r += 1
            for j, h in enumerate(['Place', 'Area', f'Price ({currency})', 'Notes', 'When'], 1):
                ws.cell(row=r, column=j, value=h)
            style_header_row(ws, r, 5)
            r += 1
            for i, p in enumerate(items):
                ws.cell(row=r, column=1, value=p.get('name', ''))
                ws.cell(row=r, column=2, value=p.get('area', ''))
                ws.cell(row=r, column=3, value=p.get('price_label') or _pick(p, 'price_local', 'price_vnd', default=''))
                ws.cell(row=r, column=4, value=p.get('description', ''))
                ws.cell(row=r, column=5, value=p.get('when', ''))
                for cc in range(1, 6):
                    cell = ws.cell(row=r, column=cc)
                    cell.font = DEFAULT_FONT
                    cell.alignment = WRAP
                    cell.border = BORDER
                    if i % 2 == 0:
                        cell.fill = ALT_FILL
                ws.row_dimensions[r].height = 36
                r += 1
            r += 1
        sub('🍜 Food — Must-Try', foods, '2E75B6')
        sub('💆 Spas', spas, '7030A0')
        sub('🍻 Nightlife', nightlife, '548235')
        set_col_widths(ws, [30, 22, 18, 60, 18])
        sheets_emitted.append('5. Food, Spas, Nightlife')

    # ===== Sheet 6: Practical Info =====
    practical = data.get('practical_info', [])
    if practical:
        ws = wb.create_sheet('13. Practical Info')
        ws.sheet_view.showGridLines = False
        write_section_title(ws, 1, '🧭 Practical Info', 4)
        write_kv_block(ws, 3, practical, ncols=4)
        set_col_widths(ws, [26, 30, 30, 30])
        sheets_emitted.append('6. Practical Info')

    # ===== Sheet 7: Pre-Departure Checklist =====
    checklist = data.get('checklist', [])
    if checklist:
        ws = wb.create_sheet('14. Pre-Departure Checklist')
        ws.sheet_view.showGridLines = False
        write_section_title(ws, 1, '✅ Pre-Departure Checklist', 3)
        r = 3
        for j, h in enumerate(['Category', 'Item', 'Done?'], 1):
            ws.cell(row=r, column=j, value=h)
        style_header_row(ws, r, 3)
        r += 1
        for i, row in enumerate(checklist):
            ws.cell(row=r, column=1, value=row.get('category', ''))
            ws.cell(row=r, column=2, value=row.get('item', ''))
            ws.cell(row=r, column=3, value='☐')
            for cc in range(1, 4):
                cell = ws.cell(row=r, column=cc)
                cell.font = DEFAULT_FONT
                cell.alignment = WRAP if cc == 2 else CENTER
                cell.border = BORDER
                if i % 2 == 0:
                    cell.fill = ALT_FILL
            ws.row_dimensions[r].height = 24
            r += 1
        set_col_widths(ws, [18, 70, 10])
        sheets_emitted.append('7. Pre-Departure Checklist')

    # ===== Sheet 8: Budget =====
    budget = data.get('budget', {})
    if budget:
        ws = wb.create_sheet('12. Budget')
        ws.sheet_view.showGridLines = False
        write_section_title(ws, 1, '💰 Budget Estimate per Person', 5)
        ws.cell(row=3, column=1, value=f'Exchange rate ({currency} per 1 SGD)').font = Font(name=ARIAL, bold=True)
        rate_val = _pick(budget, 'rate_local_per_sgd', 'rate_vnd_per_sgd', default=rate)
        rc = ws.cell(row=3, column=2, value=rate_val)
        rc.font = Font(name=ARIAL, color='0000FF', bold=True); rc.fill = WARN_FILL
        rc.number_format = '#,##0'; rc.border = BORDER
        ws.cell(row=3, column=3, value='← edit to update all SGD figures').font = Font(name=ARIAL, italic=True, color='666666')
        r = 5
        for j, h in enumerate(['Category', f'{currency} (low)', f'{currency} (high)', 'SGD (low)', 'SGD (high)'], 1):
            ws.cell(row=r, column=j, value=h)
        style_header_row(ws, r, 5)
        r += 1; start_data = r
        for cat in budget.get('categories', []):
            ws.cell(row=r, column=1, value=cat['category']).font = DEFAULT_FONT
            low = _pick(cat, 'low_local', 'low_vnd', default=0)
            high = _pick(cat, 'high_local', 'high_vnd', default=0)
            cl = ws.cell(row=r, column=2, value=low); cl.font = Font(name=ARIAL, color='0000FF')
            ch = ws.cell(row=r, column=3, value=high); ch.font = Font(name=ARIAL, color='0000FF')
            cl.number_format = '#,##0'; ch.number_format = '#,##0'
            ws.cell(row=r, column=4, value=f'=B{r}/$B$3').number_format = '"S$"#,##0'
            ws.cell(row=r, column=5, value=f'=C{r}/$B$3').number_format = '"S$"#,##0'
            for cc in range(1, 6):
                ws.cell(row=r, column=cc).border = BORDER
            r += 1
        end_data = r - 1
        subtotal_row = r
        ws.cell(row=r, column=1, value='Ground costs subtotal').font = Font(name=ARIAL, bold=True)
        ws.cell(row=r, column=2, value=f'=SUM(B{start_data}:B{end_data})').number_format = '#,##0'
        ws.cell(row=r, column=3, value=f'=SUM(C{start_data}:C{end_data})').number_format = '#,##0'
        ws.cell(row=r, column=4, value=f'=B{r}/$B$3').number_format = '"S$"#,##0'
        ws.cell(row=r, column=5, value=f'=C{r}/$B$3').number_format = '"S$"#,##0'
        for cc in range(1, 6):
            ws.cell(row=r, column=cc).fill = GOOD_FILL
            ws.cell(row=r, column=cc).font = Font(name=ARIAL, bold=True, size=10)
            ws.cell(row=r, column=cc).border = BORDER
        r += 2
        write_subsection_band(ws, r, 'Flight & hotel (direct SGD)', 5, color='305496')
        r += 1
        for j, h in enumerate(['Category', '', '', 'SGD (low)', 'SGD (high)'], 1):
            ws.cell(row=r, column=j, value=h)
        style_header_row(ws, r, 5)
        r += 1
        flight_row = r
        ws.cell(row=r, column=1, value='Flights return')
        ws.cell(row=r, column=4, value=budget.get('flight_sgd_low', 0)).number_format = '"S$"#,##0'
        ws.cell(row=r, column=5, value=budget.get('flight_sgd_high', 0)).number_format = '"S$"#,##0'
        for cc in range(1, 6):
            ws.cell(row=r, column=cc).border = BORDER; ws.cell(row=r, column=cc).font = DEFAULT_FONT
        r += 1
        hotel_row = r
        ws.cell(row=r, column=1, value=f'Hotel ({meta.get("nights","?")} nights)')
        ws.cell(row=r, column=4, value=budget.get('hotel_sgd_low', 0)).number_format = '"S$"#,##0'
        ws.cell(row=r, column=5, value=budget.get('hotel_sgd_high', 0)).number_format = '"S$"#,##0'
        for cc in range(1, 6):
            ws.cell(row=r, column=cc).border = BORDER; ws.cell(row=r, column=cc).font = DEFAULT_FONT
        r += 1
        ws.cell(row=r, column=1, value='GRAND TOTAL (per person)').font = Font(name=ARIAL, bold=True, color='FFFFFF')
        ws.cell(row=r, column=4, value=f'=D{subtotal_row}+D{flight_row}+D{hotel_row}').number_format = '"S$"#,##0'
        ws.cell(row=r, column=5, value=f'=E{subtotal_row}+E{flight_row}+E{hotel_row}').number_format = '"S$"#,##0'
        for cc in range(1, 6):
            ws.cell(row=r, column=cc).fill = TITLE_FILL
            ws.cell(row=r, column=cc).font = Font(name=ARIAL, bold=True, color='FFFFFF', size=11)
            ws.cell(row=r, column=cc).border = BORDER
        set_col_widths(ws, [42, 16, 16, 14, 14])
        sheets_emitted.append('8. Budget')

    # ===== Sheet 9: Relaxed Pace v2 =====
    if itin.get('v2_relaxed'):
        ws = wb.create_sheet('4. v2 Relaxed Pace')
        ws.sheet_view.showGridLines = False
        write_section_title(ws, 1, '🛋️ Relaxed Pace v2 — Less-Touristy', 9, fill=V2_FILL)
        write_itinerary(ws, 3, itin['v2_relaxed'], '7030A0')
        sheets_emitted.append('9. Relaxed Pace v2')

    # ===== Sheet 10: Hidden Gems & Swaps =====
    gems = data.get('hidden_gems_categorized', {})
    if gems:
        ws = wb.create_sheet('9. Hidden Gems & Swaps')
        ws.sheet_view.showGridLines = False
        write_section_title(ws, 1, '💎 Hidden Gems & Anti-Tourist Swaps', 6, fill=PatternFill('solid', start_color='C65911'))
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=6)
        sub = ws.cell(row=2, column=1,
                      value=f'All vetted as light-traffic vs the standard tourist circuit. Distance from {meta.get("base_hotel_area","base hotel")}.')
        sub.font = Font(name=ARIAL, italic=True, size=10); sub.alignment = LEFT
        r = 4
        for cat_name, items in gems.items():
            write_subsection_band(ws, r, cat_name, 6, color='C65911')
            r += 1
            for j, h in enumerate(['Place', 'Distance', 'Travel time', 'Why it stays quiet', 'Notes / When', 'Tried?'], 1):
                ws.cell(row=r, column=j, value=h)
            style_header_row(ws, r, 6)
            r += 1
            for i, g in enumerate(items):
                ws.cell(row=r, column=1, value=g.get('name', ''))
                ws.cell(row=r, column=2, value=g.get('distance', ''))
                ws.cell(row=r, column=3, value=g.get('travel_time', ''))
                ws.cell(row=r, column=4, value=g.get('why_quiet', ''))
                ws.cell(row=r, column=5, value=g.get('notes', ''))
                ws.cell(row=r, column=6, value='☐')
                for cc in range(1, 7):
                    cell = ws.cell(row=r, column=cc)
                    cell.font = DEFAULT_FONT
                    cell.alignment = WRAP
                    cell.border = BORDER
                    if i % 2 == 0:
                        cell.fill = ALT_FILL
                ws.row_dimensions[r].height = 38
                r += 1
            r += 1
        set_col_widths(ws, [28, 18, 14, 38, 32, 8])
        sheets_emitted.append('10. Hidden Gems & Swaps')

    # ===== Sheet 11: Distance Matrix =====
    dm = derive_distance_matrix(data)
    if dm:
        ws = wb.create_sheet('11. Distance Matrix')
        ws.sheet_view.showGridLines = False
        write_section_title(ws, 1, '🗺️ Distance & Travel-Time Reference Matrix', 5,
                            fill=SECTION_FILL)
        r = 4
        for j, h in enumerate(['From', 'To', 'Distance (km)', 'Travel time (min)', 'Typical fare'], 1):
            ws.cell(row=r, column=j, value=h)
        style_header_row(ws, r, 5)
        r += 1
        for i, row in enumerate(dm):
            ws.cell(row=r, column=1, value=row['from'])
            ws.cell(row=r, column=2, value=row['to'])
            ws.cell(row=r, column=3, value=row['km']).number_format = '0.0'
            ws.cell(row=r, column=4, value=row['min']).number_format = '0'
            fare = _pick(row, 'fare_local', 'fare_vnd', default='')
            ws.cell(row=r, column=5, value=fare).number_format = '#,##0'
            for cc in range(1, 6):
                cell = ws.cell(row=r, column=cc)
                cell.font = DEFAULT_FONT
                cell.alignment = WRAP if cc < 3 else CENTER
                cell.border = BORDER
                if i % 2 == 0:
                    cell.fill = ALT_FILL
            r += 1
        # Transport tips block
        tips = data.get('transport_tips', [])
        if tips:
            r += 1
            write_subsection_band(ws, r, '🚕 Transport Tips', 5, color='305496')
            r += 1
            for t in tips:
                ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=5)
                c = ws.cell(row=r, column=1, value=f'• {t}')
                c.font = DEFAULT_FONT
                c.alignment = WRAP
                c.border = BORDER
                ws.row_dimensions[r].height = 22
                r += 1
        set_col_widths(ws, [28, 32, 14, 16, 22])
        sheets_emitted.append('11. Distance Matrix')

    # ===== Sheet 12: v1 vs v2 Compare =====
    compare = data.get('v1_v2_compare', [])
    if compare:
        ws = wb.create_sheet('6. v1 vs v2 Compare')
        ws.sheet_view.showGridLines = False
        write_section_title(ws, 1, '⚖️ v1 Standard vs v2 Relaxed Less-Touristy', 4, fill=V2_FILL)
        r = 3
        for j, h in enumerate(['Item', 'v1 — Standard', 'v2 — Relaxed Less-Touristy', 'Why change'], 1):
            ws.cell(row=r, column=j, value=h)
        style_header_row(ws, r, 4)
        r += 1
        for i, row in enumerate(compare):
            ws.cell(row=r, column=1, value=row.get('item', '')).font = Font(name=ARIAL, bold=True, size=10)
            ws.cell(row=r, column=2, value=row.get('v1', ''))
            ws.cell(row=r, column=3, value=row.get('v2', ''))
            ws.cell(row=r, column=4, value=row.get('why', ''))
            for cc in range(1, 5):
                cell = ws.cell(row=r, column=cc)
                if cc != 1:
                    cell.font = DEFAULT_FONT
                cell.alignment = WRAP
                cell.border = BORDER
                if i % 2 == 0:
                    cell.fill = ALT_FILL
            ws.row_dimensions[r].height = 40
            r += 1
        set_col_widths(ws, [20, 38, 42, 36])
        sheets_emitted.append('12. v1 vs v2 Compare')

    # ===== Sheet 13: Activity Pricing =====
    pricing = data.get('activity_pricing', [])
    if pricing:
        ws = wb.create_sheet('10. Activity Pricing')
        ws.sheet_view.showGridLines = False
        write_section_title(ws, 1, '💵 Activity Pricing — Pick ONE Bundle Per Activity', 7,
                            fill=PRICING_FILL)
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=7)
        c = ws.cell(row=2, column=1,
                    value='⚠️ READ FIRST: For bundled activities PICK ONE PATH only — do NOT add rows. '
                          'GROUP DAY TOURS bundle transport + ticket + lunch in ONE price.')
        c.font = Font(name=ARIAL, italic=True, size=10); c.fill = WARN_FILL
        c.alignment = WRAP; c.border = BORDER
        ws.row_dimensions[2].height = 40
        r = 4
        for block in pricing:
            ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=7)
            c = ws.cell(row=r, column=1, value=block['category'])
            c.font = Font(name=ARIAL, bold=True, size=11, color='FFFFFF')
            c.fill = PRICING_FILL
            c.alignment = LEFT
            r += 1
            for j, h in enumerate(['Item', 'Channel', f'Local {currency}', 'SGD (≈)', 'Includes', '☐', 'Confirmed price'], 1):
                ws.cell(row=r, column=j, value=h)
            style_header_row(ws, r, 7)
            r += 1
            for i, path in enumerate(block.get('paths', []) + block.get('extras', [])):
                ws.cell(row=r, column=1, value=path['name']).font = Font(name=ARIAL, bold=True)
                ws.cell(row=r, column=2, value=path['channel'])
                per_pax = _pick(path, 'local_per_pax', 'vnd_per_pax', default=0)
                cv = ws.cell(row=r, column=3, value=per_pax)
                cv.number_format = '#,##0;[Red](#,##0);"FREE"'
                # Link FX to Budget sheet B3 so editing rate updates Pricing too.
                # Fallback to literal rate if Budget sheet not emitted.
                fx_ref = f"'12. Budget'!$B$3" if budget else rate
                ws.cell(row=r, column=4, value=f'=C{r}/{fx_ref}').number_format = '"S$"#,##0'
                ws.cell(row=r, column=5, value=path.get('includes', ''))
                ws.cell(row=r, column=6, value='☐')
                ws.cell(row=r, column=7, value='')
                for cc in range(1, 8):
                    cell = ws.cell(row=r, column=cc)
                    if cc != 1:
                        cell.font = DEFAULT_FONT
                    cell.alignment = WRAP if cc in (1, 5) else CENTER
                    cell.border = BORDER
                    if i % 2 == 0:
                        cell.fill = ALT_FILL
                ws.row_dimensions[r].height = 32
                r += 1
            r += 1
        set_col_widths(ws, [32, 22, 13, 12, 50, 6, 16])
        sheets_emitted.append('13. Activity Pricing')

    # ===== Sheet 14: Bad Weather Plan B =====
    wb_data = data.get('weather_plan_b', {})
    if wb_data.get('emit', False):
        ws = wb.create_sheet('5. v3 Bad Weather Plan B')
        ws.sheet_view.showGridLines = False
        write_section_title(ws, 1, '🌧️ Bad Weather Plan B (v3) — Indoor / Sheltered Swaps', 6,
                            fill=V3_FILL)
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=6)
        rationale = wb_data.get('rationale', '')
        c = ws.cell(row=2, column=1, value=rationale)
        c.font = Font(name=ARIAL, italic=True, size=10); c.alignment = WRAP; c.fill = WARN_FILL
        c.border = BORDER
        ws.row_dimensions[2].height = 42

        r = 4
        # Decision tree
        write_subsection_band(ws, r, '🌦️ Morning Forecast Decision Tree', 6, color='595959')
        r += 1
        for j, h in enumerate(['Condition', 'Trigger', 'Action'], 1):
            ws.cell(row=r, column=j, value=h)
        # merge action col across 4 cols for legibility
        for j in range(4, 7):
            ws.cell(row=r, column=j, value='')
        style_header_row(ws, r, 6)
        r += 1
        for i, dt in enumerate(wb_data.get('decision_tree', [])):
            ws.cell(row=r, column=1, value=dt.get('condition', ''))
            ws.cell(row=r, column=2, value=dt.get('trigger', ''))
            ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=6)
            ws.cell(row=r, column=3, value=dt.get('action', ''))
            for cc in range(1, 7):
                cell = ws.cell(row=r, column=cc)
                cell.font = DEFAULT_FONT
                cell.alignment = WRAP
                cell.border = BORDER
                if i % 2 == 0:
                    cell.fill = ALT_FILL
            ws.row_dimensions[r].height = 36
            r += 1

        # Per-day swaps
        per_day = wb_data.get('per_day_swaps', [])
        if per_day:
            r += 1
            write_subsection_band(ws, r, '🔄 Per-Day Bad-Weather Swaps', 6, color='595959')
            r += 1
            for day in per_day:
                ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
                dc = ws.cell(row=r, column=1, value=day.get('day_label', ''))
                dc.font = Font(name=ARIAL, bold=True, size=11, color='FFFFFF')
                dc.fill = PatternFill('solid', start_color='808080')
                dc.alignment = LEFT
                r += 1
                for j, h in enumerate(['Original item', 'Why at risk', 'Trigger', 'Plan-B action', f'Alt {currency}', 'Channel'], 1):
                    ws.cell(row=r, column=j, value=h)
                style_header_row(ws, r, 6)
                r += 1
                for i, sw in enumerate(day.get('swaps', [])):
                    ws.cell(row=r, column=1, value=sw.get('original', ''))
                    ws.cell(row=r, column=2, value=sw.get('why_risk', ''))
                    ws.cell(row=r, column=3, value=sw.get('trigger', ''))
                    ws.cell(row=r, column=4, value=sw.get('action', ''))
                    av = _pick(sw, 'alt_local', 'alt_vnd')
                    ws.cell(row=r, column=5, value=av if av else None).number_format = '#,##0;[Red](#,##0);"-"'
                    ws.cell(row=r, column=6, value=sw.get('channel', ''))
                    for cc in range(1, 7):
                        cell = ws.cell(row=r, column=cc)
                        cell.font = DEFAULT_FONT
                        cell.alignment = WRAP
                        cell.border = BORDER
                        if i % 2 == 0:
                            cell.fill = ALT_FILL
                    ws.row_dimensions[r].height = 40
                    r += 1
                r += 1

        # Indoor activity bank — merges explicit entries with places[] flagged indoor=true
        bank = derive_indoor_bank(data)
        if bank:
            r += 1
            write_subsection_band(ws, r, '🏠 Indoor Activity Bank', 6, color='595959')
            r += 1
            for j, h in enumerate(['Activity', 'Area', f'{currency}', 'Duration', 'Notes'], 1):
                ws.cell(row=r, column=j, value=h)
            ws.cell(row=r, column=6, value='')
            style_header_row(ws, r, 6)
            r += 1
            for i, b in enumerate(bank):
                ws.cell(row=r, column=1, value=b.get('name', ''))
                ws.cell(row=r, column=2, value=b.get('area', ''))
                v = _pick(b, 'local_cost', 'vnd')
                ws.cell(row=r, column=3, value=v if v is not None else None).number_format = '#,##0;[Red](#,##0);"FREE"'
                ws.cell(row=r, column=4, value=b.get('duration', ''))
                ws.merge_cells(start_row=r, start_column=5, end_row=r, end_column=6)
                ws.cell(row=r, column=5, value=b.get('notes', ''))
                for cc in range(1, 7):
                    cell = ws.cell(row=r, column=cc)
                    cell.font = DEFAULT_FONT
                    cell.alignment = WRAP
                    cell.border = BORDER
                    if i % 2 == 0:
                        cell.fill = ALT_FILL
                ws.row_dimensions[r].height = 28
                r += 1

        # Booking flexibility tips
        flex = wb_data.get('booking_flex_tips', [])
        if flex:
            r += 1
            write_subsection_band(ws, r, '💡 Booking Flexibility — Storm-Proof Your Itinerary', 6, color='595959')
            r += 1
            for tip in flex:
                ws.cell(row=r, column=1, value=tip.get('label', '')).font = Font(name=ARIAL, bold=True, size=10)
                ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=6)
                ws.cell(row=r, column=2, value=tip.get('text', ''))
                for cc in range(1, 7):
                    cell = ws.cell(row=r, column=cc)
                    if cc != 1:
                        cell.font = DEFAULT_FONT
                    cell.alignment = WRAP
                    cell.border = BORDER
                ws.row_dimensions[r].height = 32
                r += 1

        set_col_widths(ws, [28, 22, 14, 38, 14, 22])
        sheets_emitted.append('5. v3 Bad Weather Plan B')

    # Reorder sheets: variants 3/4/5 adjacent for easy comparison
    desired_order = [
        '1. Overview',
        '2. Booking Timeline',
        '3. v1 Daily Itinerary',
        '4. v2 Relaxed Pace',
        '5. v3 Bad Weather Plan B',
        '6. v1 vs v2 Compare',
        '7. Accommodation',
        '8. Food, Spas, Nightlife',
        '9. Hidden Gems & Swaps',
        '10. Activity Pricing',
        '11. Distance Matrix',
        '12. Budget',
        '13. Practical Info',
        '14. Pre-Departure Checklist',
    ]
    # Use public openpyxl move_sheet API. Compute target index for each
    # present sheet vs its current index; non-emitted sheets just skip.
    current = [ws.title for ws in wb.worksheets]
    target = [n for n in desired_order if n in current]
    for target_idx, name in enumerate(target):
        cur_idx = [ws.title for ws in wb.worksheets].index(name)
        if cur_idx != target_idx:
            wb.move_sheet(name, offset=target_idx - cur_idx)

    # Save
    path = out_xlsx(slug)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    actual = safe_save_xlsx(wb, path)
    print(f'WROTE: {actual}')
    print(f'Sheets in final order: {[ws.title for ws in wb.worksheets]}')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--slug', required=True)
    args = ap.parse_args()
    build(args.slug)

if __name__ == '__main__':
    main()
