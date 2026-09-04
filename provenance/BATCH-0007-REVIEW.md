# BATCH-0007 source-aligned review

OLP-0020 chapter driver: target 400 bytes, SHA-256 22a4487bc1db8672454968709cca096b76f3d6d548005ec9cff4ca2ad6c85b61. OLP-0021 function-basics.tex: source d1fa0923e303fc49a88d4e476c319d6e91a8088de44c232dcfba5878325faea3; corrected target 8443 bytes, SHA-256 246ad4e87f6a2022a077fd3f8626dff5a864adcd9a66c4a7a396637aad8fede1. Respectively 13 and 21 aligned blocks; strict audit passes. Two first-draft order mismatches in value/range exposition were rejected and corrected without weakening formula-order checks. Stable source audit OLFUN-20260904 (review bc183d34b6ac57cc00e2df76d00277cdd2fabee293d12beb142d2e27344f8d24; findings eee57facbea44f65a19a816fb12cbc86be0b18e21dcffeeed943f52f7e332960) then supplied OLFUN-002 and OLFUN-003; both are applied below without changing frozen English bytes.

Current-owner semantic and reverse-paraphrase review:

- A function assigns every allowed input exactly one output, without making the calculation method part of its identity. The black-box distinction does not claim that every function has an effective algorithm.
- Domain, codomain and attained range are distinct. Arguments are function inputs rather than arguments in the proof-theoretic sense. Every range value is attained for some input, not for every input.
- Multiplication takes a pair of naturals and outputs one natural; its full natural range is witnessed by n times 1. The square-root relation has two values for positive n, contrasting with choosing one designated root. The final-grade versus parent example retains the source's possible zero/two/more parent counts.
- For successor, the codomain is the naturals but zero is not attained, so the range is the positive integers. The two defining expressions x+1 and x+2-1 determine the same extensional function only with the same domain and codomain.
- Piecewise definition retains both x/2 on even inputs and (x+1)/2 on odd inputs, including x inside mathematical prose. Every possible input must enter exactly one case; exhaustiveness and exclusivity are both preserved.
- Diagram asset function.tikz was read completely: it contains geometry and formal drawing commands, no ordinary English labels. Its original path and caption reference are unchanged. The translated prose retains left-domain/right-codomain and forward arrow interpretation. It has not been newly rendered in a Functions reader.
- All driver imports remain, including the commented-out isomorphic-functions import. No imported file is counted translated merely because the driver is translated.

Source corrections: OLFUN-002 changes only the faulty selector adjective to nonnegative (principal), because Nat includes zero; the positive-integer two-root statement and displayed function remain intact. OLFUN-003 consistently uses x for the g-example input, matching g(x) and x+1. Adjacent stable-ID source comments and SOURCE_CORRECTIONS.jsonl disclose both changes. The audit applies one exact n-to-x comparison normalization, with locator-drift failure; no general formula exception was added.

Audit repair: nested mathematical islands inside text arguments are now retained when the prose is stripped for formula comparison. Mutation regression tests must reject changing x to y in the even-case condition. The previously supported intertext checks are retained.

Native pre-draft P007/P015 consultation and T023 provisional decisions are recorded separately. No specialized native attestation, independent human review, new reader acceptance or full-edition completion is claimed. Source translation and semantic review PASS.
