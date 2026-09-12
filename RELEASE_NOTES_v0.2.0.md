# v0.2.0 — Complete Sets chapter in EPUB 3 and PDF

This release makes the complete Punjabi Shahmukhi Sets chapter available as a genuine reflowable EPUB 3 for the first time. It also replaces the reading PDFs with the semantically repaired and fully rechecked Naskh and Nastaliq builds.

## Included scope

- Seven frozen OpenLogic source units: OLP-0004 through OLP-0010.
- Six sections: extensionality; subsets and power sets; important sets; unions and intersections; ordered pairs and Cartesian products; Russell's paradox.
- Definitions, examples, propositions, theorem/proof material and exercises.
- Three source-derived set diagrams.

This is the complete Sets chapter only. It is **not** the complete 722-unit OpenLogic edition, and no later chapter receives reader-acceptance credit from this release.

## EPUB edition

The EPUB is script-free and genuinely reflowable. It declares `pnb-Arab-PK`, right-to-left document and spine direction, and embeds Noto Naskh Arabic under the OFL. Mathematical content is native presentation MathML with TeX annotations; the three diagrams are inline SVG with Punjabi titles, descriptions and structural text alternatives.

The accepted EPUB was built twice from a clean output boundary with identical bytes and identical unpacked trees. EPUBCheck 5.3.0 reports zero fatals, errors, warnings or informational messages. Independent checks cover the source identities, Punjabi lexical preservation, 329 MathML expressions, 39 statement/exercise headings, three diagrams, 30 internal links and 11 anonymous external HTTPS checks. EPUB.js 0.3.93 in isolated Chromium loaded all five spine documents and rendered six representative locations without global overflow, browser errors, scripts, speech calls or external network attempts. Representative frames were visually inspected; three bidi presentation defects found in earlier candidates were repaired before acceptance.

## PDF editions

The Naskh PDF has 12 pages and the Nastaliq PDF has 17 pages. Both were reproduced byte-for-byte within the recorded Windows/MiKTeX toolchain, embed all used fonts, and passed a complete 29-page visual review. The PDFs are not tagged accessible PDFs.

## Attribution and limitations

The Open Logic Text is by The Open Logic Project and licensed CC BY 4.0. This independent machine translation and layout conversion is offered under the same license to the extent copyright applies. The bundled Noto fonts retain the SIL Open Font License 1.1. Changes include Punjabi Shahmukhi translation, provisional terminology, RTL/LTR layout, chapter selection, typography, MathML conversion and accessible SVG equivalents. No upstream endorsement is implied.

Specialized terminology remains provisional and has not received independent native-speaker review. MathML presentation varies by reading system; the recorded checks are bounded acceptance evidence, not an all-device or human accessibility certification.
