#!/usr/bin/env python3
"""Verify program wording, physical output, imposition and measured layout.

Run after scripts/build-program.py with the same dedicated Python environment.
Poppler pdftotext and pdffonts must be available in PATH. Visual proofing and a
physical test fold remain separate steps; this script reports measurable facts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess

from fontTools.ttLib import TTFont
from pypdf import PdfReader
from program_pdf import MM, OUTPUTS, source_hash

ROOT = Path(__file__).resolve().parent.parent


def normalized(text: str) -> str:
    """Ignore PDF line wrapping/spacing only; preserve every other character."""
    return re.sub(r"\s+", "", text)


def require(condition, message):
    if not condition:
        raise ValueError(message)


@dataclass
class Element:
    tag: str
    attrs: dict = field(default_factory=dict)
    children: list = field(default_factory=list)

    def text(self):
        return "".join(child if isinstance(child, str) else child.text() for child in self.children)

    def descendants(self):
        yield self
        for child in self.children:
            if isinstance(child, Element):
                yield from child.descendants()

    def has_class(self, name):
        return name in self.attrs.get("class", "").split()


class ProgramHTML(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = Element("document")
        self.stack = [self.root]
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = Element(tag, dict(attrs))
        self.stack[-1].children.append(node)
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Element(tag, dict(attrs)))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, text):
        self.stack[-1].children.append(text)


def _check_source_and_html(source, html):
    parts = source["parts"]
    require([part["number"] for part in parts] == [1, 2], "Expected Part 1 then Part 2")
    require([len(part["songs"]) for part in parts] == [5, 6], "Expected 5 + 6 songs")
    songs = [song for part in parts for song in part["songs"]]
    require(len({song["id"] for song in songs}) == 11, "Song ids must be unique")
    source_pdfs = list((ROOT / "プログラム").glob("*.pdf"))
    require(any(hashlib.sha256(path.read_bytes()).hexdigest() == source["source_sha256"] for path in source_pdfs),
            "The original PDF no longer matches the approved source hash")
    for part in parts:
        require([song["number"] for song in part["songs"]] == list(range(1, len(part["songs"]) + 1)),
                f"Part {part['number']}: song numbers are out of order")
    tree = ProgramHTML(html).root
    pages = [node for node in tree.descendants() if node.has_class("page") and node.tag == "article"]
    require([page.attrs.get("data-page") for page in pages] == ["1", "2", "3", "4"],
            "HTML must contain four reading pages in order")
    html_songs = [node for node in tree.descendants() if node.has_class("song")]
    require([node.attrs.get("data-song-id") for node in html_songs] == [song["id"] for song in songs],
            "HTML song ids/order differ from the approved source")
    for song, node in zip(songs, html_songs):
        body = normalized("".join(song["paragraphs"]))
        require(hashlib.sha256(body.encode("utf-8")).hexdigest() == song["source_body_sha256"],
                f"{song['id']}: source body hash differs")
        notes = [child for child in node.descendants() if child.has_class("note")]
        require([normalized(n.text()) for n in notes] == [normalized(p) for p in song["paragraphs"]],
                f"{song['id']}: HTML paragraphs differ from source")
        text = normalized(node.text())
        cursor = 0
        for value in [song["title"], *song["credits"], *song["paragraphs"]]:
            value = normalized(value)
            position = text.find(value, cursor)
            require(position >= 0, f"{song['id']}: HTML wording/order differs near {value[:24]!r}")
            cursor = position + len(value)
    full_html = normalized(tree.text())
    for part in parts:
        if part.get("intermission"):
            require(normalized(part["intermission"]) in full_html, "HTML intermission wording differs from source")
    for artist in source["artists"]:
        for value in [artist["name"], artist["instrument"], *artist["bio"]]:
            require(normalized(value) in full_html, f"HTML missing profile text for {artist['name']}: {value[:24]}")
    for node in tree.descendants():
        if node.tag == "img":
            require(node.attrs.get("alt"), "An HTML image has no alt text")
            require((ROOT / node.attrs.get("src", "")).is_file(), "An HTML image source is missing")
    return songs, tree


def _check_pdf_content(source, pdf):
    event = source["event"]
    cover_text = normalized(pdf.pages[0].extract_text())
    # Decorative lettering is now image artwork. Its exact asset was visually
    # proofed; all practical event information remains searchable PDF text.
    artwork = json.loads((ROOT / 'images/program/cover-art-review.json').read_text())
    require(hashlib.sha256((ROOT / artwork['asset']).read_bytes()).hexdigest() == artwork['sha256'],
            'Cover artwork changed: repeat visual lettering/identity review')
    for value in [event["series"], *event["venue"], event["open"] + "開場", event["start"] + "開演"]:
        require(normalized(value) in cover_text, f"Cover information differs: {value}")
    for value in re.sub(r"[〜()]", " ", event["title"]).split():
        require(normalized(value) in cover_text or value in artwork['visually_verified_text'], f"Cover title missing: {value}")
    date = re.fullmatch(r"(\d+)年(\d+)月(\d+)日（(.)）", event["date"])
    require(date is not None, "Unsupported original date format")
    year, month, day, weekday = date.groups()
    require(normalized(f"{year}年{month}月{day}日（{weekday}）") in cover_text, "Cover date differs from source")
    for part, page in zip(source["parts"], pdf.pages[1:3]):
        text = normalized(page.extract_text())
        require("\ufffd" not in text and "\x00" not in text, f"Part {part['number']}: invalid extracted glyph")
        cursor = 0
        for song in part["songs"]:
            for value in [song["title"], *song["credits"], "".join(song["paragraphs"])]:
                value = normalized(value)
                position = text.find(value, cursor)
                require(position >= 0, f"{song['id']}: PDF text missing/changed/out of order near {value[:32]!r}")
                cursor = position + len(value)
            body = normalized("".join(song["paragraphs"]))
            require(text.count(body) == 1, f"{song['id']}: PDF body duplicated")
        if part.get("intermission"):
            require(normalized(part["intermission"]) in text, "PDF intermission wording differs from source")
    profile_text = normalized(pdf.pages[3].extract_text())
    for artist in source["artists"]:
        for value in [artist["name"], artist["instrument"], *artist["bio"]]:
            require(normalized(value) in profile_text, f"PDF profile text missing for {artist['name']}: {value[:24]}")
    for value in [event["organizer"], *event["supporters"]]:
        require(normalized(value) in profile_text, f"PDF organizer/supporter missing: {value}")


def _box_mm(box):
    return [float(value) / MM for value in box]


def _same_box(actual, expected):
    return all(abs(a - b) <= 0.1 for a, b in zip(actual, expected))


def _crop_text(path, number, x_mm=0, y_mm=0):
    # Text is >=5 mm inside trim, so rounding Poppler's integer crop values is safe.
    command = ["pdftotext", "-f", str(number), "-l", str(number), "-r", "72",
               "-x", str(round(x_mm * MM)), "-y", str(round(y_mm * MM)),
               "-W", str(round(210 * MM)), "-H", str(round(297 * MM)),
               "-layout", "-enc", "UTF-8", str(path), "-"]
    return normalized(subprocess.check_output(command, text=True))


def _check_imposition():
    out = ROOT / "output/pdf"
    reading = [_crop_text(out / "yui-program-a4.pdf", n) for n in range(1, 5)]
    for filename, spec in OUTPUTS.items():
        if filename == "yui-program-a4.pdf":
            continue
        bleed = 3 if "bleed" in filename else 0
        for sheet, numbers in enumerate(spec["order"], 1):
            for side, number in enumerate(numbers):
                text = _crop_text(out / filename, sheet, side * 210 + bleed, bleed)
                require(text == reading[number - 1],
                        f"{filename}, sheet {sheet}, {'left' if side == 0 else 'right'}: differs from reading page {number}")


def _check_fonts(tree):
    fonts = list((ROOT / "fonts/program").glob("*.ttf"))
    require(fonts, "No dedicated print fonts")
    available = set()
    for path in fonts:
        with TTFont(path) as font:
            available.update(font.getBestCmap())
    bodies = [node for node in tree.descendants() if node.tag == "body"]
    required = {ord(char) for node in bodies for char in node.text() if not char.isspace()}
    missing = required - available
    require(not missing, "Missing font characters: " + " ".join(f"U+{code:04X}" for code in sorted(missing)))
    embedded = {}
    for filename in OUTPUTS:
        lines = subprocess.check_output(["pdffonts", str(ROOT / "output/pdf" / filename)], text=True).splitlines()[2:]
        require(lines, f"{filename}: no PDF fonts")
        names = []
        for line in lines:
            fields = line.split()
            require(fields[-5] == "yes", f"{filename}: font not embedded: {line}")
            require(fields[-3] == "yes", f"{filename}: missing font Unicode map: {line}")
            names.append(fields[0])
        embedded[filename] = names
    return embedded


def _check_layout(report, songs, digest):
    require(report["source_sha256"] == digest, "Layout report is stale")
    require(report["page_count"] == 4, "Layout must contain four pages")
    require(not report["issues"], "Layout issues: " + json.dumps(report["issues"][:3], ensure_ascii=False))
    by_song = {song["id"]: [] for song in songs}
    minimum = []
    for page in report["pages"]:
        require(page["text_boxes"], f"Page {page['page']}: no text boxes recorded")
        minimum.append(page["minimum_text_clearance_mm"])
        if page["page"] in (2, 3):
            require(len(page["columns"]) == 2, f"Page {page['page']}: expected two body columns")
        for box in page["text_boxes"]:
            require(box["trim_clearance_mm"] >= 4.9, f"Page {page['page']}: text too close to trim/fold")
            if box["song_id"] is not None:
                require(box["column"] is not None, f"{box['song_id']}: song text has no column")
                require(box.get("column_clearance_mm", -1) >= -0.15, f"{box['song_id']}: text crosses a column boundary")
            if box["note"] is not None:
                require(box["font_size_pt"] >= 10.49, f"{box['song_id']}: body below 10.5pt")
        for note in page["notes"]:
            require(note["song_id"] in by_song, f"Unknown song id in layout: {note['song_id']}")
            by_song[note["song_id"]].append(normalized(note["text"]))
    for song in songs:
        require(by_song[song["id"]] == [normalized(p) for p in song["paragraphs"]],
                f"{song['id']}: rendered paragraph content differs from source")
    return min(minimum)


def main():
    source = json.loads((ROOT / "プログラム/source/program.json").read_text())
    digest = source_hash(ROOT)
    songs, tree = _check_source_and_html(source, (ROOT / "program.html").read_text())
    print("PASS original PDF hash; 11 songs, complete paragraphs, credits and HTML order")
    report_path = ROOT / "tmp/pdfs/program/layout-report.json"
    report = json.loads(report_path.read_text())
    minimum = _check_layout(report, songs, digest)
    print(f"PASS layout: 4 pages, body >=10.5pt, 2 columns per part; minimum trim/fold clearance {minimum:.2f} mm")
    for filename, spec in OUTPUTS.items():
        path = ROOT / "output/pdf" / filename
        pdf = PdfReader(path)
        require(len(pdf.pages) == len(spec["order"]), f"{filename}: wrong page count")
        require(pdf.metadata.get("/YuiSourceSHA256") == digest, f"{filename}: PDF is stale")
        require(pdf.metadata.get("/YuiPageOrder") == ",".join("|".join(map(str, p)) for p in spec["order"]),
                f"{filename}: wrong page-order metadata")
        require(hashlib.sha256(path.read_bytes()).hexdigest() == report["outputs"][filename]["sha256"],
                f"{filename}: does not match the measured build")
        outer = [0, 0, *spec["size_mm"]]
        trim = [3, 3, 423, 300] if "bleed" in filename else outer
        for number, page in enumerate(pdf.pages, 1):
            for name, expected in (("mediabox", outer), ("cropbox", outer), ("bleedbox", outer), ("trimbox", trim)):
                require(_same_box(_box_mm(getattr(page, name)), expected), f"{filename} page {number}: wrong {name}")
            require(page.rotation == 0, f"{filename} page {number}: unexpected page rotation")
        if filename == "yui-program-a4.pdf":
            _check_pdf_content(source, pdf)
        print(f"PASS {filename}: current source, dimensions and PDF page boxes")
    _check_imposition()
    print("PASS A3 imposition text by physical region: outside 4|1, inside 2|3, including bleed")
    embedded = _check_fonts(tree)
    print("PASS all HTML glyphs covered; all PDF fonts embedded with Unicode maps")
    for image in report["images"]:
        ppi = min(image["effective_ppi"])
        print(f"INFO image page {image['page']}: {image['src']}, {ppi:.1f} effective ppi")
    summary = {"status": "passed", "source_sha256": digest, "song_count": len(songs),
               "minimum_text_clearance_mm": minimum, "embedded_fonts": embedded,
               "images": report["images"], "imposition": [[4, 1], [2, 3]],
               "physical_proof_checked": False}
    (report_path.parent / "verification-report.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
