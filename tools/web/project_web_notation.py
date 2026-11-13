"""Make Open Logic's text-mode notation explicit before Pandoc conversion."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re

from expand_web_math import Expander, parse_macros, CONTROL
from project_web_tags import argument
from project_web_proofs import split_array


NOTATION = set("""Log Elim Ax RightR LeftR Intro CutCS Cut True TRule MP Undef
False FalseInt QR Nec FalseCl Dual sFmla ext LogCL LogLuk mFalse RK PL
lif land lor TMtrans Hyp Taut""".split())
PROSE = {
    "stagesord": "مرحلے ترتیب وچ نیں",
    "stageshier": "مرحلے بنیادی نیں",
    "stagesacc": "مرحلے اکٹھے ہوندے نیں",
    "stagessucc": "مرحلے اگے ودھدے رہندے نیں",
    "stagesinf": "مرحلے لامتناہی تک پہنچدے نیں",
    "limofsize": "سائز دی حد",
    "stagesinex": "مرحلے مکدے نہیں",
    "stagescofin": "مرحلے ہر حد توں اگے پہنچدے نیں",
}
DERIVATION = re.compile(r"\\begin\{derivation\}([\s\S]*?)\\end\{derivation\}")
SCAN = re.compile(
    r"(?P<comment>(?<!\\)%[^\n]*)"
    r"|(?P<protected>\\begin\{(?P<env>verbatim\*?|align\*?|gather\*?|multline\*?|equation\*?|eqnarray\*?|array)\}"
    r"[\s\S]*?\\end\{(?P=env)\})"
    r"|(?P<math>(?<!\\)\$\$(?:\\.|[\s\S])*?(?<!\\)\$\$|(?<!\\)\$(?:\\.|[^$])*(?<!\\)\$"
    r"|(?<!\\)\\\[[\s\S]*?(?<!\\)\\\]|(?<!\\)\\\([\s\S]*?(?<!\\)\\\))"
    r"|(?P<cmd>\\(?P<name>[A-Za-z@]+|.))"
)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("directory", type=Path)
    root = cli.parse_args().directory
    expander = Expander(parse_macros((root / "upstream/open-logic-config.sty").read_text("utf8")))
    source = (root / "web-figure-projection.tex").read_text("utf8")
    counts = Counter()
    derivations = 0

    def make_derivation(match):
        nonlocal derivations
        rows = split_array(match[1])
        if not rows:
            raise ValueError("Empty derivation")
        cols = max(map(len, rows))
        if not 2 <= cols <= 3:
            raise ValueError(f"Unexpected derivation column count {cols}")
        derivations += 1
        pad = [""] * cols
        body = r"\\".join("&".join((row + pad)[:cols]) for row in rows)
        return "\n\n\\begin{tabular}{" + "l" * cols + "}\n" + body + "\n\\end{tabular}\n\n"

    source = DERIVATION.sub(make_derivation, source)
    # Pandoc can parse the semantic table once a fixed-width TeX box is a group.
    source, hboxes = re.subn(r"\\hbox\s+to\s*[.0-9]+\s*\\textwidth\s*(?=\{)", "", source)
    counts["fixed_width_hbox"] += hboxes
    source, single_cells = re.subn(r"\\multicolumn\{1\}\{[^{}]+\}(?=\{)", "", source)
    counts["single_column_overrides"] += single_cells
    chunks, cursor, comma = [], 0, False
    while match := SCAN.search(source, cursor):
        chunks.append(source[cursor:match.start()])
        cursor = match.end()
        name = match["name"]
        if name in NOTATION and name in expander.macros:
            _, cursor = expander.read(source, cursor, expander.macros[name].spec)
            chunks.append("$" + source[match.start():cursor] + "$")
            counts[name] += 1
        elif name in PROSE:
            chunks.append(r"\emph{" + PROSE[name] + "}")
            counts[name] += 1
        elif name == "startycommalist":
            comma = False
            counts[name] += 1
        elif name == "ycomma":
            chunks.append("، " if comma else "")
            comma = True
            counts[name] += 1
        elif name in ("article", "Article"):
            _, cursor = argument(source, cursor)
            counts[name] += 1
        elif name in ("text", "hbox") and source[cursor:cursor + 1] == "{":
            value, cursor = argument(source, cursor)
            chunks.append(value)
            counts[name] += 1
        else:
            chunks.append(match[0])
    chunks.append(source[cursor:])
    projected = "".join(chunks).encode()
    (root / "web-notation-projection.tex").write_bytes(projected)
    result = {"derivations": derivations, "notation": counts, "sha256": sha256(projected).hexdigest()}
    (root / "WEB-NOTATION-PROJECTION.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf8")
    print({"derivations": derivations, "converted": sum(counts.values()), "sha256": result["sha256"]})


if __name__ == "__main__":
    main()
