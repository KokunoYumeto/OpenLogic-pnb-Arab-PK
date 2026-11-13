"""Embed the two exact txsyc operators used by Open Logic's frozen style."""

from collections import Counter
from hashlib import sha256
import json
import re

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.t1Lib import T1Font
from fontTools.ttLib import TTFont

from expand_web_math import BOX_CONDITIONAL_MARKER, STRICT_MARKER


FONT_FILE = "OpenLogicModalSymbols.otf"
NOTICE_FILE = "Txfonts-NOTICE.txt"
GPL_FILE = "Txfonts-GPL.txt"
FONT_SHA256 = "daba10834af8bf5dcb3c6b03e919daf61e6ba74c3ef71aa3c74f80dc3945ec5e"
DATE = 3877286400
SYMBOLS = {
    STRICT_MARKER: ("fishhookright", 74, "strict", 764, 62, "strict conditional"),
    BOX_CONDITIONAL_MARKER: ("boxright", 128, "squareright", 1398, 62, "counterfactual conditional"),
}


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def build_modal_font(source_dir, out_dir):
    pfb = source_dir / "txsyc.pfb"
    if digest(pfb) != FONT_SHA256:
        raise ValueError("The txsyc input differs from the documented Type 1 font")
    original = T1Font(str(pfb))
    original.parse()
    glyphs = original.getGlyphSet()
    charset = {ord(c): value[2] for c, value in SYMBOLS.items()}
    chars = {".notdef": T2CharStringPen(500, None).getCharString()}
    widths = {".notdef": (500, 0)}
    expected = {}
    for _, slot, glyph, width, lsb, _ in SYMBOLS.values():
        if original.font["Encoding"][slot] != glyph:
            raise ValueError(f"Unexpected glyph in txsyc slot {slot}")
        raw = RecordingPen()
        glyphs[glyph].draw(raw)
        converted = T2CharStringPen(width, None)
        raw.replay(converted)
        char = converted.getCharString()
        expected[glyph] = raw.value
        chars[glyph] = char
        widths[glyph] = (width, lsb)
    family = "Open Logic Modal Symbols"
    font = FontBuilder(1000, isTTF=False)
    font.setupGlyphOrder(list(chars))
    font.setupCharacterMap(charset)
    font.setupCFF("OpenLogicModalSymbols", {"FullName": family, "FamilyName": family, "Weight": "Regular"}, chars, {})
    font.setupHorizontalMetrics(widths)
    font.setupHorizontalHeader(ascent=800, descent=-200)
    font.setupNameTable({
        "familyName": family, "styleName": "Regular", "uniqueFontIdentifier": family + " 1.0",
        "fullName": family, "psName": "OpenLogicModalSymbols", "version": "Version 1.0",
        "copyright": "Glyph outlines from Young Ryu's txsyc (TX fonts).",
        "licenseDescription": "GNU General Public License with the TX fonts document-embedding exception.",
        "licenseInfoURL": "https://ctan.org/pkg/txfonts",
    })
    font.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200)
    font.setupPost()
    font.font["head"].created = font.font["head"].modified = DATE
    font.font.recalcTimestamp = False
    destination = out_dir / FONT_FILE
    font.save(destination)
    with TTFont(destination) as encoded:
        exported = encoded.getGlyphSet()
        for name, outline in expected.items():
            emitted = RecordingPen()
            exported[name].draw(emitted)
            if outline != emitted.value:
                raise ValueError(f"Conversion changed the outline for {name}")
    for name in (NOTICE_FILE, GPL_FILE):
        (out_dir / name).write_bytes((source_dir / name).read_bytes())


def materialize_modal_symbols(document, directory, source_dir):
    upstream = directory / "upstream/sty/open-logic.sty"
    style = upstream.read_text(encoding="utf-8")
    for command, slot, *_ in SYMBOLS.values():
        pattern = re.escape("\\DeclareMathSymbol{\\" + command
                            + r"}{\mathbin}{symbolsC}{" + str(slot) + "}")
        if len(re.findall(pattern, style)) != 1:
            raise ValueError(f"The frozen style no longer uses the expected slot for {command}")
    counts = Counter()
    sections = Counter()
    section = None
    for node in document.find("body").iter():
        if node.tag in ("h1", "h2", "h3", "h4", "h5", "h6") and node.get("id"):
            section = node.get("id")
        if node.tag == "annotation" and node.text:
            for marker, (cmd, *_) in SYMBOLS.items():
                node.text = node.text.replace(r"\mathbin{" + marker + "}", "\\" + cmd + "{}")
        if node.tag not in ("mi", "mo") or node.text not in SYMBOLS:
            continue
        command, *_, label = SYMBOLS[node.text]
        node.tag = "mo"
        node.set("class", "modal-operator")
        node.set("aria-label", label)
        if section is None:
            raise ValueError(f"Operator outside a labeled section: {command}")
        counts[command] += 1
        sections[section] += 1
    if counts.keys() != {value[0] for value in SYMBOLS.values()}:
        raise ValueError(f"Missing modal symbol occurrences: {dict(counts)}")
    build_modal_font(source_dir, directory / "fonts")
    receipt = {"counts": dict(counts), "sections": dict(sorted(sections.items())),
               "source_font_sha256": FONT_SHA256, "frozen_style_sha256": digest(upstream),
               "web_font_sha256": digest(directory / "fonts" / FONT_FILE)}
    (directory / "WEB-MODAL-SYMBOLS.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt
