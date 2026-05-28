# Map Rendering — Labelled OSM Maps

Render two maps per trip using the `staticmap` Python package + PIL label overlay.

## Why two maps

1. **Regional map (zoom 10)** — shows day-trip targets at city scale. Includes destinations 30–70 km from base.
2. **City close-up (zoom 12)** — shows local sights, base hotel, airport. Less label crowding for nearby items.

Splitting maps avoids label-collision in dense urban cores while keeping outer-region context.

## Library

```bash
pip install staticmap Pillow
```

`staticmap` fetches OSM tiles from a configurable tile server and composes them into a single image. You then overlay markers + labels with PIL.

## Tile server

Default OSM tile server allows light personal use. Custom User-Agent required:

```python
m = StaticMap(
    width=1600, height=1200,
    url_template='https://a.tile.openstreetmap.org/{z}/{x}/{y}.png',
    headers={'User-Agent': 'ItineraryBuilder/1.0 peter@isspan.net'}
)
```

## Marker stack

Render each marker as 3 stacked CircleMarkers for a "halo" effect:

```python
m.add_marker(CircleMarker((lon, lat), color, 22))   # outer color halo
m.add_marker(CircleMarker((lon, lat), 'white', 12)) # white middle
m.add_marker(CircleMarker((lon, lat), color, 8))    # inner color dot
```

## Connector lines (optional)

For the regional map, draw thin grey lines from base-hotel to each day-trip target:

```python
m.add_line(Line([(base_lon, base_lat), (poi_lon, poi_lat)], '#88888899', 2))
```

Skip on close-up — too cluttered.

## Label placement — PIL overlay

After `m.render(zoom=N)`, get the PIL Image back and overlay labels with `ImageDraw`.

**Critical:** `staticmap` centers on the *bounding box* of all markers, not necessarily a named center. Compute center yourself:

```python
center_lat = (min(lats) + max(lats)) / 2
center_lon = (min(lons) + max(lons)) / 2
```

Then project each (lat, lon) to (x, y) pixels using Mercator:

```python
import math
def latlon_to_pixel(lat, lon, zoom, w, h, center_lat, center_lon):
    def project(lat, lon, z):
        x = (lon + 180.0) / 360.0 * (256 << z)
        y = (1.0 - math.log(math.tan(math.radians(lat)) +
            1 / math.cos(math.radians(lat))) / math.pi) / 2.0 * (256 << z)
        return x, y
    cx, cy = project(center_lat, center_lon, zoom)
    px, py = project(lat, lon, zoom)
    return int(px - cx + w/2), int(py - cy + h/2)
```

## Label position offsets

Each POI label gets a positional code (NE/NW/SE/SW/E/W/N/S + extended NEE/SEE/NWW/SWW) for offset spreading:

```python
OFFSETS = {
    'NE': (32, -56), 'NW': (-32, -56), 'SE': (32, 24), 'SW': (-32, 24),
    'E':  (32, -10), 'W':  (-32, -10), 'N':  (0, -62), 'S':  (0, 30),
    'NEE': (60, -38), 'SEE': (60, 18), 'NWW': (-60, -38), 'SWW': (-60, 18),
}
```

For "W" positions, also subtract text width so the box ends at the offset, not starts:

```python
if 'W' in pos:
    tx -= text_w + 10
```

## Label box style

Draw white-fill, color-border rectangle behind text — readable on any map background:

```python
pad = 3
draw.rectangle((tx-pad, ty-pad, tx+text_w+pad, ty+text_h+pad),
               fill=(255,255,255,220), outline=text_color, width=2)
draw.text((tx, ty), label, font=font, fill=text_color)
```

Font: Arial Bold 26pt for labels, Arial Bold 36pt for title, Arial Regular 18pt for legend.

## Color coding

```python
COLOR_MAP = {
    'red':    '#CC0000',  # base hotel
    'blue':   '#0033CC',  # airport / city anchor
    'orange': '#FF6600',  # sights / city
    'green':  '#00802B',  # beach / nature
    'purple': '#6600CC',  # day-trip target
    'darkblue': '#003366', # islands
}
```

## Title bar + legend

After main render, prepend a title bar (height 70 px, blue fill matching workbook headers) and overlay a legend box bottom-right with the 5–6 color categories.

## Render and save

```python
img = m.render(zoom=10)
# overlay labels + title + legend → composite image
composite.save('map_regional.jpg', 'JPEG', quality=88, optimize=True)
```

## Per-trip POI list

In `trips/<slug>/data.json`:

```json
{
  "maps": {
    "regional": {
      "zoom": 10,
      "places": [
        {"lat": 16.0544, "lon": 108.2425, "label": "BASE HOTEL\n(Da Nang / My Khe)", "color": "red", "pos": "E"},
        {"lat": 15.997,  "lon": 107.9967, "label": "Ba Na Hills",    "color": "purple", "pos": "W"},
        ...
      ]
    },
    "city_closeup": {"zoom": 12, "places": [...]}
  }
}
```

`build_map.py` reads this directly and renders both.

## Iteration

If labels collide:
1. Adjust position codes (NE→NEE, W→NW, etc.)
2. Shorten labels (`Lady Buddha\n(Son Tra)` instead of `Linh Ứng Pagoda — Lady Buddha`)
3. If a sub-cluster is irreducibly tight, consolidate them into one marker with a combined label (e.g. `BASE HOTEL\nMy Khe + 43 Factory + An Thuong`)
4. Or move the item to the other map (close-up vs regional)

3 render cycles is usually enough.

## Performance

Initial render fetches ~16–32 OSM tiles → 2–5 seconds. PIL overlay is instant. Total per map ~5–8 seconds on first run; subsequent runs same (no tile cache by default).

## Alternative tile sources

If OSM rate-limits during heavy iteration, swap URL template:
- `https://tile.openstreetmap.de/{z}/{x}/{y}.png` (Germany mirror)
- `https://maps.wikimedia.org/osm-intl/{z}/{x}/{y}.png` (Wikimedia)

For paid/branded styles, use Mapbox / Maptiler with API key.
