# OpenLogic in Punjabi Shahmukhi

پنجابی شاہ مکھی وچ اوپن لاجک

Independent machine translation and layout adaptation by Codex of **The Open Logic Project**. This is an ongoing full-edition project for `pnb-Arab-PK`, not an official upstream edition or an endorsed translation.

## Current scope

The v0.1.0 reader tranche is the **complete Sets chapter**: seven source units, six sections, three original diagrams, definitions, proofs and exercises. It is not the whole book. That release snapshot contains 21 source-aligned translations. Current `main` contains 30 reviewed source-aligned translations, leaving 692 of the frozen 722-unit inventory; the Relations and Functions chapters now have complete source translations, and Size of Sets is translated through its enumerability and Cantor zig-zag sections. Their integrated readers are not yet built, and none of these later sources is included in the Sets PDF's layout acceptance. See `provenance/CURRENT_MAIN_QA.json` for the branch/release distinction.

The chapter covers extensionality, subsets and power sets, important sets, unions and intersections, ordered pairs and products, and Russell's paradox. Both Naskh and Nastaliq reading profiles are provided. Punjabi prose is right-to-left; mathematical expressions preserve left-to-right order.

## Read and inspect

Release files include the two PDF profiles, an editable-source ZIP, and a SHA-256 inventory. See `provenance/RELEASE_QA.json` for exact accepted bytes, source coverage, reproducibility and visual checks. The entire English source is preserved in `upstream/`; translated source is separate in `translation/`.

- [Original project](https://openlogicproject.org/) and [contributors](https://openlogicproject.org/people/)
- [Frozen source revision](https://github.com/OpenLogicProject/OpenLogic/tree/9620cc73f9c8e0ad003c514a5d3748f29611c4c0)
- [OpenLogic translations hub](https://github.com/KokunoYumeto/OpenLogic-translations)

## Evidence and limitations

This is model-authored and model-reviewed translation. It has not received independent native-speaker review; no such review is claimed. Source-aligned semantic checks and reverse-paraphrase samples are recorded alongside strict formula, identifier, citation/reference, structural and Unicode checks. Every changed source-aligned block has recorded pre-draft canon consultation.

`provenance/TERMINOLOGY_REVIEW_LOG.jsonl` gives exact source/target block locations, current choices, evidence actually checked, retrospective alternatives, uncertainties and precise questions for asynchronous expert review. `provenance/SOURCE_CORRECTIONS.jsonl` separately records upstream wording/mathematical corrections by stable finding ID. These logs cover translated material only and do not imply review or completion of the untranslated remainder. Provisional choices stay open to correction; expert response is not a publication hold.

The acquired Punjabi sources support native academic syntax and the disciplinary names for logic and mathematics. They **do not establish specialized set-theory terminology**. Such terms remain explicit, reversible, definition-based provisional decisions, sometimes using shared Arabic/Urdu scholarly vocabulary or English loanwords inside Punjabi syntax. Original canon HTML/PDF files are not redistributed. Public provenance contains links, exact hashes, precise locators, brief quotations and explanatory records only.

The PDFs are not tagged accessible PDFs. A full semantic HTML reader, full-book integration and the 80 units outside the ordinary 642-unit reader graph are still outstanding. The current chapter evaluates two source conditionals against its actual included labels; the editable translations preserve both alternatives.

## Rebuild the chapter

The released PDF bytes come from the verified **reference-v3 build**, not the newer portable candidate. Its exact generated TeX inputs are preserved unchanged in `reader/reference/`, including their original fixed asset/font paths. The reference environment is Windows and MiKTeX/XeLaTeX; Noto Serif and Noto Naskh Arabic were resolved as installed font families, with an explicit static Nastaliq file. The original checkout path was `C:/interlanguage-production/openlogic-pnb-Arab-PK/repo`, and the static Nastaliq file was `C:/interlanguage-task-state/openlogic-pnb-Arab-PK/work/fonts/NotoNastaliqUrdu-Regular.ttf`. Reproduction was verified within that recorded environment, not across arbitrary installations.

The included OFL font bundle and relocatable generator are a **portable candidate, still unbuilt** because the shared TeX slot remained busy. Do not treat their inclusion as successful portability testing. All source, font, PDF and exact reference-input identities can be checked without TeX:

```powershell
python tools/verify_source_identity.py
```

The following commands generate and attempt the newer candidate, rather than asserting it produces the released bytes. They require Python 3, PowerShell 7 and installed MiKTeX packages listed in `reader/sets-preamble.tex`. Candidate fonts are loaded directly from the bundle, without system installation:

```powershell
python tools/build_sets_reader.py --output-dir output/rebuild --font-dir fonts
pwsh -NoProfile -File tools/build_reader.ps1 -InputDirectory output/rebuild
```

The launcher acquires `Global\InterlanguageTeXSlotV1` once, waits at most 30 seconds, holds it continuously across the captured process trees, all passes and log checks, and releases it in `finally`. A busy slot launches no TeX process; do not substitute an unguarded engine command. The guard rejects output outside this checkout or this task's state directory. The verified byte-reproducibility claim is within the recorded reference toolchain; different TeX/package versions may change PDF bytes or pagination and require fresh QA.

The generator inventories seven source identities, verifies pristine source hashes, checks references, preserves original TikZ assets and explicitly records direction/layout transformations. Arabic language selection in the typesetter is a shaping mechanism, not a claim that the prose is Arabic.

## License and attribution

The Open Logic Text is by **The Open Logic Project**, licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). See `LICENSE.md` and the preserved upstream license/readme. Punjabi translation, reader layout and project-authored supporting material are offered under the same license to the extent copyright applies. Changes include translation, provisional terminology, RTL/LTR layout, chapter selection and typography; no upstream endorsement is implied. Original mathematical notation and three chapter diagrams are retained. Component licenses continue to govern their respective files; bundled fonts remain under OFL 1.1, not CC BY.

The edition and its mathematical/linguistic decisions are provided without warranties. This first tranche does not imply completion or QA acceptance of the remaining corpus.
