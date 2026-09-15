# Accepted cumulative Sets masters for v0.2.0

The authoritative reproducible-source package contains the two complete TeX
masters that produced the accepted v0.2.0 PDF bytes:

- `reader/accepted-v0.2.0/sets-naskh.tex`
- `reader/accepted-v0.2.0/sets-nastaliq.tex`

It also contains the exact `INPUTS.json` and `BUILD_RECEIPT.json` from that
accepted build. These are cumulative masters: each contains the preamble and
all six Sets section bodies for frozen source units OLP-0004 through OLP-0010.
`reader/sets-preamble.tex` by itself is only a template and is not a cumulative
master.

The accepted master bytes retain the relative paths recorded by the original
acceptance build. For a relocatable rebuild after extracting the package, use
the included generator instead of editing those archived bytes:

```powershell
python tools/build_sets_reader.py --output-dir output/rebuild --font-dir fonts
pwsh -NoProfile -File tools/build_reader.ps1 -InputDirectory output/rebuild
```

The PowerShell launcher is the required TeX entrypoint. It acquires
`Global\InterlanguageTeXSlotV1` once, holds it over the complete process tree and
all passes, and releases it in `finally`. A different TeX installation can
change PDF bytes and pagination and therefore requires fresh visual QA.

The earlier `OpenLogic-Sets-Punjabi-Shahmukhi-editable-v0.2.0.zip` remains
available unchanged as historical packaging. It omitted the generated masters.
Use `OpenLogic-Sets-Punjabi-Shahmukhi-reproducible-source-v0.2.0.zip` for the
complete reproducible source package.
