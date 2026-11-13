# اوپن لاجک متن — پنجابی شاہ مکھی

ایہ اوپن لاجک پروجیکٹ دے متن دا اے آئی نال کیتا گیا پنجابی شاہ مکھی ترجمہ اے۔ انگریزی ماخذ دی مقررہ Git نظرثانی 9620cc73f9c8e0ad003c514a5d3748f29611c4c0 اے۔ پنجابی ماخذ translation/ وچ، تے انگریزی ماخذ upstream/ وچ اے۔

- [اوپن لاجک پروجیکٹ دے مصنف تے حصہ پاؤن والے](https://openlogicproject.org/people/)
- [مقررہ انگریزی ماخذ](https://github.com/OpenLogicProject/OpenLogic/tree/9620cc73f9c8e0ad003c514a5d3748f29611c4c0)
- [اوپن لاجک دے ہور ترجمے](https://github.com/KokunoYumeto/OpenLogic-translations)

نسخ تے نستعلیق PDF لئی پوری تدوین جوگ LaTeX فائل کھولو۔ نال دِتے فانٹ، سٹائل، خاکے تے حوالیاں دی فہرست اوہناں فائلاں دے نال رکھو۔

## Build from the extracted source

The two cumulative masters contain the reading sequence. The editable translation tree also includes the four alternative drivers. Keep the extracted directory structure. On Windows with XeLaTeX and BibTeX installed, run the guarded build once for each profile.

~~~powershell
./tools/build_cumulative_pdf.ps1 -InputDirectory . -Profile naskh
./tools/build_cumulative_pdf.ps1 -InputDirectory . -Profile nastaliq
~~~

To regenerate the cumulative masters from the individual translated units, run:

~~~powershell
python -X utf8 tools/build_cumulative_reader.py --inventory reader/placement.json --source-manifest reader/source-manifest.jsonl --output ./assembly --source-archive ./assembly/open-logic-pnb-sources.zip
~~~

To build the illustrated HTML and EPUB 3, install Python with fonttools, lxml and PyMuPDF, and install Pandoc. Use a fresh output directory. The bundled SVGs let you rebuild from the checked diagram assets. Add an EPUBCheck JAR path to run conformance validation.

~~~powershell
./tools/web/build_cumulative_web.ps1 -Assembly . -Output ./web-output -VerifiedDiagrams ./reader/diagrams
./tools/web/build_cumulative_web.ps1 -Assembly . -Output ./web-check -VerifiedDiagrams ./reader/diagrams -EPUBCheckJar C:/path/to/epubcheck.jar
~~~

Run the web command without the VerifiedDiagrams parameter to regenerate all diagrams from the included TikZ source under the TeX guard.

The HTML and its CSS, fonts and diagrams belong in the same relative directory structure. The EPUB includes these resources. SHA256SUMS identifies the contents of this source archive.

The text is distributed under [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/). See LICENSE.md and upstream/LICENSE.md. The Noto fonts and the derived Gödel delimiter subset are covered by the SIL Open Font License 1.1. The two exact modal symbol outlines derive from Young Ryu’s TX fonts. See tools/web/txfonts-source/Txfonts-NOTICE.txt and Txfonts-GPL.txt for their separate license and document-embedding exception.
