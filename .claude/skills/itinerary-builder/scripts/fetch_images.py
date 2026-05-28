"""Fetch royalty-free photos from Wikipedia REST + Wikimedia Commons.

Reads trips/<slug>/data.json → for each place w/ wiki_title (or alt_search_query),
downloads to trips/<slug>/images/<key>.jpg.

See references/image_sourcing.md.
"""
import sys, os, json, argparse, urllib.request, urllib.parse
from lib.common import load_data, save_data, img_dir, log_unvalidated, trip_dir

UA = {'User-Agent': 'ItineraryBuilder/1.0 (peter@isspan.net)'}

def fetch(url, dest):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        with open(dest, 'wb') as f:
            f.write(data)
        return len(data)
    except Exception as e:
        return None

def wiki_thumb(title):
    enc = urllib.parse.quote(title.replace(' ', '_'))
    url = f'https://en.wikipedia.org/api/rest_v1/page/summary/{enc}'
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=20) as r:
            j = json.loads(r.read())
        if 'originalimage' in j:
            return j['originalimage']['source']
        if 'thumbnail' in j:
            return j['thumbnail']['source']
    except Exception:
        return None

def commons_search(query):
    url = (f'https://commons.wikimedia.org/w/api.php'
           f'?action=query&list=search&srsearch={urllib.parse.quote(query)}'
           f'&srnamespace=6&format=json&srlimit=1')
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=20) as r:
            j = json.loads(r.read())
        hits = j.get('query', {}).get('search', [])
        if not hits:
            return None
        fname = hits[0]['title']
        fenc = urllib.parse.quote(fname)
        url2 = (f'https://commons.wikimedia.org/w/api.php'
                f'?action=query&titles={fenc}&prop=imageinfo&iiprop=url&format=json')
        req = urllib.request.Request(url2, headers=UA)
        with urllib.request.urlopen(req, timeout=20) as r:
            j2 = json.loads(r.read())
        for pid, p in j2['query']['pages'].items():
            ii = p.get('imageinfo')
            if ii:
                return ii[0]['url']
    except Exception:
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
                            'No Wikipedia or Commons image found — manually source.')
            continue

        size = fetch(url, dest)
        if size and size > 5000:
            print(f'{key}: {size} bytes from {url[:80]}')
            place['image_path'] = dest
        else:
            skipped.append(key)
            print(f'{key}: download failed')

    save_data(args.slug, data)
    print(f'\nDone. {len(skipped)} images skipped.')
    if skipped:
        print('Skipped:', ', '.join(skipped))

if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from lib.common import load_data, save_data, img_dir, log_unvalidated
    main()
