"""Render proof-node formulas and place the verified proof trees in the web reader."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess

from lxml import etree, html

from expand_web_math import Expander, parse_macros


PROOF_ID = re.compile(r"\\hypertarget\{(proof-tree-\d+)\}\{\}")
SPLIT_MATH = re.compile(r"(?<!\\)\$")


def read_json(path):
    return json.loads(path.read_bytes())


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf8")


class ProofMath:
    def __init__(self, expander):
        self.expander = expander
        self.expressions = {}
        self.occurrences = Counter()

    def add(self, expression):
        expression = expression.strip()
        if not expression:
            return None
        if expression not in self.expressions:
            self.expressions[expression] = "proof-formula-" + str(len(self.expressions) + 1)
        slot = self.expressions[expression]
        self.occurrences[slot] += 1
        return slot

    def fill(self, elem, value):
        pieces = SPLIT_MATH.split(value)
        if len(pieces) == 1:
            pieces = ["", value, ""] if "\\" in value else pieces
        if len(pieces) % 2 == 0:
            raise ValueError(f"Unclosed proof math delimiters in {value!r}")
        last = None
        for i, piece in enumerate(pieces):
            if not piece:
                continue
            if i % 2:
                if slot := self.add(piece):
                    last = etree.SubElement(elem, "span", {"data-proof-formula": slot})
            elif last is None:
                elem.text = (elem.text or "") + piece
            else:
                last.tail = (last.tail or "") + piece

    def ast(self, version):
        blocks = []
        for expression, identifier in self.expressions.items():
            attr = [identifier, [], []]
            math = {"t": "Math", "c": [{"t": "InlineMath"}, self.expander.expand(expression)]}
            paragraph = {"t": "Para", "c": [math]}
            blocks.append({"t": "Div", "c": [attr, [paragraph]]})
        return {"pandoc-api-version": version, "meta": {}, "blocks": blocks}


def indexed_slots(document, identifiers):
    slots = {}
    for node in document.iter():
        key = node.get("id")
        if key in identifiers:
            if key in slots:
                raise ValueError(f"Repeated placement ID {key}")
            slots[key] = node
    if slots.keys() != identifiers:
        raise ValueError(f"Missing placement IDs {identifiers - slots.keys()}")
    return slots


def replace_node(current, replacement):
    replacement.tail = current.tail
    parent = current.getparent()
    if current.tag == "div" and replacement.tag == "span":
        replacement.tag = "div"
    parent.replace(current, replacement)


def nested_table(table, fragments, converter):
    container = etree.Element("table", {"class": "proof-rule-table", "dir": "ltr"})
    body = etree.SubElement(container, "tbody")
    for row in table["rows"]:
        tr = etree.SubElement(body, "tr")
        for source_cell in row:
            td = etree.SubElement(tr, "td", source_cell["attributes"])
            for component in source_cell["content"]:
                if "table" in component:
                    td.append(nested_table(component["table"], fragments, converter))
                    continue
                original = component["tex"]
                end = 0
                for match in PROOF_ID.finditer(original):
                    if part := original[end:match.start()].strip():
                        converter.fill(etree.SubElement(td, "span"), part)
                    td.append(fragments[match[1]])
                    end = match.end()
                if part := original[end:].strip():
                    converter.fill(etree.SubElement(td, "span"), part)
    return container


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("directory", type=Path)
    root = cli.parse_args().directory
    config = (root / "upstream/open-logic-config.sty").read_text("utf8")
    converter = ProofMath(Expander(parse_macros(config)))
    markup = read_json(root / "WEB-PROOF-FRAGMENTS.json")
    tableau_path = root / "WEB-TABLEAU-FRAGMENTS.json"
    tableaux = read_json(tableau_path) if tableau_path.exists() else {}
    all_markup = markup | tableaux
    fragments = {identifier: etree.fromstring(value.encode()) for identifier, value in all_markup.items()}
    for fragment in fragments.values():
        for node in fragment.xpath(".//*[@data-tex]"):
            converter.fill(node, node.attrib.pop("data-tex"))
    nested = read_json(root / "WEB-NESTED-PROOF-TABLES.json")
    rendered_tables = {}
    nested_proofs = set()
    for identifier, table in nested.items():
        rendered = nested_table(table, fragments, converter)
        rendered.set("id", identifier)
        nested_proofs.update(rendered.xpath(".//*[starts-with(@id,'proof-tree-')]/@id"))
        rendered_tables[identifier] = rendered

    api = read_json(root / "pandoc-expanded-math.json")["pandoc-api-version"]
    ast = root / "pandoc-proof-formulas.json"
    write_json(ast, converter.ast(api))
    math_html = root / "proof-formulas.html"
    run = subprocess.run(
        ["pandoc", str(ast), "--from=json", "--to=html5", "--mathml", "--output=" + str(math_html)],
        check=True, capture_output=True,
    )
    (root / "proof-formulas.stderr").write_bytes(run.stderr)
    math = html.fromstring(math_html.read_bytes(), parser=html.HTMLParser(encoding="utf-8"))
    rendered = {}
    for node in math.xpath("//*[starts-with(@id,'proof-formula-')]"):
        matches = node.xpath("./p/*")
        if len(matches) != 1:
            raise ValueError(f"Unexpected output for {node.get('id')}")
        rendered[node.get("id")] = etree.tostring(matches[0], encoding="utf8")
    if set(rendered) != set(converter.occurrences):
        raise ValueError("Proof formula IDs changed during MathML rendering")
    body = html.fromstring((root / "web-math-diagnostic.html").read_bytes(), parser=html.HTMLParser(encoding="utf-8"))
    citation_path = root / "WEB-CITATION-FRAGMENTS.json"
    citations = {}
    if citation_path.exists():
        citation_projection = read_json(citation_path)
        citations = citation_projection["citations"]
        body.find("body").append(etree.fromstring(citation_projection["bibliography"].encode()))
    standalone = fragments.keys() - nested_proofs
    slots = indexed_slots(body, rendered_tables.keys() | standalone | citations.keys())
    for identifier, table in rendered_tables.items():
        replace_node(slots[identifier], table)
    for identifier in standalone:
        replace_node(slots[identifier], fragments[identifier])
    for identifier, citation in citations.items():
        fragment = etree.fromstring(citation.encode())
        fragment.set("id", identifier)
        replace_node(slots[identifier], fragment)

    used = Counter()
    for slot in body.xpath("//*[@data-proof-formula]"):
        identifier = slot.attrib.pop("data-proof-formula")
        used[identifier] += 1
        slot.append(etree.fromstring(rendered[identifier]))
    if used != converter.occurrences:
        raise ValueError("Missing or repeated proof math in HTML")
    emitted = Counter(k for k in body.xpath("//*[@id]/@id") if k in all_markup)
    if emitted != Counter(all_markup.keys()):
        raise ValueError("Missing or repeated proof tree or tableau in HTML")
    target = root / "web-proof-diagnostic.html"
    body.set("lang", "pnb-Arab-PK")
    body.set("dir", "rtl")
    target.write_bytes(etree.tostring(body, encoding="utf-8", method="html", doctype="<!DOCTYPE html>"))
    remaining = [k for k, v in rendered.items() if not v.startswith(b"<math ")]
    data = {
        "proof_containers": len(markup), "tableaux": len(tableaux), "nested_tables": len(nested),
        "citation_occurrences": len(citations),
        "formula_occurrences": sum(used.values()),
        "unique_formulas": len(rendered), "fallback_formula_ids": remaining,
        "fallback_occurrences": sum(used[k] for k in remaining), "html_sha256": sha256(target.read_bytes()).hexdigest(),
        "diagnostic_only": True,
    }
    write_json(root / "WEB-PROOF-RENDER.json", data)
    print({k: v for k, v in data.items() if k != "fallback_formula_ids"})


if __name__ == "__main__":
    main()
