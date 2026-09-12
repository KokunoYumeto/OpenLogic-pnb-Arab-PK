"""Build the accepted seven-unit Sets reader as a deterministic EPUB 3 package.

This builder does not widen the translation claim.  It consumes the same OLP-0004
through OLP-0010 inputs as the accepted Naskh/Nastaliq PDF reader, converts the
assembled TeX to native MathML with Pandoc, supplies accessible SVG equivalents
for the three source TikZ set diagrams, and emits a genuinely reflowable EPUB.
No TeX engine is invoked.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath

from lxml import etree


REPO = Path(__file__).resolve().parents[1]
STATE = Path(r"C:\interlanguage-task-state\openlogic-pnb-Arab-PK")
PANDOC = Path(shutil.which("pandoc") or "__missing_pandoc__")
REVISION = "9620cc73f9c8e0ad003c514a5d3748f29611c4c0"
VERSION = "0.2.0"
MODIFIED = "2026-09-10T00:00:00Z"
FIXED_ZIP_TIME = (2026, 9, 10, 0, 0, 0)
DEFAULT_NAME = "OpenLogic-Sets-Punjabi-Shahmukhi-v0.2.0.epub"

XHTML_NS = "http://www.w3.org/1999/xhtml"
MATHML_NS = "http://www.w3.org/1998/Math/MathML"
SVG_NS = "http://www.w3.org/2000/svg"
EPUB_NS = "http://www.idpf.org/2007/ops"
OPF_NS = "http://www.idpf.org/2007/opf"
DC_NS = "http://purl.org/dc/elements/1.1/"
CONTAINER_NS = "urn:oasis:names:tc:opendocument:xmlns:container"
XML_NS = "http://www.w3.org/XML/1998/namespace"

EXPECTED_UNITS = [
    ("OLP-0004", "content/sets-functions-relations/sets/sets.tex"),
    ("OLP-0005", "content/sets-functions-relations/sets/basics.tex"),
    ("OLP-0006", "content/sets-functions-relations/sets/subsets.tex"),
    ("OLP-0007", "content/sets-functions-relations/sets/important-sets.tex"),
    ("OLP-0008", "content/sets-functions-relations/sets/unions-and-intersections.tex"),
    ("OLP-0009", "content/sets-functions-relations/sets/pairs-and-products.tex"),
    ("OLP-0010", "content/sets-functions-relations/sets/russells-paradox.tex"),
]

SECTION_SLUGS = ["bas", "sub", "imp", "uni", "pai", "rus"]

DIAGRAMS = {
    "sfr-set-uni-fig-union": {
        "asset": "assets/diagrams/union.tikz",
        "title": "A تے B دا اتحاد: اوہ عنصر جو A یا B وچ نیں",
        "description": "اُبھاریا ہویا علاقہ ہر اوہ عنصر رکھدا اے جو A یا B وچ اے، دوناں وچ سانجھے عنصر وی شامل نیں۔",
        "kind": "union",
    },
    "sfr-set-uni-fig-intersection": {
        "asset": "assets/diagrams/intersection.tikz",
        "title": "A تے B دا اشتراک: دوناں دے سانجھے عنصر",
        "description": "اُبھاریا ہویا بیچلا علاقہ اوہ عنصر رکھدا اے جو A تے B، دوناں وچ نیں۔",
        "kind": "intersection",
    },
    "sfr-set-uni-difference": {
        "asset": "assets/diagrams/difference.tikz",
        "title": "A گھٹ B: اوہ عنصر جو A وچ پر B وچ نہیں",
        "description": "اُبھاریا ہویا علاقہ A دا اوہ حصہ اے جو B توں باہر اے، یعنی A دے اوہ عنصر جو B وچ نہیں۔",
        "kind": "difference",
    },
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def write_json(path: Path, value: object) -> None:
    path.write_text(json_text(value), encoding="utf-8", newline="\n")


def xq(tag: str) -> str:
    return f"{{{XHTML_NS}}}{tag}"


def sq(tag: str) -> str:
    return f"{{{SVG_NS}}}{tag}"


def xe(tag: str, parent: etree._Element | None = None, **attrs: str) -> etree._Element:
    element = etree.Element(xq(tag)) if parent is None else etree.SubElement(parent, xq(tag))
    for key, value in attrs.items():
        element.set(key, value)
    return element


def se(tag: str, parent: etree._Element, **attrs: str) -> etree._Element:
    element = etree.SubElement(parent, sq(tag))
    for key, value in attrs.items():
        element.set(key.replace("_", "-"), value)
    return element


def safe_reset(path: Path, output_root: Path) -> None:
    resolved = path.resolve()
    root = output_root.resolve()
    require(resolved.parent == root, f"refusing to reset path outside exact output root: {resolved}")
    require(resolved.name.startswith(("canonical-", "cold-", "reader-", "scratch-")), f"unexpected build path: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True)


def balanced_argument(text: str, brace: int) -> tuple[str, int]:
    require(brace < len(text) and text[brace] == "{", "expected balanced TeX argument")
    depth = 1
    pos = brace + 1
    start = pos
    while pos < len(text) and depth:
        if text[pos] == "{" and (pos == 0 or text[pos - 1] != "\\"):
            depth += 1
        elif text[pos] == "}" and (pos == 0 or text[pos - 1] != "\\"):
            depth -= 1
        pos += 1
    require(depth == 0, "unbalanced TeX argument")
    return text[start : pos - 1], pos


def render_mixed_rtl_text(body: str) -> str:
    """Turn one mixed RTL TeX text box into alternating math and mtext runs.

    The PDF reader deliberately places formal islands such as ``x`` inside
    ``\\textenglish{\\(...\\)}`` while the enclosing clause stays RTL.  Texmath
    must receive those islands as mathematics, not as characters inside
    ``\\text{...}``, or identifiers and relations lose their semantics.
    """
    output: list[str] = []
    plain: list[str] = []
    cursor = 0
    needle = r"\textenglish{"

    def flush_plain() -> None:
        if plain:
            value = "".join(plain)
            if value:
                output.append(r"\text{" + value + "}")
            plain.clear()

    while True:
        start = body.find(needle, cursor)
        if start < 0:
            plain.append(body[cursor:])
            break
        plain.append(body[cursor:start])
        argument, end = balanced_argument(body, start + len(r"\textenglish"))
        if argument.startswith(r"\(") and argument.endswith(r"\)"):
            flush_plain()
            output.append(argument[2:-2])
        else:
            plain.append(argument)
        cursor = end
    flush_plain()
    return "".join(output)


def split_mixed_text_boxes(text: str) -> str:
    needle = r"\text{\textarabic{"
    while needle in text:
        start = text.find(needle)
        outer_argument, outer_end = balanced_argument(text, start + len(r"\text"))
        require(outer_argument.startswith(r"\textarabic{"), "mixed text wrapper prefix drift")
        inner_argument, inner_end = balanced_argument(outer_argument, len(r"\textarabic"))
        require(not outer_argument[inner_end:].strip(), "unexpected material beside mixed RTL text wrapper")
        text = text[:start] + render_mixed_rtl_text(inner_argument) + text[outer_end:]
    return text


def unwrap_math_commands(text: str) -> str:
    """Remove PDF-only direction wrappers while retaining their exact content."""
    text = split_mixed_text_boxes(text)
    commands = ("textarabic", "textenglish", "shoveright", "shoveleft")

    def one_pass(value: str) -> tuple[str, bool]:
        positions = [(value.find("\\" + command + "{"), command) for command in commands]
        positions = [(pos, command) for pos, command in positions if pos >= 0]
        if not positions:
            return value, False
        pos, command = min(positions)
        brace = pos + len(command) + 1
        argument, end = balanced_argument(value, brace)
        replacement = unwrap_math_commands(argument)
        if command == "textenglish" and replacement.startswith(r"\(") and replacement.endswith(r"\)"):
            replacement = replacement[2:-2]
        return value[:pos] + replacement + value[end:], True

    changed = True
    while changed:
        text, changed = one_pass(text)
    text = text.replace(r"\nicefrac", r"\frac")
    return text


def sanitize_math_regions(tex: str) -> tuple[str, dict]:
    counts = {"environment_regions": 0, "display_regions": 0, "dollar_regions": 0, "inline_paren_regions": 0}

    environment = re.compile(
        r"\\begin\{(?P<name>align\*?|multline\*?|gather\*?|equation\*?)\}(?P<body>[\s\S]*?)\\end\{(?P=name)\}"
    )

    def environment_replacement(match: re.Match[str]) -> str:
        counts["environment_regions"] += 1
        return f"\\begin{{{match.group('name')}}}" + unwrap_math_commands(match.group("body")) + f"\\end{{{match.group('name')}}}"

    tex = environment.sub(environment_replacement, tex)

    display = re.compile(r"\\\[(?P<body>[\s\S]*?)\\\]")

    def display_replacement(match: re.Match[str]) -> str:
        counts["display_regions"] += 1
        return r"\[" + unwrap_math_commands(match.group("body")) + r"\]"

    tex = display.sub(display_replacement, tex)

    dollar = re.compile(r"(?<!\\)\$(?P<body>(?:\\.|[^$])*)\$")

    def dollar_replacement(match: re.Match[str]) -> str:
        counts["dollar_regions"] += 1
        return "$" + unwrap_math_commands(match.group("body")) + "$"

    tex = dollar.sub(dollar_replacement, tex)

    inline_paren = re.compile(r"\\\((?P<body>[\s\S]*?)\\\)")

    def inline_paren_replacement(match: re.Match[str]) -> str:
        counts["inline_paren_regions"] += 1
        return r"\(" + unwrap_math_commands(match.group("body")) + r"\)"

    tex = inline_paren.sub(inline_paren_replacement, tex)
    return tex, counts


def current_inputs() -> tuple[dict, list[dict]]:
    receipt_path = REPO / "provenance" / "PORTABLE_CANDIDATE_INPUTS.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    require(receipt.get("reader_coverage_unit_ids") == [unit for unit, _ in EXPECTED_UNITS], "accepted reader unit graph drift")
    by_path = {row["source_path"]: row for row in receipt["source_units"]}
    records: list[dict] = []
    manifest = {
        row["source_path"]: row
        for row in map(json.loads, (REPO / "provenance" / "SOURCE_MANIFEST.jsonl").read_text(encoding="utf-8-sig").splitlines())
    }
    for unit_id, path in EXPECTED_UNITS:
        require(path in by_path and path in manifest, f"missing accepted unit {path}")
        source = (REPO / "upstream" / path).read_bytes()
        translation = (REPO / "translation" / path).read_bytes()
        require(manifest[path]["unit_id"] == unit_id, f"manifest unit drift for {path}")
        require(sha(source) == manifest[path]["source_sha256"] == by_path[path]["source_sha256"], f"source hash drift for {path}")
        require(sha(translation) == by_path[path]["translation_sha256"], f"accepted translation hash drift for {path}")
        records.append(
            {
                "unit_id": unit_id,
                "source_path": path,
                "source_bytes": len(source),
                "source_sha256": sha(source),
                "translation_bytes": len(translation),
                "translation_sha256": sha(translation),
            }
        )
    return receipt, records


def make_document(title: str, body_type: str) -> tuple[etree._Element, etree._Element]:
    root = etree.Element(xq("html"), nsmap={None: XHTML_NS, "epub": EPUB_NS})
    root.set("lang", "pnb-Arab-PK")
    root.set(f"{{{XML_NS}}}lang", "pnb-Arab-PK")
    root.set("dir", "rtl")
    head = xe("head", root)
    xe("meta", head, charset="utf-8")
    title_node = xe("title", head)
    title_node.text = title
    xe("link", head, rel="stylesheet", href="../styles/reader.css")
    body = xe("body", root, dir="rtl")
    body.set(f"{{{EPUB_NS}}}type", body_type)
    return root, body


def serialize_xhtml(root: etree._Element) -> bytes:
    return etree.tostring(
        root,
        encoding="utf-8",
        xml_declaration=True,
        doctype="<!DOCTYPE html>",
        method="xml",
        pretty_print=False,
    )


def write_xhtml(path: Path, root: etree._Element) -> dict:
    payload = serialize_xhtml(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    etree.fromstring(payload, parser=etree.XMLParser(resolve_entities=False, no_network=True))
    return {"path": path.as_posix(), "bytes": len(payload), "sha256": sha(payload)}


def normalize_id(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    if not value or not value[0].isalpha():
        value = "id-" + value
    return value


def rewrite_ids(section: etree._Element) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for node in section.xpath(".//*[@id]"):
        old = node.get("id")
        new = normalize_id(old)
        require(new not in mapping.values(), f"normalized ID collision: {old} -> {new}")
        mapping[old] = new
        node.set("id", new)
    for node in section.xpath(".//*[@href]"):
        href = node.get("href")
        if href.startswith("#") and href[1:] in mapping:
            node.set("href", "#" + mapping[href[1:]])
    for node in section.xpath(".//*[@data-reference]"):
        value = node.get("data-reference")
        if value in mapping:
            node.set("data-reference", mapping[value])
    return mapping


def svg_diagram(identifier: str, record: dict, asset_sha: str) -> etree._Element:
    svg = etree.Element(sq("svg"), nsmap={None: SVG_NS})
    svg.set("id", identifier + "-graphic")
    svg.set("class", "set-diagram")
    svg.set("role", "img")
    svg.set("viewBox", "35 10 230 145")
    svg.set("aria-labelledby", identifier + "-title " + identifier + "-desc")
    svg.set("data-source-asset", record["asset"])
    svg.set("data-asset-sha256", asset_sha)
    title = se("title", svg, id=identifier + "-title")
    title.text = record["title"]
    desc = se("desc", svg, id=identifier + "-desc")
    desc.text = record["description"]
    defs = se("defs", svg)
    pattern = se(
        "pattern",
        defs,
        id=identifier + "-hatch",
        width="9",
        height="9",
        patternUnits="userSpaceOnUse",
        patternTransform="rotate(35)",
    )
    se("line", pattern, x1="0", y1="0", x2="0", y2="9", **{"class": "hatch-line"})
    if record["kind"] == "intersection":
        clip = se("clipPath", defs, id=identifier + "-clip")
        se("circle", clip, cx="115", cy="80", r="58")
        se(
            "circle",
            svg,
            cx="185",
            cy="80",
            r="58",
            fill=f"url(#{identifier}-hatch)",
            clip_path=f"url(#{identifier}-clip)",
        )
    elif record["kind"] == "difference":
        se("circle", svg, cx="115", cy="80", r="58", fill=f"url(#{identifier}-hatch)")
        se("circle", svg, cx="185", cy="80", r="58", **{"class": "set-mask"})
    else:
        se("circle", svg, cx="115", cy="80", r="58", fill=f"url(#{identifier}-hatch)")
        se("circle", svg, cx="185", cy="80", r="58", fill=f"url(#{identifier}-hatch)")
    se("circle", svg, cx="115", cy="80", r="58", **{"class": "set-boundary"})
    se("circle", svg, cx="185", cy="80", r="58", **{"class": "set-boundary"})
    left = se("text", svg, x="83", y="82")
    left.text = "A"
    right = se("text", svg, x="212", y="82")
    right.text = "B"
    return svg


def add_diagram_structure(frame: etree._Element, identifier: str, record: dict) -> None:
    structure = xe("div", frame, **{"class": "diagram-structure", "dir": "rtl"})
    p = xe("p", structure)
    strong = xe("strong", p)
    strong.text = record["title"] + "۔ "
    strong.tail = record["description"]
    dl = xe("dl", structure)
    for term, description in (
        ("سیٹ A", "کھبا دائرہ۔"),
        ("سیٹ B", "سجا دائرہ۔"),
        ("اُبھاریا ہویا علاقہ", record["description"]),
    ):
        dt = xe("dt", dl)
        dt.text = term
        dd = xe("dd", dl)
        dd.text = description
    structure.set("data-diagram-id", identifier)


def postprocess_read(section: etree._Element, units: list[dict], assets: list[dict]) -> dict:
    mapping = rewrite_ids(section)
    section.set("dir", "rtl")
    section.set("lang", "pnb-Arab-PK")
    section.set(f"{{{XML_NS}}}lang", "pnb-Arab-PK")
    section.set(f"{{{EPUB_NS}}}type", "chapter")
    section.set("data-reader-scope", "OLP-0004--OLP-0010")
    section.set("data-source-revision", REVISION)

    math = section.xpath(".//m:math", namespaces={"m": MATHML_NS})
    for node in math:
        node.set("dir", "ltr")
        node.set("class", "mathml")
    rtl_mtext = section.xpath(".//m:mtext", namespaces={"m": MATHML_NS})
    rtl_mtext = [node for node in rtl_mtext if re.search(r"[\u0600-\u06ff]", "".join(node.itertext()))]
    for node in rtl_mtext:
        node.set("dir", "rtl")
    annotations = section.xpath(".//m:annotation[@encoding='application/x-tex']", namespaces={"m": MATHML_NS})
    require(len(math) == len(annotations), "MathML annotation coverage drift")

    for node in section.xpath(".//*[@lang='en']"):
        node.set("dir", "ltr")
        classes = set((node.get("class") or "").split())
        classes.add("ltr")
        node.set("class", " ".join(sorted(classes)))

    headings = section.findall(xq("h2"))
    require(len(headings) == 6, f"unexpected Sets section count: {len(headings)}")
    for index, (heading, unit) in enumerate(zip(headings, units[1:]), 1):
        expected = f"sfr-set-{SECTION_SLUGS[index - 1]}-sec"
        require(heading.get("id") == expected, f"section identity drift: {heading.get('id')} != {expected}")
        heading.set("data-unit-id", unit["unit_id"])
        heading.set("data-source-path", unit["source_path"])
        heading.set("data-source-sha256", unit["source_sha256"])
        heading.set("data-translation-sha256", unit["translation_sha256"])
        cite = xe("p")
        cite.set("class", "source-unit-cite")
        cite.text = "ماخذ اکائی: "
        link = xe("a", cite, href=f"provenance.xhtml#unit-{unit['unit_id']}")
        link.set("dir", "ltr")
        link.text = unit["unit_id"]
        link.tail = "۔"
        parent = heading.getparent()
        parent.insert(parent.index(heading) + 1, cite)

    statement_labels = ("تعریف", "مثال", "قضیہ", "مسئلہ", "مشق")
    section_number = 0
    statement_number = 0
    last_statement: str | None = None
    label_numbers: dict[str, str] = {}
    statement_count = 0
    for child in list(section):
        if child.tag == xq("h2"):
            section_number += 1
            statement_number = 0
            last_statement = None
            continue
        if child.tag == xq("p"):
            strong = child.find(xq("strong"))
            text = "".join(strong.itertext()).strip() if strong is not None else ""
            if strong is not None and text.startswith(statement_labels):
                statement_number += 1
                statement_count += 1
                number = f"{section_number}.{statement_number}"
                child.set("class", ((child.get("class") or "") + " statement-heading").strip())
                child.set("id", child.get("id") or f"statement-{number.replace('.', '-')}")
                placeholders = strong.xpath(".//*[@lang='en' and normalize-space(.)='.']")
                require(len(placeholders) == 1, f"statement number placeholder drift at {number}")
                placeholders[0].text = number
                last_statement = number
                continue
            if last_statement:
                anchored = child.xpath(".//*[@id]")
                for anchor in anchored:
                    label_numbers[anchor.get("id")] = last_statement
                last_statement = None
        elif child.tag not in (xq("div"),):
            last_statement = None

    assets_by_path = {row["source_path"]: row for row in assets}
    figure_numbers: dict[str, str] = {}
    figures = section.findall(xq("figure"))
    require(len(figures) == 3, f"unexpected figure count: {len(figures)}")
    for index, figure in enumerate(figures, 1):
        identifier = figure.get("id")
        require(identifier in DIAGRAMS, f"unrecognized set diagram {identifier}")
        record = DIAGRAMS[identifier]
        require(record["asset"] in assets_by_path, f"diagram asset missing from accepted receipt: {record['asset']}")
        frame = figure.find(xq("div"))
        require(frame is not None, f"Pandoc diagram placeholder missing: {identifier}")
        for node in list(frame):
            frame.remove(node)
        frame.text = None
        frame.set("class", "diagram-frame")
        frame.set("data-source-asset", record["asset"])
        frame.set("data-asset-sha256", assets_by_path[record["asset"]]["sha256"])
        frame.append(svg_diagram(identifier, record, assets_by_path[record["asset"]]["sha256"]))
        add_diagram_structure(frame, identifier, record)
        caption = figure.find(xq("figcaption"))
        require(caption is not None, f"figure caption missing: {identifier}")
        prefix = caption.text or ""
        caption.text = None
        strong = xe("strong")
        strong.text = f"شکل 1.{index}۔ "
        strong.tail = prefix
        caption.insert(0, strong)
        figure_numbers[identifier] = f"1.{index}"

    unresolved: list[str] = []
    for anchor in section.xpath(".//x:a[@data-reference-type='ref']", namespaces={"x": XHTML_NS}):
        target = (anchor.get("href") or "").removeprefix("#")
        if target in label_numbers:
            anchor.text = label_numbers[target]
        elif target in figure_numbers:
            anchor.text = figure_numbers[target]
        elif (anchor.text or "").startswith("["):
            unresolved.append(target)
    require(not unresolved, f"unresolved semantic references: {unresolved}")

    ids = [node.get("id") for node in section.xpath(".//*[@id]")]
    require(len(ids) == len(set(ids)), "duplicate IDs after EPUB normalization")
    return {
        "id_rewrites": mapping,
        "mathml_roots": len(math),
        "mathml_tex_annotations": len(annotations),
        "rtl_math_text_runs": len(rtl_mtext),
        "sections": len(headings),
        "statement_headings_numbered": statement_count,
        "figures": len(figures),
        "semantic_reference_links": len(section.xpath(".//x:a[@data-reference-type='ref']", namespaces={"x": XHTML_NS})),
        "unresolved_semantic_references": unresolved,
    }


def build_cover(unit: dict) -> etree._Element:
    root, body = make_document("اوپن لاجک: سیٹ — پنجابی شاہ مکھی", "frontmatter")
    section = xe("section", body, **{"class": "cover", "id": "cover"})
    section.set(f"{{{EPUB_NS}}}type", "titlepage")
    h1 = xe("h1", section)
    h1.text = "سیٹ"
    subtitle = xe("p", section, **{"class": "subtitle"})
    subtitle.text = "اوپن لاجک — پنجابی شاہ مکھی ترجمہ"
    scope = xe("p", section, **{"class": "scope-note"})
    scope.text = "ایس ایڈیشن وچ سیٹاں دا مکمل باب اے؛ ایہ پوری کتاب دا ترجمہ نہیں۔ ماخذ دی حد OLP-0004 توں OLP-0010 تک، سات اکائیاں، اے۔"
    warning = xe("p", section)
    warning.text = "ایہ مشینی ترجمہ اے۔ خاص ریاضیاتی اصطلاحاں وچوں کجھ عارضی نیں؛ اوہناں دے ماخذ تے فیصلے نال دتے گئے ریکارڈ وچ ویکھے جا سکدے نیں۔"
    english = xe("div", section, **{"class": "ltr edition-credit", "dir": "ltr", "lang": "en"})
    for text in (
        "Independent machine translation by Codex; no upstream endorsement is implied.",
        f"Open Logic source revision {REVISION}.",
        "Reflowable EPUB 3 with native MathML. CC BY 4.0.",
        f"Chapter driver: {unit['unit_id']} — {unit['source_path']}.",
    ):
        p = xe("p", english)
        p.text = text
    start = xe("p", section, **{"class": "start-link"})
    link = xe("a", start, href="read.xhtml")
    link.text = "باب پڑھو"
    return root


def build_read(section: etree._Element) -> etree._Element:
    root, body = make_document("سیٹ — اوپن لاجک پنجابی شاہ مکھی", "bodymatter")
    scope = xe("aside", body, **{"class": "scope-note", "id": "scope"})
    heading = xe("h2", scope)
    heading.text = "ایڈیشن دی حد"
    p = xe("p", scope)
    p.text = "ایہ ری فلو ہون والا قاری سیٹاں دے مکمل باب OLP-0004–OLP-0010 نوں پیش کردا اے؛ باقی OpenLogic ہلے ایس ایڈیشن وچ شامل نہیں۔"
    body.append(copy.deepcopy(section))
    return root


def add_hash_line(parent: etree._Element, label: str, value: str) -> None:
    p = xe("p", parent, **{"class": "digest", "dir": "ltr", "lang": "en"})
    strong = xe("strong", p)
    strong.text = label + ":"
    code = xe("code", p, dir="ltr", lang="en")
    code.text = value


def build_provenance(units: list[dict], input_sha: str, builder_sha: str) -> etree._Element:
    root, body = make_document("ماخذ، دائرہ تے ایڈیشن دی تفصیل", "backmatter")
    main = xe("main", body, id="provenance")
    h1 = xe("h1", main)
    h1.text = "ماخذ، دائرہ تے ایڈیشن دی تفصیل"
    p = xe("p", main)
    p.text = "ایہ آزاد، مشینی پنجابی شاہ مکھی ترجمہ اے۔ ایہ ریلیز صرف سیٹاں دے مکمل باب دیاں سات ماخذ اکائیاں رکھدی اے؛ پوری 722-اکائی کتاب دا دعویٰ نہیں کردی۔"
    p2 = xe("p", main)
    p2.text = "ریاضی native MathML وچ اے، متن سجے توں کھبے ری فلو ہوندا اے، تے تین تصویری خاکیاں نال متنی وضاحت وی دِتّی گئی اے۔ MathML دی پیشکش پڑھائی والی ایپ دی سہولت اُتے وی منحصر اے۔"
    h2 = xe("h2", main)
    h2.text = "سات ماخذ اکائیاں"
    listing = xe("ol", main, **{"class": "unit-list"})
    for unit in units:
        li = xe("li", listing, id=f"unit-{unit['unit_id']}")
        heading = xe("p", li, **{"class": "unit-id", "dir": "ltr", "lang": "en"})
        title = xe("strong", heading, dir="ltr")
        title.text = unit["unit_id"]
        path_line = xe("p", li, **{"class": "unit-path", "dir": "ltr", "lang": "en"})
        path = xe("code", path_line, dir="ltr", lang="en")
        path.text = unit["source_path"]
        add_hash_line(li, "Source SHA-256", unit["source_sha256"])
        add_hash_line(li, "Translation SHA-256", unit["translation_sha256"])
        source = xe("p", li, dir="ltr", lang="en")
        link = xe(
            "a",
            source,
            href=f"https://github.com/OpenLogicProject/OpenLogic/blob/{REVISION}/{unit['source_path']}",
            dir="ltr",
            lang="en",
        )
        link.text = "Frozen English source"
    h2 = xe("h2", main)
    h2.text = "تولیدی شناخت"
    add_hash_line(main, "Accepted reader input receipt SHA-256", input_sha)
    add_hash_line(main, "EPUB builder SHA-256", builder_sha)
    add_hash_line(main, "OpenLogic revision", REVISION)
    p = xe("p", main)
    p.text = "PDF لئی منّے ہوئے اِن پُٹ ہِی ایس EPUB دے متن دا ماخذ نیں۔ EPUB builder کسے TeX انجن نوں نہیں چلاندا؛ Pandoc نال native MathML بناندا اے تے deterministic ZIP پیکج لکھدا اے۔"
    h2 = xe("h2", main)
    h2.text = "لائسنس تے نسبت"
    p = xe("p", main)
    p.text = "Open Logic Project دا اصل کم تے ایہ بدلیا ہویا ترجمہ Creative Commons Attribution 4.0 International دے تحت دتے گئے نیں۔ اصل مصنّفاں تے مدیران دی تفصیلی نسبت upstream ماخذ وچ محفوظ اے۔"
    links = xe("ul", main)
    for label, href in (
        ("CC BY 4.0", "https://creativecommons.org/licenses/by/4.0/"),
        ("Open Logic Project", "https://openlogicproject.org/"),
        ("OpenLogic translations hub", "https://github.com/KokunoYumeto/OpenLogic-translations"),
        ("Punjabi Shahmukhi edition repository", "https://github.com/KokunoYumeto/OpenLogic-pnb-Arab-PK"),
    ):
        li = xe("li", links)
        a = xe("a", li, href=href, dir="ltr", lang="en")
        a.text = label
    return root


def build_license() -> etree._Element:
    root, body = make_document("فونٹ دا لائسنس", "backmatter")
    main = xe("main", body, id="font-license")
    h1 = xe("h1", main)
    h1.text = "فونٹ دا لائسنس"
    p = xe("p", main)
    p.text = "ایس EPUB وچ Noto Naskh Arabic دے Regular تے Bold فونٹ شامل نیں۔ اوہ SIL Open Font License 1.1 دے تحت نیں۔"
    pre = xe("pre", main, dir="ltr", lang="en")
    pre.text = (REPO / "fonts" / "OFL.txt").read_text(encoding="utf-8")
    return root


def build_nav(read_section: etree._Element) -> etree._Element:
    root, body = make_document("فہرست — اوپن لاجک سیٹ", "frontmatter")
    nav = xe("nav", body, id="toc")
    nav.set(f"{{{EPUB_NS}}}type", "toc")
    nav.set("role", "doc-toc")
    nav.set("aria-label", "فہرست")
    h1 = xe("h1", nav)
    h1.text = "فہرست"
    ol = xe("ol", nav)

    def item(label: str, href: str, parent: etree._Element = ol) -> etree._Element:
        li = xe("li", parent)
        a = xe("a", li, href=href)
        a.text = label
        return li

    item("سرورق", "cover.xhtml")
    chapter = item("سیٹ", "read.xhtml")
    sections = xe("ol", chapter)
    for heading in read_section.findall(xq("h2")):
        # The complete English bridge remains in the chapter heading, where it is
        # an explicitly isolated LTR span.  Navigation uses the native title only;
        # flattening a mixed inline tree into one string breaks bidi isolation.
        native_label = (heading.text or "").strip()
        require(native_label, f"native navigation label missing for {heading.get('id')}")
        item(native_label, "read.xhtml#" + heading.get("id"), sections)
    item("ماخذ، دائرہ تے ایڈیشن دی تفصیل", "provenance.xhtml")
    item("فونٹ دا لائسنس", "licenses.xhtml")
    landmarks = xe("nav", body)
    landmarks.set(f"{{{EPUB_NS}}}type", "landmarks")
    landmarks.set("aria-label", "کتاب دے نشان")
    h2 = xe("h2", landmarks)
    h2.text = "کتاب دے نشان"
    listing = xe("ol", landmarks)
    for label, href, kind in (
        ("فہرست", "nav.xhtml", "toc"),
        ("اصل متن", "read.xhtml", "bodymatter"),
        ("نسبت تے لائسنس", "provenance.xhtml", "copyright-page"),
    ):
        li = xe("li", listing)
        a = xe("a", li, href=href)
        a.set(f"{{{EPUB_NS}}}type", kind)
        a.text = label
    return root


def write_css(stage: Path) -> dict:
    css = """/* Deterministic, genuinely reflowable Punjabi Shahmukhi EPUB presentation. */
@font-face { font-family: 'Noto Naskh Arabic'; src: url('../fonts/NotoNaskhArabic-Regular.ttf'); font-style: normal; font-weight: 400; }
@font-face { font-family: 'Noto Naskh Arabic'; src: url('../fonts/NotoNaskhArabic-Bold.ttf'); font-style: normal; font-weight: 700; }
:root { --surface: #ffffff; --ink: #191919; --accent: #7d1821; }
html { line-height: 1.75; }
body { margin: 5%; max-width: 52rem; color: var(--ink); background: var(--surface); font-family: 'Noto Naskh Arabic', serif; font-size: 1em; overflow-wrap: anywhere; }
main, section, article, aside, nav, header, footer, figure { display: block; }
h1, h2, h3 { line-height: 1.35; break-after: avoid; }
p { orphans: 3; widows: 3; }
a { color: inherit; text-decoration: underline; text-underline-offset: 0.12em; }
[lang|='en'], .ltr, code, pre { font-family: serif; }
code, .digest, .unit-path { overflow-wrap: anywhere; word-break: break-all; }
.unit-id, .unit-path, .digest { text-align: left; }
.unit-id { margin-block-end: 0.15em; }
.unit-path { margin-block-start: 0; }
.digest strong, .digest code { display: block; }
math { max-width: 100%; }
math[display='block'] { display: block; overflow-x: auto; overflow-y: hidden; margin: 1em auto; padding: 0.25em 0; }
.scope-note { border: 0.08em solid currentColor; padding: 0.8em 1em; margin: 1em 0 1.5em; }
.source-unit-cite { font-size: 0.85em; opacity: 0.86; margin-block-start: -0.5em; }
.statement-heading { border-inline-start: 0.22em solid var(--accent); padding-inline-start: 0.65em; margin-block-start: 1.35em; }
figure { margin: 1.5em auto; break-inside: avoid; }
figcaption { margin-block-start: 0.65em; }
.diagram-frame { text-align: center; }
.set-diagram { width: 100%; max-width: 25rem; height: auto; }
.set-boundary { fill: none; stroke: currentColor; stroke-width: 2.2; }
.set-mask { fill: var(--surface); }
.hatch-line { stroke: var(--accent); stroke-width: 3; }
.set-diagram text { fill: currentColor; font: 18px serif; }
.diagram-structure { text-align: start; border: 0.06em solid currentColor; padding: 0.65em 0.9em; margin-block-start: 0.6em; }
.diagram-structure dt { font-weight: 700; }
.diagram-structure dd { margin-inline-start: 1.5em; }
.cover { text-align: center; min-height: 75vh; display: flex; flex-direction: column; justify-content: center; }
.cover h1 { font-size: 3em; margin: 0.25em; }
.subtitle { font-size: 1.45em; }
.edition-credit { margin-block: 2em; }
.start-link a { display: inline-block; border: 0.09em solid currentColor; padding: 0.45em 1em; }
.unit-list > li { margin-block-end: 1.25em; }
.unit-list { list-style: none; padding-inline-start: 0; }
pre { white-space: pre-wrap; font-size: 0.72em; }
img, svg, table { max-width: 100%; }
@media (prefers-color-scheme: dark) { :root { --surface: #161616; --ink: #f2f2f2; --accent: #ff9aa6; } }
@page { margin: 1em; }
"""
    path = stage / "OEBPS" / "styles" / "reader.css"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(css, encoding="utf-8", newline="\n")
    return {"path": "OEBPS/styles/reader.css", "bytes": len(css.encode()), "sha256": sha(css.encode())}


def copy_fonts(stage: Path) -> list[dict]:
    records: list[dict] = []
    target = stage / "OEBPS" / "fonts"
    target.mkdir(parents=True, exist_ok=True)
    for name in ("NotoNaskhArabic-Regular.ttf", "NotoNaskhArabic-Bold.ttf"):
        source = REPO / "fonts" / name
        destination = target / name
        shutil.copyfile(source, destination)
        records.append({"path": f"OEBPS/fonts/{name}", "bytes": destination.stat().st_size, "sha256": sha(destination.read_bytes())})
    return records


def media_type(path: PurePosixPath) -> str:
    return {
        ".xhtml": "application/xhtml+xml",
        ".css": "text/css",
        ".ttf": "font/ttf",
    }[path.suffix.lower()]


def item_id(path: PurePosixPath) -> str:
    return normalize_id("item-" + path.as_posix())


def create_package(stage: Path, resources: list[PurePosixPath], input_sha: str) -> dict:
    package = etree.Element(f"{{{OPF_NS}}}package", nsmap={None: OPF_NS, "dc": DC_NS})
    package.set("version", "3.0")
    package.set("unique-identifier", "pub-id")
    package.set(f"{{{XML_NS}}}lang", "pnb-Arab-PK")
    package.set(
        "prefix",
        "schema: http://schema.org/ rendition: http://www.idpf.org/vocab/rendition/# dcterms: http://purl.org/dc/terms/",
    )
    metadata = etree.SubElement(package, f"{{{OPF_NS}}}metadata")

    def dc(name: str, value: str, identifier: str | None = None) -> None:
        node = etree.SubElement(metadata, f"{{{DC_NS}}}{name}")
        node.text = value
        if identifier:
            node.set("id", identifier)

    def meta(prop: str, value: str) -> None:
        node = etree.SubElement(metadata, f"{{{OPF_NS}}}meta")
        node.set("property", prop)
        node.text = value

    dc("identifier", f"urn:sha256:{input_sha}:sets-pnb-Arab-PK-epub3-v{VERSION}", "pub-id")
    dc("title", "OpenLogic: سیٹ — پنجابی شاہ مکھی ایڈیشن", "title")
    dc("language", "pnb-Arab-PK")
    dc("creator", "The Open Logic Project and credited contributors", "creator")
    dc("publisher", "Independent Punjabi Shahmukhi OpenLogic edition")
    dc("date", MODIFIED[:10])
    dc("type", "Textbook")
    dc("subject", "Mathematical logic")
    dc("subject", "Set theory")
    dc("description", "Complete Sets chapter in Punjabi Shahmukhi: a seven-source-unit, genuinely reflowable EPUB 3 edition with native MathML, accessible set diagrams, and exact source/translation identities. This is not the complete 722-unit book.")
    dc("source", f"OpenLogic source revision {REVISION}")
    dc("rights", "Creative Commons Attribution 4.0 International (CC BY 4.0). Translation and EPUB conversion modified independently; no upstream endorsement is implied.")
    meta("dcterms:modified", MODIFIED)
    meta("dcterms:provenance", "Independent machine translation and EPUB conversion by OpenAI Codex. Human-source credits are preserved through the frozen OpenLogic revision and public project links.")
    meta("rendition:layout", "reflowable")
    meta("rendition:orientation", "auto")
    meta("rendition:spread", "auto")
    for mode in ("textual", "visual"):
        meta("schema:accessMode", mode)
    meta("schema:accessModeSufficient", "textual")
    for feature in ("MathML", "alternativeText", "displayTransformability", "readingOrder", "structuralNavigation", "tableOfContents"):
        meta("schema:accessibilityFeature", feature)
    for hazard in ("noFlashingHazard", "noMotionSimulationHazard", "noSoundHazard"):
        meta("schema:accessibilityHazard", hazard)
    meta("schema:accessibilitySummary", "Reflowable Punjabi Shahmukhi text with RTL metadata and reading order, native presentation MathML with TeX annotations, semantic headings and landmarks, and text descriptions for all three set diagrams. The package is script-free and contains no audio, flashing, or motion. MathML rendering varies by reading system. Automated validation is not a human accessibility certification.")

    manifest = etree.SubElement(package, f"{{{OPF_NS}}}manifest")
    ids: dict[PurePosixPath, str] = {}
    for path in sorted(resources, key=lambda value: value.as_posix()):
        identifier = item_id(path)
        ids[path] = identifier
        item = etree.SubElement(manifest, f"{{{OPF_NS}}}item")
        item.set("id", identifier)
        item.set("href", path.relative_to(PurePosixPath("OEBPS")).as_posix())
        item.set("media-type", media_type(path))
        properties: list[str] = []
        if path == PurePosixPath("OEBPS/text/nav.xhtml"):
            properties.append("nav")
        if path == PurePosixPath("OEBPS/text/read.xhtml"):
            properties.extend(("mathml", "svg"))
        if properties:
            item.set("properties", " ".join(properties))
    spine = etree.SubElement(package, f"{{{OPF_NS}}}spine")
    spine.set("page-progression-direction", "rtl")
    for path in (
        PurePosixPath("OEBPS/text/cover.xhtml"),
        PurePosixPath("OEBPS/text/nav.xhtml"),
        PurePosixPath("OEBPS/text/read.xhtml"),
        PurePosixPath("OEBPS/text/provenance.xhtml"),
        PurePosixPath("OEBPS/text/licenses.xhtml"),
    ):
        itemref = etree.SubElement(spine, f"{{{OPF_NS}}}itemref")
        itemref.set("idref", ids[path])
        itemref.set("linear", "yes")
    payload = etree.tostring(package, encoding="utf-8", xml_declaration=True, pretty_print=True)
    destination = stage / "OEBPS" / "package.opf"
    destination.write_bytes(payload)
    return {"path": "OEBPS/package.opf", "bytes": len(payload), "sha256": sha(payload), "manifest_items": len(resources), "spine_items": 5}


def create_container(stage: Path) -> dict:
    mimetype = stage / "mimetype"
    mimetype.write_bytes(b"application/epub+zip")
    root = etree.Element(f"{{{CONTAINER_NS}}}container", nsmap={None: CONTAINER_NS})
    root.set("version", "1.0")
    rootfiles = etree.SubElement(root, f"{{{CONTAINER_NS}}}rootfiles")
    rootfile = etree.SubElement(rootfiles, f"{{{CONTAINER_NS}}}rootfile")
    rootfile.set("full-path", "OEBPS/package.opf")
    rootfile.set("media-type", "application/oebps-package+xml")
    payload = etree.tostring(root, encoding="utf-8", xml_declaration=True, pretty_print=True)
    destination = stage / "META-INF" / "container.xml"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(payload)
    return {"mimetype_sha256": sha(mimetype.read_bytes()), "container_sha256": sha(payload)}


def create_zip(stage: Path, destination: Path) -> dict:
    if destination.exists():
        destination.unlink()

    def info(name: str, compression: int) -> zipfile.ZipInfo:
        item = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
        item.compress_type = compression
        item.create_system = 3
        item.external_attr = 0o100644 << 16
        item.flag_bits |= 0x800
        return item

    with zipfile.ZipFile(destination, "w", allowZip64=True) as archive:
        archive.writestr(info("mimetype", zipfile.ZIP_STORED), (stage / "mimetype").read_bytes())
        for path in sorted(stage.rglob("*")):
            if not path.is_file() or path == stage / "mimetype":
                continue
            relative = path.relative_to(stage).as_posix()
            archive.writestr(info(relative, zipfile.ZIP_DEFLATED), path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    with zipfile.ZipFile(destination) as archive:
        entries = archive.infolist()
        require(entries[0].filename == "mimetype" and entries[0].compress_type == zipfile.ZIP_STORED, "invalid EPUB ZIP ordering")
        require(archive.read("mimetype") == b"application/epub+zip", "invalid EPUB mimetype")
        require(archive.testzip() is None, "EPUB ZIP CRC failure")
    payload = destination.read_bytes()
    return {"path": destination.name, "bytes": len(payload), "sha256": sha(payload), "entries": len(entries)}


def inventory(root: Path) -> list[dict]:
    return [
        {"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size, "sha256": sha(path.read_bytes())}
        for path in sorted(root.rglob("*"))
        if path.is_file()
    ]


def tree_sha(records: list[dict]) -> str:
    payload = "".join(f"{row['sha256']}  {row['path']}\n" for row in records).encode()
    return sha(payload)


def run_pandoc(tex_path: Path, html_path: Path) -> dict:
    require(PANDOC.is_file(), f"Pandoc missing at {PANDOC}")
    command = [str(PANDOC), str(tex_path), "--from=latex", "--to=html5", "--standalone", "--mathml", "--wrap=none", f"--output={html_path}"]
    completed = subprocess.run(command, cwd=tex_path.parent, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    require(completed.returncode == 0, f"Pandoc failed: {completed.stderr}")
    require("Could not convert TeX math" not in completed.stderr, f"Pandoc left non-MathML formulae:\n{completed.stderr}")
    version = subprocess.run([str(PANDOC), "--version"], capture_output=True, text=True, encoding="utf-8", check=True).stdout.splitlines()[0]
    return {"command": [PANDOC.name, tex_path.name, "--from=latex", "--to=html5", "--standalone", "--mathml", "--wrap=none"], "stderr": completed.stderr, "version": version}


def build_one(output: Path, tag: str, epub_name: str, receipt: dict, units: list[dict]) -> dict:
    stage = output / f"{tag}-unpacked"
    reader = output / f"reader-{tag}"
    scratch = output / f"scratch-{tag}"
    for path in (stage, reader, scratch):
        safe_reset(path, output)
    generated = subprocess.run(
        [sys.executable, str(REPO / "tools" / "build_sets_reader.py"), "--output-dir", str(reader), "--font-dir", str(REPO / "fonts")],
        cwd=REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    require(generated.returncode == 0, f"Sets reader assembly failed: {generated.stderr}")
    generated_receipt = json.loads((reader / "INPUTS.json").read_text(encoding="utf-8"))
    expected_receipt_sha = sha((REPO / "provenance" / "PORTABLE_CANDIDATE_INPUTS.json").read_bytes())
    require(sha((reader / "INPUTS.json").read_bytes()) == expected_receipt_sha, "reader input receipt is no longer byte-identical to the accepted candidate")
    tex = (reader / "sets-naskh.tex").read_text(encoding="utf-8")
    sanitized, math_regions = sanitize_math_regions(tex)
    sanitized_path = scratch / "sets-naskh-epub.tex"
    sanitized_path.write_text(sanitized, encoding="utf-8", newline="\n")
    raw_html = scratch / "pandoc.html"
    pandoc = run_pandoc(sanitized_path, raw_html)
    parser = etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=True)
    parsed = etree.parse(str(raw_html), parser=parser)
    sections = parsed.xpath("//x:section[@id='sfr:set::chap']", namespaces={"x": XHTML_NS})
    require(len(sections) == 1, "Pandoc chapter boundary drift")
    section = copy.deepcopy(sections[0])
    failures = parsed.xpath("//*[contains(concat(' ', normalize-space(@class), ' '), ' math ') and not(self::m:math)]", namespaces={"m": MATHML_NS})
    require(not failures, f"unconverted math containers survived: {len(failures)}")
    serialized_raw = etree.tostring(section, encoding="unicode")
    for forbidden in (r"\textarabic", r"\textenglish", r"\nicefrac", r"\shoveright", r"\shoveleft"):
        require(forbidden not in serialized_raw, f"PDF-only math wrapper survived: {forbidden}")

    read_metrics = postprocess_read(section, units, generated_receipt["assets"])
    documents = {
        "cover.xhtml": build_cover(units[0]),
        "read.xhtml": build_read(section),
        "provenance.xhtml": build_provenance(units, expected_receipt_sha, sha(Path(__file__).read_bytes())),
        "licenses.xhtml": build_license(),
        "nav.xhtml": build_nav(section),
    }
    document_records = {}
    for name, root in documents.items():
        record = write_xhtml(stage / "OEBPS" / "text" / name, root)
        record["path"] = f"OEBPS/text/{name}"
        document_records[name] = record
    css = write_css(stage)
    fonts = copy_fonts(stage)
    resources = [PurePosixPath(record["path"]) for record in document_records.values()]
    resources.append(PurePosixPath(css["path"]))
    resources.extend(PurePosixPath(row["path"]) for row in fonts)
    package = create_package(stage, resources, expected_receipt_sha)
    container = create_container(stage)
    entries = inventory(stage)
    destination = output / epub_name
    archive = create_zip(stage, destination)
    return {
        "archive": archive,
        "unpacked_tree_sha256": tree_sha(entries),
        "unpacked_inventory": entries,
        "documents": document_records,
        "css": css,
        "fonts": fonts,
        "package": package,
        "container": container,
        "pandoc": pandoc,
        "math_sanitization": math_regions,
        "read_metrics": read_metrics,
        "accepted_reader_inputs_sha256": expected_receipt_sha,
        "generated_reader_stdout": generated.stdout.strip(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--name", default=DEFAULT_NAME)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    require(output.is_relative_to(REPO.resolve()) or output.is_relative_to(STATE.resolve()), "output directory must remain inside the production repository or durable task state")
    require(output not in (REPO.resolve(), STATE.resolve()), "output directory is too broad")
    output.mkdir(parents=True, exist_ok=True)
    receipt, units = current_inputs()
    canonical = build_one(output, "canonical", args.name, receipt, units)
    cold_name = "cold-" + args.name
    cold = build_one(output, "cold", cold_name, receipt, units)
    require(canonical["archive"]["sha256"] == cold["archive"]["sha256"], "cold-build EPUB bytes differ")
    require(canonical["unpacked_tree_sha256"] == cold["unpacked_tree_sha256"], "cold-build unpacked tree differs")
    result = {
        "schema": "pnb-sets-epub3-build-receipt/1",
        "status": "pass",
        "scope": {"unit_ids": [row["unit_id"] for row in units], "source_units": 7, "body_sections": 6, "claim": "complete Sets chapter only; not the complete 722-unit edition"},
        "source_revision": REVISION,
        "version": VERSION,
        "modified": MODIFIED,
        "builder_path": "tools/build_sets_epub.py",
        "builder_sha256": sha(Path(__file__).read_bytes()),
        "accepted_reader_inputs_sha256": canonical["accepted_reader_inputs_sha256"],
        "source_units": units,
        "canonical": {key: value for key, value in canonical.items() if key != "unpacked_inventory"},
        "cold": {"archive": cold["archive"], "unpacked_tree_sha256": cold["unpacked_tree_sha256"]},
        "deterministic_cold_match": True,
        "teX_engine_invoked": False,
    }
    receipt_path = output / "BUILD_RECEIPT.json"
    write_json(receipt_path, result)
    print(json_text({"artifact": canonical["archive"], "mathml": canonical["read_metrics"]["mathml_roots"], "figures": canonical["read_metrics"]["figures"], "sections": canonical["read_metrics"]["sections"], "deterministic_cold_match": True, "receipt": {"path": str(receipt_path), "bytes": receipt_path.stat().st_size, "sha256": sha(receipt_path.read_bytes())}}), end="")


if __name__ == "__main__":
    main()
