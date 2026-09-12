# OpenLogic in Punjabi Shahmukhi

پنجابی شاہ مکھی وچ اوپن لاجک

Independent machine translation and layout adaptation by Codex of **The Open Logic Project**. This is an ongoing full-edition project for `pnb-Arab-PK`, not an official upstream edition or an endorsed translation.

The latest bounded reader release, **v0.2.0**, makes the complete Sets chapter downloadable as a genuine reflowable EPUB 3 with native MathML, RTL metadata, embedded Naskh fonts, accessible set diagrams and exact source identities. It also includes visually accepted Naskh and Nastaliq PDFs. This remains a seven-unit chapter release, not the complete 722-unit edition.

> **Canon-revalidation notice (2026-09-08):** The 74 translated units on the historical checkpoint and the immutable v0.1.0/Zenodo artifacts remain available for provenance, but only the repaired contiguous prefix is currently semantically accepted. That prefix now covers OLP-0001–OLP-0019: 313/313 choice groups, comprising 114 formal invariants and 199 explicit reversible supported-provisional choices, with zero unsupported, needs-revision, contentious, or validation-error rows. This closes the Sets and Relations chapter tranche; forward translation remains frozen while repair continues at OLP-0020. This is a prefix result, not a corpus-success claim. See [the full notice](provenance/CANON_REVALIDATION_NOTICE.md) and [the repair ledger](provenance/SEMANTIC_REPAIR_CHOICES.jsonl).

## Current scope

The v0.2.0 reader tranche is the **complete Sets chapter**: seven source units, six sections, three original diagrams, definitions, proofs and exercises. It is not the whole book. The immutable v0.1.0 release remains available as the earlier PDF/source snapshot; v0.2.0 supersedes it for reading this chapter because it uses the semantically repaired Sets text and adds EPUB. The repository snapshot contains 74 source-aligned translations, leaving 648 of the frozen 722-unit inventory; later chapters remain outside this reader release. The public canon-revalidation checkpoint represented here covers OLP-0001–OLP-0019, including the complete Sets and Relations chapter tranche. Only Sets has an integrated visually accepted reader in both PDF and EPUB form. See `provenance/CURRENT_MAIN_QA.json` for the source-coverage, semantic-acceptance and release distinctions.

The chapter covers extensionality, subsets and power sets, important sets, unions and intersections, ordered pairs and products, and Russell's paradox. Both Naskh and Nastaliq reading profiles are provided. Punjabi prose is right-to-left; mathematical expressions preserve left-to-right order.

## Read and inspect

Release files include the reflowable EPUB, both PDF profiles, a bounded editable-source ZIP, a QA-evidence ZIP and a SHA-256 inventory. See `provenance/SETS_EPUB_RELEASE_QA.json` for exact accepted bytes, source coverage, EPUBCheck, content/link/runtime checks and representative visual review. The entire English source is preserved in `upstream/`; translated source is separate in `translation/`. Git text normalization is disabled for `upstream/**`, so all 722 public source blobs retain the manifest-addressed bytes. `provenance/UPSTREAM-EOL-REPAIR.json` records the one-time repair of 84 historical newline-only Git representations and the staged 722/722 verification.

- [Download the v0.2.0 EPUB](https://github.com/KokunoYumeto/OpenLogic-pnb-Arab-PK/releases/download/v0.2.0/OpenLogic-Sets-Punjabi-Shahmukhi-v0.2.0.epub)
- [Inspect the complete v0.2.0 release](https://github.com/KokunoYumeto/OpenLogic-pnb-Arab-PK/releases/tag/v0.2.0)

- [Original project](https://openlogicproject.org/) and [contributors](https://openlogicproject.org/people/)
- [Frozen source revision](https://github.com/OpenLogicProject/OpenLogic/tree/9620cc73f9c8e0ad003c514a5d3748f29611c4c0)
- [OpenLogic translations hub](https://github.com/KokunoYumeto/OpenLogic-translations)

## Evidence and limitations

This is model-authored and model-reviewed translation. It has not received independent native-speaker review; no such review is claimed. Historical source-aligned semantic checks and reverse-paraphrase samples remain provenance evidence, but the independent canon revalidation supersedes their acceptance claims. The repair lane records an exact source/target group, exact narrowly scoped passages, alternatives, justification, confidence, and a precise review question for each language-bearing choice. Human feedback can inform later revisions but is not a hold.

No current global benefit or priority rank is claimed. The 722-unit denominator measures frozen-source coverage only, not audience size or learning effect, and a census label such as “Punjabi” is not treated as an exact Shahmukhi readership denominator. Any future catch-up, foundational, pronunciation or oral companion must have its own manifest and receives no credit toward this corpus.

`provenance/TERMINOLOGY_REVIEW_LOG.jsonl` gives exact units, structural sections, source/target files and line ranges, current choices, `pnb-Arab-PK` Shahmukhi identity, evidence actually checked, retrospective alternatives, confidence/priority status and precise questions for asynchronous expert review. The [translation-decision package](provenance/translation-decisions/START_HERE.md) projects that reversible ledger into the shared OpenLogic schema as a readable complete index, priority-only view, one-row-per-occurrence CSV and canonical machine JSON. Reader pages are recorded only for a public artifact whose text is byte-identical to the current repaired source. The historical v0.1.0 page map is therefore not reused, and all current page locators remain explicitly pending. `provenance/SOURCE_CORRECTIONS.jsonl` separately records upstream wording/mathematical corrections by stable finding ID. These logs cover translated material only and do not imply review or completion of the untranslated remainder. Provisional choices stay open to correction; expert response is not a publication hold.

The acquired scholarly Punjabi sources support native academic syntax and the disciplinary names for logic and mathematics. Revision-bound Western Punjabi Wikipedia pages additionally evidence actual community Shahmukhi mathematical/logic usage, but are **not peer-reviewed scholarly canon**. Neither class of source establishes most specialized set-theory terminology. Such terms remain explicit, reversible, definition- or source-governed provisional decisions, with English bridges where convention is unproven. Original restricted canon HTML/PDF files are not redistributed. Wikipedia excerpts and metadata retain their recorded CC BY-SA 4.0 terms; other public provenance is limited to links, exact hashes, precise locators, brief quotations and explanatory records.

The PDFs are not tagged accessible PDFs. The EPUB is reflowable, script-free and validated as EPUB 3.3; it uses native presentation MathML with TeX annotations and text alternatives for all three diagrams. Reading-system MathML support varies, and the checks are not a human accessibility certification. Full-book reader integration and the 80 units outside the ordinary 642-unit reader graph are still outstanding. The current chapter evaluates two source conditionals against its actual included labels; the editable translations preserve both alternatives.

## Rebuild the chapter

The v0.2.0 PDF bytes come from the verified relocatable Sets build. It reproduced byte-for-byte in both Naskh and Nastaliq under the shared TeX mutex, embeds its fonts, and all 29 generated pages passed visual review. The generator isolates all 65 explicit English terminology bridges so their internal LTR order survives RTL paragraph layout. See [`PORTABLE_CANDIDATE_QA.json`](provenance/PORTABLE_CANDIDATE_QA.json). The immutable v0.1.0 PDFs remain the historical reference-v3 artifacts. All source, font and accepted reader identities can be checked without TeX:

```powershell
python tools/verify_source_identity.py
```

The following commands regenerate the v0.2.0 PDF inputs. They require Python 3, PowerShell 7 and installed MiKTeX packages listed in `reader/sets-preamble.tex`. Fonts are loaded directly from the bundle, without system installation:

```powershell
python tools/build_sets_reader.py --output-dir output/rebuild --font-dir fonts
pwsh -NoProfile -File tools/build_reader.ps1 -InputDirectory output/rebuild
```

The launcher acquires `Global\InterlanguageTeXSlotV1` once, waits at most 30 seconds, holds it continuously across the captured process trees, all passes and log checks, and releases it in `finally`. A busy slot launches no TeX process; do not substitute an unguarded engine command. The guard rejects output outside this checkout or this task's state directory. The verified byte-reproducibility claim is within the recorded reference toolchain; different TeX/package versions may change PDF bytes or pagination and require fresh QA.

The generator inventories seven source identities, verifies pristine source hashes, checks references, preserves original TikZ assets, isolates explicit English bridges, and records every direction/layout transformation. Arabic language selection in the typesetter is a shaping mechanism, not a claim that the prose is Arabic.

The EPUB build is separate and invokes no TeX engine. It requires Python 3, Pandoc and `lxml`; it creates a canonical build and an independent cold build, then requires the EPUB bytes and unpacked trees to match:

```powershell
python tools/build_sets_epub.py --output-dir output/epub-v0.2.0
java -jar path/to/epubcheck.jar output/epub-v0.2.0/OpenLogic-Sets-Punjabi-Shahmukhi-v0.2.0.epub
```

`tools/audit_sets_epub.py` verifies package safety, manifest/spine order, 7/7 source identities, lexical preservation, 329 native MathML expressions, 39 statement/exercise headings, three described SVG diagrams and all internal links. `tools/accept_sets_epub_runtime.mjs` reuses the established English EPUB.js/Chromium runtime stack to load every archived spine document and render six representative locations with narrow-width, text-spacing and 200% probes. Exact accepted outputs are recorded under `provenance/SETS_EPUB_*.json`.

## License and attribution

The Open Logic Text is by **The Open Logic Project**, licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). See `LICENSE.md` and the preserved upstream license/readme. Punjabi translation, reader layout and project-authored supporting material are offered under the same license to the extent copyright applies. Changes include translation, provisional terminology, RTL/LTR layout, chapter selection and typography; no upstream endorsement is implied. Original mathematical notation and three chapter diagrams are retained. Component licenses continue to govern their respective files; bundled fonts remain under OFL 1.1, not CC BY.

The edition and its mathematical/linguistic decisions are provided without warranties. This first tranche does not imply completion or QA acceptance of the remaining corpus.
