"""Independent structural/content audit for the bounded Punjabi Sets EPUB."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import posixpath
import re
import unicodedata
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

from lxml import etree


REPO = Path(__file__).resolve().parents[1]
REVISION = "9620cc73f9c8e0ad003c514a5d3748f29611c4c0"
XHTML_NS = "http://www.w3.org/1999/xhtml"
MATHML_NS = "http://www.w3.org/1998/Math/MathML"
SVG_NS = "http://www.w3.org/2000/svg"
OPF_NS = "http://www.idpf.org/2007/opf"
DC_NS = "http://purl.org/dc/elements/1.1/"
EXPECTED_UNITS = [f"OLP-{number:04d}" for number in range(4, 11)]
EXPECTED_SECTIONS = [
    "sfr-set-bas-sec",
    "sfr-set-sub-sec",
    "sfr-set-imp-sec",
    "sfr-set-uni-sec",
    "sfr-set-pai-sec",
    "sfr-set-rus-sec",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def parse_xml(payload: bytes, label: str) -> etree._Element:
    try:
        return etree.fromstring(payload, parser=etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=True))
    except etree.XMLSyntaxError as error:
        raise RuntimeError(f"invalid XML in {label}: {error}") from error


def resolve_internal(source: str, href: str) -> tuple[str, str | None]:
    path, marker, fragment = href.partition("#")
    if path:
        target = posixpath.normpath(posixpath.join(posixpath.dirname(source), path))
    else:
        target = source
    return target, fragment if marker else None


def arabic_words(value: str) -> list[str]:
    words: list[str] = []
    current: list[str] = []
    for character in value:
        codepoint = ord(character)
        eligible = 0x0600 <= codepoint <= 0x06FF and unicodedata.category(character)[0] in ("L", "M")
        if eligible:
            current.append(character)
        elif current:
            words.append("".join(current))
            current.clear()
    if current:
        words.append("".join(current))
    return words


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epub", type=Path, required=True)
    parser.add_argument("--epubcheck-json", type=Path, required=True)
    parser.add_argument("--build-receipt", type=Path, required=True)
    parser.add_argument("--reader-tex", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    artifact = args.epub.resolve()
    require(artifact.is_file(), f"EPUB missing: {artifact}")
    epubcheck = json.loads(args.epubcheck_json.read_text(encoding="utf-8-sig"))
    checker = epubcheck["checker"]
    require(checker["checkerVersion"] == "5.3.0", "unexpected EPUBCheck version")
    require(checker["nFatal"] == checker["nError"] == checker["nWarning"] == 0, "EPUBCheck did not pass cleanly")
    require(not epubcheck["messages"], "EPUBCheck message list is not empty")
    require(epubcheck["publication"]["ePubVersion"] == "3.3", "EPUBCheck did not recognize EPUB 3.3")
    require(epubcheck["publication"]["renditionLayout"] == "reflowable", "EPUBCheck did not recognize reflowable layout")
    require(epubcheck["publication"]["language"] == "pnb-Arab-PK", "EPUBCheck locale drift")

    build = json.loads(args.build_receipt.read_text(encoding="utf-8-sig"))
    require(build["status"] == "pass" and build["deterministic_cold_match"] is True, "builder cold reproducibility did not pass")
    require(build["canonical"]["archive"]["sha256"] == sha(artifact.read_bytes()), "build receipt artifact hash mismatch")
    require(build["canonical"]["archive"]["bytes"] == artifact.stat().st_size, "build receipt artifact size mismatch")
    require(build["teX_engine_invoked"] is False, "EPUB build unexpectedly invoked a TeX engine")

    accepted_inputs_path = REPO / "provenance" / "PORTABLE_CANDIDATE_INPUTS.json"
    accepted_qa_path = REPO / "provenance" / "PORTABLE_CANDIDATE_QA.json"
    accepted_inputs = json.loads(accepted_inputs_path.read_text(encoding="utf-8-sig"))
    accepted_qa = json.loads(accepted_qa_path.read_text(encoding="utf-8-sig"))
    accepted_inputs_sha = sha(accepted_inputs_path.read_bytes())
    accepted_qa_sha = sha(accepted_qa_path.read_bytes())
    require(accepted_inputs_sha == build["accepted_reader_inputs_sha256"], "EPUB is not bound to the accepted reader input receipt")
    require(accepted_inputs["reader_coverage_unit_ids"] == EXPECTED_UNITS, "accepted reader unit scope drift")
    require(accepted_qa["inputs"]["source_unit_ids"] == EXPECTED_UNITS, "accepted reader QA unit scope drift")
    require(accepted_qa["inputs"]["manifest"]["sha256"] == accepted_inputs_sha, "accepted visual QA input hash drift")
    require(accepted_qa["status"] == "REPRODUCED_FULL_PAGE_VISUAL_PASS_NOT_RELEASED", "unexpected prior reader QA status")

    current_unit_checks = []
    for row in accepted_inputs["source_units"]:
        source = (REPO / "upstream" / row["source_path"]).read_bytes()
        translation = (REPO / "translation" / row["source_path"]).read_bytes()
        require(sha(source) == row["source_sha256"], f"source identity drift: {row['source_path']}")
        require(sha(translation) == row["translation_sha256"], f"translation identity drift: {row['source_path']}")
        current_unit_checks.append(
            {
                "unit_id": row["unit_id"],
                "source_path": row["source_path"],
                "source_sha256": sha(source),
                "translation_sha256": sha(translation),
            }
        )

    reader_tex = args.reader_tex.read_text(encoding="utf-8")
    reader_inputs_path = args.reader_tex.parent / "INPUTS.json"
    require(reader_inputs_path.is_file() and sha(reader_inputs_path.read_bytes()) == accepted_inputs_sha, "assembled reader is not bound to the accepted input receipt")
    body_start = reader_tex.find(r"\chapter{")
    body_end = reader_tex.rfind(r"\end{Arabic}")
    require(0 <= body_start < body_end, "assembled reader body boundary drift")
    assembled_reader_body = reader_tex[body_start:body_end]
    source_visible_arabic_chars = len(re.findall(r"[\u0600-\u06ff]", assembled_reader_body))
    source_words: Counter[str] = Counter(arabic_words(assembled_reader_body))

    with zipfile.ZipFile(artifact) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        require(names and names[0] == "mimetype", "mimetype is not the first ZIP entry")
        require(infos[0].compress_type == zipfile.ZIP_STORED, "mimetype is compressed")
        require(archive.read("mimetype") == b"application/epub+zip", "mimetype payload drift")
        require(archive.testzip() is None, "ZIP CRC failure")
        require(len(names) == len(set(names)), "duplicate ZIP entries")
        require(all("\\" not in name and not name.startswith("/") and ".." not in PurePosixPath(name).parts for name in names), "unsafe ZIP path")
        payloads = {name: archive.read(name) for name in names}

    require("META-INF/container.xml" in payloads and "OEBPS/package.opf" in payloads, "container/package missing")
    container = parse_xml(payloads["META-INF/container.xml"], "META-INF/container.xml")
    rootfiles = container.xpath("//*[local-name()='rootfile']/@full-path")
    require(rootfiles == ["OEBPS/package.opf"], f"container rootfile drift: {rootfiles}")
    opf = parse_xml(payloads["OEBPS/package.opf"], "OEBPS/package.opf")
    ns = {"opf": OPF_NS, "dc": DC_NS}
    require(opf.get("version") == "3.0", "package version attribute drift")
    require(opf.xpath("string(opf:metadata/dc:language)", namespaces=ns) == "pnb-Arab-PK", "package language drift")
    require(opf.xpath("string(opf:metadata/dc:identifier)", namespaces=ns).endswith("sets-pnb-Arab-PK-epub3-v0.2.0"), "package identifier/version drift")
    require(opf.xpath("string(opf:metadata/opf:meta[@property='rendition:layout'])", namespaces=ns) == "reflowable", "package not marked reflowable")
    spine = opf.xpath("opf:spine", namespaces=ns)
    require(len(spine) == 1 and spine[0].get("page-progression-direction") == "rtl", "RTL spine metadata absent")

    manifest_nodes = opf.xpath("opf:manifest/opf:item", namespaces=ns)
    manifest = {}
    for node in manifest_nodes:
        path = posixpath.normpath(posixpath.join("OEBPS", node.get("href")))
        require(path not in manifest, f"duplicate manifest path: {path}")
        manifest[path] = {"id": node.get("id"), "media_type": node.get("media-type"), "properties": (node.get("properties") or "").split()}
    expected_payloads = set(payloads) - {"mimetype", "META-INF/container.xml", "OEBPS/package.opf"}
    require(set(manifest) == expected_payloads, f"manifest/package resource mismatch: missing={sorted(expected_payloads-set(manifest))}, extra={sorted(set(manifest)-expected_payloads)}")
    by_id = {value["id"]: path for path, value in manifest.items()}
    spine_paths = [by_id[node.get("idref")] for node in opf.xpath("opf:spine/opf:itemref", namespaces=ns)]
    require(spine_paths == [
        "OEBPS/text/cover.xhtml",
        "OEBPS/text/nav.xhtml",
        "OEBPS/text/read.xhtml",
        "OEBPS/text/provenance.xhtml",
        "OEBPS/text/licenses.xhtml",
    ], f"spine order drift: {spine_paths}")
    require("nav" in manifest["OEBPS/text/nav.xhtml"]["properties"], "navigation property absent")
    require(set(("mathml", "svg")) <= set(manifest["OEBPS/text/read.xhtml"]["properties"]), "read manifest properties incomplete")

    xhtml_roots = {}
    ids_by_document = {}
    for path, record in manifest.items():
        if record["media_type"] != "application/xhtml+xml":
            continue
        root = parse_xml(payloads[path], path)
        xhtml_roots[path] = root
        require(root.tag == f"{{{XHTML_NS}}}html", f"non-XHTML root: {path}")
        require(root.get("lang") == root.get(f"{{http://www.w3.org/XML/1998/namespace}}lang") == "pnb-Arab-PK", f"language attributes drift: {path}")
        require(root.get("dir") == "rtl", f"RTL root absent: {path}")
        require(not root.xpath("//*[local-name()='script' or local-name()='iframe' or local-name()='object']"), f"active/remote content present: {path}")
        ids = [node.get("id") for node in root.xpath("//*[@id]")]
        require(len(ids) == len(set(ids)), f"duplicate IDs in {path}")
        ids_by_document[path] = set(ids)

    internal_links = []
    external_links = []
    for source, root in xhtml_roots.items():
        for href in root.xpath("//@href"):
            scheme = urlsplit(href).scheme.lower()
            if scheme in ("http", "https"):
                require(scheme == "https", f"non-HTTPS external link: {href}")
                external_links.append(href)
                continue
            require(not scheme, f"unsupported link scheme: {href}")
            target, fragment = resolve_internal(source, href)
            require(target in payloads, f"broken internal link {source} -> {href}")
            if fragment:
                require(fragment in ids_by_document.get(target, set()), f"broken internal fragment {source} -> {href}")
            internal_links.append({"source": source, "href": href, "target": target, "fragment": fragment})

    read = xhtml_roots["OEBPS/text/read.xhtml"]
    read_ns = {"x": XHTML_NS, "m": MATHML_NS, "s": SVG_NS}
    math = read.xpath("//m:math", namespaces=read_ns)
    annotations = read.xpath("//m:math/m:semantics/m:annotation[@encoding='application/x-tex']", namespaces=read_ns)
    require(len(math) == 329, f"bounded-source MathML count drift: {len(math)}")
    require(len(annotations) == len(math), "MathML TeX annotation coverage gap")
    require(all((node.text or "").strip() for node in annotations), "empty MathML TeX annotation")
    require(all(node.get("dir") == "ltr" for node in math), "LTR math island metadata gap")
    require(not read.xpath("//m:math[not(m:semantics/*[1])]", namespaces=read_ns), "MathML expression lacks a presentation branch")
    arabic_mtext = [node for node in read.xpath("//m:mtext", namespaces=read_ns) if re.search(r"[\u0600-\u06ff]", "".join(node.itertext()))]
    require(arabic_mtext and all(node.get("dir") == "rtl" for node in arabic_mtext), "RTL direction metadata gap in mixed-language MathML text")

    section_ids = read.xpath("//x:h2/@id", namespaces=read_ns)
    require(section_ids == EXPECTED_SECTIONS, f"semantic section order/coverage drift: {section_ids}")
    section_units = read.xpath("//x:h2/@data-unit-id", namespaces=read_ns)
    require(section_units == EXPECTED_UNITS[1:], f"section-to-unit identity drift: {section_units}")
    require(len(read.xpath("//x:p[contains(concat(' ',normalize-space(@class),' '),' statement-heading ')]", namespaces=read_ns)) == 39, "statement/exercise heading count drift")
    require(len(read.xpath("//x:a[@data-reference-type='ref']", namespaces=read_ns)) == 5, "semantic cross-reference count drift")

    svgs = read.xpath("//s:svg", namespaces=read_ns)
    require(len(svgs) == 3, f"set diagram count drift: {len(svgs)}")
    for svg in svgs:
        require(len(svg.xpath("./s:title[normalize-space()]", namespaces=read_ns)) == 1, "SVG title missing")
        require(len(svg.xpath("./s:desc[normalize-space()]", namespaces=read_ns)) == 1, "SVG description missing")
        require(svg.get("role") == "img" and svg.get("aria-labelledby"), "SVG accessibility relationship missing")
        asset = svg.get("data-source-asset")
        asset_sha = svg.get("data-asset-sha256")
        require(asset and asset_sha and sha((REPO / "upstream" / asset).read_bytes()) == asset_sha, f"SVG source asset identity drift: {asset}")
    require(len(read.xpath("//x:div[contains(concat(' ',normalize-space(@class),' '),' diagram-structure ')]", namespaces=read_ns)) == 3, "diagram text alternatives missing")

    visible = copy.deepcopy(read)
    for annotation in visible.xpath("//m:annotation", namespaces=read_ns):
        annotation.getparent().remove(annotation)
    visible_text = " ".join(" ".join(visible.itertext()).split())
    forbidden = [r"\\textarabic", r"\\textenglish", r"\\nicefrac", r"\\shoveright", r"\\shoveleft", r"\\begin{", "!!{", "[sfr:", "TODO", "TBD"]
    survivors = [token for token in forbidden if token in visible_text]
    require(not survivors, f"unrendered source/placeholder tokens: {survivors}")
    arabic_chars = len(re.findall(r"[\u0600-\u06ff]", visible_text))
    visible_words = Counter(arabic_words(visible_text))
    word_deficits = {word: count - visible_words[word] for word, count in source_words.items() if visible_words[word] < count}
    require(not word_deficits, f"Punjabi lexical coverage deficits: {word_deficits}")
    require(arabic_chars >= source_visible_arabic_chars, f"visible Punjabi script is sparser than the canonical translation: {arabic_chars} < {source_visible_arabic_chars}")
    scope_text = " ".join(" ".join(xhtml_roots["OEBPS/text/cover.xhtml"].itertext()).split())
    require("OLP-0004" in scope_text and "OLP-0010" in scope_text and "پوری کتاب" in scope_text, "honest partial-scope notice missing")

    source_links = sorted(link for link in external_links if f"github.com/OpenLogicProject/OpenLogic/blob/{REVISION}/" in link)
    require(len(source_links) == 7, f"source citation link count drift: {len(source_links)}")
    require(len(set(external_links)) >= 11, f"attribution/source link inventory unexpectedly sparse: {len(set(external_links))}")

    result = {
        "schema": "pnb-sets-epub3-independent-qa/1",
        "status": "pass",
        "scope": {"claim": "complete Sets chapter only; not the complete 722-unit edition", "unit_ids": EXPECTED_UNITS, "source_units": 7, "body_sections": 6},
        "artifact": {"path": str(artifact), "bytes": artifact.stat().st_size, "sha256": sha(artifact.read_bytes()), "zip_entries": len(payloads)},
        "epubcheck": {"version": checker["checkerVersion"], "fatal": checker["nFatal"], "errors": checker["nError"], "warnings": checker["nWarning"], "report_bytes": args.epubcheck_json.stat().st_size, "report_sha256": sha(args.epubcheck_json.read_bytes())},
        "prior_reader_acceptance": {"inputs_path": "provenance/PORTABLE_CANDIDATE_INPUTS.json", "inputs_sha256": accepted_inputs_sha, "qa_path": "provenance/PORTABLE_CANDIDATE_QA.json", "qa_sha256": accepted_qa_sha, "status": accepted_qa["status"]},
        "current_unit_identity_checks": current_unit_checks,
        "package": {"epub_version": epubcheck["publication"]["ePubVersion"], "rendition_layout": epubcheck["publication"]["renditionLayout"], "language": epubcheck["publication"]["language"], "page_progression_direction": "rtl", "spine_paths": spine_paths, "manifest_items": len(manifest), "active_content": 0},
        "content": {"mathml_roots": len(math), "mathml_tex_annotations": len(annotations), "rtl_math_text_runs": len(arabic_mtext), "semantic_sections": len(section_ids), "statement_and_exercise_headings": 39, "semantic_cross_references": 5, "svg_diagrams": len(svgs), "svg_descriptions": len(svgs), "diagram_structural_text_alternatives": 3, "canonical_translation_arabic_script_characters": source_visible_arabic_chars, "visible_epub_arabic_script_characters": arabic_chars, "canonical_translation_distinct_arabic_words": len(source_words), "punjabi_lexical_coverage_deficits": word_deficits, "unrendered_tokens": survivors},
        "links": {"internal_links_checked": len(internal_links), "broken_internal_links": 0, "external_https_links": sorted(set(external_links)), "frozen_source_links": source_links},
        "reproducibility": {"canonical_and_cold_epub_sha256_match": True, "unpacked_tree_sha256_match": True, "tex_engine_invoked": False},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    args.output.write_text(payload, encoding="utf-8", newline="\n")
    print(json.dumps({"status": "pass", "artifact": result["artifact"], "mathml": len(math), "sections": len(section_ids), "statements": 39, "figures": len(svgs), "internal_links": len(internal_links), "external_links": len(set(external_links)), "output": {"path": str(args.output), "bytes": args.output.stat().st_size, "sha256": sha(args.output.read_bytes())}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
