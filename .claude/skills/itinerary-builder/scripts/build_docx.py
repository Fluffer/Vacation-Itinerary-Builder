"""Build the illustrated Word document.

Reads trips/<slug>/data.json + images/. Produces Word doc with title page,
two labelled maps, per-POI sections (photo + description + hyperlinks),
hotels, practical-link blocks.

See references/workflow.md Phase 8.
"""
import sys, os, argparse, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.common import load_data, out_docx, img_dir
from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

def add_hyperlink(paragraph, url, text, color='0563C1', underline=True):
    part = paragraph.part
    r_id = part.relate_to(url,
        'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink',
        is_external=True)
    hl = OxmlElement('w:hyperlink')
    hl.set(qn('r:id'), r_id)
    new_run = OxmlElement('w:r')
    rPr = OxmlElement('w:rPr')
    rFonts = OxmlElement('w:rFonts'); rFonts.set(qn('w:ascii'), 'Arial'); rFonts.set(qn('w:hAnsi'), 'Arial')
    rPr.append(rFonts)
    c = OxmlElement('w:color'); c.set(qn('w:val'), color); rPr.append(c)
    if underline:
        u = OxmlElement('w:u'); u.set(qn('w:val'), 'single'); rPr.append(u)
    sz = OxmlElement('w:sz'); sz.set(qn('w:val'), '22'); rPr.append(sz)
    new_run.append(rPr)
    t = OxmlElement('w:t'); t.text = text; t.set(qn('xml:space'), 'preserve')
    new_run.append(t)
    hl.append(new_run)
    paragraph._p.append(hl)

def build(slug):
    data = load_data(slug)
    meta = data.get('metadata', {})
    folder = img_dir(slug)

    doc = Document()
    s = doc.styles['Normal']
    s.font.name = 'Arial'; s.font.size = Pt(11)
    sec = doc.sections[0]
    sec.page_width = Cm(21.0); sec.page_height = Cm(29.7)
    sec.left_margin = sec.right_margin = sec.top_margin = sec.bottom_margin = Cm(2.0)

    def h(text, level=1, color='1F4E78'):
        p = doc.add_heading(text, level=level)
        for r in p.runs:
            r.font.name = 'Arial'
            r.font.color.rgb = RGBColor.from_string(color)

    def p(text, italic=False, size=11):
        para = doc.add_paragraph()
        r = para.add_run(text)
        r.font.name = 'Arial'; r.font.size = Pt(size); r.italic = italic
        return para

    def add_pic(filename, width_in=6.0, caption=None):
        path = os.path.join(folder, filename)
        if not os.path.exists(path):
            para = doc.add_paragraph()
            r = para.add_run(f'[Image placeholder: {filename}]')
            r.font.color.rgb = RGBColor.from_string('999999'); r.italic = True
            return
        para = doc.add_paragraph(); para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        para.add_run().add_picture(path, width=Inches(width_in))
        if caption:
            cap = doc.add_paragraph(); cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cr = cap.add_run(caption); cr.italic = True
            cr.font.size = Pt(9); cr.font.color.rgb = RGBColor.from_string('666666')

    def link_para(label, url, prefix=''):
        para = doc.add_paragraph()
        if prefix:
            r = para.add_run(prefix); r.font.name='Arial'; r.bold=True; r.font.size=Pt(10)
        add_hyperlink(para, url, label)

    def gmaps(name):
        return 'https://www.google.com/maps/search/' + urllib.parse.quote(
            f'{name}, {meta.get("destination","")}')

    # ===== Title =====
    title = doc.add_paragraph(); title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tr = title.add_run(f'{meta.get("destination","Trip")} Trip Guide')
    tr.font.name='Arial'; tr.font.size=Pt(36); tr.font.bold=True
    tr.font.color.rgb = RGBColor.from_string('1F4E78')
    sub = doc.add_paragraph(); sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sr = sub.add_run(f'{meta.get("dates_start","")} – {meta.get("dates_end","")} · '
                     f'{meta.get("nights","?")} nights · {meta.get("origin","")} → {meta.get("destination","")}')
    sr.font.name='Arial'; sr.font.size=Pt(16); sr.font.color.rgb=RGBColor.from_string('2E75B6')
    doc.add_paragraph()

    # Hero photo — first iconic place
    iconic = [pl for pl in data.get('places', []) if pl.get('category') == 'iconic']
    if iconic:
        hero = iconic[0]
        if hero.get('image_path'):
            add_pic(os.path.basename(hero['image_path']), width_in=6.5,
                    caption=f'{hero.get("name", "")} — {meta.get("destination", "")}')
    p('Companion to the Excel booking-strategy workbook. Each place has description, '
      'photo, official link, and Google Maps pin.', italic=True)
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    # ===== Maps =====
    if os.path.exists(os.path.join(folder, 'map_regional.jpg')):
        h('🗺️ Regional Overview Map')
        add_pic('map_regional.jpg', width_in=6.8,
                caption='Regional map — base hotel + day-trip targets · OpenStreetMap data')
    if os.path.exists(os.path.join(folder, 'map_city.jpg')):
        h('🗺️ City Close-up', level=2)
        add_pic('map_city.jpg', width_in=6.8,
                caption=f'{meta.get("destination","")} city close-up — local sights')
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    # ===== Iconic Sights =====
    if iconic:
        h('🏯 Iconic Sights')
        for place in iconic:
            h(place['name'], level=2)
            if place.get('image_path'):
                add_pic(os.path.basename(place['image_path']), width_in=6.0,
                        caption=place.get('area', ''))
            if place.get('description'):
                p(place['description'])
            for link in place.get('links', []):
                link_para(link['label'], link['url'], prefix='• ')
            link_para('Google Maps', gmaps(place['name']), prefix='Map: ')

    # ===== Hidden Gems =====
    gems = [pl for pl in data.get('places', []) if pl.get('category') == 'hidden_gem']
    if gems:
        doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        h('💎 Hidden Gems & Less-Touristy Alternatives')
        for place in gems:
            h(place['name'], level=3)
            if place.get('description'):
                p(place['description'], size=10)
            for link in place.get('links', []):
                link_para(link['label'], link['url'], prefix='• ')

    # ===== Food =====
    food = [pl for pl in data.get('places', []) if pl.get('category') == 'food']
    if food:
        doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        h('🍜 Food — Where to Eat')
        for place in food:
            h(f'{place["name"]} — {place.get("area","")}', level=3)
            if place.get('description'):
                p(place['description'], size=10)
            for link in place.get('links', []):
                link_para(link['label'], link['url'], prefix='• ')

    # ===== Spas =====
    spas = [pl for pl in data.get('places', []) if pl.get('category') == 'spa']
    if spas:
        h('💆 Spas')
        for place in spas:
            h(f'{place["name"]} — {place.get("area","")}', level=3)
            if place.get('description'):
                p(place['description'], size=10)
            for link in place.get('links', []):
                link_para(link['label'], link['url'], prefix='• ')

    # ===== Nightlife =====
    night = [pl for pl in data.get('places', []) if pl.get('category') == 'nightlife']
    if night:
        h('🍻 Nightlife', level=1)
        for place in night:
            h(f'{place["name"]} — {place.get("area","")}', level=3)
            if place.get('description'):
                p(place['description'], size=10)
            for link in place.get('links', []):
                link_para(link['label'], link['url'], prefix='• ')

    # ===== Hotels =====
    hotels = data.get('hotels', [])
    if hotels:
        doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        h('🏨 Accommodation Picks')
        for hotel in hotels:
            h(f'{hotel["name"]} — {hotel.get("tier","")} · S${hotel.get("sgd_low","?")}–{hotel.get("sgd_high","?")}/night', level=3)
            if hotel.get('notes'):
                p(hotel['notes'], size=10)
            for link in hotel.get('links', []):
                link_para(link['label'], link['url'], prefix='• ')

    # ===== Practical Links =====
    pl = data.get('practical_links', {})
    if pl:
        doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        h('🔗 Practical Links & Resources')
        for category, items in pl.items():
            h(category, level=2)
            for it in items:
                link_para(it['label'], it['url'], prefix='• ')

    # Footer
    doc.add_paragraph()
    note = doc.add_paragraph()
    nr = note.add_run(
        'All photos from Wikimedia Commons under permissive licences (CC-BY-SA / public domain). '
        'Map data © OpenStreetMap contributors. Verify all prices and operating hours 2 weeks before travel.')
    nr.italic = True; nr.font.name='Arial'; nr.font.size=Pt(9)
    nr.font.color.rgb = RGBColor.from_string('666666')

    path = out_docx(slug)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    doc.save(path)
    print(f'WROTE: {path}  ({os.path.getsize(path)} bytes)')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--slug', required=True)
    args = ap.parse_args()
    build(args.slug)

if __name__ == '__main__':
    main()
