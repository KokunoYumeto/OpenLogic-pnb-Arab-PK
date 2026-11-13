param(
    [Parameter(Mandatory=$true)][string]$Assembly,
    [Parameter(Mandatory=$true)][string]$Output,
    [string]$EPUBCheckJar,
    [string]$VerifiedDiagrams
)

$ErrorActionPreference='Stop'
$src=(Resolve-Path -LiteralPath $Assembly).Path
$dest=[IO.Path]::GetFullPath($Output)
if (Test-Path -LiteralPath $dest) { throw 'Use a fresh output directory' }
$toolRoot=$PSScriptRoot
$diagramRoot=Join-Path $dest 'diagram-render'
$webRoot=Join-Path $dest 'web'
New-Item -ItemType Directory -Path $diagramRoot,$webRoot | Out-Null

function Invoke-Python([string]$Script,[string[]]$Parameters) {
    & python -X utf8 (Join-Path $toolRoot $Script) @Parameters
    if ($LASTEXITCODE) { throw "$Script failed ($LASTEXITCODE)" }
}
function Invoke-Pandoc([string[]]$Parameters,[string]$Log) {
    & pandoc @Parameters 2> $Log
    if ($LASTEXITCODE) { throw "Pandoc failed ($LASTEXITCODE)" }
}

foreach ($name in @('fonts','reader','translation','upstream','open-logic-pnb-naskh.tex')) {
    Copy-Item -LiteralPath (Join-Path $src $name) -Destination $webRoot -Recurse
}
foreach ($name in @(
    'project_web_tags.py','project_web_structure.py','project_web_proofs.py',
    'project_web_tableaux.py','project_web_displays.py','project_web_figures.py','project_web_notation.py'
)) {
    Invoke-Python $name @($webRoot)
}
if ($VerifiedDiagrams) {
    $verifiedRoot=(Resolve-Path -LiteralPath $VerifiedDiagrams).Path
    $proof=Get-Content -Raw -LiteralPath (Join-Path $verifiedRoot 'WEB-DIAGRAM-EXPORT.json') | ConvertFrom-Json
    $figures=Get-Content -Raw -LiteralPath (Join-Path $webRoot 'WEB-FIGURE-PROJECTION.json') | ConvertFrom-Json
    $assets=Join-Path $verifiedRoot 'diagram-assets'
    if ($proof.vector_svgs -ne $figures.figures -or $proof.artifacts.Count -ne $figures.figures) {
        throw 'Diagram count changed'
    }
    for ($index=0; $index -lt $figures.figures; $index++) {
        $image=$proof.artifacts[$index]
        $source=$figures.figures_by_order[$index]
        if ($image.id -ne $source.id -or $image.source_sha256 -ne $source.sha256) {
            throw "Frozen diagram identity changed ($($source.id))"
        }
        $asset=Join-Path $assets ($image.id+'.svg')
        if ((Get-FileHash -LiteralPath $asset -Algorithm SHA256).Hash -ne $image.sha256) {
            throw "SVG hash changed ($($image.id))"
        }
    }
} else {
    foreach ($name in @('fonts','reader','translation','upstream','WEB-FIGURE-PROJECTION.json')) {
        Copy-Item -LiteralPath (Join-Path $webRoot $name) -Destination $diagramRoot -Recurse
    }
    Copy-Item -LiteralPath (Join-Path $webRoot 'web-diagrams.tex') -Destination (Join-Path $diagramRoot 'open-logic-pnb-naskh.tex')
    & (Join-Path $src 'tools/build_cumulative_pdf.ps1') -InputDirectory $diagramRoot -Profile naskh -Diagnostic
    $diagramPdf=Join-Path $diagramRoot 'open-logic-pnb-naskh.pdf'
    $diagramReceipt=Join-Path $diagramRoot 'BUILD-naskh.json'
    Invoke-Python 'export_web_figure_svgs.py' @($diagramRoot,'--pdf',$diagramPdf,'--build-receipt',$diagramReceipt)
    $assets=Join-Path $diagramRoot 'diagram-assets'
}

Invoke-Pandoc @(
    (Join-Path $webRoot 'web-notation-projection.tex'),'--from=latex+raw_tex','--to=json',
    ('--output='+(Join-Path $webRoot 'pandoc-proof-projection.json'))
) (Join-Path $webRoot 'pandoc-proof-projection.stderr')
Invoke-Python 'expand_web_math.py' @($webRoot)
Invoke-Python 'build_web_bibliography.py' @($webRoot)
Invoke-Pandoc @(
    (Join-Path $webRoot 'pandoc-citation-slots.json'),'--from=json','--to=html5','--standalone','--mathml',
    '--metadata=title:Open Logic',('--output='+(Join-Path $webRoot 'web-math-diagnostic.html'))
) (Join-Path $webRoot 'web-math-diagnostic.stderr')
Invoke-Python 'render_web_proofs.py' @($webRoot)
Invoke-Python 'package_web_reader.py' @($webRoot,'--diagram-assets',$assets)
$epub=Join-Path $webRoot 'open-logic-pnb.epub'
Invoke-Python 'package_cumulative_epub.py' @((Join-Path $webRoot 'open-logic-pnb.html'),$epub)
if ($EPUBCheckJar) {
    & java -jar $EPUBCheckJar $epub --json (Join-Path $webRoot 'EPUBCHECK.json')
    if ($LASTEXITCODE) { throw "EPUBCheck failed ($LASTEXITCODE)" }
}
