"""Render the program once, then export reading and folded print editions.

All lengths in the layout report are millimetres from the master page's top
left. PDF boxes use PDF's bottom-left origin. A master page is 216 x 303 mm,
with its 210 x 297 mm trim rectangle inset by 3 mm on every side.
"""
from __future__ import annotations

import copy
import hashlib
from html.parser import HTMLParser
import io
import json
import os
from pathlib import Path

MM = 72 / 25.4
CSS_MM = 96 / 25.4
OUTPUTS = {
    "yui-program-a4.pdf": {"size_mm": [210, 297], "order": [[1], [2], [3], [4]]},
    "yui-program-a3.pdf": {"size_mm": [420, 297], "order": [[4, 1], [2, 3]]},
    "yui-program-a3-bleed.pdf": {"size_mm": [426, 303], "order": [[4, 1], [2, 3]]},
}


def source_hash(root: Path) -> str:
    """Hash named inputs, so asset additions/removals also invalidate PDFs."""
    paths = [root / p for p in (
        "プログラム/source/program.json", "scripts/build-program.py",
        "scripts/program_pdf.py", "css/program.css",
    )]
    for folder in ("images/program", "fonts/program"):
        directory = root / folder
        if not directory.is_dir():
            raise FileNotFoundError(directory)
        paths.extend(p for p in directory.rglob("*") if p.is_file() and not p.name.startswith("."))
    # The generated HTML is not itself hashed, but all local images it uses are.
    # This includes original site portraits that remain outside images/program.
    class ImageSources(HTMLParser):
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == "img":
                src = attrs.get("src", "")
                if src and ":" not in src:
                    paths.append(root / src)
    html_path = root / "program.html"
    if html_path.is_file():
        ImageSources().feed(html_path.read_text())
    digest = hashlib.sha256()
    for path in sorted(set(paths), key=lambda p: p.relative_to(root).as_posix()):
        name = path.relative_to(root).as_posix().encode("utf-8")
        content = path.read_bytes()
        digest.update(len(name).to_bytes(8, "big"))
        digest.update(name)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def _bounds(box) -> list[float]:
    return [round(value / CSS_MM, 4) for value in (
        box.content_box_x(), box.content_box_y(), box.width, box.height,
    )]


def _clearance(bounds, container):
    x, y, w, h = bounds
    cx, cy, cw, ch = container
    return min(x - cx, y - cy, cx + cw - x - w, cy + ch - y - h)


def _collect_layout(document, root: Path, digest: str) -> dict:
    from PIL import Image

    report = {"source_sha256": digest, "page_count": len(document.pages),
              "coordinate_system": "master top-left, mm", "pages": [],
              "images": [], "issues": []}
    for page_number, page in enumerate(document.pages, 1):
        record = {"page": page_number, "size_mm": [round(page.width / CSS_MM, 4), round(page.height / CSS_MM, 4)],
                  "trim_mm": [3, 3, 210, 297], "columns": [], "text_boxes": [], "notes": [], "reserved_regions": []}
        note_ids = {}
        seen_columns = set()
        seen_regions = set()

        def walk(box, song_id=None, note_id=None, column_id=None):
            if type(box).__name__ == "AbsolutePlaceholder":
                box = box._box
            element = box.element
            classes = set(element.get("class", "").split()) if element is not None else set()
            kind = type(box).__name__
            is_container = kind not in {"TextBox", "LineBox"}
            if element is not None and "song" in classes:
                song_id = element.get("data-song-id")
            region = next((name for name in ("page-footer", "section-heading") if name in classes), None)
            if region and is_container and id(element) not in seen_regions:
                seen_regions.add(id(element))
                record["reserved_regions"].append({"role": region, "bounds_mm": _bounds(box)})
            if element is not None and "column" in classes and is_container:
                element_id = id(element)
                if element_id not in seen_columns:
                    seen_columns.add(element_id)
                    column_id = len(record["columns"]) + 1
                    record["columns"].append({"column": column_id, "bounds_mm": _bounds(box)})
            if element is not None and "note" in classes and is_container:
                element_id = id(element)
                if element_id not in note_ids:
                    note_id = len(record["notes"]) + 1
                    note_ids[element_id] = note_id
                    record["notes"].append({"note": note_id, "song_id": song_id,
                        "column": column_id, "bounds_mm": _bounds(box),
                        "font_size_pt": round(box.style["font_size"] * 72 / 96, 4), "text": ""})
                else:
                    note_id = note_ids[element_id]
            if kind == "TextBox":
                bounds = _bounds(box)
                item = {"text": box.text, "bounds_mm": bounds, "song_id": song_id,
                        "note": note_id, "column": column_id,
                        "font_size_pt": round(box.style["font_size"] * 72 / 96, 4),
                        "trim_clearance_mm": round(_clearance(bounds, record["trim_mm"]), 4)}
                if column_id is not None:
                    item["column_clearance_mm"] = round(_clearance(bounds, record["columns"][column_id - 1]["bounds_mm"]), 4)
                record["text_boxes"].append(item)
                if note_id is not None:
                    record["notes"][note_id - 1]["text"] += box.text
                if item["trim_clearance_mm"] < 4.9:
                    report["issues"].append({"page": page_number, "kind": "trim-clearance", **item})
                if page_number in (2, 3) and column_id is not None and item["column_clearance_mm"] < -0.15:
                    report["issues"].append({"page": page_number, "kind": "column-overflow", **item})
                if note_id is not None and item["font_size_pt"] < 10.49:
                    report["issues"].append({"page": page_number, "kind": "body-size", **item})
            if element is not None and element.tag == "img" and "ReplacedBox" in kind:
                src = element.get("src", "")
                path = root / src
                if path.is_file() and path.suffix.lower() not in (".svg",):
                    with Image.open(path) as img:
                        pixels = list(img.size)
                    bounds = _bounds(box)
                    painted = bounds[2:]
                    fit = box.style["object_fit"]
                    if fit in ("contain", "cover"):
                        scale = (min if fit == "contain" else max)(bounds[2] / pixels[0], bounds[3] / pixels[1])
                        painted = [pixels[0] * scale, pixels[1] * scale]
                    ppi = [round(pixels[0] * 25.4 / painted[0], 2), round(pixels[1] * 25.4 / painted[1], 2)]
                    report["images"].append({"page": page_number, "src": src, "pixels": pixels,
                        "bounds_mm": bounds, "painted_size_mm": [round(v, 4) for v in painted],
                        "object_fit": fit, "effective_ppi": ppi,
                        "below_300_ppi": min(ppi) < 300})
            for child in getattr(box, "children", ()):
                walk(child, song_id, note_id, column_id)

        walk(page._page_box)
        for item in record["text_boxes"]:
            if item["song_id"] is None:
                continue
            x, y, w, h = item["bounds_mm"]
            for region in record["reserved_regions"]:
                rx, ry, rw, rh = region["bounds_mm"]
                if min(x + w, rx + rw) - max(x, rx) <= 0.1:
                    continue
                overlaps = min(y + h, ry + rh) - max(y, ry) > 0.1
                # Footer starts a reserved bottom area, including below its text.
                enters_footer = region["role"] == "page-footer" and y + h > ry + 0.1
                if overlaps or enters_footer:
                    report["issues"].append({"page": page_number, "kind": "reserved-region-overlap",
                        "region": region, **item})
        record["minimum_text_clearance_mm"] = min((b["trim_clearance_mm"] for b in record["text_boxes"]), default=None)
        report["pages"].append(record)
    return report


def _merge_clipped(target, source, rectangle_mm, translate_mm):
    """Use a real PDF clip before merging; only outer sheet bleed survives."""
    from pypdf import Transformation
    from pypdf.generic import RectangleObject

    clipped = copy.copy(source)
    for name in ("cropbox", "trimbox"):
        setattr(clipped, name, RectangleObject([value * MM for value in rectangle_mm]))
    target.merge_transformed_page(clipped, Transformation().translate(
        tx=translate_mm[0] * MM, ty=translate_mm[1] * MM), expand=False)


def _set_boxes(page, size, trim=None):
    from pypdf.generic import RectangleObject
    outer = [0, 0, size[0] * MM, size[1] * MM]
    page.mediabox = RectangleObject(outer)
    page.cropbox = RectangleObject(outer)
    page.bleedbox = RectangleObject(outer)
    page.trimbox = RectangleObject([v * MM for v in (trim or [0, 0, *size])])


def render_and_export(root: Path, source_hash: str) -> dict:
    """Write three PDFs and a diagnostic report; checks run separately.

    Layout problems stay visible in both PDF and report for proofing. Wrong
    page counts/sizes fail here because imposition would otherwise lose data.
    """
    root = Path(root).resolve()
    temp = root / "tmp/pdfs/program"
    temp.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("XDG_CACHE_HOME", str(temp / "cache"))
    from weasyprint import HTML
    from pypdf import PdfReader, PdfWriter

    document = HTML(filename=str(root / "program.html")).render()
    report = _collect_layout(document, root, source_hash)
    report_path = temp / "layout-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    if len(document.pages) != 4:
        raise ValueError(f"Expected 4 reading pages; got {len(document.pages)}. See {report_path}")
    for record in report["pages"]:
        if any(abs(actual - expected) > 0.1 for actual, expected in zip(record["size_mm"], (216, 303))):
            raise ValueError(f"Master page {record['page']} is {record['size_mm']}; expected 216 x 303 mm")
    raw = document.write_pdf()
    master_writer = PdfWriter()
    for page in PdfReader(io.BytesIO(raw)).pages:
        _set_boxes(page, [216, 303], [3, 3, 213, 300])
        master_writer.add_page(page)
    master_writer.add_metadata({"/Title": "結 コンサートプログラム 内部マスター",
                               "/YuiSourceSHA256": source_hash, "/YuiPageOrder": "1,2,3,4"})
    master_path = temp / "master.pdf"
    master_writer.write(master_path)
    master = PdfReader(master_path)
    output_dir = root / "output/pdf"
    output_dir.mkdir(parents=True, exist_ok=True)
    report["outputs"] = {}
    for filename, spec in OUTPUTS.items():
        writer = PdfWriter()
        is_bleed = "bleed" in filename
        for numbers in spec["order"]:
            target = writer.add_blank_page(width=spec["size_mm"][0] * MM, height=spec["size_mm"][1] * MM)
            for side, number in enumerate(numbers):
                if is_bleed:
                    # Left page retains left/top/bottom bleed; right retains right/top/bottom.
                    clip = [0, 0, 213, 303] if side == 0 else [3, 0, 216, 303]
                    translation = [0, 0] if side == 0 else [210, 0]
                else:
                    clip, translation = [3, 3, 213, 300], [side * 210 - 3, -3]
                _merge_clipped(target, master.pages[number - 1], clip, translation)
            _set_boxes(target, spec["size_mm"], [3, 3, 423, 300] if is_bleed else None)
        metadata = {"/Title": "マリンバコンサート「結」 配布プログラム",
                    "/Author": "マリンバ北星会", "/YuiSourceSHA256": source_hash,
                    "/YuiPageOrder": ",".join("|".join(map(str, p)) for p in spec["order"]),
                    "/Subject": "A3二つ折り・A4仕上がり。RGB。原寸100%。"}
        if len(spec["order"][0]) == 2:
            metadata["/YuiFoldXMM"] = "213" if is_bleed else "210"
        writer.add_metadata(metadata)
        path = output_dir / filename
        writer.write(path)
        report["outputs"][filename] = {**spec, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        print(f"Created {filename}: {len(spec['order'])} pages, {spec['size_mm'][0]} x {spec['size_mm'][1]} mm")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    if report["issues"]:
        print(f"Layout report: {len(report['issues'])} issue(s); run scripts/check-program.py after adjustment.")
    return report
