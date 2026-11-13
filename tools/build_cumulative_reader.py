"""Assemble the Punjabi Shahmukhi Open Logic reader from editable TeX units."""

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
from shutil import copyfile
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


REPO = Path(__file__).resolve().parents[1]
IMPORT = re.compile(
    r"(?m)^[ \t]*\\(?P<command>olimport|subfile)(?P<star>\*)?"
    r"(?:\[(?P<directory>[^\]\n]*)\])?\{(?P<file>[^{}\n]+)\}"
    r"(?:\[(?P<section>[^\]\n]+)\])?[ \t]*(?:%[^\n]*)?$"
)
GRAPH_BRANCH = re.compile(
    r"(?m)^\\iftag\{(?P<tag>FOL|prfSC|prfND|prfTab|prfAX)\}\{(?:%[^\n]*)?\n"
    r"(?P<body>(?:[ \t]+\\olimport[^\n]+\n)+)\}\{\}[ \t]*$"
)
WRAPPER = re.compile(
    r"(?ms)^\\begin\{document\}[^\S\n]*(?:%[^\n]*)?\n"
    r"(.*?)^\\end\{document\}[^\S\n]*(?:%[^\n]*)?$"
)
LATIN_BRIDGE = re.compile(r"\([A-Za-z][A-Za-z'’.,/&–\-]*(?:\s+[A-Za-z][A-Za-z'’.,/&–\-]*)+\)")
HEADING_BRIDGE = re.compile(r"\([A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ'’\x60.,:/&–\-]*(?:[ \t]+[A-Za-zÀ-ÖØ-öø-ÿ'’\x60.,:/&–\-]+)*\)")
HEADING_LINE = re.compile(r"(?m)^[ \t]*\\(?:olpart|olchapter|olsection|part|chapter|section|subsection|subsubsection)\*?(?![A-Za-z])[^\n]*")
BOOKMARK_HEADING = re.compile(
    r"(?m)^(?P<command>[ \t]*\\(?:olchapter\{[^{}]+\}\{[^{}]+\}|olsection|section|subsection|subsubsection|chapter))"
    r"\{(?P<title>(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*)\}"
)
BOOKMARK_MATH = {
    r"\Nat": "ℕ", r"\Int": "ℤ", r"\Rat": "ℚ", r"\Real": "ℝ",
    r"\Th{Q}": "Q", r"\Th{PA}": "PA", r"\Log{LK}": "LK", r"\LogCL": "C",
    r"\omega": "ω", r"\alpha": "α", r"\beta": "β", r"\eta": "η", r"\beta\eta": "βη",
    r"\Sigma": "Σ", r"\Sigma_1": "Σ₁", r"\aleph": "ℵ", r"\True": "𝕋",
    r"\Z": "Z", r"\Z^-": "Z⁻", r"\ZF": "ZF", r"\ZFminus": "ZF⁻", r"\ZFC": "ZFC",
    r"V_\alpha": r"V\textunderscore{}α",
}
PROTECTED_TEXT = re.compile(
    r"(?ms)\\begin\{verbatim\*?\}.*?\\end\{verbatim\*?\}"
    r"|\\verb\*?(?P<delimiter>[|+]).*?(?P=delimiter)"
    r"|(?<!\\)%[^\n]*|(?<!\\)\$\$.*?(?<!\\)\$\$|(?<!\\)\$[^$]*?(?<!\\)\$"
    r"|\\\[.*?\\\]|\\\(.*?\\\)"
    r"|\\begin\{(?P<math>align\*?|alignat\*?|equation\*?|gather\*?|multline\*?|eqnarray\*?)\}"
    r".*?\\end\{(?P=math)\}"
)
FORMULA_AT_ALIGNMENT = re.compile(
    r"(?m)(?P<start>(?:^|&)[ \t]*)!(?P<letter>[ABCDEFGHKLORST])(?![a-zA-Z])"
)
ALIGNMENT_ENV = re.compile(
    r"\\begin\{(?P<env>align\*?|alignat\*?|aligned|gather\*?|gathered|multline\*?|eqnarray\*?|array|split)\}"
    r"(?P<rows>[\s\S]*?)\\end\{(?P=env)\}"
)
TEXT_TOKEN = re.compile(r"(?P<call>!![\^a]{0,2}|\\(?:use|print)token\{[^{}\n]+\})\{(?P<key>[^{}]+)\}")
ALTERNATE_DRIVER_NOTE = {
    646: "نحو تے معنویات اکّو باب وچ",
    719: "تعلق دا مُڈھلا باب",
    720: "سیٹ، تعلق تے فنکشن دا مُڈھلا حصہ",
    722: "سیٹاں دے سائز دا مُڈھلا باب",
}
PROFILE = {
    "nastaliq": r"""\babelfont[urdu]{rm}[Path=fonts/,Script=Arabic,
  BoldFont=NotoNastaliqUrdu-Regular.ttf,BoldFeatures={FakeBold=1.5}]{NotoNastaliqUrdu-Regular.ttf}
\linespread{1.65}""",
    "naskh": r"""\babelfont[urdu]{rm}[Path=fonts/,Script=Arabic,
  BoldFont=NotoNaskhArabic-Bold.ttf]{NotoNaskhArabic-Regular.ttf}
\linespread{1.25}""",
}
BUILD_FILES = (
    "upstream/LICENSE.md",
    "upstream/README.md",
    "upstream/open-logic-config.sty",
    "upstream/open-logic-envs.sty",
    "upstream/open-logic-locale.sty",
    "upstream/bib/natbib-oup.bst",
    "upstream/bib/open-logic.bib",
    "translation/pnb-morphology.sty",
    "reader/cumulative-localization.tex",
    "reader/ai-attribution.json",
    "fonts/NOTICE.md",
    "fonts/OFL.txt",
    "fonts/NotoNastaliqUrdu-Regular.ttf",
    "fonts/NotoNaskhArabic-Regular.ttf",
    "fonts/NotoNaskhArabic-Bold.ttf",
    "fonts/NotoSerif-Regular.ttf",
    "fonts/NotoSerif-Bold.ttf",
    "fonts/NotoSerif-Italic.ttf",
    "fonts/NotoSerif-BoldItalic.ttf",
)
PROPOSITIONAL_LINKS = r"""
\chapter{قضیاتی منطق دے ثبوتی نظام}
قضیاتی ثبوتاں دے قاعدے تے تمامیت دے ثبوت اِنہاں باباں وچ ویکھو۔
\begin{itemize}
\item \hyperref[fol:prf::chap]{اخذ نظام}
\item \hyperref[fol:seq::chap]{سیکوئنٹ حساب}
\item \hyperref[fol:ntd::chap]{فطری استنباط}
\item \hyperref[fol:tab::chap]{تابلو}
\item \hyperref[fol:axd::chap]{مسلّمی اخذ}
\item \hyperref[fol:com::chap]{تمامیت دا قضیہ}
\end{itemize}
ماخذ فائل توں اِنہاں باباں دا صرف قضیاتی روپ وی تیار ہو سکدا اے۔
"""


def digest(data):
    return sha256(data).hexdigest()


def replace_once(text, old, new, unit):
    if text.count(old) != 1:
        raise ValueError(f"{unit}: expected one occurrence of {old!r}")
    return text.replace(old, new, 1)


def direct_import(path, match):
    directory = match["directory"] or ""
    base = "content" if match["star"] else posixpath.dirname(path)
    result = posixpath.normpath(posixpath.join(base, directory, match["file"]))
    return result if result.endswith(".tex") else result + ".tex"


def topic_note(notes):
    items = "؛ ".join(
        title + r" (\texttt{" + PurePosixPath(path).stem + ".tex})" for title, path in notes
    )
    return "\n\\par\\noindent\\emph{متبادل ترتیب۔} " + items + "۔ ایہ ترتیب تدوین جوگ ماخذ فائل وچ موجود اے۔\n"


def directionally_isolate_bridges(body):
    rendered = []
    cursor = total = 0
    for match in PROTECTED_TEXT.finditer(body):
        text, count = wrap_latin_bridges(body[cursor:match.start()])
        rendered.extend((text, match[0]))
        total += count
        cursor = match.end()
    text, count = wrap_latin_bridges(body[cursor:])
    rendered.append(text)
    return "".join(rendered), total + count


BOOKMARK_WORDS = {
    '\\printtoken{S}{c.e.}': 'قابلِ حساب گنتی وار فہرست بنن جوگ',
    '!!^{axiomatizable}': 'مسلّماتی طور متعین ہون جوگ',
    '\\usetoken{S}{derivability}': 'اخذ ہون دی اہلیت',
    '\\usetoken{P}{derivation}': 'اخذ',
    '\\Ax{K}': 'K',
}


def wrap_latin_bridges(text):
    def mark(match):
        return r"\pnbLatin{" + re.sub(r"\s+", " ", match[0]) + "}"

    def heading(match):
        return HEADING_BRIDGE.sub(
            lambda bridge: bridge[0]
            if match[0][:bridge.start()].endswith(r"\pnbLatin{")
            else mark(bridge),
            match[0],
        )

    updated = HEADING_LINE.sub(heading, text)
    updated = LATIN_BRIDGE.sub(
        lambda match: match[0]
        if updated[max(0,match.start()-len(r"\pnbLatin{")):match.start()] == r"\pnbLatin{"
        else mark(match),
        updated,
    )
    return updated, updated.count(r"\pnbLatin{") - text.count(r"\pnbLatin{")


def bookmark_titles(body):
    def replace(match):
        title = match["title"]
        if r"\texorpdfstring" in title:
            return match[0]
        math = re.findall(r"\$([^$\n]+)\$", title)
        if not math and r"\Ax{K}" not in title:
            return match[0]
        if any(term not in BOOKMARK_MATH and not re.fullmatch(r"[A-Za-z]", term) for term in math):
            return match[0]
        plain = re.sub(r"\$([^$\n]+)\$", lambda m: BOOKMARK_MATH.get(m[1], m[1]), title)
        plain = re.sub(r"\\pnbLatin\{([^{}]+)\}", r"\1", plain)
        for old, new in BOOKMARK_WORDS.items():
            plain = plain.replace(old, new)
        if "\\" in plain.replace(r"\textunderscore{}", "") or "$" in plain or "!!" in plain:
            return match[0]
        plain = " ".join(plain.replace("~", " ").split())
        return match["command"] + r"{\texorpdfstring{" + title + "}{" + plain + "}}"

    return BOOKMARK_HEADING.subn(replace, body)



def normalize_text_token_names(body):
    return TEXT_TOKEN.sub(
        lambda match: match["call"] + "{" + " ".join(match["key"].split()) + "}", body
    )


def stage_build_files(output):
    paths = list(BUILD_FILES)
    for directory, suffix in (("upstream/sty", "*.sty"), ("upstream/assets/diagrams", "*.tikz")):
        paths.extend(path.relative_to(REPO).as_posix() for path in sorted((REPO / directory).glob(suffix)))
    receipt = {}
    for relpath in paths:
        destination = output / relpath
        destination.parent.mkdir(parents=True, exist_ok=True)
        copyfile(REPO / relpath, destination)
        receipt[relpath] = digest(destination.read_bytes())
    return receipt


def source_archive(output, inventory, source_names, build_inputs, source_hashes, archive):
    """Package the checked inputs and assembled masters with stable ZIP metadata."""
    entries = {
        path: (output / path).read_bytes()
        for path in (*build_inputs, *source_names)
    }
    for relpath in (
        "LICENSE.md",
        "reader/cumulative.tex",
        "reader/cumulative-build.md",
        "tools/build_cumulative_reader.py",
        "tools/build_cumulative_pdf.ps1",
    ):
        entries[relpath] = (REPO / relpath).read_bytes()
    for path in sorted((REPO / "upstream/include").glob("*.tex")):
        entries[path.relative_to(REPO).as_posix()] = path.read_bytes()
    clean_inventory = {"schema": "pnb-cumulative-reader-inputs/1", "units": []}
    for unit in inventory["units"]:
        public_unit = {
            key: unit[key] for key in (
                "unit_id", "source_path", "target_sha256", "proposed_placement", "related_units"
            )
        }
        relpath = unit["source_path"]
        expected = source_hashes[(unit["unit_id"], relpath)]
        for root in ("translation", "upstream"):
            name = f"{root}/{relpath}"
            entries[name] = (REPO / name).read_bytes()
        if digest(entries[f"upstream/{relpath}"]) != expected:
            raise ValueError(f"{relpath}: English source hash differs from the frozen input inventory")
        public_unit["source_sha256"] = expected
        clean_inventory["units"].append(public_unit)
    entries["reader/source-units.json"] = (
        json.dumps(clean_inventory, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")
    entries["SHA256SUMS"] = "".join(
        f"{digest(entries[name])}  {name}\n" for name in sorted(entries)
    ).encode("utf-8")
    archive.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(archive, "w", compression=ZIP_DEFLATED, compresslevel=9) as bundle:
        for name, data in sorted(entries.items()):
            info = ZipInfo(name, date_time=(2026, 11, 13, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, data, compress_type=ZIP_DEFLATED, compresslevel=9)
    return {"sha256": digest(archive.read_bytes()), "bytes": archive.stat().st_size, "files": len(entries)}


class Reader:
    def __init__(self, plan):
        self.units = {int(u["unit_id"][4:]): u for u in plan["units"]}
        if sorted(self.units) != list(range(1, 723)):
            raise ValueError("Expected each of the 722 source units")
        self.paths = {u["source_path"]: n for n, u in self.units.items()}
        self.bodies = {}
        self.additional = defaultdict(list)
        self.notes = defaultdict(list)
        self.alternate_drivers = {}
        self.visits = Counter()
        self.parent = {}
        self.order = []
        self.changes = defaultdict(list)
        for n, u in self.units.items():
            raw = (REPO / "translation" / u["source_path"]).read_bytes()
            if digest(raw) != u["target_sha256"]:
                raise ValueError(f"OLP-{n:04d}: translation hash differs from the input inventory")
            body = raw.decode("utf-8").replace("\r\n", "\n")
            wrapper = WRAPPER.search(body)
            if wrapper is None and re.search(r"(?m)^\\documentclass\b", body):
                raise ValueError(f"OLP-{n:04d}: invalid document wrapper")
            self.bodies[n] = wrapper[1] if wrapper else body
            mode = u["proposed_placement"]
            if mode == "reader_alternative_at_topic":
                host, = u["related_units"]
                self.additional[int(host[4:])].append(n)
            elif mode == "editable_alternate_driver_and_in_topic_index":
                self.alternate_drivers[n] = u["source_path"]
                for host in u["related_units"]:
                    self.notes[int(host[4:])].append((ALTERNATE_DRIVER_NOTE[n], u["source_path"]))

    def project(self, n, body):
        def change(old, new, reason):
            nonlocal body
            body = replace_once(body, old, new, f"OLP-{n:04d}")
            self.changes[n].append(reason)

        # The exact same source files have a second, propositional-only entry point.
        # Keep that driver in the source bundle and link to the shared reader chapters.
        if n == 55:
            start = body.index(r"\tagfalse{FOL}")
            end = body.index(r"\tagtrue{FOL}", start) + len(r"\tagtrue{FOL}")
            change(body[start:end], PROPOSITIONAL_LINKS, "link to six shared proof-system chapters")
        if n == 40:
            change(r"\label{sfr:siz:red:prob:nat-nat}",
                   r"\label{sfr:siz:red-alt:prob:nat-nat}", "distinct label for alternate exercise")
        if n == 47:
            body, labels = re.subn(
                r"(?m)^([ \t]*)\\emph\{([^{}\n]+)\}([ \t]*&[ \t]*&)",
                r"\1\\text{\\textbf{\2}}\3",
                body,
            )
            if labels != 6:
                raise ValueError("OLP-0047: expected six arithmetic alignment labels")
            self.changes[n].append("typeset six arithmetic alignment labels as bold text in math")
        if n == 132:
            change("\\end{proof}\n}\n\n\\iftag{FOL}{%",
                   "\\end{proof}\n}{}\n\n\\iftag{FOL}{%", "supply omitted empty tag branch")
        if n == 154:
            change("وچ اوہناں دا وکھرا معاملہ کرن دی لوڑ نہیں۔}",
                   "وچ اوہناں دا وکھرا معاملہ کرن دی لوڑ نہیں۔}{}", "supply omitted empty tag branch")
        if n == 163:
            for connective in ("Ex", "All"):
                change(r"\tagprob{def" + connective + "}",
                       r"\tagprob[def" + connective + "]{notdef" + connective + "}",
                       "keep exercise with the corresponding defined-connective proposition")
        if n == 207:
            first = r"\begin{gathered}" + "\n" + r"\forall m\,(Z(m)\to\exists h\,J(m,m,h)),"
            last = r"\end{gathered}"
            start = body.index(first)
            end = body.index(last, start) + len(last)
            original = body[start:end]
            revised = original.replace(r"\begin{gathered}", r"\begin{aligned}", 1)
            revised = revised.removesuffix(last) + r"\end{aligned}"
            revised, conditions = re.subn(r"(?m)^(\\forall (?:m\\,|d,m,h,e,))", r"&\1", revised)
            revised, continuations = re.subn(
                r"(?m)^(\\exists k,|\\forall u,v\\,)", r"&\\quad\1", revised,
            )
            revised, breaks = re.subn(r"(\\to|G\(k,a,b\)\\land)\n(?=&)", r"\1 \\\\\n", revised)
            if (conditions, continuations, breaks) != (3, 4, 4):
                raise ValueError(f"OLP-0207: extension conditions changed {(conditions, continuations, breaks)}")
            change(original, revised, "break both extension implications across aligned rows")
        if n == 239:
            change("آؤٹ پٹ دیندا اے؛ نہیں تاں اوہ~$a$ واپس دیندا اے۔}",
                   "آؤٹ پٹ دیندا اے؛ نہیں تاں اوہ~$a$ واپس دیندا اے۔}{}", "supply omitted empty tag branch")
        if n == 310:
            change('حساب دی زبان دی پہلے درجے دی منطق (یعنی سیٹ\n$\\Setabs{!A}{\\text{$!A$ پہلے درجے دی منطق وچ ثابت ہو سکدا اے}}$)',
                   'حساب دی زبان دی پہلے درجے دی منطق، یعنی سیٹ\n\\[\n\\Setabs{!A}{\\text{$!A$ پہلے درجے دی منطق وچ ثابت ہو سکدا اے}}\n\\]',
                   "allow the definition of the set of provable formulas to wrap")
        if n == 549:
            original = re.compile(r"\\begin\{center\}(\s*\\begin\{tikzpicture\}[\s\S]*?\\end\{tikzpicture\}\s*)\\end\{center\}")
            body, count = original.subn(r"\\begin{pnbDiagramLine}\1\\end{pnbDiagramLine}", body)
            if count != 3:
                raise ValueError("OLP-0549: expected three ordinal diagrams")
            self.changes[n].append("center the full ordinal diagrams in a left-to-right line")
        if n == 596:
            change('ہُن $f(x) = \\text{$<$ مطابق سبھ توں چھوٹا رکن، جیہڑا ایس سیٹ وچ اے }x$',
                   'ہُن ایہ تعریف لو:\n\\[\nf(x) = \\text{$<$ مطابق سبھ توں چھوٹا رکن، جیہڑا ایس سیٹ وچ اے }x\n\\]',
                   "allow the least-element definition of the choice function to wrap")
        if n == 668:
            pattern = r"\$\\pheight\{\\delta\} =\s+\\max\(\\pheight\{\\delta_1\}, \\pheight\{\\delta_2\}, \\pheight\{\\delta_3\}\) \+ 1\$"
            found = re.findall(pattern, body)
            if len(found) != 1:
                raise ValueError("OLP-0668: expected the three-premise height identity")
            new = r"\[\pheight{\delta} = \max(\pheight{\delta_1}, \pheight{\delta_2}, \pheight{\delta_3}) + 1\]"
            change(found[0], new, "display the three-premise height identity")
        if n == 461:
            change(r"$\Diamond$}}{$\Diamond$} لئی نیں۔",
                   r"$\Diamond$}{}}{$\Diamond$} لئی نیں۔", "supply omitted nested empty tag branch")
        if n == 643:
            for part in ("fol", "pl"):
                change(r"\olfileid{" + part + r"}{axd}{prv}",
                       r"\olfileid{" + part + r"}{axd}{prv-alt}", "distinct section namespace")
            change(r"\olref[fol][axd][prv]{prop:provability}",
                   r"\olref{prop:provability}", "point to proposition within the alternate section")
        if n == 644:
            corrected = re.sub(
                r"(fol:(?:seq|ntd)):prv:prop:provability-(land-left|land-right|lor-left|lor-right|mp|lif)",
                lambda m: m[1] + ":ppr:prop:provability-" + {
                    "lor-left": "lor", "lor-right": "lor", "mp": "lif-left", "lif": "lif-right",
                }.get(m[2], m[2]),
                body,
            )
            if corrected == body:
                raise ValueError("OLP-0644: expected references to legacy propositional provability labels")
            body = corrected
            self.changes[n].append("resolve references to the corresponding current provability clauses")
        if n == 660:
            body = "\\olfileid{pt}{cut}{intuitionistic}\n" + body
            self.changes[n].append("attach unwrapped text to proof theory reference context")
        if n in (692, 693):
            change(r"\textbf{Axioms:}", r"\textbf{مسلّمے}", "localize rule table header")
            change(r"\textbf{Inference Rules:}", r"\textbf{استنباط دے قاعدے}", "localize rule table header")
        if n == 693:
            change(r"$\Gamma \Sequent x:!A$ if $x:!A \in \Gamma$",
                   r"$\Gamma \Sequent x:!A$ جے $x:!A \in \Gamma$", "localize rule side condition")
            change(r"\ollabel{tab:tN2ip}", r"\ollabel{tab:tN3ip}", "distinct tN3ip table label")
        if n == 697:
            change(r"\olref{tab:tN2ip}", r"\olref{tab:tN3ip}", "reference the tN3ip rule table")
        if n in (705, 708, 709, 710):
            old, new = {
                705: ("G1c", "G1i"), 708: ("G3c", "G3i"),
                709: ("G1c", "LK"), 710: ("G3c", "mG3i"),
            }[n]
            change(r"\ollabel{tab:" + old + "}", r"\label{pt:seq:alt:tab:" + new + "}",
                   "give the additional rule table a distinct system label")
        if n == 714:
            if body.count(r"\olref[axd]{prop:phi}") != 2:
                raise ValueError("OLP-0714: expected two references to the consistency dichotomy")
            body = body.replace(r"\olref[axd]{prop:phi}", r"\olref[fol][axd][prv]{prop:provability-exhaustive}")
            self.changes[n].append("resolve two references to the consistency dichotomy")
            change(r"\olref[axd]{prop:prov-incons}", r"\olref[fol][axd][prv]{prop:prov-incons}",
                   "reference the axiomatic provability and inconsistency proposition")
        if n == 718:
            # The frozen source accidentally uses the prose article command
            # for the first schematic formula in this induction example.
            malformed = "!!^a"
            if body.count(malformed) != 16:
                raise ValueError("OLP-0718: expected sixteen malformed first-formula metavariables")
            body = body.replace(malformed, "!A")
            self.changes[n].append("restore the first schematic formula paired with !B")
        if n == 715:
            change(r"\olref[sem]{prop:semanticalfacts}",
                   r"\olref[pl][syn][sem]{prop:semanticalfacts}", "reference the propositional semantics")

        # The English token mechanism consumes plural s and leaves past-tense d.
        # Punjabi already supplies the inflection in the words after these calls.
        corrected = body.replace("!!{prove}d", "!!{prove}")
        if corrected != body:
            body = corrected
            self.changes[n].append("remove English past-tense suffix from Punjabi proof token")
        if self.units[n]["source_path"].endswith("/proof-search/introduction.tex"):
            change("معتبر سیکوئنٹ !!{prove}s۔", "معتبر سیکوئنٹ !!{prove} کردا اے۔",
                   "supply Punjabi verbal inflection for finite proof token")

        theory_bars = {307: ("T", 2), 309: ("Q", 5), 310: ("Q", 3), 311: ("Q", 1)}
        if n in theory_bars:
            name, expected = theory_bars[n]
            old = r"\Th{\bar " + name + "}"
            if body.count(old) != expected:
                raise ValueError(f"OLP-{n:04d}: unexpected barred theory notation")
            body = body.replace(old, r"\bar{\Th{" + name + "}}")
            self.changes[n].append("move the overbar outside the bold theory name")

        count_formula_cells = 0

        def explicit_first_formula(alignment):
            nonlocal count_formula_cells
            rows, changed = FORMULA_AT_ALIGNMENT.subn(
                lambda m: m["start"] + r"\formula " + m["letter"], alignment["rows"],
            )
            count_formula_cells += changed
            return alignment[0].replace(alignment["rows"], rows, 1)

        body = ALIGNMENT_ENV.sub(explicit_first_formula, body)
        if count_formula_cells:
            self.changes[n].append(f"expand formula metavariables at alignment starts ({count_formula_cells})")

        normalized = normalize_text_token_names(body)
        if normalized != body:
            body = normalized
            self.changes[n].append("normalize line breaks inside text-token names")
        body, branches = GRAPH_BRANCH.subn(lambda match: match["body"].rstrip("\n"), body)
        if branches:
            self.changes[n].append(f"select the full corpus import branches ({branches})")
        body, bridges = directionally_isolate_bridges(body)
        if bridges:
            self.changes[n].append(f"left-to-right parenthesized Latin phrases ({bridges})")
        body, bookmarks = bookmark_titles(body)
        if bookmarks:
            self.changes[n].append(f"preserve mathematical notation in PDF bookmarks ({bookmarks})")
        return body

    def expand(self, n, parent=None, section=None, direct=False):
        self.visits[n] += 1
        if self.visits[n] != 1:
            raise ValueError(f"OLP-{n:04d}: duplicate/cyclic import under {parent}")
        self.parent[n] = parent
        self.order.append(n)
        path = self.units[n]["source_path"]
        body = self.project(n, self.bodies[n])

        if n == 2:
            body = replace_once(
                body, r"\olimport[intuitionistic-logic]{intuitionistic-logic}",
                "\\olimport[intuitionistic-logic]{intuitionistic-logic}\n\n"
                "\\olimport[proof-theory]{proof-theory}", n,
            )
        if n == 685:
            body = replace_once(
                body, r"\olimport[cut-elimination]{cut-elimination}",
                "\\olimport[cut-elimination]{cut-elimination}\n"
                "\\olimport[proof-search]{proof-search}", n,
            )
        if n == 289:
            body = replace_once(
                body, r"\olimport{undecidability}",
                "\\olimport{c}\n\\olimport{c-representable}\n\\olimport{undecidability}", n,
            )

        def include(match):
            imported = self.paths[direct_import(path, match)]
            is_subfile = match["command"] == "subfile"
            return self.expand(imported, n, match["section"] or "section", direct=is_subfile)

        body = IMPORT.sub(include, body)
        if n in self.notes:
            body = "\n".join((body, topic_note(self.notes[n])))
        for child in self.additional[n]:
            if self.visits[child]:
                continue
            content = self.expand(child, n)
            hook = next((h for h in (r"\OLEndChapterHook", r"\OLEndPartHook") if h in body), None)
            if hook:
                body = replace_once(body, hook, content + "\n" + hook, n)
            else:
                body += "\n" + content

        opening = [rf"% OLP-{n:04d} {path}"]
        closing = []
        if parent is not None:
            opening.append(r"\begingroup")
            closing.append(r"\endgroup")
            if not direct:
                opening.extend((
                    rf"\def\olfilename{{{PurePosixPath(path).stem}}}",
                    r"\expandafter\def\csname ol@sectioncs\endcsname{" + (section or "section") + "}",
                ))
        return "\n".join([*opening, body.rstrip("\n"), *closing, rf"% /OLP-{n:04d}"])


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--inventory", type=Path, required=True)
    cli.add_argument("--output", type=Path, required=True)
    cli.add_argument("--stage-build-files", action="store_true")
    cli.add_argument("--source-archive", type=Path)
    cli.add_argument("--source-manifest", type=Path)
    args = cli.parse_args()
    inventory = args.inventory.read_bytes()
    inventory_data = json.loads(inventory)
    reader = Reader(inventory_data)
    about = reader.expand(1)
    body = reader.expand(2)
    expected = set(reader.units) - set(reader.alternate_drivers)
    if set(reader.visits) != expected or any(count != 1 for count in reader.visits.values()):
        raise ValueError(f"Reader coverage mismatch. Missing {expected - set(reader.visits)}")
    template = (REPO / "reader/cumulative.tex").read_text("utf-8")
    credits = json.loads((REPO / "reader/ai-attribution.json").read_bytes())
    attribution = "\\par\n".join(
        rf"{{\small {credit['role']} — \pnbLatin{{{credit['model']}}}۔}}"
        for credit in credits
    )
    models = ", ".join(credit["model"] for credit in credits)
    args.output.mkdir(parents=True, exist_ok=True)
    sources = {}
    for profile, settings in PROFILE.items():
        source = template
        replacements = {
            "PROFILE": settings, "ABOUT": about, "BODY": body,
            "ATTRIBUTION": attribution, "ATTRIBUTION_MODELS": models,
        }
        for marker, content in replacements.items():
            source = replace_once(source, f"@@{marker}@@", content, profile)
        data = source.encode("utf-8")
        destination = args.output / f"open-logic-pnb-{profile}.tex"
        destination.write_bytes(data)
        sources[destination.name] = {"sha256": digest(data), "bytes": len(data)}
    build_inputs = stage_build_files(args.output) if args.stage_build_files or args.source_archive else {}
    receipt = {
        "schema": "pnb-cumulative-reader-assembly/1",
        "inventory_sha256": digest(inventory),
        "sources": sources,
        "build_inputs": build_inputs,
        "units": [
            {
                "id": f"OLP-{n:04d}",
                "source_path": reader.units[n]["source_path"],
                "reader_parent": f"OLP-{reader.parent[n]:04d}" if reader.parent[n] else None,
                "reader_changes": reader.changes[n],
            }
            for n in reader.order
        ],
        "editable_alternate_drivers": {
            f"OLP-{n:04d}": path for n, path in reader.alternate_drivers.items()
        },
    }
    if args.source_archive:
        rows = (
            [json.loads(line) for line in args.source_manifest.read_text("utf-8").splitlines()]
            if args.source_manifest else inventory_data["units"]
        )
        hashes = {(row["unit_id"], row["source_path"]): row["source_sha256"] for row in rows}
        receipt["source_archive"] = source_archive(
            args.output, inventory_data, sources, build_inputs, hashes, args.source_archive
        )
    (args.output / "ASSEMBLY.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"Assembled {len(reader.visits)} reader units and indexed {len(reader.alternate_drivers)} editable drivers.")


if __name__ == "__main__":
    main()
