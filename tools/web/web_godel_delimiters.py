"""Preserve the two directional Gödel delimiters from the pinned Open Logic style."""

from collections import Counter
from hashlib import sha256
import json

from fontTools import subset
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from lxml import etree

from expand_web_math import GODEL_CLOSING_MARKER, GODEL_OPENING_MARKER


FONT_FILE = "OpenLogicGodelDelimiters.ttf"
FONT_NAME = "Open Logic Godel Delimiters"
OPEN_GLYPH = "godel.open"
FONT_SOURCE = "NotoSerif-Regular.ttf"
FONT_SOURCE_SHA256 = "19e72cd8d595fae5bd74a5206f5d938512e1183d4fed7abb1ec1be1d7efa5f88"


def make_font(fonts):
    source = fonts / FONT_SOURCE
    if sha256(source.read_bytes()).hexdigest() != FONT_SOURCE_SHA256:
        raise ValueError("Gödel delimiter base font differs from the verified Noto Serif font")
    font = TTFont(source, recalcTimestamp=False)
    glyph = font.getBestCmap()[ord("#")]
    metrics = font["hmtx"].metrics
    advance, _ = metrics[glyph]
    source_outline = font.getGlyphSet()[glyph]
    normal_pen = TTGlyphPen(None)
    mirror_pen = TTGlyphPen(None)
    source_outline.draw(normal_pen)
    source_outline.draw(TransformPen(mirror_pen, (-1, 0, 0, 1, advance, 0)))
    glyph_order = font.getGlyphOrder().copy()
    font["glyf"][glyph] = normal_pen.glyph()
    font["glyf"][OPEN_GLYPH] = mirrored = mirror_pen.glyph()
    font.setGlyphOrder([*glyph_order, OPEN_GLYPH])
    mirrored.recalcBounds(font["glyf"])
    metrics[OPEN_GLYPH] = (advance, mirrored.xMin)
    for cmap in font["cmap"].tables:
        if cmap.isUnicode():
            cmap.cmap[ord(GODEL_OPENING_MARKER)] = OPEN_GLYPH

    options = subset.Options()
    options.hinting = False
    options.name_IDs = ["*"]
    options.name_legacy = True
    options.name_languages = ["*"]
    sub = subset.Subsetter(options=options)
    sub.populate(unicodes=[ord("#"), ord(GODEL_OPENING_MARKER)])
    sub.subset(font)

    name_replacements = {
        1: FONT_NAME, 2: "Regular", 3: FONT_NAME + " Regular 1.0",
        4: FONT_NAME, 6: "OpenLogicGodelDelimiters", 16: FONT_NAME, 17: "Regular",
        18: FONT_NAME, 20: "OpenLogicGodelDelimiters", 21: FONT_NAME, 22: "Regular",
        25: "OpenLogicGodelDelimiters",
    }
    for record in font["name"].names:
        if record.nameID in name_replacements:
            record.string = name_replacements[record.nameID]
    font["name"].setName(
        "Subset of Noto Serif containing its number sign and a horizontally mirrored copy.",
        10, 3, 1, 0x409,
    )
    font.save(fonts / FONT_FILE, reorderTables=True)
    license_path = fonts / "OFL.txt"
    license_text = license_path.read_text(encoding="utf-8")
    license_body = license_text.split("\n", maxsplit=1)[1]
    (fonts / "OpenLogicGodelDelimiters-OFL.txt").write_text(
        "Copyright 2022 The Noto Project Authors (https://github.com/notofonts/latin-greek-cyrillic)\n"
        "Open Logic Godel Delimiters is a modified subset of Noto Serif.\n"
        + license_body, encoding="utf-8", newline="\n",
    )


def materialize_godel_delimiters(document, directory):
    counts = Counter()
    by_section = Counter()
    section = None
    for node in document.find("body").iter():
        if node.tag in ("h1", "h2", "h3", "h4", "h5", "h6") and node.get("id"):
            section = node.get("id")
        if node.tag == "annotation" and node.text:
            node.text = node.text.replace(
                r"\text{" + GODEL_OPENING_MARKER + "}", r"\reflectbox{\tiny\#}"
            ).replace(
                r"\text{" + GODEL_CLOSING_MARKER + "}", r"\mbox{\tiny\#}"
            )
        if node.tag != "mtext":
            continue
        if node.text == GODEL_OPENING_MARKER:
            node.set("class", "godel-delimiter godel-opening")
            counts["opening"] += 1
            by_section[section] += 1
        elif node.text == GODEL_CLOSING_MARKER:
            node.text = "#"
            node.set("class", "godel-delimiter godel-closing")
            counts["closing"] += 1
    if not counts["opening"] or counts["opening"] != counts["closing"] or None in by_section:
        raise ValueError(f"Gödel delimiter placements do not agree: {dict(counts)}")
    xml = etree.tostring(document, encoding="utf-8")
    if (xml.count(GODEL_OPENING_MARKER.encode()) != counts["opening"]
            or GODEL_CLOSING_MARKER.encode() in xml):
        raise ValueError("Unexpected internal marker outside a Gödel delimiter")
    make_font(directory / "fonts")
    data = {
        **counts, "sections": dict(sorted(by_section.items())),
        "font_sha256": sha256((directory / "fonts" / FONT_FILE).read_bytes()).hexdigest(),
        "base_font_sha256": FONT_SOURCE_SHA256,
    }
    (directory / "WEB-GODEL-DELIMITERS.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return data
