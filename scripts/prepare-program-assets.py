#!/usr/bin/env python3
"""Make isolated print fonts for the program; keep the existing brochure intact."""
from pathlib import Path
import argparse
from copy import deepcopy
from urllib.request import urlopen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.subset import Subsetter, Options

ROOT = Path(__file__).resolve().parent.parent


def preserve_fullwidth_tilde(font):
    """Give visually identical wave dash/tilde separate IDs for PDF text extraction."""
    cmap = font.getBestCmap()
    original = cmap.get(0xFF5E)
    if original is None or original != cmap.get(0x301C):
        return
    name = 'fullwidthTildeProgram'
    order = list(font.getGlyphOrder())
    font['glyf'][name] = deepcopy(font['glyf'][original])
    for table in ('hmtx', 'vmtx'):
        if table in font:
            font[table].metrics[name] = font[table].metrics[original]
    font.setGlyphOrder(order + [name])
    for table in font['cmap'].tables:
        if table.isUnicode() and 0xFF5E in table.cmap:
            table.cmap[0xFF5E] = name


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--font-source', type=Path, default=ROOT / 'tmp/pdfs/program/font-source')
    args = parser.parse_args()
    args.font_source.mkdir(parents=True, exist_ok=True)
    destination = ROOT / 'fonts/program'
    destination.mkdir(parents=True, exist_ok=True)
    source = next(ROOT.glob('*/source/program.json'))
    text = source.read_text() + (ROOT / 'scripts/build-program.py').read_text() + (ROOT / 'css/program.css').read_text()
    text += ''.join(chr(n) for n in range(32, 127))
    for family in ('NotoSansJP', 'NotoSerifJP'):
        base = 'https://raw.githubusercontent.com/google/fonts/main/ofl/' + family.lower() + '/'
        for remote, local in ((family + '%5Bwght%5D.ttf', family + '.ttf'), ('OFL.txt', family + '-OFL.txt')):
            path = args.font_source / local
            if not path.exists():
                with urlopen(base + remote, timeout=60) as response:
                    path.write_bytes(response.read())
        (destination / (family + '-OFL.txt')).write_bytes((args.font_source / (family + '-OFL.txt')).read_bytes())
    for family, weight, label in [('NotoSansJP', 400, 'Regular'), ('NotoSansJP', 500, 'Medium'), ('NotoSerifJP', 400, 'Regular'), ('NotoSerifJP', 500, 'Medium')]:
        font = instantiateVariableFont(TTFont(args.font_source / (family + '.ttf')), {'wght': weight}, inplace=True)
        options = Options()
        options.name_IDs = ['*']
        options.name_legacy = True
        subset = Subsetter(options=options)
        subset.populate(text=text)
        subset.subset(font)
        preserve_fullwidth_tilde(font)
        font.save(destination / (family + '-' + label + '.ttf'))
    print('Prepared 4 program font files and 2 OFL licenses.')


if __name__ == '__main__':
    main()
