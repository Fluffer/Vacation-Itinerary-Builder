"""Render labelled regional + city close-up maps.

Reads data['maps']['regional'] and data['maps']['city_closeup'] from
trips/<slug>/data.json. Writes map_regional.jpg and map_danang.jpg
(or map_<destination_slug>.jpg) into trips/<slug>/images/.

See references/map_rendering.md.
"""
import sys
import os
import math
import argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.common import load_data, img_dir
from staticmap import StaticMap, CircleMarker, Line
from PIL import Image, ImageDraw, ImageFont

UA = {'User-Agent': 'ItineraryBuilder/1.0 peter@isspan.net'}
TILE = 'https://a.tile.openstreetmap.org/{z}/{x}/{y}.png'

COLOR_MAP = {
    'red': '#CC0000', 'blue': '#0033CC', 'orange': '#FF6600',
    'green': '#00802B', 'purple': '#6600CC', 'darkblue': '#003366',
}
OFFSETS = {
    'NE': (32, -56), 'NW': (-32, -56), 'SE': (32, 24), 'SW': (-32, 24),
    'E': (32, -10), 'W': (-32, -10), 'N': (0, -62), 'S': (0, 30),
    'NEE': (60, -38), 'SEE': (60, 18), 'NWW': (-60, -38), 'SWW': (-60, 18),
}

def project(lat, lon, z):
    x = (lon + 180.0) / 360.0 * (256 << z)
    y = (1.0 - math.log(math.tan(math.radians(lat)) +
        1 / math.cos(math.radians(lat))) / math.pi) / 2.0 * (256 << z)
    return x, y

def latlon_to_pixel(lat, lon, zoom, w, h, center_lat, center_lon):
    cx, cy = project(center_lat, center_lon, zoom)
    px, py = project(lat, lon, zoom)
    return int(px - cx + w/2), int(py - cy + h/2)

def render_map(places, out_path, title, zoom, size=(1600, 1200), draw_lines=True):
    w, h = size
    m = StaticMap(w, h, url_template=TILE, headers=UA)
    for p in places:
        color = p['color']
        lat, lon = p['lat'], p['lon']
        m.add_marker(CircleMarker((lon, lat), color, 22))
        m.add_marker(CircleMarker((lon, lat), 'white', 12))
        m.add_marker(CircleMarker((lon, lat), color, 8))
    if draw_lines and places:
        base = places[0]
        for p in places[1:]:
            m.add_line(Line([(base['lon'], base['lat']), (p['lon'], p['lat'])], '#88888899', 2))
    img = m.render(zoom=zoom)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype('arialbd.ttf', 26)
        font_sm = ImageFont.truetype('arial.ttf', 18)
        title_font = ImageFont.truetype('arialbd.ttf', 34)
    except Exception:
        font = ImageFont.load_default()
        font_sm = font
        title_font = font

    lats = [p['lat'] for p in places]
    lons = [p['lon'] for p in places]
    center_lat = (min(lats) + max(lats)) / 2
    center_lon = (min(lons) + max(lons)) / 2

    for p in places:
        x, y = latlon_to_pixel(p['lat'], p['lon'], zoom, w, h, center_lat, center_lon)
        dx, dy = OFFSETS.get(p['pos'], (28, -10))
        tx, ty = x + dx, y + dy
        lines = p['label'].split('\n')
        line_h = 30
        text_w = max(draw.textbbox((0,0), L, font=font)[2] for L in lines)
        text_h = line_h * len(lines)
        if 'W' in p['pos']:
            tx -= text_w + 10
        if p['pos'] in ('N','S'):
            tx -= text_w // 2
        txt_color = COLOR_MAP.get(p['color'], '#000000')
        pad = 3
        draw.rectangle((tx-pad, ty-pad, tx+text_w+pad, ty+text_h+pad),
                       fill=(255,255,255,220), outline=txt_color, width=2)
        for i, L in enumerate(lines):
            draw.text((tx, ty + i*line_h), L, font=font, fill=txt_color)

    title_h = 70
    out = Image.new('RGB', (w, h + title_h), 'white')
    out.paste(img, (0, title_h))
    draw = ImageDraw.Draw(out)
    draw.rectangle([0, 0, w, title_h], fill='#1F4E78')
    draw.text((20, 18), title, font=title_font, fill='white')

    legend_y = h + title_h - 130
    legend_x = w - 320
    draw.rectangle([legend_x-10, legend_y-5, w-10, legend_y+125], fill='white', outline='#888', width=2)
    legend = [
        ('● Base hotel', '#CC0000'),
        ('● Airport', '#0033CC'),
        ('● Sights / city', '#FF6600'),
        ('● Beach / nature', '#00802B'),
        ('● Day-trip target', '#6600CC'),
        ('● Islands', '#003366'),
    ]
    for i, (txt, col) in enumerate(legend):
        draw.text((legend_x, legend_y + i*19), txt, font=font_sm, fill=col)

    out.save(out_path, 'JPEG', quality=88, optimize=True)
    print(f'WROTE: {out_path}  ({os.path.getsize(out_path)} bytes)')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--slug', required=True)
    args = ap.parse_args()

    data = load_data(args.slug)
    maps = data.get('maps', {})
    folder = img_dir(args.slug)
    dest = data.get('metadata', {}).get('destination', args.slug)

    if 'regional' in maps and maps['regional'].get('places'):
        cfg = maps['regional']
        render_map(cfg['places'],
                   os.path.join(folder, 'map_regional.jpg'),
                   f'Regional Map — {dest} & Surroundings',
                   zoom=cfg['zoom'])
    if 'city_closeup' in maps and maps['city_closeup'].get('places'):
        cfg = maps['city_closeup']
        render_map(cfg['places'],
                   os.path.join(folder, 'map_city.jpg'),
                   f'{dest} City Close-up — Local Sights & Base',
                   zoom=cfg['zoom'], draw_lines=False)

if __name__ == '__main__':
    main()
