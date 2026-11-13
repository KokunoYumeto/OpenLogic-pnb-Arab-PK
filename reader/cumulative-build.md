# اوپن لاجک متن — پنجابی شاہ مکھی

ایہ اوپن لاجک پروجیکٹ دے متن دا پنجابی شاہ مکھی ایڈیشن اے۔ مقررہ انگریزی ماخذ دی Git نظرثانی 9620cc73f9c8e0ad003c514a5d3748f29611c4c0 اے۔ پنجابی ماخذ دیاں 722 اکائیاں translation/ وچ نیں۔

### اے آئی ترجمہ تے صفحہ بندی

- ترجمے دی مُڈھلی لکھائی — OpenAI Codex — GPT-5.6 Sol (Ultra)۔
- ترجمے دے اگلے حصیاں دی لکھائی — OpenAI Codex — GPT-6 Sol (Ultra)۔
- باقی ترجمہ، ترجمے دیاں اصلاحاں تے ایڈیشن دی صفحہ بندی — OpenAI Codex — GPT-6.1 Sol (Ultra)۔

- [Open Logic Project and contributors](https://openlogicproject.org/people/)
- [Original English source at the cited revision](https://github.com/OpenLogicProject/OpenLogic/tree/9620cc73f9c8e0ad003c514a5d3748f29611c4c0)
- [Open Logic translations](https://github.com/KokunoYumeto/OpenLogic-translations)
- [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/)

The original and translation use CC BY 4.0. The bundled fonts use the SIL Open Font License. See the notices in the `fonts` directory.

Run the commands from the root of the unpacked source archive. Python 3 assembles the reader from the editable units. The PDF build uses XeLaTeX, BibTeX, and the Open Logic LaTeX dependencies, with MiKTeX on Windows.

~~~powershell
python tools/build_cumulative_reader.py --inventory reader/source-units.json --output build --stage-build-files
./tools/build_cumulative_pdf.ps1 -InputDirectory build -Profile nastaliq
./tools/build_cumulative_pdf.ps1 -InputDirectory build -Profile naskh
~~~

The input inventory records the SHA-256 of each exact translated file. To assemble with edited units, update the matching entries in `reader/source-units.json` to the SHA-256 of the edited bytes.
