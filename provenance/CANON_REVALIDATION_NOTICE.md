# Canon revalidation and semantic repair status

Status date: 2026-09-07

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

- OLP-0018-B005 now renders source “completeness theorems” with `تمامیت دے قضیاں`, not the erroneous problem/issue noun `مسئلیاں`. Exact revision-bound community Shahmukhi logic passages support the local theorem/problem distinction; the full specialist phrase remains reversible provisional terminology, not peer-reviewed attestation.
- All 14 extensionality conflicts are choice-level resolved as `عنصراں نال تعیّن دا اصول`, with first use `عنصراں نال تعیّن دا اصول (Extensionality)`. Eight exact corpus queries found no attestation for either competing candidate or tested loan forms. The selected definition-transparent phrase is therefore explicitly provisional. The strict-order result keeps distinct “extensionality-like” wording, and the function case remains explicitly scoped to functions.
- These isolated repairs do not semantically accept their later units. Each unit becomes accepted only when it falls inside a separately validated contiguous repaired prefix.

## Current validated prefix

The contiguous repair validator covers OLP-0001 through OLP-0008 and reports:

- 128/128 choice groups accounted for;
- 60 reverified formal invariants;
- 68 language-bearing groups with exact supported-provisional repair records;
- 0 unsupported, 0 needs-revision, and 0 contentious groups;
- no target-span, passage-identity, formula, command, protected-argument, placeholder-token, brace, Unicode, or source-manifest failures.

OLP-0005 includes visible first-use bridges for unattested `element/member`, `empty set`, `if and only if`, `positive integers`, `set-builder notation`, `perfect number`, and `proper divisors`. OLP-0006 adds exact definition-governed bridges for `subset`, `proper subset`, `even natural numbers`, `integers`, and `power set`. OLP-0007 makes all number-class, infinity, string, alphabet, length, sequence, and one-way-list choices reversible at their definitions. OLP-0008 does the same for `definition by abstraction`, `union`, `dual operation`, `intersection`, `disjoint`, `index`, and `set difference`, and also repairs four latent TeX-command-count mismatches without changing mathematical-token order. This establishes semantic acceptance only for the repaired prefix OLP-0001–OLP-0008 under the documented provisional-term policy. It is not a claim that the 74-unit draft, the v0.1.0 reader, or the complete 722-unit edition is semantically accepted or complete. The next repair choice is `pnb-Arab-PK:OLP-0009-B004:C001`.

The relocatable Sets-reader candidate was also rebuilt after this checkpoint. Three XeLaTeX passes in each profile reproduced stable Naskh and Nastaliq bytes, all 29 pages were rendered and visually inspected, and all 41 explicit English terminology bridges retained their internal LTR order. This is layout and reproducibility smoke evidence only: no PDF release changed, and the reader's historical-draft OLP-0009 and OLP-0010 content remains semantically unaccepted. Exact evidence is in [`PORTABLE_CANDIDATE_QA.json`](PORTABLE_CANDIDATE_QA.json).

## Evidence policy

Every repaired language-bearing group must record its exact authoritative source and current target span, exact consulted passage identities, alternatives, justification, confidence, and a precise review question. A missing conventional term after bounded research becomes an explicit reversible provisional choice; it is never reported as canon-attested.

The newly retained Western Punjabi Wikipedia revision snapshots are native-script community technical-usage evidence under CC BY-SA 4.0. They are not promoted to peer-reviewed Pakistani Punjabi scholarship. Their quoted excerpts, titles, revision URLs, and metadata retain CC BY-SA 4.0; inclusion here is a collection of evidence records and does not relicense those excerpts under the repository’s CC BY 4.0 translation license.

Human feedback remains welcome but is not a production or publication hold. Corpus-wide semantic-success publication remains disallowed until the repaired contiguous prefix advances through every relevant translated unit with zero unsupported and zero needs-revision groups.
