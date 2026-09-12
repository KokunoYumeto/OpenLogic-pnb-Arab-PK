"""Prepare the narrowly scoped, validated Sets EPUB/PDF v0.2.0 release.

The script performs no network action and invokes no TeX engine.  It refuses to
package bytes not identified by the accepted PDF, EPUB, runtime, link and visual
receipts.  Public receipts replace local absolute prefixes with stable labels.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
STATE = Path(r"C:\interlanguage-task-state\openlogic-pnb-Arab-PK")
EPUB_WORK = STATE / "work" / "sets-epub-v020"
PDF_WORK = STATE / "work" / "checkpoint-0010-build"
OUTPUT = REPO / "output" / "release-v0.2.0"
PROVENANCE = REPO / "provenance"
VERSION = "0.2.0"
FIXED_ZIP_TIME = (2026, 9, 13, 0, 0, 0)
UNITS = [f"OLP-{number:04d}" for number in range(4, 11)]

EPUB_NAME = "OpenLogic-Sets-Punjabi-Shahmukhi-v0.2.0.epub"
PDF_NAMES = {
    "naskh": "OpenLogic-Sets-Punjabi-Shahmukhi-Naskh-v0.2.0.pdf",
    "nastaliq": "OpenLogic-Sets-Punjabi-Shahmukhi-Nastaliq-v0.2.0.pdf",
}

RECEIPTS = {
    "BUILD_RECEIPT.json": "SETS_EPUB_BUILD_RECEIPT.json",
    "EPUBCHECK.json": "SETS_EPUB_EPUBCHECK.json",
    "INDEPENDENT_QA.json": "SETS_EPUB_INDEPENDENT_QA.json",
    "EPUB_RUNTIME_ACCEPTANCE.json": "SETS_EPUB_RUNTIME_ACCEPTANCE.json",
    "EXTERNAL_LINK_QA.json": "SETS_EPUB_EXTERNAL_LINK_QA.json",
    "VISUAL_REVIEW.json": "SETS_EPUB_VISUAL_REVIEW.json",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")


def identity(path: Path, name: str | None = None) -> dict:
    payload = path.read_bytes()
    return {"name": name or path.name, "bytes": len(payload), "sha256": sha(payload)}


def sanitized(value: object) -> object:
    if isinstance(value, dict):
        return {key: sanitized(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitized(item) for item in value]
    if isinstance(value, str):
        result = value
        substitutions = (
            (str(STATE.resolve()) + "\\", "durable-state/"),
            (str(STATE.resolve()).replace("\\", "/") + "/", "durable-state/"),
            (str(REPO.resolve()) + "\\", "repository/"),
            (str(REPO.resolve()).replace("\\", "/") + "/", "repository/"),
        )
        for old, new in substitutions:
            result = result.replace(old, new)
        return result.replace("\\", "/") if result.startswith(("durable-state/", "repository/")) else result
    return value


def reset_output() -> None:
    resolved = OUTPUT.resolve()
    expected_parent = (REPO / "output").resolve()
    require(resolved.parent == expected_parent and resolved.name == "release-v0.2.0", f"unsafe release output path: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True)


def deterministic_zip(destination: Path, files: list[tuple[Path, str]]) -> dict:
    if destination.exists():
        destination.unlink()
    seen = set()
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source, name in sorted(files, key=lambda item: item[1]):
            require(source.is_file(), f"ZIP input missing: {source}")
            require(name not in seen and not name.startswith("/") and ".." not in Path(name).parts, f"unsafe or duplicate ZIP entry: {name}")
            seen.add(name)
            info = zipfile.ZipInfo(name.replace("\\", "/"), date_time=FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.flag_bits |= 0x800
            archive.writestr(info, source.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    with zipfile.ZipFile(destination) as archive:
        require(archive.testzip() is None, f"ZIP CRC failure: {destination.name}")
        require(archive.namelist() == sorted(archive.namelist()), f"ZIP entry order drift: {destination.name}")
    record = identity(destination)
    record["entries"] = len(files)
    return record


def main() -> None:
    reset_output()
    raw_receipts = {name: read_json(EPUB_WORK / name) for name in RECEIPTS}
    build = raw_receipts["BUILD_RECEIPT.json"]
    independent = raw_receipts["INDEPENDENT_QA.json"]
    runtime = raw_receipts["EPUB_RUNTIME_ACCEPTANCE.json"]
    links = raw_receipts["EXTERNAL_LINK_QA.json"]
    visual = raw_receipts["VISUAL_REVIEW.json"]
    epubcheck = raw_receipts["EPUBCHECK.json"]
    artifact = EPUB_WORK / EPUB_NAME
    artifact_identity = identity(artifact)
    require(build["status"] == "pass" and build["deterministic_cold_match"] is True, "EPUB deterministic build not accepted")
    require(independent["status"] == runtime["status"] == links["status"] == visual["status"] == "pass", "one or more EPUB acceptance gates did not pass")
    require(epubcheck["checker"]["nFatal"] == epubcheck["checker"]["nError"] == epubcheck["checker"]["nWarning"] == 0, "EPUBCheck did not pass cleanly")
    expected_epub_hashes = {
        build["canonical"]["archive"]["sha256"],
        independent["artifact"]["sha256"],
        runtime["input"]["epub_sha256"],
        visual["artifact"]["sha256"],
        artifact_identity["sha256"],
    }
    require(len(expected_epub_hashes) == 1, f"EPUB identity disagreement: {expected_epub_hashes}")
    require(independent["scope"]["unit_ids"] == UNITS, "EPUB scope drift")
    require(independent["content"]["mathml_roots"] == 329 and independent["content"]["punjabi_lexical_coverage_deficits"] == {}, "EPUB math/content gate drift")
    require(runtime["failures"] == [] and runtime["network"]["external_request_attempts"] == [], "EPUB runtime gate drift")
    require(links["links_checked"] == 11 and links["links_failed"] == 0, "external link gate drift")

    portable_qa_path = PROVENANCE / "PORTABLE_CANDIDATE_QA.json"
    portable_qa = read_json(portable_qa_path)
    require(portable_qa["status"] == "REPRODUCED_FULL_PAGE_VISUAL_PASS_NOT_RELEASED", "portable PDF QA status drift")
    require(portable_qa["inputs"]["source_unit_ids"] == UNITS, "portable PDF scope drift")

    shutil.copyfile(artifact, OUTPUT / EPUB_NAME)
    release_files = [identity(OUTPUT / EPUB_NAME)]
    pdf_records = []
    for profile, name in PDF_NAMES.items():
        source = PDF_WORK / f"sets-{profile}.pdf"
        expected = portable_qa["profiles"][profile]
        actual = identity(source, name)
        require(actual["bytes"] == expected["bytes"] and actual["sha256"] == expected["sha256"], f"{profile} PDF identity drift")
        require(expected["reproduced"] is True and expected["all_fonts_embedded"] is True, f"{profile} PDF acceptance drift")
        shutil.copyfile(source, OUTPUT / name)
        actual["pages"] = expected["pages"]
        actual["profile"] = profile
        pdf_records.append(actual)
        release_files.append(identity(OUTPUT / name))

    public_receipts = []
    for source_name, public_name in RECEIPTS.items():
        destination = PROVENANCE / public_name
        write_json(destination, sanitized(raw_receipts[source_name]))
        public_receipts.append(identity(destination, f"provenance/{public_name}"))

    aggregate = {
        "schema": "pnb-sets-reader-release-qa/2",
        "status": "accepted_for_publication",
        "version": VERSION,
        "scope": {
            "claim": "complete Sets chapter only; not the complete 722-unit OpenLogic edition",
            "unit_ids": UNITS,
            "source_units": 7,
            "sections": 6,
            "source_revision": "9620cc73f9c8e0ad003c514a5d3748f29611c4c0",
        },
        "reader_files": {"epub": artifact_identity, "pdfs": pdf_records},
        "epub_checks": {
            "genuine_epub_version": "3.3",
            "rendition_layout": "reflowable",
            "language": "pnb-Arab-PK",
            "rtl_spine_and_documents": True,
            "deterministic_cold_byte_match": True,
            "epubcheck_5_3_0": {"fatals": 0, "errors": 0, "warnings": 0, "infos": 0},
            "native_mathml_roots": 329,
            "mathml_tex_annotations": 329,
            "rtl_math_text_runs": independent["content"]["rtl_math_text_runs"],
            "statement_and_exercise_headings": 39,
            "svg_diagrams_with_text_alternatives": 3,
            "internal_links_checked": 30,
            "external_https_links_checked_anonymously": 11,
            "runtime_spine_documents_loaded": 5,
            "representative_runtime_renders_visually_reviewed": 6,
            "unrendered_tokens": 0,
            "punjabi_lexical_coverage_deficits": 0,
            "tex_engine_invoked_for_epub": False,
        },
        "pdf_checks": {
            "naskh_pages": 12,
            "nastaliq_pages": 17,
            "all_29_pages_visually_inspected": True,
            "same_toolchain_byte_reproduction": True,
            "all_fonts_embedded": True,
            "tagged_pdf": False,
        },
        "evidence": public_receipts + [identity(portable_qa_path, "provenance/PORTABLE_CANDIDATE_QA.json")],
        "limits": [
            "Specialized terminology remains provisional and lacks independent native-speaker review.",
            "Only the complete Sets chapter has integrated reader acceptance; later chapters receive no release credit here.",
            "MathML rendering varies by reading system; bounded automated and representative visual checks are not an all-device or human accessibility certification.",
            "The PDFs are not tagged accessible PDFs.",
        ],
    }
    aggregate_path = PROVENANCE / "SETS_EPUB_RELEASE_QA.json"
    write_json(aggregate_path, aggregate)
    public_receipts.append(identity(aggregate_path, "provenance/SETS_EPUB_RELEASE_QA.json"))

    qa_files = [(PROVENANCE / Path(record["name"]).name, record["name"]) for record in public_receipts]
    qa_files.extend(
        [
            (PROVENANCE / "PORTABLE_CANDIDATE_INPUTS.json", "provenance/PORTABLE_CANDIDATE_INPUTS.json"),
            (PROVENANCE / "PORTABLE_CANDIDATE_QA.json", "provenance/PORTABLE_CANDIDATE_QA.json"),
        ]
    )
    qa_zip_name = "OpenLogic-Sets-Punjabi-Shahmukhi-QA-v0.2.0.zip"
    qa_zip = deterministic_zip(OUTPUT / qa_zip_name, qa_files)
    release_files.append(qa_zip)

    accepted_inputs = read_json(PROVENANCE / "PORTABLE_CANDIDATE_INPUTS.json")
    source_paths = [row["source_path"] for row in accepted_inputs["source_units"]]
    asset_paths = [row["source_path"] for row in accepted_inputs["assets"]]
    editable_paths = [
        "README.md",
        "LICENSE.md",
        ".gitattributes",
        ".gitignore",
        "RELEASE_NOTES_v0.2.0.md",
        "reader/sets-preamble.tex",
        "fonts/NOTICE.md",
        "fonts/OFL.txt",
        "fonts/NotoNaskhArabic-Regular.ttf",
        "fonts/NotoNaskhArabic-Bold.ttf",
        "fonts/NotoNastaliqUrdu-Regular.ttf",
        "fonts/NotoSerif-Regular.ttf",
        "fonts/NotoSerif-Bold.ttf",
        "fonts/NotoSerif-Italic.ttf",
        "fonts/NotoSerif-BoldItalic.ttf",
        "tools/build_sets_reader.py",
        "tools/build_reader.ps1",
        "tools/build_sets_epub.py",
        "tools/audit_sets_epub.py",
        "tools/accept_sets_epub_runtime.mjs",
        "tools/check_epub_external_links.py",
        "tools/prepare_sets_v020_release.py",
        "tools/verify_source_identity.py",
        "provenance/SOURCE_MANIFEST.jsonl",
        "provenance/PORTABLE_CANDIDATE_INPUTS.json",
        "provenance/PORTABLE_CANDIDATE_QA.json",
        "provenance/SETS_EPUB_RELEASE_QA.json",
    ]
    editable_paths.extend(f"upstream/{path}" for path in source_paths + asset_paths)
    editable_paths.extend(f"translation/{path}" for path in source_paths)
    editable_paths.extend(record["name"] for record in public_receipts if record["name"] != "provenance/SETS_EPUB_RELEASE_QA.json")
    editable_files = [(REPO / path, path) for path in sorted(set(editable_paths))]
    for source, name in editable_files:
        require(source.is_file(), f"editable-source input missing: {name}")
        if source.suffix.lower() in {".md", ".json", ".jsonl", ".tex", ".py", ".ps1", ".mjs", ".txt"}:
            text = source.read_text(encoding="utf-8-sig")
            profile_markers = ("C:" + "\\Users\\", "C:/" + "Users/")
            credential_markers = ("ghp" + "_", "github" + "_pat_", "ZENODO" + "_TOKEN")
            require(not any(marker in text for marker in profile_markers), f"user-profile path rejected from public source: {name}")
            require(not any(marker in text for marker in credential_markers), f"credential-like text rejected from public source: {name}")
    editable_name = "OpenLogic-Sets-Punjabi-Shahmukhi-editable-v0.2.0.zip"
    editable_zip = deterministic_zip(OUTPUT / editable_name, editable_files)
    release_files.append(editable_zip)

    sums_path = OUTPUT / "SHA256SUMS.txt"
    sums_path.write_text("".join(f"{row['sha256']}  {row['name']}\n" for row in sorted(release_files, key=lambda row: row["name"])), encoding="utf-8", newline="\n")
    sums = identity(sums_path)
    release_files.append(sums)
    manifest = {
        "schema": "pnb-sets-v020-release-manifest/1",
        "status": "accepted_for_publication",
        "version": VERSION,
        "scope": "complete Sets chapter OLP-0004 through OLP-0010 only; 7 of 722 source units",
        "files": sorted(release_files, key=lambda row: row["name"]),
        "primary_preview": PDF_NAMES["naskh"],
        "release_notes": "RELEASE_NOTES_v0.2.0.md",
        "aggregate_qa": identity(aggregate_path, "provenance/SETS_EPUB_RELEASE_QA.json"),
    }
    manifest_path = OUTPUT / "RELEASE_MANIFEST.json"
    write_json(manifest_path, manifest)
    print(json.dumps({"status": "accepted_for_publication", "scope_units": len(UNITS), "files": manifest["files"], "manifest": identity(manifest_path)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
