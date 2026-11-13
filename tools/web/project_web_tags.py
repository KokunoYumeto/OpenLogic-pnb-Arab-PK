"""Select the cumulative reader's tagged branches before semantic conversion."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re


TAG_SET = re.compile(r"\\tag(true|false)\{([^{}]+)\}")
CONDITIONAL = re.compile(
    r"\\(?:iftag|tagitem|tagrefs|tagtrue|tagfalse|tagprob|tagendprob|begingroup|endgroup)\b"
    r"|\\(?:begin|end)\{(?:editorial|tagblock|tagenumerate|verbatim\*?)\}"
)
TAG_PAIR = re.compile(r"([\w]+)\s*/\s*\{([^{}]+)\}")
LEX = re.compile(r"%[^\n]*|\\[A-Za-z@]+|\\[^A-Za-z@]|[{}]")
AFTER_CONDITIONAL = re.compile(r"(?:\s|%[^\n]*(?:\n|$))*")


def argument(text, cursor, opener="{", closer="}"):
    while cursor < len(text):
        if text[cursor].isspace():
            cursor += 1
        elif text[cursor] == "%":
            newline = text.find("\n", cursor)
            cursor = len(text) if newline == -1 else newline + 1
        else:
            break
    if cursor == len(text) or text[cursor] != opener:
        raise ValueError(f"Expected {opener} near {text[cursor:cursor + 90]!r}")
    depth = 1
    if opener == "[":
        stop = text.index(closer, cursor + 1)
        return text[cursor + 1:stop], stop + 1
    for match in LEX.finditer(text, cursor + 1):
        if match[0] == opener:
            depth += 1
        elif match[0] == closer:
            depth -= 1
        if depth == 0:
            return text[cursor + 1:match.start()], match.end()
    raise ValueError(f"Unclosed group near {text[cursor:cursor + 90]!r}")


class Projection:
    def __init__(self, config):
        self.tags = {}
        for match in TAG_SET.finditer(config):
            self.set_tags(match[2], match[1] == "true")
        self.groups = []
        self.enum = []
        self.count = Counter()
        self.missing_false_branches = []

    def set_tags(self, names, value):
        for tag in names.split(","):
            tag = tag.strip()
            self.tags[tag] = value
            self.tags["not" + tag] = not value

    def selected(self, names):
        return sum(self.tags[name.strip()] for name in names.split(",") if name.strip())

    def project(self, text):
        output = []
        cursor = 0
        while match := CONDITIONAL.search(text, cursor):
            before = text[cursor:match.start()]
            line_prefix = text[text.rfind("\n", 0, match.start()) + 1:match.start()]
            if re.search(r"(?<!\\)%", line_prefix):
                output.append(text[cursor:match.end()])
                cursor = match.end()
                continue
            output.append(before)
            cursor = match.end()
            command = match[0][1:]
            self.count[command] += 1
            if command in ("tagtrue", "tagfalse"):
                tags, cursor = argument(text, cursor)
                self.set_tags(tags, command == "tagtrue")
            elif command == "begingroup":
                self.groups.append(self.tags.copy())
            elif command == "endgroup":
                self.tags = self.groups.pop()
            elif command.startswith("begin{verbatim"):
                end = "\\" + command.replace("begin", "end", 1)
                cursor = text.index(end, cursor) + len(end)
                output.append(text[match.start():cursor])
            elif command == "begin{editorial}":
                cursor = text.index(r"\end{editorial}", cursor) + len(r"\end{editorial}")
            elif command == "begin{tagblock}":
                tags, cursor = argument(text, cursor)
                stop = text.index(r"\end{tagblock}", cursor)
                if self.selected(tags):
                    output.append(self.project(text[cursor:stop]))
                cursor = stop + len(r"\end{tagblock}")
            elif command == "begin{tagenumerate}":
                tags, cursor = argument(text, cursor)
                enumerated = self.selected(tags) > 1
                self.enum.append(enumerated)
                if enumerated:
                    output.append(r"\begin{enumerate}")
            elif command == "end{tagenumerate}":
                if self.enum.pop():
                    output.append(r"\end{enumerate}")
            elif command == "tagprob":
                requirement = "tagTrue"
                if text[cursor:].lstrip().startswith("["):
                    requirement, cursor = argument(text, cursor, "[", "]")
                excluded, cursor = argument(text, cursor)
                stop = text.index(r"\tagendprob", cursor)
                if self.selected(requirement) and not self.selected(excluded):
                    output.append(self.project(text[cursor:stop]))
                cursor = stop + len(r"\tagendprob")
            elif command == "tagrefs":
                pairs, cursor = argument(text, cursor)
                links = [m[2] for m in TAG_PAIR.finditer(pairs) if self.selected(m[1])]
                if links:
                    output.append(r"\cref{" + ",".join(links) + "}")
            elif command in ("iftag", "tagitem"):
                tags, cursor = argument(text, cursor)
                yes, cursor = argument(text, cursor)
                following = AFTER_CONDITIONAL.match(text, cursor).end()
                if text[following:following + 1] == "{":
                    no, cursor = argument(text, cursor)
                else:
                    self.count["missing_empty_false_branch"] += 1
                    marker = list(re.finditer(r"(?m)^% (OLP-\d{4}) ([^\n]+)", text[:match.start()]))
                    self.missing_false_branches.append({
                        "unit_id": marker[-1][1] if marker else None,
                        "line": text.count("\n", 0, match.start()) + 1,
                        "tag": tags,
                        "before": yes[-100:],
                        "after": text[following:following + 100],
                    })
                    no = ""
                choice = yes if self.selected(tags) else no
                if choice and command == "tagitem" and (not self.enum or self.enum[-1]):
                    output.append(r"\item ")
                output.append(self.project(choice))
            else:
                raise ValueError(f"Unexpected {command}")
        output.append(text[cursor:])
        return "".join(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    root = args.directory
    source = (root / "open-logic-pnb-naskh.tex").read_text("utf8")
    config = (root / "upstream/open-logic-config.sty").read_text("utf8")
    config += (root / "upstream/sty/open-logic.sty").read_text("utf8")
    selector = Projection(config)
    start = source.index(r"\begin{document}") + len(r"\begin{document}")
    stop = source.index(r"\backmatter", start)
    body = selector.project(source[start:stop])
    if selector.groups or selector.enum:
        raise ValueError("Unclosed reader group")
    body = re.sub(r"(?m)^\\(?:def\\olfilename|expandafter\\def\\csname ol@sectioncs)[^\n]*\n", "", body)
    result = body.encode("utf8")
    (root / "web-tag-projection.tex").write_bytes(result)
    receipt = {"sha256": sha256(result).hexdigest(), "bytes": len(result), "constructs": selector.count,
               "missing_false_branches": selector.missing_false_branches}
    (root / "WEB-TAG-PROJECTION.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(json.dumps({k: v for k, v in receipt.items() if k != "missing_false_branches"}))
    if selector.missing_false_branches:
        raise SystemExit("Repair malformed source conditionals before conversion.")


if __name__ == "__main__":
    main()
