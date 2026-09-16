#!/usr/bin/env python3
"""Build an independent six-panel concert program, preserving the bifold."""
from pathlib import Path
from html import escape
import argparse
import json
import os
import io
import re
import subprocess

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault('XDG_CACHE_HOME', str(ROOT / 'tmp/pdfs/program/cache'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--paper', choices=['a4', 'a3', 'a2'], default='a3')
    args = parser.parse_args()
    from weasyprint import HTML
    from pypdf import PdfReader, PdfWriter, Transformation
    from pypdf.generic import RectangleObject, DictionaryObject, NameObject, DecodedStreamObject
    data = json.loads((ROOT / 'プログラム/source/program.json').read_text())
    overrides=json.loads((ROOT/'プログラム/source/program-trifold-overrides.json').read_text())
    for artist in data['artists']:
        if artist['name'] in overrides['artist_bios']:
            artist['bio']=overrides['artist_bios'][artist['name']]
    if args.paper == 'a4':
        revised = json.loads((ROOT/'プログラム/source/program-trifold-a4-part2.json').read_text())
        data['parts'][1]['songs'] = revised['songs']
    from fontTools.ttLib import TTFont
    cmap=TTFont(ROOT/'fonts/program-trifold/NotoSerifJP-Regular.ttf').getBestCmap()
    body_text=''.join(p for part in data['parts'] for song in part['songs'] for p in song['paragraphs'])+''.join(p for a in data['artists'] for p in a['bio'])
    missing={c for c in body_text if not c.isspace() and ord(c) not in cmap}
    assert not missing, f'Trifold body font missing glyphs: {missing}'
    e = escape
    event = data['event']
    year,month,day,weekday=re.fullmatch(r'(\d+)年(\d+)月(\d+)日（(.)）',event['date']).groups()
    width, height, size, leading = {'a4':(99,210,9,12),'a3':(140,297,12.5,18),'a2':(198,420,15,22)}[args.paper]
    cover_asset = 'images/program-trifold/cover-narrow-v2.png' if args.paper=='a4' else 'images/program/cover-art-v2.png'
    panels = []
    venue = '<br>'.join(e(x) for x in event['venue'])
    panels.append(f'''<section class="panel cover"><header><p>{e(event['series'])}</p><h2>午後のコンサート</h2></header><img class="cover-art" src="{cover_asset}" alt="結 Yuiと3人の演奏の水彩画"><div class="event"><p class="date">{year}年 <strong>{month}月{day}日</strong>（{e(weekday)}）</p><p>{e(event['open'])} 開場 ／ {e(event['start'])} 開演</p><p class="venue">{venue}</p></div></section>''')
    for part, songs, continuation in [(data['parts'][0],data['parts'][0]['songs'][:3],False),(data['parts'][0],data['parts'][0]['songs'][3:],True),(data['parts'][1],data['parts'][1]['songs'][:3],False),(data['parts'][1],data['parts'][1]['songs'][3:],True)]:
        content = ''
        for song in songs:
            credits = '<br>'.join(e(c) for c in song['credits'])
            paragraphs = ''.join(f'<p class="note">{e(p)}</p>' for p in song['paragraphs'])
            inline = song['id'] not in ('p1-01','p1-04','p2-03')
            heading = e(song['title']) + (f' <span class="inline-credit">{credits}</span>' if inline else '')
            credit_line = '' if inline else f'<p class="credits">{credits}</p>'
            content += f'''<article class="song" data-song-id="{song['id']}"><h3><span class="number">{song['number']:02d}</span>{heading}</h3>{credit_line}{paragraphs}</article>'''
        if part['number']==1 and continuation:
            content += f'<aside class="intermission">{e(part["intermission"])}</aside>'
        page = len(panels)
        panels.append(f'''<section class="panel notes"><header class="heading"><span>Program notes</span><h2>プログラム　第{part['number']}部</h2></header>{content}<footer><span>午後のコンサート　結</span><span>{page:02d}</span></footer></section>''')
    artists = ''
    for artist, key in zip(data['artists'], ['yasuda','tanaka','tsuchida']):
        bio = ''.join(f'<p class="bio">{e(p)}</p>' for p in artist['bio'])
        portrait=f'<img src="images/program/portrait-{key}-v2.png" alt="{e(artist["name"])}の水彩画">'
        if args.paper=='a4':
            artists += f'''<article class="artist"><header><h3>{e(artist['name'])}</h3><i>{e(artist['instrument'])}</i></header>{bio}</article>'''
        else:
            artists += f'''<article class="artist"><header>{portrait}<div><h3>{e(artist['name'])}</h3><i>{e(artist['instrument'])}</i></div></header>{bio}</article>'''
    supporters = ' ／ '.join(e(x) for x in event['supporters'])
    panels.append(f'''<section class="panel artists"><header class="heading"><span>Artists</span><h2>出演者</h2></header>{artists}<div class="organizers"><p>主催　{e(event['organizer'])}</p><p>後援　{supporters}</p></div></section>''')
    css = f''':root{{--w:{width}mm;--h:{height}mm;--body:{size}pt;--leading:{leading}pt;}} @page{{size:{width}mm {height}mm;margin:0;}}'''
    extra='<link rel="stylesheet" href="css/program-trifold-a4.css">' if args.paper=='a4' else ''
    markup = '<!doctype html><html lang="ja"><meta charset="utf-8"><title>結・三つ折り当日プログラム</title><link rel="stylesheet" href="css/program-trifold.css">'+extra+'<style>'+css+'</style><body>'+''.join(panels)+'</body></html>'
    html_path = ROOT / ('program-trifold-a4.html' if args.paper=='a4' else 'program-trifold.html')
    html_path.write_text(markup)
    doc = HTML(filename=str(html_path)).render()
    if len(doc.pages)!=6:
        raise ValueError(f'Expected 6 panels, got {len(doc.pages)}')
    issues=[]
    mm=96/25.4
    def walk(box,in_footer=False):
        if type(box).__name__=='AbsolutePlaceholder':
            box=box._box
        in_footer=in_footer or (box.element is not None and box.element.tag=='footer')
        yield box,in_footer
        for child in getattr(box,'children',[]):
            yield from walk(child,in_footer)
    for number,page in enumerate(doc.pages,1):
        body_bottom=0
        footer_top=height
        for box,is_footer in walk(page._page_box):
            if type(box).__name__=='TextBox':
                x,y,w,h=box.position_x/mm,box.position_y/mm,box.width/mm,box.height/mm
                if min(x,y,width-x-w,height-y-h)<5:
                    issues.append({'panel':number,'text':box.text,'bounds':[x,y,w,h]})
                if is_footer:
                    footer_top=min(footer_top,y)
                else:
                    body_bottom=max(body_bottom,y+h)
        if number in (2,3,4,5) and footer_top-body_bottom<3:
            issues.append({'panel':number,'footer_gap_mm':footer_top-body_bottom})
    (ROOT/'tmp/pdfs/program-trifold/layout.json').write_text(json.dumps(issues,ensure_ascii=False,indent=2))
    if issues:
        raise ValueError(f'Text exceeds panel safe region: {issues[:3]}')
    raw=doc.write_pdf()
    pdf=PdfReader(io.BytesIO(raw))
    norm=lambda s: ''.join(s.split())
    full=norm(''.join(p.extract_text() for p in pdf.pages))
    for part in data['parts']:
        for song in part['songs']:
            for text in [song['title'],*song['credits'],*song['paragraphs']]:
                assert norm(text) in full, 'Missing text: '+text[:30]
    for artist in data['artists']:
        for text in [artist['name'],*artist['bio']]:
                assert norm(text) in full, 'Missing biography: '+text[:30]
    for text in [event['date'],event['series'],*event['venue'],event['open'],event['start'],event['organizer'],*event['supporters']]:
        assert norm(text) in full, 'Missing event information: '+text
    out=ROOT/'output/pdf'
    reading=out/f'yui-program-trifold-{args.paper}-reading.pdf'
    reading.write_bytes(raw)
    writer=PdfWriter()
    pt=72/25.4
    print_orders = ([0,1,2],[3,4,5]) if args.paper == 'a4' else ([4,5,0],[1,2,3])
    for order in print_orders:
        target=writer.add_blank_page(width=width*3*pt,height=height*pt)
        forms=DictionaryObject()
        commands=[]
        for column,index in enumerate(order):
            # Isolate each panel's fonts, alpha masks and graphics state.
            source=pdf.pages[index]
            form=DecodedStreamObject()
            form.set_data(source.get_contents().get_data())
            form.update({NameObject('/Type'):NameObject('/XObject'),NameObject('/Subtype'):NameObject('/Form'),NameObject('/BBox'):RectangleObject(source.mediabox),NameObject('/Resources'):source['/Resources'].clone(writer)})
            name=f'/Panel{column}'
            forms[NameObject(name)]=writer._add_object(form)
            commands.append(f'q 1 0 0 1 {column*width*pt:.8f} 0 cm {name} Do Q')
        target[NameObject('/Resources')]=DictionaryObject({NameObject('/XObject'):forms})
        stream=DecodedStreamObject()
        stream.set_data('\n'.join(commands).encode())
        target[NameObject('/Contents')]=writer._add_object(stream)
        target.trimbox=RectangleObject([0,0,width*3*pt,height*pt])
    writer.add_metadata({'/Title':'結 当日プログラム 三つ折り','/Subject':f'{args.paper.upper()} landscape Z-fold, panel order {print_orders}, actual size. Body {size}pt.'})
    printing=out/f'yui-program-trifold-{args.paper}.pdf'
    writer.write(printing)
    for page_number,order in enumerate(print_orders,1):
        for column,index in enumerate(order):
            extracted=subprocess.check_output(['pdftotext','-f',str(page_number),'-l',str(page_number),'-r','72','-x',str(round(column*width*pt)),'-y','0','-W',str(round(width*pt)),'-H',str(round(height*pt)),'-layout',str(printing),'-'],text=True)
            expected=subprocess.check_output(['pdftotext','-f',str(index+1),'-l',str(index+1),'-layout',str(reading),'-'],text=True)
            assert norm(extracted)==norm(expected),f'Imposed panel {index+1} text differs'
    print(f'PASS 6 panels; 11 complete notes and all biographies; body {size}pt/{leading}pt.\n{reading}\n{printing}')


if __name__=='__main__':
    main()
