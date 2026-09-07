# Punjabi Shahmukhi translation-decision package

Start with `PRIORITY_REVIEW.md` for focused expert questions or `TRANSLATION_DECISIONS_FULL.md` for the complete readable register. `DECISION_OCCURRENCES.csv` is the one-row-per-occurrence view; `DECISIONS.json` is the canonical machine projection validated by `translation-decision.schema.json`.

Current scope: 172 decisions, 2724 exact source-target occurrences, and 74 of 722 source units translated through `OLP-0074`. This is a partial current-main checkpoint, not a claim that the full edition or independent human review is complete.

Exact public-reader pages are present for 0 current occurrences. The historical v0.1.0 Sets PDFs predate the repaired source and their page locations are deliberately not reused. A through-OLP-0010 Naskh/Nastaliq candidate is reproducible and visually accepted but not released, so every current page locator remains explicitly pending—none is guessed from source order.

The durable `TERMINOLOGY_REVIEW_LOG.jsonl` remains the reversible source record. This package adapts it to the shared schema without retranslating accepted prose or inventing earlier consultation. Provisional decisions remain open to correction, but missing specialist dictionary evidence is not used as a reason to leave source text untranslated.

Edition policy: Pakistan Punjabi in Shahmukhi is the present semantic edition; Naskh and Nastaliq are display profiles. A future Indian Punjabi Gurmukhi edition requires its own semantic review, canon and terminology decisions and must not be produced by blind script conversion. International mathematical notation is retained in explicit LTR islands inside RTL prose.

The immutable v0.1.0 Sets release and its Zenodo record are not rewritten. The current-main source and decision surfaces may advance independently; a later binary release on the existing Zenodo lineage requires an explicitly accepted reader scope.

Shared contract: OpenLogic translation-decision schema at commit `811091d54be4989918864732073279a588340e6f`, 10,787 bytes, SHA-256 `50e7fa407b62c711f92f8b93be591d3b4a6e1c4adb1386c398bb5f76844d9f90`.
