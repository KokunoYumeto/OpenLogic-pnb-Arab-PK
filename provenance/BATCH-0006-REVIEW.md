# BATCH-0006 source-aligned review

OLP-0018 trees.tex: source a158f1ce5b84c8c3f681dd6347b22491d1b67a91e110138b9cb6833e3d9dc23c; target 7549 bytes, dbbed8326ed97abd2258641294a0d32401e89d5665fd218d6cd435e2f5589fce. OLP-0019 operations.tex: source 73c8bdb301aca93f687a06a045533d75d30088ae711f5e1dfd577b7864f8d3d5; target 2914 bytes, 69d68cfcfc731e99de12763278ba5ead52e8c9a237a40f6af53622279a1c25af. Both 21-block units pass all strict audit checks, with no formula-order repair needed. Native pre-draft prose consultation is identified in BATCH-0006-CONSULTATION.json; T020-T022 are provisional, not canon-attested technical senses.

Current-owner semantic and reverse-paraphrase review:

- A tree is a rooted partial order with well-ordered predecessor sets. Least means <= every element, not merely no smaller element. Well-ordering applies to every nonempty subset. The definition's unique least/root condition is explicit.
- Finite-tree picture: root r; children a,b; children c,d,e of a. The full original TikZ structure is retained, with upward growth. Ancestor is upward reachability. Introductory immediate-parent uniqueness in the pictured finite tree is not confused with the subsequent general theorem's at-most-one predecessor.
- Successor requires x<y with no intervening z. The predecessor proof uses linear comparability in a well-ordered subset to put one purported predecessor between the other and x. It concludes that both cannot be immediate predecessors; no existence theorem is inserted.
- Finitely branching is explicitly local finite successor count at every vertex. It does not assert finitely many maximal branches. A branch is a chain that cannot be enlarged, not a longest chain. Binary tree has exactly two successors s0,s1; the natural-number tree has infinitely many sn. Downward closure is stated using s' prefix s, not the reverse.
- Kőnig's lemma retains all three hypotheses (tree, infinite, finitely branching) and the infinite-branch conclusion. The weak version concerns an infinite binary subtree. The proper name retains all source TeX accent commands; other ordinary prose is translated.
- Operations: inverse swaps coordinates; relative product follows R then S via an existential intermediate y. Restriction is R intersect A squared, so both endpoints belong to A. Application/image quantifies x in A and outputs y; it is not inverse image.
- Successor examples preserve x+1, inverse x-1, relative square x+2, natural restriction and {1,2,3} mapping to {2,3,4}. Transitive closure uses positive n only; reflexive transitive closure adds Id(A). The final successor closure is strict <, while the reflexive closure is <=. The proof request remains an exercise.

Source issues, preserved rather than silently corrected:

1. The branch definition uses X in z in X minus B although the tree carrier was A and no local X is defined. The target retains X exactly. Later reader clarification must be explicitly editorial.
2. The subtree paragraph calls every downward-closed A a subtree, but the stated tree definition requires a root; the empty downward-closed set is an exception unless a nonempty convention is understood. This qualification is recorded.
3. R+ is locally reflexive closure in orders.tex but transitive closure in operations.tex. Both explicit local definitions are preserved; no global symbol replacement performed.

No ordinary English exposition remains; literal Kőnig, TeX/TikZ code, comments, stable lexical tokens and identifiers are documented exceptions. Source translation PASS, with source issues recorded. Relations chapter source translation now covers driver plus all eight sections OLP-0011 through OLP-0019; its integrated reader and visual QA remain outstanding. This is not acceptance of a full book.
