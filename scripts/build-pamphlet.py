#!/usr/bin/env python3
"""Render the same HTML used by the preview into two printable PDFs.

Install scripts/print-requirements.txt into a virtual environment first.
No Chromium, browser automation, network request, or JavaScript is involved.
"""
from pathlib import Path
import io
import json
import os
import hashlib

ROOT = Path(__file__).resolve().parent.parent
TMP = ROOT / 'tmp' / 'pdfs'
TMP.mkdir(parents=True, exist_ok=True)
os.environ.setdefault('XDG_CACHE_HOME', str(TMP / 'cache'))

from weasyprint import HTML
from pypdf import PdfReader, PdfWriter, Transformation
from pypdf.generic import RectangleObject

OUT = ROOT / 'output' / 'pdf'
MM = 72 / 25.4


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    document = HTML(filename=str(ROOT / 'pamphlet.html')).render()
    if len(document.pages) != 2:
        raise ValueError(f'Expected exactly 2 spreads, got {len(document.pages)}')
    report=[]
    for n,page in enumerate(document.pages,1):
        for panel in page._page_box.descendants():
            if panel.element is None or not panel.element.get('class','').startswith('panel ') or type(panel).__name__!='FlexBox':
                continue
            margins=[]
            for box in panel.descendants():
                if type(box).__name__!='TextBox':
                    continue
                clearance=min(box.position_x-panel.position_x,
                    panel.position_x+panel.border_width()-box.position_x-box.width,
                    box.position_y-3*96/25.4,
                    213*96/25.4-box.position_y-box.height)*25.4/96
                margins.append(clearance)
                if clearance < 4.9:
                    raise ValueError(f'Text too close to fold/trim: {panel.element.get("class")}: {box.text}')
            report.append({'page':n,'panel':panel.element.get('class'),'minimum_text_clearance_mm':round(min(margins),2)})
    (TMP/'layout-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    source_hash=hashlib.sha256((ROOT/'pamphlet.html').read_bytes()+(ROOT/'css/pamphlet.css').read_bytes()).hexdigest()
    raw = document.write_pdf()
    bleed = PdfReader(io.BytesIO(raw))
    writer = PdfWriter()
    for page in bleed.pages:
        page.trimbox = RectangleObject([3*MM, 3*MM, 300*MM, 213*MM])
        page.bleedbox = RectangleObject([0, 0, 303*MM, 216*MM])
        writer.add_page(page)
    writer.add_metadata({'/Title':'マリンバコンサート「結」三つ折りパンフレット - 塗り足し付き', '/Author':'マリンバ北星会', '/Subject':'A4 landscape, roll fold, 3 mm bleed. Outside: 97/100/100 mm. Inside: 100/100/97 mm.'})
    writer.add_metadata({'/YuiSourceSHA256':source_hash})
    writer.write(OUT / 'yui-pamphlet-bleed.pdf')

    a4 = PdfWriter()
    for source in PdfReader(io.BytesIO(raw)).pages:
        target = a4.add_blank_page(width=297*MM, height=210*MM)
        target.merge_transformed_page(source, Transformation().translate(-3*MM,-3*MM))
        target.trimbox = RectangleObject([0,0,297*MM,210*MM])
    a4.add_metadata({'/Title':'マリンバコンサート「結」三つ折りパンフレット - A4', '/Author':'マリンバ北星会', '/Subject':'A4 landscape, duplex short-edge binding, actual size.'})
    a4.add_metadata({'/YuiSourceSHA256':source_hash})
    a4.write(OUT / 'yui-pamphlet-a4.pdf')

    # Check physical page size and that every page has selectable text.
    for name in ('yui-pamphlet-bleed.pdf','yui-pamphlet-a4.pdf'):
        pdf = PdfReader(OUT / name)
        assert len(pdf.pages) == 2
        for page in pdf.pages:
            assert len(page.extract_text()) > 400
        print(f'{name}: 2 pages, {float(pdf.pages[0].mediabox.width)/MM:.1f} × {float(pdf.pages[0].mediabox.height)/MM:.1f} mm')

    print('PASS all text at least 5 mm from trim and folds (0.1 mm layout tolerance)')


if __name__ == '__main__':
    main()
