param(
    [Parameter(Mandatory=$true)][string]$InputDirectory,
    [string[]]$Profiles=@('naskh','nastaliq'),
    [ValidateRange(100,60000)][int]$TimeoutMilliseconds=30000
)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath($InputDirectory).TrimEnd('\')
$checkout=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..')).TrimEnd('\')
$permitted=@(($checkout+'\'),'C:\interlanguage-task-state\openlogic-pnb-Arab-PK\')
if (-not ($permitted | Where-Object { ($root+'\').StartsWith($_,[StringComparison]::OrdinalIgnoreCase) })) { throw 'Build output boundary violation' }
foreach($profile in $Profiles) {
    if($profile -notin @('naskh','nastaliq')) { throw 'Unknown profile' }
    if(-not(Test-Path -LiteralPath (Join-Path $root "sets-$profile.tex"))) { throw 'Missing input; no TeX launched' }
}
$slot=[Threading.Mutex]::new($false,'Global\InterlanguageTeXSlotV1')
$acquired=$false
$abandoned=$false
$records=@()
$stamp=[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ')
$receipt=[ordered]@{schema='pnb-reader-build/1';mutex='Global\InterlanguageTeXSlotV1';timeout_ms=$TimeoutMilliseconds;acquired=$false;abandoned_recovery=$false;status='not_started';started_utc=[DateTime]::UtcNow.ToString('o');processes=@();source_date_epoch='1788470400'}
try {
    try{$acquired=$slot.WaitOne($TimeoutMilliseconds)}catch [Threading.AbandonedMutexException]{$acquired=$true;$abandoned=$true}
    $receipt.acquired=$acquired
    $receipt.abandoned_recovery=$abandoned
    if(-not $acquired){$receipt.status='slot_busy';return}
    $env:SOURCE_DATE_EPOCH='1788470400'
    $env:FORCE_SOURCE_DATE='1'
    $engine=(Get-Command xelatex -ErrorAction Stop).Source
    foreach($profile in $Profiles){
        $stem="sets-$profile"
        $pass2Hash=$null
        for($pass=1;$pass -le 3;$pass++){
            $arguments=@('--disable-installer','-no-shell-escape','-interaction=nonstopmode','-halt-on-error','-recorder',('"-output-directory='+$root+'"'),($stem+'.tex'))
            # Windows -Wait holds for the captured process tree. The same mutex remains
            # held across every pass/profile and all immediate log/hash checks.
            $process=Start-Process -FilePath $engine -ArgumentList $arguments -WorkingDirectory $root -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput (Join-Path $root "$stem-pass$pass.stdout.log") -RedirectStandardError (Join-Path $root "$stem-pass$pass.stderr.log")
            $logPath=Join-Path $root "$stem.log"
            $log=if(Test-Path -LiteralPath $logPath){Get-Content -LiteralPath $logPath -Raw}else{''}
            $pattern='(?m)^!.*$|Missing character:.*$|Overfull \\hbox.*$|Overfull \\vbox.*$'
            if($pass -ge 2){$pattern+='|LaTeX Warning:.*undefined.*$|LaTeX Warning:.*multiply defined.*$'}
            $defects=@([regex]::Matches($log,$pattern)|ForEach-Object Value)
            $pdfPath=Join-Path $root "$stem.pdf"
            $entry=[ordered]@{profile=$profile;pass=$pass;root_pid=$process.Id;tree_wait='Start-Process -Wait';exit_code=$process.ExitCode;defects=$defects;log_sha256=if(Test-Path -LiteralPath $logPath){(Get-FileHash -LiteralPath $logPath -Algorithm SHA256).Hash.ToLowerInvariant()}else{$null};pdf_sha256=$null;pdf_bytes=$null}
            if(Test-Path -LiteralPath $pdfPath){$entry.pdf_sha256=(Get-FileHash -LiteralPath $pdfPath -Algorithm SHA256).Hash.ToLowerInvariant();$entry.pdf_bytes=(Get-Item -LiteralPath $pdfPath).Length}
            Copy-Item -LiteralPath $logPath -Destination (Join-Path $root "$stem-pass$pass.log")
            if($pass -eq 2){$pass2Hash=$entry.pdf_sha256}
            if($pass -eq 3){$entry.reproduced=($entry.pdf_sha256 -eq $pass2Hash)}
            $records+=$entry
            if($process.ExitCode -ne 0 -or $defects.Count -gt 0){$receipt.status='deterministic_defect';return}
            if($pass -eq 3 -and -not $entry.reproduced){$receipt.status='reproducibility_mismatch';return}
        }
    }
    $receipt.status='reproduced_pending_visual_review'
}catch{
    $receipt.status='operational_failure'
    $receipt.error_type=$_.Exception.GetType().FullName
    throw
}finally{
    $receipt.processes=$records
    $receipt.finished_utc=[DateTime]::UtcNow.ToString('o')
    try{
        $receipt|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $root "BUILD-$stamp.json") -Encoding utf8
        $receipt|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $root 'BUILD_RECEIPT.json') -Encoding utf8
    }finally{
        if($acquired){$slot.ReleaseMutex()}
        $slot.Dispose()
    }
    $receipt|ConvertTo-Json -Depth 8
}
