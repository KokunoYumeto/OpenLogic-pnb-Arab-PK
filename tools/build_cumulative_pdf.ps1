param(
    [Parameter(Mandatory=$true)][string]$InputDirectory,
    [ValidateSet('naskh','nastaliq')][string]$Profile='nastaliq',
    [ValidateRange(100,30000)][int]$TimeoutMilliseconds=3000,
    [switch]$Diagnostic
)

$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath($InputDirectory)
$stem="open-logic-pnb-$Profile"
$source=Join-Path $root "$stem.tex"
if(-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Missing $stem.tex" }
if(Test-Path -LiteralPath (Join-Path $root "$stem.aux")) { throw 'Use a fresh assembly directory for each PDF build.' }
$xeLaTeX=(Get-Command xelatex -ErrorAction Stop).Source
$bibTeX=(Get-Command bibtex -ErrorAction Stop).Source
$mutexName='Global\InterlanguageTeXSlotV1'
$slot=[Threading.Mutex]::new($false,$mutexName)
$acquired=$false
$records=[Collections.Generic.List[object]]::new()
$receipt=[ordered]@{
    schema='pnb-cumulative-reader-build/1'
    mutex=$mutexName
    timeout_ms=$TimeoutMilliseconds
    acquired=$false
    recovered_abandoned_mutex=$false
    profile=$Profile
    source_sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $source).Hash.ToLowerInvariant()
    source_date_epoch='1794528000'
    status='not_started'
    started_utc=[DateTime]::UtcNow.ToString('o')
}

function Invoke-ReaderProcess([string]$Program,[string[]]$Arguments,[string]$Step,[string]$LogName) {
    # -Wait waits for the process tree. The caller holds the mutex throughout.
    $options=@{
        FilePath=$Program;ArgumentList=$Arguments;WorkingDirectory=$root
        WindowStyle='Hidden';Wait=$true;PassThru=$true
        RedirectStandardOutput=(Join-Path $root "$stem-$Step.stdout.log")
        RedirectStandardError=(Join-Path $root "$stem-$Step.stderr.log")
    }
    $process=Start-Process @options
    $logPath=Join-Path $root $LogName
    $patterns=@{
        errors='(?m)^!.*$|^Error--.*$|^I couldn.t open .*$'
        missing_characters='(?m)^Missing character:.*$'
        overfull='(?m)^Overfull \\[hv]box.*$'
        references='(?m)^(?:LaTeX|Package .*?) Warning:.*(?:undefined|multiply defined|duplicate).*$'
        citations='(?m)^Warning--I didn.t find a database entry.*$'
        bookmarks='(?m)^Package hyperref Warning: Token not allowed in a PDF string.*$'
    }
    $entry=[ordered]@{step=$Step;pid=$process.Id;exit_code=$process.ExitCode;log_sha256=$null;pdf_sha256=$null;pdf_bytes=$null}
    if(Test-Path -LiteralPath $logPath){
        $entry.log_sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $logPath).Hash.ToLowerInvariant()
        $log=[IO.File]::ReadAllText($logPath)
        Copy-Item -LiteralPath $logPath -Destination (Join-Path $root "$stem-$Step.full.log")
        foreach($category in $patterns.Keys){
            $entry[$category]=@([regex]::Matches($log,$patterns[$category]) | ForEach-Object Value)
        }
    }
    $pdf=Join-Path $root "$stem.pdf"
    if(Test-Path -LiteralPath $pdf -PathType Leaf){
        $entry.pdf_sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $pdf).Hash.ToLowerInvariant()
        $entry.pdf_bytes=(Get-Item -LiteralPath $pdf).Length
    }
    $records.Add($entry)
    return $entry
}

try{
    try{$acquired=$slot.WaitOne($TimeoutMilliseconds)}
    catch [Threading.AbandonedMutexException]{$acquired=$true;$receipt.recovered_abandoned_mutex=$true}
    $receipt.acquired=$acquired
    if(-not $acquired){$receipt.status='slot_busy';return}

    $env:SOURCE_DATE_EPOCH=$receipt.source_date_epoch
    $env:FORCE_SOURCE_DATE='1'
    $texArguments=@('--disable-installer','-no-shell-escape','-interaction=nonstopmode','-halt-on-error','-recorder',"$stem.tex")
    $steps=if($Diagnostic){1}else{4}
    for($pass=1;$pass -le $steps;$pass++){
        $result=Invoke-ReaderProcess $xeLaTeX $texArguments "pass$pass" "$stem.log"
        if($result.exit_code -ne 0 -or $result.errors.Count -ne 0){
            $receipt.status='tex_error'
            return
        }
        if($pass -eq 1 -and -not $Diagnostic){
            $bib=Invoke-ReaderProcess $bibTeX @('--disable-installer',$stem) 'bibtex' "$stem.blg"
            if($bib.exit_code -ne 0 -or $bib.errors.Count -ne 0 -or $bib.citations.Count -ne 0){
                $receipt.status='bibliography_error'
                return
            }
        }
        if($pass -eq 3){$passThree=$result.pdf_sha256}
    }
    $receipt.status=if($Diagnostic){'diagnostic_rendered'}elseif(
        $result.missing_characters.Count -or $result.references.Count -or $result.overfull.Count -or $result.bookmarks.Count
    ){'rendered_with_findings'}elseif($result.pdf_sha256 -and $result.pdf_sha256 -eq $passThree){
        'reproduced_pending_visual_review'
    }else{'reproducibility_mismatch'}
}
catch{
    $receipt.status='operational_failure'
    $receipt.exception_type=$_.Exception.GetType().FullName
    throw
}
finally{
    try{
        $receipt.finished_utc=[DateTime]::UtcNow.ToString('o')
        $receipt.processes=@($records.ToArray())
        $json=$receipt | ConvertTo-Json -Depth 8
        [IO.File]::WriteAllText((Join-Path $root "BUILD-$Profile.json"),$json+[Environment]::NewLine)
        Write-Output ($receipt.status)
        foreach($result in $records){
            Write-Output "$($result.step) exit=$($result.exit_code) errors=$($result.errors.Count) missing=$($result.missing_characters.Count) overfull=$($result.overfull.Count) references=$($result.references.Count) bookmarks=$($result.bookmarks.Count)"
        }
    }finally{
        if($acquired){$slot.ReleaseMutex()}
        $slot.Dispose()
    }
}
