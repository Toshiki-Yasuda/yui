#!/usr/bin/env python3
"""Check brochure information, PDF text, physical page sizes and printed QR codes.

Run after build-pamphlet.py. Requires Poppler pdftoppm in PATH.
"""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit
import re
import subprocess
import unicodedata
import hashlib
from pypdf import PdfReader
from PIL import Image
import zxingcpp

ROOT=Path(__file__).resolve().parent.parent
def normalized(text): return re.sub(r'\s+','',unicodedata.normalize('NFKC',text))

class Brochure(HTMLParser):
    def __init__(self,html):
        super().__init__(); self.images=[]; self.links=[]; self.panels=0; self.feed(html)
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='article' and 'panel' in attrs.get('class','').split():self.panels+=1
        if tag=='img':self.images.append(attrs)
        if tag=='a':self.links.append(attrs.get('href',''))

def main():
    html=(ROOT/'pamphlet.html').read_text()
    page=Brochure(html)
    assert page.panels==6
    assert '調整中' not in html
    for image in page.images:
        assert image.get('alt') and image.get('width') and image.get('height')
        assert (ROOT/image['src']).is_file()
    for link in page.links:
        url=urlsplit(link)
        if not url.scheme and url.path:assert (ROOT/url.path).is_file(),link
    # Keep the original concept and lead biography, with the current membership update.
    old=subprocess.check_output(['git','show','e9adaa7:pamphlet.html'],cwd=ROOT,text=True)
    bio=re.findall(r'<p class="artist-bio">([\s\S]*?)</p>',old)
    for text in bio:
        text=text.replace('日本マリンバ協会会員。','日本マリンバ協会会員、北海道打楽器協会会員。')
        assert normalized(text) in normalized(html),'Original lead biography missing'
    required=['木の温もりあふれるマリンバの音色を通し、世代を超えて音楽が結びつく場を目指します。',
      '今回のコンサートタイトル「結」には、いくつもの不思議なご縁が重なり、このソロ演奏会が実現に至ったことへの感謝が込められています。',
      'これらの重なるご縁から生まれたコンサートとして、一音一音を大切に作り上げていきます。音楽を通じた心の旅路をお届けします。',
      '北海道打楽器協会','札幌市教育委員会','田中 K助','土田 祐生','全12曲程度',
      '2,000円','1,000円','500円','無料','13:00','13:30','15:15','2026','10.25',
      '安田までご一報いただけますと幸いです','応援・ご支援はこちらから','yui.concert.2026@gmail.com']
    for filename,size in [('yui-pamphlet-a4.pdf',(297,210)),('yui-pamphlet-bleed.pdf',(303,216))]:
        pdf=PdfReader(ROOT/'output/pdf'/filename); assert len(pdf.pages)==2
        expected_hash=hashlib.sha256((ROOT/'pamphlet.html').read_bytes()+(ROOT/'css/pamphlet.css').read_bytes()).hexdigest()
        assert pdf.metadata.get('/YuiSourceSHA256')==expected_hash,'PDF is older than its HTML/CSS source'
        text=normalized(''.join(p.extract_text() for p in pdf.pages))
        for value in required: assert normalized(value) in text, f'{filename}: missing {value}'
        for p in pdf.pages:
            assert abs(float(p.mediabox.width)*25.4/72-size[0])<.01
            assert abs(float(p.mediabox.height)*25.4/72-size[1])<.01
        print('PASS',filename,': 2 pages, correct dimensions, current information and text')
    temp=ROOT/'tmp/pdfs';temp.mkdir(parents=True,exist_ok=True)
    subprocess.run(['pdftoppm','-r','150','-png',str(ROOT/'output/pdf/yui-pamphlet-a4.pdf'),str(temp/'qr-check')],check=True)
    found=set()
    for n in (1,2):
        found.update(code.text for code in zxingcpp.read_barcodes(Image.open(temp/f'qr-check-{n}.png')))
    expected={'https://teket.jp/16938/63047','https://toshiki-yasuda.github.io/yui/','https://ofuse.me/ayccmarimba'}
    assert found==expected,f'Printed QR mismatch: {found}'
    print('PASS all 3 QR codes decoded from the rendered PDF')

if __name__=='__main__':main()
