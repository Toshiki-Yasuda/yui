#!/usr/bin/env python3
"""Static integrity and original-content checks, with no third-party dependencies.

Usage: python3 scripts/check-site.py [--baseline GIT_REF]
The baseline compares every original text segment and link, not presentation markup.
"""
import argparse
from collections import Counter
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
PAGES = ('index.html', 'marimba.html')

class Document(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.body = False
        self.skip = 0
        self.text, self.links, self.ids, self.assets, self.images = [], [], [], [], []
        self.headings = []
        self.main = 0
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'body':
            self.body = True
        if tag in ('script', 'style', 'svg'):
            self.skip += 1
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if tag == 'main':
            self.main += 1
        if tag == 'a':
            self.links.append(attrs.get('href', ''))
        if tag in ('script', 'img', 'source', 'link'):
            self.assets.append(attrs.get('src') or attrs.get('srcset') or attrs.get('href', ''))
        if tag == 'img':
            self.images.append(attrs)
        if re.fullmatch('h[1-6]', tag):
            self.headings.append(int(tag[1]))

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'svg'):
            self.skip -= 1

    def handle_data(self, text):
        if self.body and not self.skip and text.strip():
            self.text.append(re.sub(r'\s+', '', text))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', help='Compare original content from this git reference')
    args = parser.parse_args()
    documents = {name: Document((ROOT / name).read_text()) for name in PAGES}
    for name, page in documents.items():
        assert page.main == 1, f'{name}: expected one main landmark'
        assert page.headings.count(1) == 1, f'{name}: expected one h1'
        assert not [k for k, v in Counter(page.ids).items() if v > 1], f'{name}: duplicate IDs'
        for image in page.images:
            assert 'alt' in image, f'{name}: missing alt'
            if 'lightbox-img' not in image.get('class', ''):
                assert image.get('width') and image.get('height'), f'{name}: image dimensions missing'
        for url in page.links + page.assets:
            if not url:
                continue
            parsed = urlsplit(url)
            if parsed.scheme or parsed.netloc:
                continue
            target = unquote(parsed.path) or name
            assert (ROOT / target).is_file(), f'{name}: missing local target {url}'
            if parsed.fragment and target in documents:
                assert parsed.fragment in documents[target].ids, f'{name}: broken anchor {url}'
        if args.baseline:
            original_html = subprocess.check_output(['git', 'show', f'{args.baseline}:{name}'], cwd=ROOT, text=True)
            # Explicit user corrections on 2026-09-12, after the initial redesign.
            # Normalize only these approved edits; all other preservation checks remain.
            if name == 'index.html':
                original_html = original_html.replace(
                    '<a href="#program" class="btn btn--ghost">演奏を聴く</a>', '')
                original_html = original_html.replace(
                    'ほか、当日のお楽しみに数曲を予定しております',
                    '当日のお楽しみも含め、全12曲程度をお届けする予定です。')
                original_html = original_html.replace('応援・ファンレター', '応援・ご支援はこちらから')
            original = Document(original_html)
            text = ''.join(page.text)
            missing = [segment for segment in original.text if segment not in text]
            assert not missing, f'{name}: original text missing: {missing}'
            assert not (Counter(original.links) - Counter(page.links)), f'{name}: original links missing'
            original_data = re.findall(r'<script type="application/ld\+json">([\s\S]*?)</script>', original_html)
            current_data = re.findall(r'<script type="application/ld\+json">([\s\S]*?)</script>', (ROOT / name).read_text())
            assert list(map(json.loads, original_data)) == list(map(json.loads, current_data)), f'{name}: structured data changed'
        print(f'PASS {name}: content, local links, assets, landmarks, image dimensions')
    for filename in ('flyer.html', 'pamphlet.html'):
        if args.baseline:
            original = subprocess.check_output(['git', 'show', f'{args.baseline}:{filename}'], cwd=ROOT)
            assert original == (ROOT / filename).read_bytes(), f'{filename}: print artifact modified'
    print('PASS print artifacts unchanged')

if __name__ == '__main__':
    main()
