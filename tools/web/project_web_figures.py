"""Extract the original TikZ diagrams as separate numbered rendering inputs."""

import argparse
from hashlib import sha256
from pathlib import Path
import json
import re

from project_web_structure import optional
from project_web_tags import argument


FIGURES = re.compile(
    r"(?m)^% (?P<close>/)?(?P<unit>OLP-\d{4})(?: [^\n]+)?$"
    r"|(?P<comment>(?<!\\)%[^\n]*)"
    r"|(?P<tikz>\\begin\{tikzpicture\}[\s\S]*?\\end\{tikzpicture\})"
    r"|(?P<asset>\\olasset)(?![A-Za-z@])"
)
MATH_DISPLAY = re.compile(r"(?<!\\)\\\[(?P<body>[\s\S]*?)(?<!\\)\\\]")
FIGURE_ONLY = re.compile(r"(?:\s|&|\\hypertarget\{diagram-\d+\}\{\})*")


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("directory", type=Path)
    root = cli.parse_args().directory
    source = (root / "web-display-projection.tex").read_text("utf8")
    units, rows, chunks, figures = [], [], [], []
    cursor = 0
    while match := FIGURES.search(source, cursor):
        chunks.append(source[cursor:match.start()])
        cursor = match.end()
        if match["unit"]:
            if match["close"]:
                if units.pop() != match["unit"]:
                    raise ValueError("Unbalanced source-unit markers")
            else:
                units.append(match["unit"])
            chunks.append(match[0])
            continue
        if match["comment"]:
            chunks.append(match[0])
            continue
        source_path = None
        width = None
        if match["asset"]:
            width, cursor = optional(source, cursor)
            source_path, cursor = argument(source, cursor)
            source_path = source_path.removeprefix(r"\olpath/")
            if not re.fullmatch(r"assets/diagrams/[a-z-]+\.tikz", source_path):
                raise ValueError(f"Unexpected source diagram path {source_path}")
            path = root / "upstream" / source_path
            raw = path.read_bytes()
            text = raw.decode("utf8")
        else:
            text = match["tikz"]
            raw = text.encode("utf8")
        identifier = f"diagram-{len(rows) + 1}"
        rows.append({"id": identifier, "source_unit": units[-1], "path": source_path,
                     "width": width, "sha256": sha256(raw).hexdigest()})
        figures.append(text)
        chunks.append(r"\hypertarget{" + identifier + "}{}")
    chunks.append(source[cursor:])
    text, isolated_lines = re.subn(
        r"\\begin\{pnbDiagramLine\}\s*(\\hypertarget\{diagram-\d+\}\{\})\s*\\end\{pnbDiagramLine\}",
        r"\n\1\n", "".join(chunks),
    )
    if isolated_lines not in (0, 3):
        raise ValueError("Expected three complete isolated ordinal diagram placements")
    text = MATH_DISPLAY.sub(
        lambda m: "\n\n" + m["body"].strip() + "\n\n"
        if ("diagram-" in m["body"] and FIGURE_ONLY.fullmatch(m["body"])) or
           re.fullmatch(r"\s*(?:\\centering\s*)?\\begin\{tabular\}[\s\S]*?\\end\{tabular\}\s*", m["body"])
        else m[0],
        text,
    )
    out = text.encode("utf8")
    (root / "web-figure-projection.tex").write_bytes(out)
    data = {"figures": len(rows), "inline_tikz": sum(not r["path"] for r in rows),
            "external_assets": sum(bool(r["path"]) for r in rows), "figures_by_order": rows,
            "projection_sha256": sha256(out).hexdigest()}
    (root / "WEB-FIGURE-PROJECTION.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf8")
    # Each diagram occupies a separate page in one guarded compiler invocation.
    # The pages are individual illustrations, with no body prose or scanned pages.
    tex = r"""\PassOptionsToPackage{bidi=default}{babel}
\documentclass[14pt,oneside,openany]{memoir}
\usepackage[paperwidth=35cm,paperheight=32cm,margin=1cm]{geometry}
\setstocksize{32cm}{35cm}
\usepackage{fontspec}
\newcommand*{\olpath}{upstream}
\input{\olpath/sty/open-logic.sty}
\babelprovide[import]{urdu}
\babelfont[urdu]{rm}[Path=fonts/,Script=Arabic]{NotoNaskhArabic-Regular.ttf}
\input{translation/pnb-morphology.sty}
\newif\ifpnbDiagramReader
\pnbDiagramReadertrue
\input{reader/cumulative-localization.tex}
\newfontfamily\pnbDiagramArabic[Path=fonts/,Script=Arabic]{NotoNaskhArabic-Regular.ttf}
\newcommand{\pnbDiagramStart}{\hbox{\beginR\pnbDiagramArabic شروع\endR}}

\pagestyle{empty}
\begin{document}
\selectlanguage{english}
\tikzset{every initial by arrow/.append style={font=\pnbDiagramArabic}}
"""
    for i, diagram in enumerate(figures):
        diagram = re.sub(r"(?<=\[)initial(?=\s*[,\]])", r"initial,initial text={\\pnbDiagramStart}", diagram)
        # TikZ coordinates are left-to-right; retain Shahmukhi direction inside its label.
        if re.search(r"[\u0600-\u06ff]", diagram):
            label = "$p$ دا اعلان"
            if diagram.count(label) != 1:
                raise ValueError(f"Unmapped Shahmukhi label in diagram {i + 1}")
            diagram = diagram.replace(label, r"{\beginR\pnbDiagramArabic " + label + r"\endR}")
        if i:
            tex += "\n\\clearpage\n"
        tex += "\n\\null\\vfill\\begin{center}\n" + diagram + "\n\\end{center}\\vfill\\null\n"
    tex += "\n\\end{document}\n"
    (root / "web-diagrams.tex").write_bytes(tex.encode("utf8"))
    print({k: v for k, v in data.items() if k != "figures_by_order"})


if __name__ == "__main__":
    main()
