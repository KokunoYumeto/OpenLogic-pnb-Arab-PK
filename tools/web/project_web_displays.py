"""Keep text and links in AMS intertext paragraphs outside MathML."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re

from project_web_tags import argument


ENV = re.compile(r"\\begin\{(?P<name>align\*?|alignat\*?|gather\*?|multline\*?)\}"
                 r"(?P<body>[\s\S]*?)\\end\{(?P=name)\}")
INTERTEXT = re.compile(r"(?<!\\)\\(?:shortintertext|intertext)\s*(?=\{)")
ROW_END = re.compile(r"(?<!\\)\\\\(?:\s*\[[^\]]+\])?\s*$")
TIKZ = re.compile(r"\\begin\{tikzpicture\}[\s\S]*?\\end\{tikzpicture\}")


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("directory", type=Path)
    root = cli.parse_args().directory
    original = (root / "web-tableau-projection.tex").read_text("utf8")
    counts = Counter()

    def one(m):
        body = m["body"]
        if not INTERTEXT.search(body):
            return m[0]
        name = m["name"]
        counts["environments"] += 1
        cursor = 0
        blocks = []

        def display(content):
            content = ROW_END.sub("", content.strip())
            if not content:
                return ""
            if TIKZ.search(content):
                # A standalone diagram in a math alignment still uses a figure slot.
                only_tikz = TIKZ.sub("", content).strip("& \n\t")
                if not only_tikz:
                    counts["diagram_only_blocks"] += 1
                    return "\n\n" + content.lstrip("& \n\t") + "\n\n"
            counts["math_blocks"] += 1
            return "\n\n\\begin{" + name + "}\n" + content + "\n\\end{" + name + "}\n\n"

        while inter := INTERTEXT.search(body, cursor):
            blocks.append(display(body[cursor:inter.start()]))
            paragraph, cursor = argument(body, inter.end())
            blocks.extend(("\n\n", paragraph, "\n\n"))
            counts["prose_paragraphs"] += 1
            counts["retained_inline_links"] += paragraph.count(r"\hyperlink{")
        blocks.append(display(body[cursor:]))
        return "".join(blocks)

    result = ENV.sub(one, original).encode()
    (root / "web-display-projection.tex").write_bytes(result)
    data = {"counts": counts, "sha256": sha256(result).hexdigest()}
    (root / "WEB-DISPLAY-PROJECTION.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf8")
    print(data)


if __name__ == "__main__":
    main()
