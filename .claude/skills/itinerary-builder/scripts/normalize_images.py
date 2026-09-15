"""Normalize every downloaded image via PIL.

python-docx is strict about JPEG markers. This re-encodes everything to a
canonical JPEG with predictable structure.

Run after fetch_images.py, before build_docx.py.
"""
import sys
import os
import argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.common import img_dir
from PIL import Image

MAX_W = 1600

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--slug', required=True)
    ap.add_argument('--max-width', type=int, default=MAX_W)
    args = ap.parse_args()

    folder = img_dir(args.slug)
    for fn in os.listdir(folder):
        path = os.path.join(folder, fn)
        if not fn.lower().endswith(('.jpg', '.jpeg', '.png')):
            continue
        try:
            im = Image.open(path)
            im.load()
            if im.mode in ('RGBA', 'P'):
                im = im.convert('RGB')
            if im.width > args.max_width:
                ratio = args.max_width / im.width
                im = im.resize((args.max_width, int(im.height * ratio)), Image.LANCZOS)
            out = os.path.splitext(path)[0] + '.jpg'
            im.save(out, 'JPEG', quality=85, optimize=True)
            if out != path:
                os.remove(path)
            print(f'{fn} → {os.path.basename(out)} ({im.width}x{im.height})')
        except Exception as e:
            print(f'{fn} FAIL: {e}')

if __name__ == '__main__':
    main()
