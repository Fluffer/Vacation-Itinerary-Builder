"""Fetch royalty-free photos from Wikipedia REST + Wikimedia Commons.

Reads trips/<slug>/data.json â†’ for each place w/ wiki_title (or alt_search_query),
downloads to trips/<slug>/images/<key>.jpg.

Only raster image responses (JPEG/PNG/WebP/GIF) are accepted â€” Wikipedia
`originalimage` can be SVG or PDF, which would break PIL normalisation and the
docx build. Non-image results are rejected and any stale file removed.

See references/image_sourcing.md.
"""
import sys
import os
import argparse
import json
import urllib.request
import urllib.parse
import urllib.error
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.common import load_data, save_data, img_dir, log_unvalidated

UA = {'User-Agent': 'ItineraryBuilder/1.0 (trip-planner)'}

_IMAGE_TYPES = ('image/jpeg', 'image/png', 'image/webp', 'image/gif')


def _urlopen(req, timeout):
    """urlopen restricted to https (prevents file:/custom-scheme reads).

    `req` may be a URL string or a urllib.request.Request.
    """
    url = req.full_url if isinstance(req, urllib.request.Request) else str(req)
    if not url.lower().startswith('https://'):
        raise ValueError(f'refusing non-https URL: {url[:60]}')
    return urllib.request.urlopen(req, timeout=timeout)  # nosec B310 - scheme restricted above


def _is_image_response(resp) -> bool:
    ctype = (resp.headers.get('Content-Type') or '').split(';')[0].strip().lower()
    return ctype in _IMAGE_TYPES


def fetch(url, dest):
    req = urllib.request.Request(url, headers=UA)
    try:
        with _urlopen(req, timeout=30) as r:
            if not _is_image_response(r):
                return None
            data = r.read()
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None
    if not data:
        return None
    try:
        with open(dest, 'wb') as f:
            f.write(data)
    except OSError:
        return None
    return len(data)


def wiki_thumb(title):
    enc = urllib.parse.quote(title.replace(' ', '_'))
    url = f'https://en.wikipedia.org/api/rest_v1/page/summary/{enc}'
    try:
        req = urllib.request.Request(url, headers=UA)
        with _urlopen(req, timeout=20) as r:
            j = json.loads(r.read())
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
        return None
    # Prefer the raster thumbnail; `originalimage` may be SVG/PDF which PIL cannot open.
    if 'thumbnail' in j:
        return j['thumbnail']['source']
    if 'originalimage' in j:
        return j['originalimage']['source']
    return None


def commons_search(query):
    url = (f'https://commons.wikimedia.org/w/api.php'
           f'?action=query&list=search&srsearch={urllib.parse.quote(query)}'
           f'&srnamespace=6&format=json&srlimit=1')
    try:
        req = urllib.request.Request(url, headers=UA)
        with _urlopen(req, timeout=20) as r:
            j = json.loads(r.read())
        hits = j.get('query', {}).get('search', [])
        if not hits:
            return None
        fname = hits[0]['title']
        fenc = urllib.parse.quote(fname)
        url2 = (f'https://commons.wikimedia.org/w/api.php'
                f'?action=query&titles={fenc}&prop=imageinfo&iiprop=url&format=json')
        req = urllib.request.Request(url2, headers=UA)
        with _urlopen(req, timeout=20) as r:
            j2 = json.loads(r.read())
        for _pid, p in j2['query']['pages'].items():
            ii = p.get('imageinfo')
            if ii:
                return ii[0]['url']
    except (urllib.error.URLError, TimeoutError, OSError, ValueError,
            KeyError, json.JSONDecodeError):
        return None
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--slug', required=True)
    args = ap.parse_args()

    data = load_data(args.slug)
    out = img_dir(args.slug)
    skipped = []

    for place in data.get('places', []):
        key = place['key']
        dest = os.path.join(out, f'{key}.jpg')
        if os.path.exists(dest) and os.path.getsize(dest) > 5000:
            print(f'{key}: cached, skip')
            place['image_path'] = dest
            continue

        url = None
        if place.get('wiki_title'):
            url = wiki_thumb(place['wiki_title'])
        if not url and place.get('alt_search_query'):
            url = commons_search(place['alt_search_query'])
        if not url:
            print(f'{key}: NO IMAGE FOUND')
            skipped.append(key)
            log_unvalidated(args.slug, f'image for "{place["name"]}"',
                            'No Wikipedia or Commons image found â€” manually source.')
            continue

        size = fetch(url, dest)
        if size and size > 5000:
            print(f'{key}: {size} bytes from {url[:80]}')
            place['image_path'] = dest
        else:
            # Reject/clean a non-image or partial file so downstream falls back
            # to the placeholder branch instead of crashing on PIL/docx.
            if os.path.exists(dest):
                try:
                    os.remove(dest)
                except OSError:
                    pass
            skipped.append(key)
            print(f'{key}: download failed or not a raster image')

    save_data(args.slug, data)
    print(f'\nDone. {len(skipped)} images skipped.')
    if skipped:
        print('Skipped:', ', '.join(skipped))


if __name__ == '__main__':
    main()
