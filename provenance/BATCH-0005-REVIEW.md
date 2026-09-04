# BATCH-0005 source-aligned review

OLP-0017 graphs.tex: source SHA-256 dec624ef4e71903b72a9f0b5fcc6a15a2e0f897f9ebe881dd9c9e21333aeee75; target 4078 bytes, SHA-256 ce38dee00c8b2fc272360e1b89cdc26881c93638f4dd70cb7578c1c87806fc81. Ten blocks align; all strict checks pass. The initial exercise reordered the standalone <= and vertex-set expressions; the audit rejected that draft and the sentence was corrected without relaxing order parity. Plural agreement and the oblique plural راساں were corrected before acceptance.

Semantic review by the current model owner:

- Introductory graph varieties retain direction, labels, self-loops and multiple-edge possibilities as distinctions in the literature. The subsequent selected definition is specifically a vertex set with a binary edge relation; it does not silently introduce multiple edges into this definition.
- Nodes and vertices are synonymous points here. The source's English singular/plural aside is localized as the target term's singular/plural explanation rather than leaving ordinary English vocabulary untranslated.
- Reverse paraphrase: a bare relation does not fix all isolated vertices; a graph specifies V as well as E. Every R on X yields (X,R), and conversely (V,E) gives E subset V squared with V explicit. Neither direction drops the specified vertex set.
- The first example retains vertices 1,2,3,4; a loop at 1; arrows 1 to 2, 1 to 3 and 2 to 3. The second removes only isolated vertex 4, not an edge. Its edge relation is identical, but it is a different graph. Both complete TikZ bodies are byte-identical to the source.
- All prose inside intertext was translated, while both embedded formulas retain source sequence. The <= exercise retains its set and drawing task, without inserting a solution.

Audit repair: intertext is prose between aligned math rows. The checker now removes only its linguistic content while retaining every embedded formula in place and order; ordinary align/TikZ content is still compared. This is distinct from dropping the whole intertext argument and requires corruption regression tests. No math equality checks are waived.

Canon: exact complete native Rvel paragraphs PNB-P013 and PNB-P015 were personally re-read before drafting, with source and paragraph hashes in BATCH-0005-CONSULTATION.json. Evidence is for Punjabi explanatory syntax only; historical/political claims and an embedded Urdu quotation are excluded. T019 graph terminology is provisional.

Disposition: source-aligned translation and semantic review PASS. No graph reader has yet been built or visually accepted. The checked Sets release is a separate seven-unit tranche; no full-edition completion claimed.
