"""Create linked author–year citations and a bibliography from the pinned BibTeX."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re
from copy import deepcopy
import subprocess

from lxml import etree, html

from project_web_structure import optional
from project_web_tags import argument


CITE = re.compile(r"\\(cite(?:alt|alp|author|yearpar|year|p|t)?)(\*)?(?![A-Za-z])")


def render_notes(calls):
    notes = sorted({value for call in calls for value in call[2:4] if value})
    if not notes:
        return {}
    result = {}
    for value in notes:
        rendered, _ = pandoc(["-f", "latex", "-t", "html5", "--mathml"], value.encode())
        root = html.fragment_fromstring(rendered.decode(), create_parent="div")
        wrapper = etree.Element("span", {"class": "citation-note", "dir": "auto"})
        if len(root) != 1 or root[0].tag != "p":
            raise ValueError(f"Unexpected citation note markup for {value!r}")
        paragraph = root[0]
        wrapper.text = paragraph.text
        for child in paragraph:
            wrapper.append(deepcopy(child))
        result[value] = wrapper
    return result


def citation_call(raw):
    match = CITE.match(raw)
    if not match:
        return None
    first, cursor = optional(raw, match.end())
    second, cursor = optional(raw, cursor)
    keys, cursor = argument(raw, cursor)
    if raw[cursor:].strip():
        raise ValueError(f"Unparsed citation suffix {raw[cursor:]!r}")
    return match[1], bool(match[2]), first, second, keys.split(",")


def enumerate_citations(ast):
    calls = []

    def visit(node):
        if isinstance(node, list):
            for child in node:
                visit(child)
        elif isinstance(node, dict):
            if node.get("t") == "Cite":
                raw = [x["c"][1] for x in node["c"][1] if x["t"] == "RawInline"]
                if len(raw) != 1:
                    raise ValueError(f"Expected one native citation payload, got {raw}")
                parsed = citation_call(raw[0])
                if not parsed:
                    raise ValueError(f"Unsupported citation command {raw[0]}")
                calls.append(parsed)
                key = f"citation-slot-{len(calls)}"
                node.clear()
                node.update(t="Span", c=[[key, [], []], []])
            else:
                for child in node.values():
                    visit(child)

    visit(ast["blocks"])
    return calls


def pandoc(args, data=None):
    run = subprocess.run(["pandoc", *map(str, args)], input=data, capture_output=True, check=True)
    return run.stdout, run.stderr


def citation_index(bibliography):
    data, stderr = pandoc(["--from=bibtex", "--to=csljson", bibliography])
    if stderr:
        raise ValueError(stderr.decode("utf8", errors="replace"))
    return {entry["id"]: entry for entry in json.loads(data)}


def key_text(entry, full=False):
    names = entry.get("author") or entry.get("editor") or []
    labels = [n.get("family") or n.get("literal") or n.get("given") for n in names]
    if not labels:
        return re.sub("<[^>]+>", "", entry.get("title", entry["id"]))
    if len(labels) > 2 and not full:
        return labels[0] + " et al."
    return " & ".join(labels)


def year_text(entry):
    issued = entry.get("issued", {})
    values = issued.get("date-parts")
    return str(values[0][0]) if values and values[0] else (issued.get("literal") or "n.d.")


def make_citation(call, entries, years, notes):
    kind, full, first, second, keys = call
    keys = [k.strip() for k in keys]
    group = etree.Element("span", {"class": "citation", "dir": "ltr", "lang": "en"})
    if kind in ("cite", "citep", "citeyearpar"):
        group.text = "("
    if second is not None and first:
        note = deepcopy(notes[first])
        group.append(note)
        note.tail = " "
    for i, key in enumerate(keys):
        entry = entries[key]
        name, year = key_text(entry, full), years[key]
        if kind.startswith("citeyear"):
            label = year
        elif kind == "citeauthor":
            label = name
        elif kind == "citet":
            label = f"{name} ({year})"
        else:
            label = f"{name} {year}"
        child = etree.SubElement(group, "a", href="#ref-" + key)
        child.text = label
        if i < len(keys) - 1:
            child.tail = "; "
    if post := (second if second is not None else first):
        child.tail = (child.tail or "") + ", "
        note = deepcopy(notes[post])
        group.append(note)
        child = note
    if kind in ("cite", "citep", "citeyearpar"):
        child.tail = (child.tail or "") + ")"
    return group


# Notes in these pinned records explicitly cite their translations.
BIBLIOGRAPHY_TRANSLATIONS = {"Frege1884": "Frege1953", "Peter1951": "Peter1967"}


def translated_references(bibtex, keys):
    for record, translation in BIBLIOGRAPHY_TRANSLATIONS.items():
        if record not in keys:
            continue
        match = re.search(r"(?im)^@\w+\{" + record + r",[\s\S]*?^\}", bibtex)
        if not match or not re.search(r"\\citep?\{" + translation + "}", match[0]):
            raise ValueError(f"Expected pinned translation note in {record}")
        yield record, translation


LAYOUT_ONLY = {
    r"\hfill", r"\quad", r"\qquad", r"\centering", r"\;", r"\selectlanguage{urdu}",
    r"\pnbEnableSharedLabels", r"\XeTeXgenerateactualtext=0", r"\relax", r"\frontmatter",
    r"\addcontentsline{toc}{chapter}{اوپن لاجک پروجیکٹ بارے}",
    r"\tableofcontents*", r"\mainmatter", r"\clearpage", r"\small",
    r"\setpnumwidth{3em}", r"\setrmarg{4em}",
    r"\phantom{$\TMtrans{\TMstroke}{q_1}{\TMright}$}",
}


def clear_layout_nodes(node, counts):
    if isinstance(node, list):
        retained = []
        for item in node:
            if isinstance(item, dict) and item.get("t") in ("RawInline", "RawBlock"):
                format_name, tex = item["c"]
                tex = tex.strip()
                if format_name != "latex":
                    raise ValueError(f"Unexpected raw format {format_name!r}")
                if tex in LAYOUT_ONLY:
                    counts[tex] += 1
                    continue
                if tex.startswith(r"\begin{titlingpage}") and tex.endswith(r"\end{titlingpage}"):
                    # The web packager supplies the localized title, credit and license links.
                    counts["titlingpage"] += 1
                    continue
                raise ValueError(f"Unconverted raw TeX: {tex!r}")
            retained.append(item)
            clear_layout_nodes(item, counts)
        node[:] = retained
    elif isinstance(node, dict):
        for value in node.values():
            clear_layout_nodes(value, counts)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("directory", type=Path)
    root = cli.parse_args().directory
    bibliography = root / "upstream/bib/open-logic.bib"
    entries = citation_index(bibliography)
    source = json.loads((root / "pandoc-expanded-math.json").read_bytes())
    calls = enumerate_citations(source)
    keys = {key.strip() for call in calls for key in call[-1]}
    translations = dict(translated_references(bibliography.read_text("utf-8"), keys))
    keys.update(translations.values())
    if missing := keys - entries.keys():
        raise ValueError(f"Citation keys absent from pinned BibTeX: {sorted(missing)}")
    # The same author and year must remain distinguishable in the citation links.
    groups = Counter((key_text(entries[k]), year_text(entries[k])) for k in keys)
    years = {}
    for names_year, size in groups.items():
        members = sorted((k for k in keys if (key_text(entries[k]), year_text(entries[k])) == names_year),
                         key=lambda k: entries[k].get("title", "").casefold())
        for i, key in enumerate(members):
            years[key] = names_year[1] + (chr(97 + i) if size > 1 else "")

    for key in sorted(keys):
        if not re.fullmatch(r"[-A-Za-z0-9_:.]+", key):
            raise ValueError(f"Unsupported citation identifier {key!r}")
    # Pandoc citeproc formats the bibliography from the exact selected records.
    md = "---\nnocite: |\n  " + " ".join("@" + key for key in sorted(keys)) + "\n---\n"
    refs, warnings = pandoc(["-f", "markdown", "-t", "html5", "--citeproc", "--bibliography", bibliography], md.encode())
    if warnings:
        raise ValueError(warnings.decode("utf8", errors="replace"))
    reference = html.fragment_fromstring(refs.decode(), create_parent="section")
    ids = set(reference.xpath(".//*[starts-with(@id,'ref-')]/@id"))
    if ids != {"ref-" + key for key in keys}:
        raise ValueError(f"Bibliography keys changed: {ids ^ {'ref-' + key for key in keys}}")
    for record, translation in translations.items():
        element, = reference.xpath(".//*[@id=$key]", key="ref-" + record)
        note = etree.SubElement(element, "span", {"class": "bibliography-translation"})
        note.text = " "
        link = etree.SubElement(note, "a", href="#ref-" + translation)
        link.text = "Translation in " + key_text(entries[translation]) + " (" + years[translation] + ")"
        link.tail = "."
    reference.set("id", "bibliography")
    reference.set("dir", "ltr")
    reference.set("lang", "en")
    h = etree.Element("h2", lang="pnb-Arab-PK", dir="rtl")
    h.text = "حوالیاں دی فہرست"
    reference.insert(0, h)
    notes = render_notes(calls)
    citation_html = {
        f"citation-slot-{i}": etree.tostring(make_citation(call, entries, years, notes), encoding="unicode")
        for i, call in enumerate(calls, 1)
    }
    result = {"citations": citation_html, "bibliography": etree.tostring(reference, encoding="unicode")}
    markup = (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode()
    (root / "WEB-CITATION-FRAGMENTS.json").write_bytes(markup)
    layout_nodes = Counter()
    clear_layout_nodes(source, layout_nodes)
    (root / "pandoc-citation-slots.json").write_text(json.dumps(source, ensure_ascii=False, separators=(",", ":")), encoding="utf8")
    data = {"cite_commands": dict(Counter(call[0] for call in calls)), "citation_occurrences": len(calls),
            "references": len(keys), "sha256": sha256(markup).hexdigest(),
            "known_layout_nodes_removed": dict(layout_nodes)}
    (root / "WEB-CITATION-PROJECTION.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf8")
    print(data)


if __name__ == "__main__":
    main()
