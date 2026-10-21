#!/usr/bin/env python3
"""Regenerate vector QR codes and print fonts after editing pamphlet text.

Original variable fonts are downloaded from Google Fonts only if not cached.
The generated subset fonts and licenses are checked into fonts/print/ so the
HTML preview and PDF build themselves work without an external font service.
"""
from pathlib import Path
import argparse
from urllib.request import urlopen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.subset import Subsetter, Options
import qrcode
import qrcode.image.svg

ROOT = Path(__file__).resolve().parent.parent
URLS = {'ticket':'https://teket.jp/16938/63047', 'site':'https://toshiki-yasuda.github.io/yui/', 'ofuse':'https://ofuse.me/ayccmarimba'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--font-source',type=Path,default=ROOT/'tmp/pdfs/font-source')
    args=parser.parse_args()
    args.font_source.mkdir(parents=True,exist_ok=True)
    font_dir=ROOT/'fonts/print'; font_dir.mkdir(parents=True,exist_ok=True)
    for family in ('NotoSansJP','NotoSerifJP'):
        base='https://raw.githubusercontent.com/google/fonts/main/ofl/'+family.lower()+'/'
        for remote,local in ((family+'%5Bwght%5D.ttf',family+'.ttf'),('OFL.txt',family+'-OFL.txt')):
            path=args.font_source/local
            if not path.exists():
                with urlopen(base+remote,timeout=60) as response: path.write_bytes(response.read())
        (font_dir/(family+'-OFL.txt')).write_bytes((args.font_source/(family+'-OFL.txt')).read_bytes())
    text=(ROOT/'pamphlet.html').read_text()+(ROOT/'css/pamphlet.css').read_text()+''.join(chr(i) for i in range(32,127))
    for family,weight,label in [('NotoSansJP',400,'Regular'),('NotoSansJP',500,'Medium'),('NotoSerifJP',400,'Regular')]:
        font=instantiateVariableFont(TTFont(args.font_source/(family+'.ttf')),{'wght':weight},inplace=True)
        options=Options(); options.name_IDs=['*']; options.name_legacy=True
        subset=Subsetter(options=options); subset.populate(text=text); subset.subset(font)
        font.save(font_dir/(family+'-'+label+'.ttf'))
    qr_dir=ROOT/'images/print'; qr_dir.mkdir(parents=True,exist_ok=True)
    for name,url in URLS.items():
        qr=qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,border=4,box_size=10)
        qr.add_data(url); qr.make(fit=True)
        qr.make_image(image_factory=qrcode.image.svg.SvgPathFillImage).save(qr_dir/('qr-'+name+'.svg'))
    print('Prepared 3 print fonts, 2 licenses and 3 vector QR codes.')

if __name__=='__main__': main()
