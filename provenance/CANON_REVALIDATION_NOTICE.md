# Canon revalidation and semantic repair status

Status date: 2026-09-08

This notice supersedes semantic-acceptance claims for the existing Punjabi Shahmukhi translation without deleting or rewriting historical evidence.

## What remains historical

- Commit `6c4b2f319903b3ec36af7841b108bfc74ebadf58` contains 74 source-aligned translated units and remains a provenance-verifiable historical draft.
- GitHub release v0.1.0 and Zenodo record `10.5281/zenodo.22308437` remain immutable and publicly available. Their bytes, layout history, source identity, and prior receipts are preserved.
- Prior structural, formula, identifier, reference, Unicode, reverse-paraphrase, and visual checks remain evidence for exactly what they tested. They do not establish specialist Shahmukhi terminology or current semantic acceptance.

## Why acceptance changed

The independent audit `CANON-REVALIDATION-pnb-Arab-PK-20260906` examined 1,221 choice groups: all 1,220 source-aligned segments through OLP-0074 plus one morphology support group. Its frozen result was:

- 430 formal invariants;
- 776 unsupported language-bearing choices;
- 1 needs-revision choice;
- 14 contentious choices;
- 0 supported and 0 supported-provisional choices.

The audit therefore classified all 74 translated units as historically and provenancially accepted but semantically unaccepted draft. Forward authoring after OLP-0074 is frozen while repair proceeds contiguously from OLP-0001-B001.

## Corrections already recorded

- OLP-0018 now has a complete choice-level repair. It renders source “completeness theorems” with `تمامیت دے قضیاں`, not the erroneous problem/issue noun `مسئلیاں`, and records source defect `PNBREL-001`: the maximal-chain definition uses undefined `X` where its carrier is `A`. Frozen source bytes remain unchanged; the target changes only that variable and carries an adjacent disclosure.
- All 14 extensionality conflicts are choice-level resolved as `عنصراں نال تعیّن دا اصول`, with first use `عنصراں نال تعیّن دا اصول (Extensionality)`. Twelve now fall inside complete prefix records. The two later isolated records at OLP-0023-B008 and OLP-0036-B012 do not accept those units.
- OLP-0019 preserves the source formulas and explicitly discloses that local `R+` denotes transitive closure, whereas OLP-0016 used the same printed symbol for reflexive closure. The relation-restriction construction is also kept distinct from function restriction.

## Current validated prefix

The contiguous repair validator covers OLP-0001 through OLP-0019 and reports:

- 313/313 choice groups accounted for;
- 114 reverified formal invariants;
- 199 language-bearing groups with exact supported-provisional repair records;
- 0 unsupported, 0 needs-revision, and 0 contentious groups;
- no target-span, passage-identity, formula, command, protected-argument, placeholder-token, brace, Unicode, or source-manifest failures.

OLP-0005–OLP-0010 make the Sets chapter’s core vocabulary reversible at its definitions and distinguish Russell's named paradox, the derived contradiction, comprehension, and extensionality. OLP-0011–OLP-0019 do the same for the complete Relations chapter: relations as sets, identity and order relations, relation properties, equivalence classes and quotients, order variants, graphs, trees, and relation operations. Exact revision-bound community evidence supports only bounded items such as the mathematical-relation head and graph/vertex/edge wording; specialist terms without attestation retain visible English bridges and explicit uncertainty. Sixteen bounded OLP-0019 relation-operation searches returned zero hits, which is recorded as search absence rather than proof of linguistic absence.

This establishes semantic acceptance only for the repaired prefix OLP-0001–OLP-0019 under the documented provisional-term policy. It is not a claim that the remaining 55 translated draft units, the historical v0.1.0 reader, or the complete 722-unit edition is semantically accepted or complete. The effective unresolved count is 590 of the immutable 791 non-formal baseline choices after accounting for 201 validator-compatible repairs, including two isolated later repairs. The next repair choice is `pnb-Arab-PK:OLP-0020-B004:C001`.

The relocatable Sets-reader candidate was rebuilt after this checkpoint. Three XeLaTeX passes in each profile reproduced stable Naskh and Nastaliq bytes, all 29 pages were rendered and visually inspected, and all fonts were embedded. The first visual pass caught an apostrophe-sensitive bidirectional reversal in the `Russell's Paradox` heading; the bridge recognizer was corrected, both profiles were rebuilt, and all 65 English bridges then retained their internal LTR order. This is complete-page layout and local reproducibility evidence only: no PDF release changed, and it does not establish cross-platform byte reproducibility. Exact evidence is in [`PORTABLE_CANDIDATE_QA.json`](PORTABLE_CANDIDATE_QA.json).

## Evidence policy

Every repaired language-bearing group must record its exact authoritative source and current target span, exact consulted passage identities, alternatives, justification, confidence, and a precise review question. A missing conventional term after bounded research becomes an explicit reversible provisional choice; it is never reported as canon-attested.

The newly retained Western Punjabi Wikipedia revision snapshots are native-script community technical-usage evidence under CC BY-SA 4.0. They are not promoted to peer-reviewed Pakistani Punjabi scholarship. Their quoted excerpts, titles, revision URLs, and metadata retain CC BY-SA 4.0; inclusion here is a collection of evidence records and does not relicense those excerpts under the repository’s CC BY 4.0 translation license.

Human feedback remains welcome but is not a production or publication hold. Corpus-wide semantic-success publication remains disallowed until the repaired contiguous prefix advances through every relevant translated unit with zero unsupported and zero needs-revision groups.
