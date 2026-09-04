# BATCH-0010 source-aligned review

OLP-0026 partial-functions.tex: source 2601 bytes, SHA-256 `0f638e25ad1f565b9256846fb8b293c03663072b69a2adc5f2cfea1e94d00933`; target 3637 bytes, SHA-256 `3ea309ad0bc113567d1b404492840620f722da78bc7ed3109b8e16191268baed`. Fourteen aligned blocks. Strict audit `work/batch-0010-audit.json`, SHA-256 `9511a4589137c537106290816b3e3199efe31f2195519fcb78d9e5d991ae33e6`, passes every check. The first strict run rejected two pairs of reordered mathematical islands; the target sentence order was corrected while the checker remained unchanged.

Current-owner semantic and reverse-paraphrase review:

- A partial function may lack an output at some declared inputs but still assigns at most one output wherever it is defined. “At most one” permits zero or one, never multiple values.
- Definedness and undefinedness retain the `\fdefined`/`\fundefined` symbols. The actual domain is exactly the subset of `A` at which the partial function is defined, not the full declared source set by default.
- Every ordinary function is also partial; a partial function defined everywhere on its declared source set is total. The reciprocal example is undefined exactly at zero and defined at every other real input.
- The inverse-style exercise defines `g(y)` only when `y` has a unique `f`-preimage. For injective `f`, it asks for the two stated identities only on `dom(f)` and `ran(f)` respectively, so no totality outside those sets is implied.
- A partial function graph still consists exactly of the pairs satisfying `f(x)=y`. A binary relation determines a partial function when a fixed first coordinate has at most one second coordinate; it becomes total when seriality supplies at least one second coordinate for every first-coordinate element.
- The proof uses the relation property for uniqueness, concludes well-definedness, preserves graph equality, and invokes seriality only for totality.

PNB-T028 records reversible labels for partial/total functions, definedness and seriality. The transliterated serial label is immediately accompanied by its quantified definition. PNB-P007/P015 were freshly read before drafting and support Punjabi syntax only; no specialized native attestation or dictionary acquisition is claimed. Source comments, identifiers, macros and `!!{...}` lexical tokens are documented non-prose exceptions. The Functions chapter driver and all six sections OLP-0020 through OLP-0026 now have reviewed source translations. No independent human review, integrated reader acceptance or full-edition completion is claimed. Source translation and semantic review PASS.
