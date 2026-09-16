#!/usr/bin/env python3
"""Build the program HTML and all print editions from one checked manuscript."""
from pathlib import Path
from html import escape
import argparse
import json
import os
import re

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault('XDG_CACHE_HOME', str(ROOT / 'tmp/pdfs/program/cache'))


def text(value):
    return escape(str(value), quote=True)


def footer(left, right):
    return f'<footer class="page-footer"><span>{left}</span><span>{right}</span></footer>'


def song_markup(song):
    title = text(song['title'])
    if song['id'] == 'p1-01':
        title = title.replace(' プレリュード', '<br>プレリュード')
    credits = ''.join(f'<span>{text(c)}</span>' for c in song['credits'])
    paragraphs = ''.join(f'<p class="note">{text(p)}</p>' for p in song['paragraphs'])
    compact = song['id'] not in ('p1-01', 'p1-04', 'p2-03')
    heading = title + (f' <span class="inline-credits">{credits}</span>' if compact else '')
    credit_line = '' if compact else f'<p class="credits">{credits}</p>'
    return f'''<article class="song {'compact-credit' if compact else ''}" data-song-id="{song['id']}"><header class="song-heading"><span class="song-number">{song['number']:02d}</span><h3>{heading}</h3></header>{credit_line}<div class="song-copy">{paragraphs}</div></article>'''


def part_markup(part):
    number = part['number']
    left = ''.join(song_markup(s) for s in part['songs'][:3])
    right = ''.join(song_markup(s) for s in part['songs'][3:])
    if part.get('intermission'):
        right += f'<aside class="intermission"><span class="intermission-label">INTERMISSION</span><p>{text(part["intermission"])}</p></aside>'
    return f'''<article class="page page-notes part-{number}" data-page="{number+1}" id="part-{number}"><section class="trim"><header class="section-heading"><span class="section-kicker">Program notes</span><h2>プログラム <span>第{number}部</span></h2><span class="section-count">{len(part['songs']):02d} pieces</span></header><div class="columns"><div class="column">{left}</div><div class="column">{right}</div></div>{footer('午後のコンサート <span class="footer-yui">結</span>',f'{number:02d}')}</section></article>'''


def render_html(data):
    event = data['event']
    year, month, day, weekday = re.fullmatch(r'(\d+)年(\d+)月(\d+)日（(.)）', event['date']).groups()
    venue = '<br>'.join(f'<strong>{text(line)}</strong>' if i else text(line) for i, line in enumerate(event['venue']))
    concert_title = event['title'].split('〜')[0].strip()
    cover = f'''<article class="page page-cover" data-page="1" id="cover"><section class="trim"><header class="cover-heading"><p>{text(event['series'])}</p><h2>{text(concert_title)}</h2></header><img class="cover-art" src="images/program/cover-art-v2.png" width="1054" height="1492" alt="結 Yui：3人の演奏を描く水彩と筆文字の表紙"><div class="cover-details"><p class="cover-date"><span>{year}年</span><b>{month}<em>月</em>{day}<em>日</em></b><small>（{text(weekday)}）</small></p><p class="cover-time">{text(event['open'])} 開場 <span>／</span> {text(event['start'])} 開演</p><div class="cover-rule"></div><p class="cover-venue">{venue}</p></div></section></article>'''
    assets = ['images/program/portrait-yasuda-v2.png', 'images/program/portrait-tanaka-v2.png', 'images/program/portrait-tsuchida-v2.png']
    sizes = [(1254,1254), (1254,1254), (1254,1254)]
    artists = []
    for idx, artist in enumerate(data['artists']):
        paragraphs = ''.join(f'<p>{text(p)}</p>' for p in artist['bio'])
        width, height = sizes[idx]
        portrait = f'<figure><img src="{assets[idx]}" width="{width}" height="{height}" alt="{text(artist["name"])}の演奏を描いた水彩画"></figure>'
        name = f'<header><h3>{text(artist["name"])}</h3><span>{text(artist["instrument"])}</span></header>'
        if idx == 0:
            rest = ''.join(f'<p>{text(p)}</p>' for p in artist['bio'][1:])
            artists.append(f'''<article class="artist artist-1"><div class="lead-profile-top">{portrait}<div class="artist-copy">{name}<div class="biography"><p>{text(artist['bio'][0])}</p></div></div></div><div class="biography lead-full-copy">{rest}</div></article>''')
        else:
            artists.append(f'''<article class="artist artist-{idx+1}">{portrait}<div class="artist-copy">{name}<div class="biography">{paragraphs}</div></div></article>''')
    supporters = '<span>／</span>'.join(text(s) for s in event['supporters'])
    back = f'''<article class="page page-artists" data-page="4" id="artists"><section class="trim"><header class="section-heading"><span class="section-kicker">Artists</span><h2>出演者</h2></header><div class="artist-list">{''.join(artists)}</div><img class="back-vignette" src="images/program/marimba-vignette-v2.png" alt="マリンバの鍵盤とマレットの小さな水彩画"><div class="back-signature"><span>結</span><i>Yui</i></div><dl class="organizers"><div><dt>主催</dt><dd>{text(event['organizer'])}</dd></div><div><dt>後援</dt><dd>{supporters}</dd></div></dl>{footer(f'{year}.{month}.{day}', 'CONCERT PROGRAM')}</section></article>'''
    return f'''<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="description" content="午後のコンサート 結。当日配布プログラム・曲目紹介全文。"><title>配布プログラム｜午後のコンサート 結</title><link rel="icon" href="favicon.svg"><link rel="stylesheet" href="css/program.css"></head><body>
<header class="preview-header"><div><a href="index.html" class="home-link">結</a><h1>当日配布プログラム<small>A3二つ折り・A4仕上がり</small></h1></div><nav aria-label="PDFダウンロード"><a href="output/pdf/yui-program-a4.pdf" download>閲覧用 A4</a><a href="output/pdf/yui-program-a3.pdf" download>印刷用 A3</a><a href="output/pdf/yui-program-a3-bleed.pdf" download>塗り足し付き</a></nav></header>
<main class="preview-pages"><div class="page-frame">{cover}</div><div class="page-frame">{part_markup(data['parts'][0])}</div><div class="page-frame">{part_markup(data['parts'][1])}</div><div class="page-frame">{back}</div></main>
<footer class="preview-footer"><p>曲目紹介は原稿の全文を掲載しています。</p><p>印刷はA3版を原寸100%・両面短辺綴じで。中央で二つ折りにしてください。</p><a href="docs/program-production.md">制作・印刷メモ</a></footer>
</body></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--html-only', action='store_true')
    args = parser.parse_args()
    data = json.loads(next(ROOT.glob('*/source/program.json')).read_text())
    (ROOT / 'program.html').write_text(render_html(data))
    if not args.html_only:
        from program_pdf import render_and_export, source_hash
        render_and_export(ROOT, source_hash(ROOT))


if __name__ == '__main__':
    main()
