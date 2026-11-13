"""Convert bussproofs trees to nested, reflowable HTML proof structures."""

import argparse
from collections import Counter
from dataclasses import dataclass, field
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re

from project_web_tags import argument


PROOF_ENV = re.compile(r"\\begin\{prooftree\}([\s\S]*?)\\end\{prooftree\}")
DISPLAY = re.compile(r"(?<!\\)\\\[(?P<square>[\s\S]*?)(?<!\\)\\\]|"
                     r"\\begin\{(?P<env>align\*?|gather\*?|equation\*?|multline\*?)\}"
                     r"(?P<body>[\s\S]*?)\\end\{(?P=env)\}")
TREE_START = re.compile(r"\\(?:AxiomC?|(?:Left|Right)Label)(?![A-Za-z])")
DELIMITED = re.compile(r"\s*\$((?:\\.|[^$])*)\$", re.S)
COMMAND = re.compile(r"\\([A-Za-z@]+|\\)")
ARRAY = re.compile(r"\\def\\arraystretch\{[^{}]+\}\\begin\{array\}\{[^{}]+\}([\s\S]*?)\\end\{array\}")
TABLE = re.compile(r"\\begin\{(?P<env>tabular\*?|longtable)\}(?P<body>[\s\S]*?)\\end\{(?P=env)\}")
TABLE_BOUNDARY = re.compile(r"\\(?P<side>begin|end)\{(?P<env>tabular\*?|longtable)\}")
ALIGNMENT_CELL = re.compile(r"(?:^|\n)\s*(?=\\(?:bottomAlignProof|centerAlignProof|AxiomC?|LeftLabel|RightLabel|shortDeduce|noLine)\b)")
STANDALONE = re.compile(r"\\(?:bottomAlignProof|centerAlignProof|AxiomC?|LeftLabel|RightLabel)(?![A-Za-z@])")
DISPLAY_END = re.compile(r"\\DisplayProof(?![A-Za-z@])")
NODE = re.compile(r"(Axiom|Deduce|UnaryInf|BinaryInf|TrinaryInf|QuaternaryInf|QuinaryInf)(C?)")
ARITY = {"Axiom": 0, "Deduce": 1, "UnaryInf": 1, "BinaryInf": 2,
         "TrinaryInf": 3, "QuaternaryInf": 4, "QuinaryInf": 5}
LAYOUT = {"bottomAlignProof", "centerAlignProof", "quad", "qquad", "hfill", "small", "footnotesize"}
LAYOUT_ARG = {"insertBetweenHyps", "hspace", "kernUpper", "kernLower"}
LINES = {"noLine": "none", "singleLine": "single", "doubleLine": "double",
         "dashedLine": "dashed", "solidLine": "single", "straightDeduce": "dotted",
         "shortDeduce": "dotted", "branchDeduce": "branched", "ddotsDeduce": "diagonal-down",
         "dotsdDeduce": "diagonal-up"}
LABELS = {"RightLabel": "right", "LeftLabel": "left",
          "LeftSubproofLabel": "subproof-left", "RightSubproofLabel": "subproof-right",
          "LeftLineLabel": "line-left", "RightLineLabel": "line-right"}
GAP = re.compile(r"(?:\s|%[^\n]*(?:\n|$))*")
DIMENSION = re.compile(r"\s*-?\d+(?:\.\d+)?\s*(?:em|ex|pt|mm|cm)")


@dataclass
class Step:
    conclusion: str
    premises: list = field(default_factory=list)
    style: str = "single"
    labels: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Prose:
    text: str
    is_math: bool = False


def command_at(text, cursor):
    m = COMMAND.match(text, cursor)
    if m is None:
        raise ValueError(f"expected proof command near {text[cursor:cursor+90]!r}")
    return m[1], m.end()


def parse_tree(text):
    output, stack = [], []
    line, deduce, labels = "single", "dotted", {}
    cursor = 0
    while cursor < len(text):
        cursor = GAP.match(text, cursor).end()
        if cursor == len(text):
            break
        cmd, cursor = command_at(text, cursor)
        matched = NODE.fullmatch(cmd)
        if matched:
            command, c_argument = matched.groups()
            if c_argument:
                formula, cursor = argument(text, cursor)
            else:
                m = DELIMITED.match(text, cursor)
                if m is None:
                    raise ValueError(f"{cmd}: missing dollar-delimited proof formula")
                formula, cursor = "$" + m[1] + "$", m.end()
            arity = ARITY[command]
            if len(stack) < arity:
                raise ValueError(f"{cmd}: {arity} premises needed, found {len(stack)}")
            children = []
            if arity:
                children = stack[-arity:]
                del stack[-arity:]
            step = Step(formula.strip(), children, deduce if command == "Deduce" else line, labels)
            stack.append(step)
            line, deduce, labels = "single", "dotted", {}
        elif cmd == "DisplayProof":
            if len(stack) != 1:
                raise ValueError(f"DisplayProof: expected one root, found {len(stack)}")
            output.append(stack.pop())
        elif cmd in LINES:
            if cmd.endswith("Deduce"):
                deduce = LINES[cmd]
            else:
                line = LINES[cmd]
        elif cmd in LABELS:
            value, cursor = argument(text, cursor)
            side = LABELS[cmd]
            if "Subproof" in cmd:
                stack[-1].labels[side] = value
            else:
                labels[side] = value
        elif cmd == "DischargeRule":
            labels["right"], cursor = argument(text, cursor)
            index, cursor = argument(text, cursor)
            labels["left"] = "$" + index + "$"
        elif cmd in LAYOUT_ARG:
            _, cursor = argument(text, cursor)
        elif cmd == "hskip":
            value = DIMENSION.match(text, cursor)
            if value is None:
                raise ValueError("Unexpected hskip dimension")
            cursor = value.end()
        elif cmd == "text":
            value, cursor = argument(text, cursor)
            output.append(Prose(value))
        elif cmd in ("redone", "longrightarrow"):
            output.append(Prose("\\" + cmd, is_math=True))
        elif cmd == "\\":
            row_space = re.match(r"\s*\[[-0-9.]+\s*(?:em|ex|pt|mm|cm)\]", text[cursor:])
            if row_space:
                cursor += row_space.end()
        elif cmd not in LAYOUT:
            raise ValueError(f"unsupported proof command {cmd}")
    if len(stack) > 1 or labels:
        raise ValueError(f"unattached premises or labels: {len(stack)} {tuple(labels)}")
    if stack:
        output.append(stack.pop())
    if not any(isinstance(item, Step) for item in output):
        raise ValueError("empty proof tree")
    return output


def html_fragment(roots, identifier):
    def span(kind, value):
        return f'<span class="proof-{kind}" data-tex="{escape(value, quote=True)}"></span>'

    def render(node):
        if isinstance(node, Prose):
            if node.is_math:
                return span("relation", node.text)
            return f'<span class="proof-relation" lang="pnb-Arab-PK" dir="rtl">{escape(node.text)}</span>'
        items = []
        if node.premises:
            children = "".join(render(premise) for premise in node.premises)
            items.append(f'<span class="proof-premises">{children}</span>')
        items.append('<span class="proof-inference">')
        items.extend(span(k, v) for k, v in node.labels.items())
        items.append(span("conclusion", node.conclusion))
        items.append("</span>")
        return f'<span class="proof-step proof-line-{node.style}">' + "".join(items) + "</span>"

    return f'<div id="{identifier}" class="proof-trees" dir="ltr">' + "".join(map(render, roots)) + "</div>"


def split_array(text):
    rows = [[]]
    start = depth = 0
    environments = []
    for m in re.finditer(r"(?<!\\)%[^\n]*|\\(?:begin|end)\{(?:tabular\*?|longtable|array|aligned|matrix)\}|"
                         r"\\\\(?:\[[^\]]*\])?|\\[A-Za-z@]+|\\.|[{}&]", text):
        token = m[0]
        if token.startswith(r"\begin{"):
            environments.append(token[7:-1])
            continue
        if token.startswith(r"\end{"):
            if not environments or environments.pop() != token[5:-1]:
                raise ValueError("Unbalanced nested proof array")
            continue
        if token == "{":
            depth += 1
        elif token == "}":
            depth -= 1
        elif depth == 0 and not environments and (token == "&" or token.startswith(r"\\")):
            rows[-1].append(text[start:m.start()])
            if token != "&":
                rows.append([])
            start = m.end()
    if depth or environments:
        raise ValueError("Unbalanced proof array cell")
    if text[start:].strip() or rows[-1]:
        rows[-1].append(text[start:])
    return [row for row in rows if row]


def regularize_tables(text):
    """Remove TeX spacing-only syntax while retaining tables and spans."""
    def simplify_columns(columns):
        value = columns
        while m := re.search(r"@\s*\{", value):
            _, stop = argument(value, m.end() - 1)
            value = value[:m.start()] + value[stop:]
        return value

    def transform(m):
        name = m[1]
        offset = GAP.match(text, m.end()).end()
        if text[offset:offset + 1] == "[":
            offset = text.index("]", offset + 1) + 1
        columns, stop = argument(text, offset)
        return rf"\begin{{{name}}}{{{simplify_columns(columns)}}}", stop

    output = []
    cursor = 0
    start = re.compile(r"\\begin\{(tabular|longtable)\}")
    while m := start.search(text, cursor):
        output.append(text[cursor:m.start()])
        replacement, cursor = transform(m)
        output.append(replacement)
    output.append(text[cursor:])
    text = "".join(output)

    def multicolumn(m):
        return m[1] + "{" + simplify_columns(m[2]) + "}"

    return re.sub(r"(\\multicolumn\{\d+\})\{((?:[^{}]|@\{[^{}]*\})+)\}", multicolumn, text)


def table_blocks(text):
    stack = []
    for m in TABLE_BOUNDARY.finditer(text):
        if re.search(r"(?<!\\)%", text[text.rfind("\n", 0, m.start()) + 1:m.start()]):
            continue
        if m["side"] == "begin":
            stack.append(m)
        else:
            opening = stack.pop()
            if opening["env"] != m["env"]:
                raise ValueError("Inconsistent table nesting")
            if not stack:
                yield opening, m
    if stack:
        raise ValueError("Unclosed TeX table")


def project_nested_proof_tables(text, root):
    """Keep complex table cells addressable when Pandoc cannot parse their nesting."""
    result, offset, all_tables = [], 0, {}

    def build_table(body, kind):
        start = GAP.match(body).end()
        _, stop = argument(body, start)
        rows = split_array(body[stop:])
        converted = []
        for row in rows:
            cells = []
            for cell in row:
                cell = re.sub(r"(?m)(?<!\\)%[^\n]*|\\(?:hline|centering)\b", "", cell).strip()
                attrs = {}
                if multi := re.match(r"\\multicolumn\b", cell):
                    attrs["colspan"], cursor = argument(cell, multi.end())
                    _, cursor = argument(cell, cursor)
                    cell, end = argument(cell, cursor)
                components, last = [], 0
                for b, e in table_blocks(cell):
                    if plain := cell[last:b.start()].strip():
                        components.append({"tex": plain})
                    components.append({"table": build_table(cell[b.end():e.start()], b["env"])})
                    last = e.end()
                if plain := cell[last:].strip():
                    components.append({"tex": plain})
                cells.append({"attributes": attrs, "content": components})
            converted.append(cells)
        return {"environment": kind, "rows": converted}

    for start, stop in table_blocks(text):
        source = text[start.end():stop.start()]
        if "proof-tree-" not in source or r"\begin{tabular" not in source:
            continue
        tree = build_table(source, start["env"])
        identifier = f"nested-proof-table-{len(all_tables) + 1}"
        all_tables[identifier] = tree
        result.append(text[offset:start.start()])
        result.append(rf"\hypertarget{{{identifier}}}{{}}")
        offset = stop.end()
    result.append(text[offset:])
    (root / "WEB-NESTED-PROOF-TABLES.json").write_text(
        json.dumps(all_tables, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    return "".join(result)


def proof_in_cell(cell):
    """Keep the cell and replace only its proof commands."""
    multi = re.match(r"\s*\\multicolumn\b", cell)
    if multi:
        _, cursor = argument(cell, multi.end())
        _, cursor = argument(cell, cursor)
        content, end = argument(cell, cursor)
        m = GAP.match(cell, cursor)
        nested = proof_in_cell(content)
        if nested:
            left, proof, right, roots = nested
            return cell[:m.end() + 1] + left, proof, right + cell[end - 1:], roots
    m = ALIGNMENT_CELL.search(cell)
    if not m or not TREE_START.search(cell[m.end():]):
        return None
    prefix = cell[:m.end()]
    candidate = cell[m.end():].rstrip()
    for end in sorted({len(candidate), *(m.end() for m in re.finditer(r"\\DisplayProof\b", candidate))}, reverse=True):
        try:
            roots = parse_tree(candidate[:end])
        except (ValueError, IndexError):
            continue
        suffix = candidate[end:]
        if TREE_START.search(suffix):
            continue
        return prefix, candidate[:end], suffix, roots
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    root = parser.parse_args().directory
    src = root / "web-structure-projection.tex"
    markup, records, failures = {}, [], []

    def replace(m, content, kind, tentative=False, ready=None):
        identifier = f"proof-tree-{len(records) + len(failures) + 1}"
        try:
            array = ARRAY.fullmatch(content.strip())
            cells = None
            if ready is not None:
                roots = ready
            elif array:
                cells = []
                for row in split_array(array[1]):
                    converted = []
                    for cell in row:
                        cell = re.sub(r"(?m)(?<!\\)%[^\n]*|\\hline\b", "", cell).strip()
                        converted.append(parse_tree(cell) if TREE_START.search(cell) else [Prose(cell, is_math=True)])
                    cells.append(converted)
                roots = [item for row in cells for cell in row for item in cell]
            else:
                # Top-level alignment marks position adjacent proofs but carry no formula content.
                if kind.startswith("align"):
                    content = re.sub(r"(?m)^[ \t]*&[ \t]*", "", content)
                if kind.startswith("multline"):
                    shove = re.compile(r"\\shove(?:left|right)(?=\s*\{)")
                    while m_shove := shove.search(content):
                        argument_body, stop = argument(content, m_shove.end())
                        content = content[:m_shove.start()] + argument_body + content[stop:]
                roots = parse_tree(content)
        except (ValueError, IndexError) as exc:
            if tentative:
                deferred.append({"line": text.count("\n", 0, m.start()) + 1,
                                 "container": kind, "failure": str(exc)})
                return m[0]
            failures.append({"id": identifier, "line": text.count("\n", 0, m.start()) + 1, "failure": str(exc)})
            return m[0]
        if cells:
            rows = []
            for i, row in enumerate(cells):
                rows.append("<tr>" + "".join(
                    "<td>" + html_fragment(cell, f"{identifier}-{i + 1}-{j + 1}") + "</td>"
                    for j, cell in enumerate(row)
                ) + "</tr>")
            markup[identifier] = (
                f'<div id="{identifier}" class="proof-array" dir="ltr"><table><tbody>'
                + "".join(rows) + "</tbody></table></div>"
            )
        else:
            markup[identifier] = html_fragment(roots, identifier)
        counts = Counter()

        def count(node):
            if isinstance(node, Prose):
                return
            counts["nodes"] += 1
            counts["leaves"] += not node.premises
            counts["labels"] += len(node.labels)
            for child in node.premises:
                count(child)

        for tree in roots:
            count(tree)
        records.append({
            "id": identifier, "line": text.count("\n", 0, m.start()) + 1,
            "trees": sum(isinstance(root, Step) for root in roots), "container": kind,
            "source_sha256": sha256(content.encode()).hexdigest(), **counts,
        })
        return "\n\\hypertarget{" + identifier + "}{}\n"

    text = src.read_text("utf8")
    deferred = []
    projected = PROOF_ENV.sub(lambda m: replace(m, m[1], "prooftree"), text)
    text = projected

    def replace_display(m):
        content = m["square"] if m["square"] is not None else m["body"]
        searchable = re.sub(r"(?m)(?<!\\)%[^\n]*", "", content)
        if not TREE_START.search(searchable):
            return m[0]
        return replace(m, content, m["env"] or "display", tentative=True)

    projected = DISPLAY.sub(replace_display, projected)
    text = projected

    def replace_table(m):
        content = m["body"]
        if not TREE_START.search(content) or r"\begin{tabular" in content:
            return m[0]
        head = GAP.match(content, 0).end()
        if content[head:head + 1] != "{":
            return m[0]
        _, column_end = argument(content, head)
        try:
            rows = split_array(content[column_end:])
        except ValueError as exc:
            deferred.append({"line": text.count("\n", 0, m.start()) + 1, "container": m["env"], "failure": str(exc)})
            return m[0]
        converted = []
        modified = False
        for row in rows:
            converted_cells = []
            for cell in row:
                parts = proof_in_cell(cell)
                if parts:
                    left, source, right, trees = parts
                    replacement = replace(m, source, "tabular-cell", ready=trees).strip()
                    cell = left + replacement + right
                    modified = True
                converted_cells.append(cell)
            converted.append(converted_cells)
        if not modified:
            return m[0]
        for i, row in enumerate(converted):
            for j, cell in enumerate(row):
                # Pandoc cannot handle @{} column overrides in \multicolumn.
                # Retain the span and text, and remove only edge-spacing directives.
                converted[i][j] = re.sub(
                    r"(\\multicolumn\{\d+\})\{((?:[^{}]|@\{\})+)\}",
                    lambda v: v[1] + "{" + v[2].replace("@{}", "") + "}", cell,
                )
        columns, _ = argument(content, head)
        columns = columns.replace("@{}", "")
        return r"\begin{" + m["env"] + "}{" + columns + "}" + "\\\\\n".join(
            "&".join(row) for row in converted
        ) + r"\end{" + m["env"] + "}"

    projected = TABLE.sub(replace_table, projected).encode("utf8")
    text = projected.decode("utf8")
    segments = []
    cursor = 0
    while m := STANDALONE.search(text, cursor):
        segments.append(text[cursor:m.start()])
        cursor = m.end()
        line = text[text.rfind("\n", 0, m.start()) + 1:m.start()]
        end = DISPLAY_END.search(text, m.end())
        if end is None or re.search(r"(?<!\\)%", line):
            segments.append(m[0])
            continue
        content = text[m.start():end.end()]
        try:
            roots = parse_tree(content)
        except (ValueError, IndexError):
            segments.append(m[0])
            continue
        segments.append(replace(m, content, "explicit-display", ready=roots).strip())
        cursor = end.end()
    segments.append(text[cursor:])
    projected = regularize_tables("".join(segments))
    projected = re.sub(r"\\(begin|end)\{sidewaysfigure\}", r"\\\1{figure}", projected)
    projected = project_nested_proof_tables(projected, root)
    projected = projected.encode("utf8")
    (root / "web-proof-projection.tex").write_bytes(projected)
    (root / "WEB-PROOF-FRAGMENTS.json").write_text(json.dumps(markup, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    result = {
        "sha256": sha256(projected).hexdigest(), "containers": len(records),
        "trees": sum(r["trees"] for r in records), "nodes": sum(r["nodes"] for r in records),
        "labels": sum(r["labels"] for r in records), "failures": failures,
        "mixed_displays_deferred": deferred, "records": records,
    }
    (root / "WEB-PROOF-PROJECTION.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print({k: v for k, v in result.items() if k != "records"})
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
