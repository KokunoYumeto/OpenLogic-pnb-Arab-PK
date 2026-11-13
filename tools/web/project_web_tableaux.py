"""Convert Open Logic tableaux to ordered, reflowable branch markup."""

import argparse
from collections import Counter
from dataclasses import dataclass, field
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re

from project_web_tags import argument


ENVIRONMENT = re.compile(r"\\begin\{(?P<kind>oltableau|tableau)\}(?P<body>[\s\S]*?)\\end\{(?P=kind)\}")
TOKEN = re.compile(r"\\[A-Za-z@]+|\\.|[{}\[\],]")
PROPERTY = re.compile(r"(?P<key>just|checked|close|name|move by)(?:\s*=\s*(?P<value>[\s\S]+))?$")


@dataclass
class Node:
    formula: str
    attributes: dict
    children: list = field(default_factory=list)


def header_fields(source):
    fields, cursor = [], 0
    braces = brackets = 0
    for token in TOKEN.finditer(source):
        value = token[0]
        if value == "{":
            braces += 1
        elif value == "}":
            braces -= 1
        elif not braces:
            if value == "[":
                brackets += 1
            elif value == "]":
                brackets -= 1
            elif value == "," and not brackets:
                fields.append(source[cursor:token.start()].strip())
                cursor = token.end()
    fields.append(source[cursor:].strip())
    return fields


def parse_node(source, start):
    if source[start] != "[":
        raise ValueError(f"Expected branch at {source[start:start + 50]!r}")
    braces = 0
    cursor = start + 1
    children = []
    header_end = None
    while token := TOKEN.search(source, cursor):
        value = token[0]
        if value == "{":
            braces += 1
        elif value == "}":
            braces -= 1
        elif not braces and value == "[":
            # Optional formula/rule arguments sit on the same line as the macro
            # or immediately follow a closing mandatory brace.
            before = source[start + 1:token.start()]
            if header_end is None and before and not before[-1].isspace() and before[-1] in "}]":
                _, cursor = optional_argument(source, token.start())
                continue
            if header_end is None:
                header_end = token.start()
            child, cursor = parse_node(source, token.start())
            children.append(child)
            continue
        elif not braces and value == "]":
            fields = header_fields(source[start + 1:header_end if header_end is not None else token.start()])
            formula = fields[0]
            attrs = {}
            for item in fields[1:]:
                if not item:
                    continue
                prop = PROPERTY.fullmatch(item)
                if prop is None:
                    raise ValueError(f"Unrecognized tableau field {item!r}")
                val = prop["value"]
                if val and val.startswith("{"):
                    val, end = argument(val, 0)
                    if prop["value"][end:].strip():
                        raise ValueError("Unexpected tableau property suffix")
                attrs[prop["key"]] = val if val is not None else True
            return Node(formula, attrs, children), token.end()
        cursor = token.end()
    raise ValueError("Unclosed tableau branch")


def optional_argument(source, start):
    depth = 1
    for m in TOKEN.finditer(source, start + 1):
        if m[0] == "[":
            depth += 1
        elif m[0] == "]":
            depth -= 1
            if not depth:
                return source[start + 1:m.start()], m.end()
    raise ValueError("Unclosed tableau option")


def render(root, identifier, line_numbers):
    counts = Counter()

    def visit(node, line):
        counts["nodes"] += 1
        result = ['<li class="tableau-node"><div class="tableau-entry">']
        if node.formula:
            counts["formulas"] += 1
            if line_numbers:
                result.append(f'<span class="tableau-line">{line}</span>')
            formula = node.formula
            if not formula.startswith("$"):
                formula = "$" + formula + "$"
            result.append(f'<span class="tableau-formula" data-tex="{escape(formula, quote=True)}"></span>')
        if value := node.attributes.get("just"):
            counts["justifications"] += 1
            if value.strip() == r"\TAss":
                result.append('<span class="tableau-just" dir="rtl">مفروضہ</span>')
            else:
                result.append(f'<span class="tableau-just" data-tex="{escape(value, quote=True)}"></span>')
        if node.attributes.get("checked"):
            counts["checked"] += 1
            result.append('<span class="tableau-checked" aria-label="جانچیا ہویا">✓</span>')
        if node.attributes.get("close"):
            counts["closed"] += 1
            result.append('<span class="tableau-close" aria-label="بند ٹہنی">×</span>')
        result.append("</div>")
        if node.children:
            result.append('<ul class="tableau-branches">')
            result.extend(visit(child, line + int(bool(node.formula))) for child in node.children)
            result.append("</ul>")
        result.append("</li>")
        return "".join(result)

    html = '<div id="' + identifier + '" class="tableau" dir="ltr"><ul>' + visit(root, 1) + "</ul></div>"
    return html, counts


def project(text):
    fragments, failures, totals = {}, [], Counter()

    def replace(match):
        value = re.sub(r"(?m)(?<!\\)%[^\n]*", "", match["body"]).strip()
        numbering = True
        if value.startswith("{"):
            opts, cursor = argument(value, 0)
            numbering = "not line numbering" not in opts
            value = value[cursor:].lstrip()
        identifier = f"tableau-tree-{len(fragments) + len(failures) + 1}"
        try:
            root, end = parse_node(value, 0)
            if value[end:].strip():
                raise ValueError(f"Unexpected tableau text: {value[end:].strip()[:120]}")
        except ValueError as exc:
            failures.append({"id": identifier, "line": text.count("\n", 0, match.start()) + 1, "error": str(exc)})
            return match[0]
        markup, counts = render(root, identifier, numbering)
        fragments[identifier] = markup
        totals.update(counts)
        return "\n\\hypertarget{" + identifier + "}{}\n"

    return ENVIRONMENT.sub(replace, text), fragments, failures, totals


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("directory", type=Path)
    root = cli.parse_args().directory
    source = (root / "web-proof-projection.tex").read_text("utf8")
    result, fragments, errors, counts = project(source)
    (root / "web-tableau-projection.tex").write_bytes(result.encode())
    (root / "WEB-TABLEAU-FRAGMENTS.json").write_text(json.dumps(fragments, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    data = {"tableaux": len(fragments), "counts": counts, "errors": errors, "sha256": sha256(result.encode()).hexdigest()}
    (root / "WEB-TABLEAU-PROJECTION.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(data)
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
