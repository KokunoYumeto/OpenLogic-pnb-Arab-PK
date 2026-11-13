"""Expand the pinned Open Logic math macros for Pandoc's MathML writer."""

import argparse
from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re

from project_web_structure import optional, NEXT_ARGUMENT
from project_web_tags import argument


GODEL_OPENING_MARKER = "\ue000"
GODEL_CLOSING_MARKER = "\ue001"
STRICT_MARKER = "\ue002"
BOX_CONDITIONAL_MARKER = "\ue003"


DECLARATION = re.compile(
    r"(?m)^[ \t]*\\(DeclareDocumentCommand|DeclareDocumentMacro|DeclareMathOperator|newcommand)\*?"
    r"\s*(?:\{\\([A-Za-z@]+)\}|\\([A-Za-z@]+))"
)
CONTROL = re.compile(r"\\([A-Za-z@]+|.)")
MATH_REFERENCE = re.compile(r"\\hyperlink(?=\s*\{)")
MATH_TAG = re.compile(r"\\tag\*?(?=\s*\{)")
SPEC = re.compile(r"t\{([^{}])\}|d\(\)|[mos]")
PLACEHOLDER = re.compile(r"#([1-9])")
GREEK = dict(zip("ABCDEFGHKLORST", (
    "varphi", "psi", "chi", "theta", "alpha", "beta", "gamma", "delta",
    "xi", "zeta", "omega", "rho", "sigma", "tau",
), strict=True))


@dataclass(frozen=True)
class Macro:
    spec: tuple
    body: str


def first_token(text, cursor):
    cursor = NEXT_ARGUMENT.match(text, cursor).end()
    if cursor >= len(text):
        raise ValueError("Missing mandatory TeX argument")
    if text[cursor] == "{":
        return argument(text, cursor)
    match = CONTROL.match(text, cursor)
    if match:
        return match[0], match.end()
    if text[cursor] == "!" and text[cursor + 1:cursor + 2] in GREEK:
        return text[cursor:cursor + 2], cursor + 2
    return text[cursor], cursor + 1


def delimited_parentheses(text, cursor):
    start = NEXT_ARGUMENT.match(text, cursor).end()
    if text[start:start + 1] != "(":
        return None, cursor
    depth = 1
    for match in re.finditer(r"\\.|[()]", text[start + 1:]):
        if match[0] == "(":
            depth += 1
        elif match[0] == ")":
            depth -= 1
            if depth == 0:
                stop = start + 1 + match.start()
                return text[start + 1:stop], stop + 1
    raise ValueError("Unclosed parenthesized macro argument")


def math_optional(text, cursor):
    start = NEXT_ARGUMENT.match(text, cursor).end()
    if text[start:start + 1] != "[":
        return None, cursor
    brackets, braces = 1, 0
    for match in re.finditer(r"\\.|[{}\[\]]", text[start + 1:]):
        char = match[0]
        if char == "{":
            braces += 1
        elif char == "}":
            braces -= 1
        elif char == "[" and braces == 0:
            brackets += 1
        elif char == "]" and braces == 0:
            brackets -= 1
            if not brackets:
                stop = start + 1 + match.start()
                return text[start + 1:stop], stop + 1
    raise ValueError("Unclosed optional argument")


def parse_macros(source):
    macros = {}
    for m in DECLARATION.finditer(source):
        name = m[2] or m[3]
        cursor = m.end()
        if m[1] == "DeclareDocumentCommand":
            raw, cursor = argument(source, cursor)
            spec = tuple(x[0] for x in SPEC.finditer(raw))
            if "".join(spec) != "".join(raw.split()):
                continue
        elif m[1] == "newcommand":
            count, cursor = optional(source, cursor)
            spec = ("m",) * (int(count) if count else 0)
        else:
            spec = ()
        try:
            body, _ = first_token(source, cursor)
        except ValueError:
            continue
        if m[1] == "DeclareMathOperator":
            body = r"\operatorname{" + body + "}"
        macros[name] = Macro(spec, body.strip())
    # Engine primitives and font declarations are represented directly in MathML input.
    macros.update({
        "ensuremath": Macro(("m",), "{#1}"),
        "mathsfit": Macro(("m",), r"\mathsf{\mathit{#1}}"),
        "mathexclaim": Macro((), "!"),
        "oldphi": Macro((), r"\phi"),
        "oldepsilon": Macro((), r"\epsilon"),
        "gn": Macro(("m",), r"\ulcorner #1\urcorner"),
        "nicefrac": Macro(("m", "m"), r"{}^{#1}\!/\!{}_{#2}"),
        "textarabic": Macro(("m",), "#1"),
        "textenglish": Macro(("m",), "#1"),
        "pnbLatin": Macro(("m",), "#1"),
        "phantomsection": Macro((), ""),
        "relax": Macro((), ""),
        "shoveright": Macro(("m",), "#1"),
        "shoveleft": Macro(("m",), "#1"),
        "sFmla": Macro(("m", "m", "o"), r"\IfNoValueTF{#3}{}{#3\,}#1\,#2"),
        "pFmla": Macro(("m", "m", "m"), r"#3\,#1\,#2"),
        "xLongrightarrow": Macro(("m",), r"\overset{#1}{\Longrightarrow}"),
        "xrightarrowdbl": Macro(("o", "m"),
            r"\IfNoValueTF{#1}{\overset{#2}{\twoheadrightarrow}}"
            r"{\underset{#1}{\overset{#2}{\twoheadrightarrow}}}"),
        "emph": Macro(("m",), r"\text{#1}"),
        "textsc": Macro(("m",), r"\mathrm{#1}"),
        "small": Macro((), ""),
        "centering": Macro((), ""),
        "formula": Macro(("m",), "!#1"),
        "varolessthan": Macro((), r"\mathbin{⧀}"),
        "pto": Macro((), r"\mathrel{⇸}"),
        "smash": Macro(("m",), "#1"),
        "fishhookright": Macro((), r"\mathbin{" + STRICT_MARKER + "}"),
        "leftrightarroweq": Macro((), r"\mathrel{\underset{=}{\leftrightarrow}}"),
        "Gn": Macro(("m",), (
            r"{}^{\text{" + GODEL_OPENING_MARKER + r"}}{#1}{}^{\text{" + GODEL_CLOSING_MARKER + "}}"
        )),
        "notag": Macro((), ""),
        "raisebox": Macro(("m", "m"), "#2"),
        "boxright": Macro((), r"\mathbin{" + BOX_CONDITIONAL_MARKER + "}"),
        "lnotY": Macro((), r"\lnot Y"),
        "allowbreak": Macro((), ""),
        "mathrlap": Macro(("m",), "#1"),
    })
    return macros


MATH_TEXT_BOLD = re.compile(r"\\text\{\\textbf\{([^{}\n]+)\}\}")


def remove_math_links_and_tags(original):
    """Return TeX plus original hyperlinks and manual equation tags."""
    references, tags = [], []
    def replace_controls(source, pattern, action):
        output, cursor = [], 0
        while match := pattern.search(source, cursor):
            output.append(source[cursor:match.start()])
            item, cursor = argument(source, match.end())
            replacement, cursor = action(item, source, cursor)
            output.append(replacement)
        output.append(source[cursor:])
        return "".join(output)

    def link(key, source, cursor):
        label, end = argument(source, cursor)
        references.append((key, label))
        return label, end

    def tag(value, source, cursor):
        tags.append(value.strip())
        return "", cursor

    original = MATH_TEXT_BOLD.sub(r"\\text{\1}", original)
    text = replace_controls(original, MATH_REFERENCE, link)
    return replace_controls(text, MATH_TAG, tag), references, tags


class Expander:
    def __init__(self, macros):
        self.macros = macros
        self.counts = Counter()

    def read(self, text, cursor, spec):
        result = []
        for item in spec:
            if item == "m":
                value, cursor = first_token(text, cursor)
            elif item == "o":
                value, cursor = math_optional(text, cursor)
            elif item == "d()":
                value, cursor = delimited_parentheses(text, cursor)
            else:
                token = "*" if item == "s" else item[2]
                offset = NEXT_ARGUMENT.match(text, cursor).end()
                value = text[offset:offset + 1] == token
                if value:
                    cursor = offset + 1
            result.append(value)
        return result, cursor

    def select(self, body, values):
        cond = re.compile(r"\\(IfNoValue[TF]{1,2}|IfBoolean[TF]{1,2})\s*(?:\{\s*#([1-9])\s*\}|#([1-9]))")
        chunks = []
        cursor = 0
        while match := cond.search(body, cursor):
            chunks.append(body[cursor:match.start()])
            test, position = match[1], int(match[2] or match[3])
            variant, cursor = first_token(body, match.end())
            alternative = ""
            if test.endswith("TF"):
                alternative, cursor = first_token(body, cursor)
            is_true = values[position - 1] is None if test.startswith("IfNoValue") else bool(values[position - 1])
            selected = (variant if is_true else alternative) if test.endswith("TF") else (
                variant if is_true == test.endswith("T") else ""
            )
            chunks.append(self.select(selected, values))
        chunks.append(body[cursor:])
        return "".join(chunks)

    def expand(self, text, parents=()):
        if len(parents) > 32:
            raise ValueError("Macro expansion depth exceeded")
        text = re.sub(r"(?m)(?<!\\)%[^\n]*", "", text)
        text = re.sub(r"\\mathrel\s*\{\|\|\}\s*\\joinrel\s*\\Relbar\b", r"\\Vdash ", text)
        text = text.replace(r"\lnotY", r"\lnot Y")
        chunks, cursor = [], 0
        while match := CONTROL.search(text, cursor):
            chunks.append(self.formula_letters(text[cursor:match.start()]))
            name, cursor = match[1], match.end()
            if name == "applytofirst":
                font, cursor = first_token(text, cursor)
                content, cursor = first_token(text, cursor)
                lead, offset = first_token(content, 0)
                chunks.append(self.expand(font + "{" + lead + "}" + content[offset:], parents))
            elif name in ("text", "mbox", "textrm"):
                value, cursor = first_token(text, cursor)
                value = re.sub(r"\\(?:quad|qquad)\b", " ", value.replace(r"\/", ""))
                parts = re.split(r"(?<!\\)\$", value)
                chunks.append("".join(
                    self.expand(part, parents) if i % 2 else self.expand_math_text(part, parents)
                    for i, part in enumerate(parts)
                ))
            elif name == "intertext":
                value, cursor = first_token(text, cursor)
                # An intertext paragraph is split out before math conversion.
                chunks.append(r"\intertext{" + value + "}")
            elif name in self.macros:
                macro = self.macros[name]
                if parents.count(name) > 8:
                    raise ValueError(f"Recursive math macro {name}")
                values, cursor = self.read(text, cursor, macro.spec)
                body = self.select(macro.body, values)
                if any(int(m[1]) > len(values) for m in PLACEHOLDER.finditer(body)):
                    chunks.append(text[match.start():cursor])
                    continue
                replacement = PLACEHOLDER.sub(lambda m: str(values[int(m[1]) - 1] or ""), body)
                if name in ("ensuremath", "textarabic", "textenglish", "pnbLatin"):
                    chunks.append(self.expand(replacement, parents))
                else:
                    chunks.append(self.expand(replacement, (*parents, name)))
                if replacement and re.search(r"\\[A-Za-z@]+$", replacement):
                    chunks.append(" ")
                self.counts[name] += 1
            else:
                chunks.append(match[0])
        chunks.append(self.formula_letters(text[cursor:]))
        return "".join(chunks)

    @staticmethod
    def formula_letters(text):
        return re.sub(r"!([A-Z])", lambda m: "\\" + GREEK[m[1]] + " " if m[1] in GREEK else m[1], text)

    def expand_math_text(self, part, parents):
        result, cursor = [], 0
        for match in re.finditer(r"\\(?:Taut|PL)(?![A-Za-z@])", part):
            if plain := part[cursor:match.start()]:
                result.append(r"\text{" + plain + "}")
            result.append(self.expand(match[0], parents))
            cursor = match.end()
        if plain := part[cursor:]:
            result.append(r"\text{" + plain + "}")
        return "".join(result)


def manual_tag_inlines(tag, expander):
    tagged = []
    if "$" in tag:
        tagged.append({"t": "Str", "c": "("})
        for i, part in enumerate(re.split(r"(?<!\\)\$", tag)):
            if not part:
                continue
            tagged.append({"t": "Math", "c": [{"t": "InlineMath"}, expander.expand(part)]}
                          if i % 2 else {"t": "Str", "c": part})
        tagged.append({"t": "Str", "c": ")"})
    else:
        tagged.append({"t": "Math", "c": [{"t": "InlineMath"}, expander.expand("(" + tag + ")")]})
    return tagged


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    root = parser.parse_args().directory
    config = (root / "upstream/open-logic-config.sty").read_text("utf8")
    expander = Expander(parse_macros(config))
    source = json.loads((root / "pandoc-proof-projection.json").read_bytes())
    failures, formulas, residual = [], Counter(), Counter()
    linked_formulas = tagged_formulas = 0

    def visit(value):
        nonlocal linked_formulas, tagged_formulas
        if isinstance(value, dict):
            if value.get("t") == "Math":
                kind, original = value["c"]
                formulas[kind["t"]] += 1
                try:
                    clean, references, tags = remove_math_links_and_tags(original)
                    expanded = expander.expand(clean).replace(r"\lnotY", r"\lnot Y")
                    expanded = re.sub(r"(\\begin\{cases\}[\s\S]*?\\end\{cases\})",
                        lambda m: re.sub(r"(?<!\\)\$([0-9]+)\$", r"\1", m[0]), expanded)
                except (ValueError, IndexError) as exc:
                    failures.append({"source": original, "error": str(exc)})
                    return
                value["c"][1] = expanded
                if references or tags:
                    linked_formulas += bool(references)
                    tagged_formulas += bool(tags)
                    annotation = []
                    for target, label in references:
                        if annotation:
                            annotation.append({"t": "Space"})
                        annotation.append({"t": "Link", "c": [["", [], []],
                            [{"t": "Str", "c": label}], ["#" + target, ""]]})
                    for tag in tags:
                        if annotation:
                            annotation.append({"t": "Space"})
                        annotation.extend(manual_tag_inlines(tag, expander))
                    attr = ["", ["annotated-equation"], []]
                    math = {"t": "Math", "c": value["c"]}
                    notes = {"t": "Span", "c": [["", ["equation-notes"], []], annotation]}
                    value.clear()
                    value.update(t="Span", c=[attr, [math, notes]])
                residual.update(m[1] for m in CONTROL.finditer(expanded) if m[1] in expander.macros)
            else:
                for child in value.values():
                    visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(source["blocks"])
    output = json.dumps(source, ensure_ascii=False, separators=(",", ":")).encode()
    (root / "pandoc-expanded-math.json").write_bytes(output)
    receipt = {
        "sha256": sha256(output).hexdigest(), "formulas": formulas,
        "linked_formulas": linked_formulas, "tagged_formulas": tagged_formulas,
        "declarations_loaded": len(expander.macros), "expanded_calls": expander.counts,
        "remaining_expandable_names": residual, "failures": failures,
    }
    (root / "WEB-MATH-EXPANSION.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(f"{sum(formulas.values())} formulas, {sum(expander.counts.values())} expanded calls, {len(failures)} failed expansions")


if __name__ == "__main__":
    main()
