# BATCH-0004 source-aligned review

OLP-0016, orders.tex. Source SHA-256 79593789022fef31c0609b9c94856e2aef5cd5e88e92864e782bb6e6e5f4bce4. Target SHA-256 b957b557e39645cb45ebec7d1220b261381561434389eb32c0e0f82670a80317, 9043 bytes. All 30 aligned blocks and all strict structural checks pass in batch-0004-audit.json. No ordinary English prose remains; source comments, macro names and identifiers are retained. Personal pre-draft consultation is recorded in BATCH-0004-CONSULTATION.json, using PNB-P007 and PNB-P015; no retroactive adoption of recovered-owner consultation claims.

Current-owner semantic review, not independent human review:

- Preorder requires reflexivity and transitivity; partial order adds antisymmetry; linear/total order adds connectedness of distinct elements. Both converse failures are preserved.
- No-longer-than compares lengths, not lexical order. The distinct strings 01 and 10 witness failed antisymmetry even though connectedness holds.
- Inclusion is not generally linear. The unequal singleton witnesses and their power-set setting remain unchanged.
- Divisibility on natural numbers is distinguished from divisibility on integers. The two incomparable positive numbers witness failure of linearity; 1 and -1 witness failure of antisymmetry over integers. The existence of an integer multiplier is translated as an iff, not a one-way implication.
- Sequence extension is prefix extension, not unordered inclusion. Empty, identical, and longer-prefix alternatives are all retained. Initial segment is explicitly a sequence prefix.
- Strict order retains all three given properties, including irreflexivity and asymmetry as separately stated. Adding the diagonal gives reflexivity, while antisymmetry uses the off-diagonal contradiction. Transitivity handles two original R-pairs, then each possible identity-pair case. Connectedness passes to the superset.
- Removing the diagonal is a separate proposition; its proof remains an exercise, and the exercise reference is preserved. No invented proof inserted into the translation.
- Reverse paraphrase of the final proof: equal strict-predecessor profiles rule out a<b by substituting x=a and obtaining a<a; similarly b<a is ruled out; comparability of distinct objects forces equality. The target preserves exactly these steps and the displayed quantifiers.

Source qualification: the extension example says the relation on A* is not linear, then gives a witness requiring a != b. For alphabets of size at most one, that blanket nonlinearity claim does not follow and the relation is linear. This is an upstream qualification issue, not repaired silently in the faithful translation. The adjacent example retains the explicit witness condition. Any reader note must be visibly editorial.

Terms T018 remain definition-based provisional Punjabi/scholarly bridges. Rvel prose is evidence for native sequence/reason-giving syntax, not an attestation of order theory. No external political or historical claims are imported.

Disposition: translation and source-aligned semantic review PASS for OLP-0016, with the source qualification recorded. Reader layout for this new unit has not yet been built or accepted. Full edition remains incomplete.
