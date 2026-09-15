"""Add the exact accepted cumulative TeX masters to the v0.2.0 source package.

This is a narrow packaging correction. It preserves every byte and entry from
the published editable ZIP, adds the two masters and their accepted build
receipts, builds twice deterministically, and invokes no TeX engine.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
STATE = Path(r"C:\interlanguage-task-state\openlogic-pnb-Arab-PK")
RELEASE = REPO / "output" / "release-v0.2.0"
BUILD = STATE / "work" / "checkpoint-0010-build"
LEGACY = RELEASE / "OpenLogic-Sets-Punjabi-Shahmukhi-editable-v0.2.0.zip"
OUTPUT = RELEASE / "OpenLogic-Sets-Punjabi-Shahmukhi-reproducible-source-v0.2.0.zip"
RECEIPT = REPO / "provenance" / "SETS_REPRODUCIBLE_SOURCE_QA.json"
COLD = STATE / "work" / "sets-source-correction-v020" / "cold.zip"
FIXED_ZIP_TIME = (2026, 9, 15, 0, 0, 0)

EXPECTED = {
    "legacy": (2173252, "92e27880ff2a48d33d19e03c85723a150875a0e5f9deeadbcf037fa7bdf98af0"),
    "naskh_pdf": (136127, "1e3f2fa2413534872123995b7128ee64ed37e42a51a21eb13621ddca59b9a313"),
    "nastaliq_pdf": (192407, "c4239acb125435c4fb756ebae514f6ec3136c1c4c2fdae756d0612e9a70b7ff7"),
    "naskh_master": (42256, "dacae70b697d38570ea354781f8c4d43eb501b07b10e9d6dd82ff525bd3babad"),
    "nastaliq_master": (42291, "a910a168e9d4b1a2101318d4f0d121e438af0a9246d49b46df43a8c5d2746335"),
    "inputs": (29715, "86406d66d07836d6b5eb498d6b80828d1d5ad13d09f83d215f266826c766791b"),
    "build_receipt": (2713, "f37815dcd736256a7d58f99432e53ec09a5bfc2291df2eb5689e52e4a45bdfeb"),
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def identity(path: Path, name: str | None = None) -> dict:
    payload = path.read_bytes()
    return {"name": name or path.name, "bytes": len(payload), "sha256": sha(payload)}


def require_identity(path: Path, key: str) -> dict:
    actual = identity(path)
    expected_bytes, expected_sha = EXPECTED[key]
    require(
        (actual["bytes"], actual["sha256"]) == (expected_bytes, expected_sha),
        f"{key} identity drift: {actual}",
    )
    return actual


def write_zip(destination: Path, entries: dict[str, bytes]) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.unlink()
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(entries):
            require(not name.startswith("/") and ".." not in Path(name).parts, f"unsafe entry: {name}")
            info = zipfile.ZipInfo(name, date_time=FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.flag_bits |= 0x800
            archive.writestr(info, entries[name], compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    with zipfile.ZipFile(destination) as archive:
        require(archive.testzip() is None, f"ZIP CRC failure: {destination}")
        require(archive.namelist() == sorted(entries), f"ZIP order drift: {destination}")


def main() -> None:
    legacy_identity = require_identity(LEGACY, "legacy")
    naskh_pdf = require_identity(RELEASE / "OpenLogic-Sets-Punjabi-Shahmukhi-Naskh-v0.2.0.pdf", "naskh_pdf")
    nastaliq_pdf = require_identity(RELEASE / "OpenLogic-Sets-Punjabi-Shahmukhi-Nastaliq-v0.2.0.pdf", "nastaliq_pdf")

    added_paths = {
        "reader/accepted-v0.2.0/sets-naskh.tex": (BUILD / "sets-naskh.tex", "naskh_master"),
        "reader/accepted-v0.2.0/sets-nastaliq.tex": (BUILD / "sets-nastaliq.tex", "nastaliq_master"),
        "reader/accepted-v0.2.0/INPUTS.json": (BUILD / "INPUTS.json", "inputs"),
        "reader/accepted-v0.2.0/BUILD_RECEIPT.json": (BUILD / "BUILD_RECEIPT.json", "build_receipt"),
        "reader/ACCEPTED_MASTERS_v0.2.0.md": (REPO / "reader" / "ACCEPTED_MASTERS_v0.2.0.md", None),
        "tools/prepare_sets_v020_source_correction.py": (Path(__file__).resolve(), None),
    }
    added = []
    for name, (path, expected_key) in added_paths.items():
        require(path.is_file(), f"added package input missing: {path}")
        record = require_identity(path, expected_key) if expected_key else identity(path)
        record["name"] = name
        added.append(record)

    with zipfile.ZipFile(LEGACY) as archive:
        require(archive.testzip() is None, "legacy editable ZIP CRC failure")
        legacy_names = archive.namelist()
        require(len(legacy_names) == 50 and len(set(legacy_names)) == 50, "legacy entry inventory drift")
        require(legacy_names == sorted(legacy_names), "legacy entry order drift")
        require(not any(name.startswith("reader/accepted-v0.2.0/") for name in legacy_names), "legacy ZIP unexpectedly contains accepted masters")
        entries = {name: archive.read(name) for name in legacy_names}
    legacy_entry_hashes = {name: sha(payload) for name, payload in entries.items()}
    for name, (path, _) in added_paths.items():
        require(name not in entries, f"new entry collides with legacy entry: {name}")
        entries[name] = path.read_bytes()

    write_zip(OUTPUT, entries)
    if COLD.exists():
        COLD.unlink()
    write_zip(COLD, entries)
    output_identity = identity(OUTPUT)
    cold_identity = identity(COLD)
    require(output_identity == {**cold_identity, "name": OUTPUT.name}, "deterministic cold archive mismatch")

    with zipfile.ZipFile(OUTPUT) as archive:
        require(archive.testzip() is None, "corrected package CRC failure")
        require(len(archive.namelist()) == 56, "corrected package entry count drift")
        for name, expected_sha in legacy_entry_hashes.items():
            require(sha(archive.read(name)) == expected_sha, f"legacy entry changed: {name}")
        for record in added:
            require(sha(archive.read(record["name"])) == record["sha256"], f"added entry changed: {record['name']}")

    inputs = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8-sig"))
    build_receipt = json.loads((BUILD / "BUILD_RECEIPT.json").read_text(encoding="utf-8-sig"))
    require(inputs["reader_coverage_unit_ids"] == [f"OLP-{number:04d}" for number in range(4, 11)], "accepted input scope drift")
    require(inputs["body_sections"] == 6 and inputs["chapter_driver_count"] == 1, "accepted cumulative topology drift")
    final_processes = {row["profile"]: row for row in build_receipt["processes"] if row.get("reproduced") is True}
    require(final_processes["naskh"]["pdf_sha256"] == naskh_pdf["sha256"], "Naskh master/PDF binding drift")
    require(final_processes["nastaliq"]["pdf_sha256"] == nastaliq_pdf["sha256"], "Nastaliq master/PDF binding drift")

    receipt = {
        "schema": "pnb-sets-reproducible-source-qa/1",
        "status": "pass",
        "version": "0.2.0",
        "scope": {
            "claim": "complete Sets chapter only; not the complete 722-unit OpenLogic edition",
            "unit_ids": [f"OLP-{number:04d}" for number in range(4, 11)],
            "source_units": 7,
            "sections": 6,
        },
        "legacy_package": {**legacy_identity, "preserved_unchanged": True, "entries": 50},
        "corrected_package": {**output_identity, "entries": 56, "deterministic_cold_match": True},
        "added_entries": added,
        "legacy_entry_bytes_preserved": 50,
        "accepted_pdf_bindings": {"naskh": naskh_pdf, "nastaliq": nastaliq_pdf},
        "checks": {
            "both_actual_accepted_cumulative_masters_present": True,
            "accepted_inputs_and_build_receipt_present": True,
            "preamble_not_misrepresented_as_master": True,
            "crc": "pass",
            "safe_paths": "pass",
            "tex_engine_invoked": False,
        },
        "limits": [
            "The archived accepted master bytes retain the original acceptance-build relative paths.",
            "Use the included generator for a relocatable rebuild; different TeX installations require fresh visual QA.",
            "The package covers OLP-0004 through OLP-0010 only and does not claim a complete 722-unit reader.",
        ],
    }
    RECEIPT.write_text(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": "pass", "package": output_identity, "receipt": identity(RECEIPT), "entries": 56}, indent=2))


if __name__ == "__main__":
    main()
