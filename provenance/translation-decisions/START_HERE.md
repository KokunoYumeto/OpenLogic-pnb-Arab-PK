# Punjabi Shahmukhi translation-decision package

Start with `PRIORITY_REVIEW.md` for focused expert questions or `TRANSLATION_DECISIONS_FULL.md` for the complete readable register. `DECISION_OCCURRENCES.csv` is the one-row-per-occurrence view; `DECISIONS.json` is the canonical machine projection validated by `translation-decision.schema.json`.

Current scope: 131 decisions, 2489 exact source-target occurrences, and 64 of 722 source units translated through `OLP-0064`. This is a partial current-main checkpoint, not a claim that the full edition or independent human review is complete.

Exact accepted-reader pages are present for 243 occurrences in the seven-unit Sets reader. Page values name both Naskh and Nastaliq when available; they are typography profiles over exactly the same `pnb-Arab-PK` Shahmukhi semantic text. All other pages are explicitly pending until a reader is accepted—none are guessed from source order.

The durable `TERMINOLOGY_REVIEW_LOG.jsonl` remains the reversible source record. This package adapts it to the shared schema without retranslating accepted prose or inventing earlier consultation. Provisional decisions remain open to correction, but missing specialist dictionary evidence is not used as a reason to leave source text untranslated.

Edition policy: Pakistan Punjabi in Shahmukhi is the present semantic edition; Naskh and Nastaliq are display profiles. A future Indian Punjabi Gurmukhi edition requires its own semantic review, canon and terminology decisions and must not be produced by blind script conversion. International mathematical notation is retained in explicit LTR islands inside RTL prose.

The immutable v0.1.0 Sets release and its Zenodo record are not rewritten. These current-main decision surfaces are intended for the next worthwhile nonduplicative release on the existing Zenodo lineage after its reader scope is accepted.

Shared contract: OpenLogic translation-decision schema at commit `811091d54be4989918864732073279a588340e6f`, 10,787 bytes, SHA-256 `50e7fa407b62c711f92f8b93be591d3b4a6e1c4adb1386c398bb5f76844d9f90`.
