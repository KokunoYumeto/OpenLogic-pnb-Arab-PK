"""Apply Punjabi Shahmukhi book metadata and navigation to the cumulative HTML."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re
from shutil import copyfile
from urllib.parse import unquote

from lxml import etree, html

from web_godel_delimiters import materialize_godel_delimiters
from web_modal_symbols import materialize_modal_symbols


TITLE = "اوپن لاجک متن — پنجابی شاہ مکھی"
ATTRIBUTION = "ایہ اوپن لاجک پروجیکٹ دے اوپن لاجک متن دا اے آئی نال کیتا گیا پنجابی شاہ مکھی ترجمہ اے۔ ریاضی دیاں کجھ اصطلاحاں ہجے عارضی نیں۔"
LINKS = (
    ("اوپن لاجک پروجیکٹ", "https://openlogicproject.org/people/"),
    ("انگریزی ماخذ", "https://github.com/OpenLogicProject/OpenLogic/tree/9620cc73f9c8e0ad003c514a5d3748f29611c4c0"),
    ("کریئیٹو کامنز انتساب ۴٫۰ بین الاقوامی لائسنس", "https://creativecommons.org/licenses/by/4.0/"),
    ("ہور ترجمے", "https://github.com/KokunoYumeto/OpenLogic-translations"),
)


def add(parent, tag, value=None, **attributes):
    result = etree.SubElement(parent, tag, attributes)
    result.text = value
    return result


def build_navigation(header, body):
    nav = add(header, "nav", **{"aria-label": "فہرست"})
    add(nav, "h2", "فہرست")
    first = add(nav, "ol")
    part_items = None
    count = 0
    for node in body:
        if node.tag not in ("h1", "h2") or not node.get("id"):
            continue
        target = node.get("id")
        name = " ".join(node.xpath(".//text()[not(ancestor::annotation)]"))
        name = " ".join(name.split())
        if node.tag == "h1":
            item = add(first, "li")
            add(item, "a", name, href="#" + target)
            part_items = add(item, "ol")
        else:
            item = add(part_items if part_items is not None else first, "li")
            add(item, "a", name, href="#" + target)
        count += 1
    return count


def wrap_tables(body):
    for table in body.xpath(".//table[not(ancestor::table)]"):
        wrapper = etree.Element("div", {"class": "table-wrap"})
        wrapper.tail, table.tail = table.tail, None
        table.getparent().replace(table, wrapper)
        wrapper.append(table)


def figure_description(slot):
    def text(node):
        return " ".join(" ".join(node.xpath(".//text()[not(ancestor::annotation)]")).split())
    caption = slot.xpath("ancestor::figure[1]/figcaption")
    if caption and text(caption[0]):
        return text(caption[0])
    context = slot.xpath("preceding::p[1]")
    if context and text(context[0]):
        prose = text(context[0])
        if len(prose) > 360:
            prose = " ".join(prose[-360:].split()[1:])
        return prose
    section = slot.xpath("preceding::*[self::h2 or self::h3 or self::h4][1]")
    if section:
        return text(section[0]) + " دا خاکہ"
    raise ValueError(f"No nearby description for {slot.get('id')}")


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("directory", type=Path)
    cli.add_argument("--diagram-assets", type=Path)
    cli.add_argument("--txfonts-source", type=Path, default=Path(__file__).with_name("txfonts-source"))
    args = cli.parse_args()
    root = args.directory
    doc = html.fromstring((root / "web-proof-diagnostic.html").read_bytes(),
                          parser=html.HTMLParser(encoding="utf-8"))
    godel_delimiters = materialize_godel_delimiters(doc, root)
    modal_symbols = materialize_modal_symbols(doc, root, args.txfonts_source)
    head = doc.find("head")
    body = doc.find("body")
    for title_block in body.xpath("./header[@id='title-block-header']"):
        if title_block.xpath(".//a|.//*[@id]") or doc.xpath("//a[@href='#title-block-header']"):
            raise ValueError("The generated title block contains navigation targets")
        body.remove(title_block)
    head.find("title").text = TITLE
    add(head, "meta", name="author", content="Open Logic Project")
    credits = json.loads((root / "reader/ai-attribution.json").read_bytes())
    description = " ".join(
        f"{credit['role']} — {credit['model']}۔" for credit in credits
    )
    add(head, "meta", name="description", content=f"{ATTRIBUTION} {description}")
    add(head, "link", rel="stylesheet", href="open-logic-pnb.css")
    for old in head.xpath("./style"):
        head.remove(old)
    header = etree.Element("header")
    add(header, "h1", TITLE)
    add(header, "p", ATTRIBUTION)
    credit_list = add(header, "ul")
    for credit in credits:
        item = add(credit_list, "li", credit["role"] + " — ")
        add(item, "bdi", credit["model"], lang="en", dir="ltr").tail = "۔"
    provenance = add(header, "ul")
    for label, url in LINKS:
        add(add(provenance, "li"), "a", label, href=url)
    navigation = build_navigation(header, body)
    body.insert(0, header)
    wrap_tables(body)
    diagrams = [x for x in body.xpath(".//*[@id]") if re.fullmatch(r"diagram-\d+", x.get("id"))]
    diagram_targets = {x.get("id") for x in diagrams}
    mapping = json.loads((root / "WEB-FIGURE-PROJECTION.json").read_bytes())
    assert diagram_targets == {r["id"] for r in mapping["figures_by_order"]}
    descriptions = json.loads(Path(__file__).with_name("diagram_alternatives_pnb.json").read_bytes())
    if descriptions.keys() - diagram_targets or any(not value.strip() for value in descriptions.values()):
        raise ValueError("Diagram descriptions do not match the reader placements")
    for slot in diagrams:
        description = descriptions.get(slot.get("id")) or figure_description(slot)
        slot.set("aria-label", description)
    if args.diagram_assets:
        dest = root / "diagrams"
        dest.mkdir(exist_ok=True)
        for slot in diagrams:
            key = slot.get("id")
            image = args.diagram_assets / (key + ".svg")
            if not image.is_file():
                raise ValueError(f"Missing diagram image {image}")
            if image.resolve() != (dest / image.name).resolve():
                copyfile(image, dest / image.name)
            label = slot.get("aria-label")
            if not label:
                raise ValueError(f"Missing text alternative for {key}")
            add(slot, "img", alt=" ".join(label.split()), src="diagrams/" + image.name)
    copyfile(Path(__file__).with_name("reader_web.css"), root / "open-logic-pnb.css")
    doc.set("dir", "rtl")
    doc.set("lang", "pnb-Arab-PK")
    all_ids = Counter(doc.xpath("//*[@id]/@id"))
    links = [unquote(href[1:]) for href in doc.xpath("//a[starts-with(@href,'#')]/@href")]
    unresolved = set(links) - all_ids.keys()
    duplicate = [key for key, count in all_ids.items() if count != 1]
    if unresolved or duplicate:
        raise ValueError(f"Unresolved internal links: {sorted(unresolved)}. Repeated IDs: {duplicate}.")
    fallbacks = doc.xpath("//span[@class='math inline' or @class='math display']")
    if fallbacks:
        raise ValueError(f"MathML rendering has {len(fallbacks)} fallbacks.")
    out = etree.tostring(doc, encoding="utf-8", method="html", doctype="<!DOCTYPE html>")
    name = "open-logic-pnb.html" if args.diagram_assets else "open-logic-pnb-diagnostic.html"
    (root / name).write_bytes(out)
    record = {"file": name, "sha256": sha256(out).hexdigest(), "navigation_entries": navigation,
              "internal_links": len(links), "unique_anchors": len(all_ids), "mathml_elements": len(doc.xpath("//math")),
              "godel_delimiters": godel_delimiters,
              "modal_symbols": modal_symbols,
              "math_fallbacks": len(fallbacks), "diagram_slots": len(diagrams),
              "diagram_assets_embedded": len(diagrams) if args.diagram_assets else 0}
    (root / "WEB-READER-PACKAGE.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf8")
    print(record)


if __name__ == "__main__":
    main()
