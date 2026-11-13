"""Resolve Open Logic sectioning, labels, and text tokens before web conversion."""

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import json
import re

from project_web_tags import argument


STATEMENTS = {
    "thm": "قضیہ", "defn": "تعریف", "lem": "لما", "prop": "نتیجہ",
    "cor": "لازمی نتیجہ", "ex": "مثال", "prob": "مشق", "probd": "مشق",
    "probtag": "مشق", "rem": "تبصرہ", "conv": "رواج", "axiom": "مسلّمہ",
    "note": "نوٹ", "case": "صورت", "proof": "ثبوت",
}
CONTEXTUAL_ENVS = {
    "explain": "", "digress": "", "informal": "", "intro": "", "defish": "",
    "history": "تاریخی نوٹ", "reading": "ہور پڑھائی", "pedantic": "",
}
CAPTIONS = {
    "chapter": "باب", "part": "حصہ", "section": "حصہ", "subsection": "ذیلی حصہ",
    "figure": "شکل", "sidewaysfigure": "شکل", "table": "جدول", "equation": "مساوات",
}
MATH_ENVS = frozenset(("align", "equation", "multline", "gather", "alignat", "eqnarray", "flalign"))
HEADING = {"olpart": "part", "olchapter": "chapter", "olsection": "section"}
SHARED = frozenset(("prf", "seq", "ntd", "tab", "axd", "com"))
STRUCTURE = {
    *HEADING, *CAPTIONS, "subsubsection", "olfileid", "oliflabeldef", "ollabel", "label",
    "olref", "Olref", "cref", "Cref", "crefrange", "eqref", "ref", "pageref",
    "hyperref", "pnbLatin", "pnboblique", "usetoken", "printtoken", "texorpdfstring",
    "OLEndChapterHook", "OLEndPartHook", "noindent", "olphoto", "indcase",
}
LEXEME = re.compile(
    r"(?m)^% (?P<close>/)?(?P<unit>OLP-\d{4})(?: [^\n]+)?$"
    r"|(?P<comment>(?<!\\)%[^\n]*)"
    r"|\\begin\{(?P<protected>verbatim\*?|tikzpicture)\}"
    r"|(?P<math>\\\[(?P<display_body>[\s\S]*?)\\\]"
    r"|(?<!\\)\$\$(?P<double_body>[\s\S]*?)(?<!\\)\$\$)"
    r"|(?P<token>!!(?P<form>\^?a?)\{(?P<key>[^{}\n]+)\}(?P<plural>s)?)"
    r"|\\(?P<boundary>begin|end)\{(?P<env>[A-Za-z*]+)\}"
    r"|\\(?P<cmd>" + "|".join(sorted(STRUCTURE, key=lambda v: (-len(v), v))) + r")(?![A-Za-z@])"
    r"|\\(?P<skip>[A-Za-z@]+|[^A-Za-z@])"
)
SET_TOKEN = re.compile(r"\\settexttoken(?=\s*\{)")
NEXT_ARGUMENT = re.compile(r"(?:\s|%[^\n]*(?:\n|$))*")


def optional(text, cursor):
    offset = NEXT_ARGUMENT.match(text, cursor).end()
    if text[offset:offset + 1] != "[":
        return None, cursor
    depth = 0
    for m in re.finditer(r"\\[A-Za-z@]+|\\.|[%{}\[\]]", text[offset + 1:]):
        symbol = m[0]
        if symbol == "{":
            depth += 1
        elif symbol == "}":
            depth -= 1
        elif symbol == "]" and depth == 0:
            stop = offset + 1 + m.start()
            return text[offset + 1:stop], stop + 1
    raise ValueError("Unclosed optional argument")


def localized_tokens(styles):
    values = {}
    for text in styles:
        for m in SET_TOKEN.finditer(text):
            key, cursor = argument(text, m.end())
            singular, cursor = argument(text, cursor)
            plural, cursor = argument(text, cursor)
            capital, cursor = optional(text, cursor)
            capital_plural, cursor = optional(text, cursor)
            values[key] = (singular, plural, capital or singular, capital_plural or plural)
    return values


@dataclass(frozen=True)
class Anchor:
    label: str
    target: str
    kind: str
    number: str
    unit: str

    @property
    def description(self):
        return " ".join(x for x in (CAPTIONS.get(self.kind) or STATEMENTS.get(self.kind), self.number) if x)


class Structure:
    def __init__(self, tokens, known=None):
        self.tokens = tokens
        self.known = known
        self.labels = {}
        self.duplicates = defaultdict(list)
        self.unresolved = defaultdict(Counter)
        self.counts = Counter()
        self.references = Counter()
        self.units = []
        self.envs = []
        self.file_id = ("udf",) * 3
        self.current = None
        self.part = self.chapter = self.section = self.subsection = 0
        self.chapter_counts = Counter()
        self.heading_anchors = set()
        self.oblique = False
        self.equation_anchors = None

    @property
    def unit(self):
        return self.units[-1][0] if self.units else ""

    def record_label(self, label, kind, number):
        if not re.fullmatch(r"[-\w:./=+]+", label):
            raise ValueError(f"{self.unit}: malformed label {label!r}")
        existing = self.labels.get(label)
        suffix = f"-{len(self.duplicates[label]) + 2}" if existing else ""
        target = label.replace("=", "-equals-").replace("+", "-plus-").replace("/", "-slash-") + suffix
        node = Anchor(label, target, kind, number, self.unit)
        if existing:
            self.duplicates[label].append(node)
        else:
            self.labels[label] = node
        return node

    def destination(self, key):
        catalog = self.known if self.known is not None else self.labels
        found = catalog.get(key)
        if not found:
            prefix, separator, rest = key.partition(":")
            if prefix == "pl" and rest.split(":", 1)[0] in SHARED:
                found = catalog.get("fol" + separator + rest)
        return found

    def link(self, key, name=None, kind="cref"):
        self.references[key] += 1
        dest = self.destination(key)
        if dest:
            if name is None:
                name = dest.number if kind in ("ref", "eqref") else dest.description
            name = name or "حوالہ"
            if kind == "eqref":
                name = "(" + name + ")"
            return rf"\hyperlink{{{dest.target}}}{{{name}}}"
        self.unresolved[key][self.unit] += 1
        return rf"\pnbunresolved{{{key}}}{{{name or 'حوالہ'}}}"

    def relative_label(self, items, name):
        base = self.file_id[:3 - len(items)] + tuple(items)
        return ":".join((*base, name))

    def count_heading(self, kind, starred):
        if starred:
            return ""
        if kind == "part":
            self.part += 1
            return str(self.part)
        if kind == "chapter":
            self.chapter += 1
            self.section = self.subsection = 0
            self.chapter_counts.clear()
            return str(self.chapter)
        if kind == "section":
            self.section += 1
            self.subsection = 0
            return f"{self.chapter}.{self.section}"
        if kind == "subsection":
            self.subsection += 1
            return f"{self.chapter}.{self.section}.{self.subsection}"
        return ""

    def count_statement(self, kind):
        if kind in ("proof", "axiom"):
            return ""
        if kind in ("ex", "thm", "defn", "lem", "prop", "cor"):
            counter = "thm"
        elif kind in ("prob", "probd", "probtag"):
            counter = "prob"
        elif kind in ("figure", "sidewaysfigure"):
            counter = "figure"
        else:
            counter = kind
        self.chapter_counts[counter] += 1
        return f"{self.chapter}.{self.chapter_counts[counter]}"

    def render_token(self, key, form, plural):
        self.counts["text_tokens"] += 1
        if self.oblique and key == "element" and plural:
            return "عنصراں"
        return self.tokens[key][2 * ("^" in form) + bool(plural)]

    def visit(self, text):
        result = []
        cursor = 0
        while m := LEXEME.search(text, cursor):
            result.append(text[cursor:m.start()])
            cursor = m.end()
            if m["unit"]:
                if m["close"]:
                    unit, self.file_id, self.current = self.units.pop()
                    if unit != m["unit"]:
                        raise ValueError(f"Unbalanced unit markers {unit}, {m['unit']}")
                else:
                    self.units.append((m["unit"], self.file_id, self.current))
                result.append(m[0])
            elif m["protected"]:
                end = rf"\end{{{m['protected']}}}"
                cursor = text.index(end, cursor) + len(end)
                result.append(text[m.start():cursor])
            elif m["math"]:
                opening, closing, body = (
                    (r"\[", r"\]", m["display_body"]) if m["display_body"] is not None
                    else ("$$", "$$", m["double_body"])
                )
                result.append(self.math_block(opening, closing, body))
            elif m["comment"] or m["skip"]:
                result.append(m[0])
            elif m["token"]:
                result.append(self.render_token(m["key"], m["form"], m["plural"]))
            elif m["boundary"]:
                env = m["env"]
                if m["boundary"] == "begin" and env.rstrip("*") in MATH_ENVS:
                    end = rf"\end{{{env}}}"
                    stop = text.index(end, cursor)
                    result.append(self.math_block(m[0], end, text[cursor:stop], env))
                    cursor = stop + len(end)
                else:
                    converted, cursor = self.environment(text, cursor, m["boundary"], env)
                    result.append(converted)
            elif m["cmd"]:
                converted, cursor = self.command(text, cursor, m["cmd"])
                result.append(converted)
        result.append(text[cursor:])
        return "".join(result)

    def math_block(self, opening, closing, source, env=""):
        previous = self.current
        self.current = ("equation", "")
        self.equation_anchors = []
        rendered = self.visit(source)
        anchors = self.equation_anchors
        self.equation_anchors = None
        self.current = previous
        self.counts["math_anchors"] += len(anchors)
        targets = "".join(rf"\hypertarget{{{node.target}}}{{}}" for node in anchors)
        return targets + opening + rendered + closing

    def environment(self, text, cursor, boundary, env):
        if env not in STATEMENTS and env not in CONTEXTUAL_ENVS and env not in CAPTIONS:
            return rf"\{boundary}{{{env}}}", cursor
        if boundary == "end":
            previous, kind, actual = self.envs.pop()
            if kind != env:
                raise ValueError(f"{self.unit}: expected environment end {kind}, found {env}")
            self.current = previous
            return f"\n\\end{{{actual}}}", cursor
        self.counts[f"env:{env}"] += 1
        previous = self.current
        if env in CAPTIONS:
            self.current = (env, self.count_statement(env) if env != "equation*" else "")
            self.envs.append((previous, env, env))
            return rf"\begin{{{env}}}", cursor
        if env in STATEMENTS:
            if env == "probtag":
                _, cursor = argument(text, cursor)
            title, cursor = optional(text, cursor)
            number = self.count_statement(env)
            self.current = (env, number)
            title = self.visit(title) if title else ""
            heading = " ".join(s for s in (STATEMENTS[env], number, title) if s)
        else:
            heading = CONTEXTUAL_ENVS[env]
        self.envs.append((previous, env, "quote"))
        markup = r"\textbf{" + heading + "}\n\n" if heading else ""
        return "\n\\begin{quote}\n" + markup, cursor

    def command(self, text, cursor, cmd):
        if cmd in ("OLEndChapterHook", "OLEndPartHook", "noindent"):
            return "", cursor
        if cmd == "indcase":
            starred = text[cursor:cursor + 1] == "*"
            if starred:
                cursor += 1
            exercise = text[cursor:cursor + 1] == "!"
            if exercise:
                cursor += 1
            form, cursor = argument(text, cursor)
            compound, cursor = argument(text, cursor)
            explanation, cursor = argument(text, cursor)
            if exercise:
                explanation = "مشق۔"
            else:
                replacement = {"indfrm": form, "indfrmp": form, "indcomplex": compound}
                explanation = re.sub(
                    r"\\(indfrm|indfrmp|indcomplex)(?![A-Za-z@])", lambda m: "{" + replacement[m[1]] + "}", explanation,
                )
            self.counts["indcase"] += 1
            prefix = "$" + form + "$ جوہری اے۔ " if starred else "$" + form + r" \ident " + compound + "$۔ "
            return prefix + self.visit(explanation), cursor
        if cmd in HEADING or cmd in ("part", "chapter", "section", "subsection", "subsubsection"):
            return self.heading(text, cursor, cmd)
        if cmd in ("olfileid", "oliflabeldef"):
            if cmd == "olfileid":
                _, cursor = optional(text, cursor)
                a, cursor = argument(text, cursor)
                b, cursor = argument(text, cursor)
                c, cursor = argument(text, cursor)
                self.file_id = a, b, c
                return "", cursor
            key, cursor = argument(text, cursor)
            yes, cursor = argument(text, cursor)
            no, cursor = argument(text, cursor)
            return self.visit(yes if self.destination(key) else no), cursor
        if cmd in ("label", "ollabel"):
            value, cursor = argument(text, cursor)
            kind, number = self.current or ("", "")
            key = self.relative_label((), value) if cmd == "ollabel" else value
            anchor = self.record_label(key, kind, number)
            if self.equation_anchors is not None:
                self.equation_anchors.append(anchor)
                return "", cursor
            return rf"\hypertarget{{{anchor.target}}}{{}}", cursor
        if cmd in ("olref", "Olref"):
            fields = []
            for _ in range(3):
                field, cursor = optional(text, cursor)
                if field is None:
                    break
                fields.append(field)
            value, cursor = argument(text, cursor)
            return self.link(self.relative_label(fields, value)), cursor
        if cmd in ("cref", "Cref", "crefrange", "eqref", "ref", "pageref", "hyperref"):
            if cmd == "hyperref":
                key, cursor = optional(text, cursor)
                name, cursor = argument(text, cursor)
                return self.link(key, self.visit(name)), cursor
            value, cursor = argument(text, cursor)
            keys = value.split(",")
            if cmd == "crefrange":
                endpoint, cursor = argument(text, cursor)
                keys.append(endpoint)
            separator = " توں " if cmd == "crefrange" else "، "
            return separator.join(self.link(k.strip(), kind=cmd) for k in keys), cursor
        if cmd in ("usetoken", "printtoken"):
            switch, cursor = argument(text, cursor)
            key, cursor = argument(text, cursor)
            return self.render_token(key, "^" if switch.isupper() else "", switch.lower() == "p"), cursor
        if cmd in ("pnbLatin", "pnboblique", "texorpdfstring", "olphoto"):
            if cmd == "olphoto":
                _, cursor = optional(text, cursor)
                photo, cursor = argument(text, cursor)
                title, cursor = argument(text, cursor)
                self.counts[f"unavailable_photo:{photo}"] += 1
                return "", cursor
            value, cursor = argument(text, cursor)
            if cmd == "texorpdfstring":
                _, cursor = argument(text, cursor)
                return self.visit(value), cursor
            if cmd == "pnbLatin":
                return r"\foreignlanguage{english}{" + value + "}", cursor
            old = self.oblique
            self.oblique = True
            localized = self.visit(value)
            self.oblique = old
            return localized, cursor
        return "\\" + cmd, cursor

    def heading(self, text, cursor, cmd):
        starred = text[cursor:cursor + 1] == "*"
        if starred:
            cursor += 1
        _, cursor = optional(text, cursor)
        kind = HEADING.get(cmd, cmd)
        number = self.count_heading(kind, starred)
        self.current = (kind, number)
        self.counts[f"heading:{kind}"] += 1
        key = None
        if cmd == "olpart":
            part, cursor = argument(text, cursor)
            key = f"{part}:::part"
        elif cmd == "olchapter":
            part, cursor = argument(text, cursor)
            chapter, cursor = argument(text, cursor)
            key = f"{part}:{chapter}::chap"
        elif cmd == "olsection":
            key = self.relative_label((), "sec")
        title, cursor = argument(text, cursor)
        suffix = ""
        if key:
            anchor = self.record_label(key, kind, number)
            suffix = rf"\label{{{anchor.target}}}"
            self.heading_anchors.add(anchor.target)
        return "\\" + kind + ("*" if starred else "") + "{" + self.visit(title) + "}" + suffix, cursor


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    root = parser.parse_args().directory
    projected = (root / "web-tag-projection.tex").read_text("utf8")
    tokens = localized_tokens(
        (root / path).read_text("utf8") for path in (
            "translation/pnb-morphology.sty", "reader/cumulative-localization.tex"
        )
    )
    discovery = Structure(tokens)
    discovery.visit(projected)
    build = Structure(tokens, discovery.labels)
    result = build.visit(projected).encode("utf8")
    if build.units or build.envs:
        raise ValueError("Unclosed reader structure")
    if build.labels != discovery.labels:
        raise ValueError("The reference conditionals changed the target catalog")
    (root / "web-structure-projection.tex").write_bytes(result)
    data = {
        "sha256": sha256(result).hexdigest(),
        "bytes": len(result),
        "counts": dict(build.counts),
        "labels": len(build.labels),
        "heading_anchors": len(build.heading_anchors),
        "reference_occurrences": sum(build.references.values()),
        "unresolved": build.unresolved,
        "duplicates": {k: [vars(build.labels[k]), *(vars(a) for a in v)] for k, v in build.duplicates.items() if v},
        "catalog": {k: vars(v) for k, v in build.labels.items()},
    }
    (root / "WEB-STRUCTURE-PROJECTION.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    print({k: v for k, v in data.items() if k not in ("catalog", "unresolved", "duplicates", "counts")})
    print(f"{len(data['unresolved'])} unresolved target keys and {len(data['duplicates'])} duplicate target keys")


if __name__ == "__main__":
    main()
