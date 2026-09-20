param()
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'process-record.ps1')
$workspace=Split-Path $PSScriptRoot -Parent
$testDirectory=Join-Path $workspace ('.runtime/ownership-test-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $testDirectory | Out-Null
$helper=Join-Path $testDirectory 'parent.cjs'
@"
const {spawn}=require('node:child_process');
const fs=require('node:fs');
const child=spawn(process.execPath,['-e','setInterval(()=>{},1000)'],{windowsHide:true,stdio:'ignore'});
fs.writeFileSync(process.argv[2],JSON.stringify({pid:child.pid}));
setInterval(()=>{},1000);
"@ | Set-Content -LiteralPath $helper -Encoding utf8
$childFile=Join-Path $testDirectory 'child.json'
$parent=$null;$childRecord=$null
try {
 $parent=Start-Process -FilePath (Get-Command node).Source -ArgumentList @(('"'+$helper+'"'),('"'+$childFile+'"')) -WindowStyle Hidden -PassThru
 $record=[pscustomobject]@{pid=$parent.Id;started_at=$parent.StartTime.ToUniversalTime().ToString('o');exe=$parent.Path}
 for($i=0;$i -lt 50 -and -not (Test-Path -LiteralPath $childFile);$i++){Start-Sleep -Milliseconds 100}
 if(-not(Test-Path -LiteralPath $childFile)){throw 'Child did not start'}
 $childId=(Get-Content -LiteralPath $childFile -Raw | ConvertFrom-Json).pid
 $child=Get-Process -Id $childId
 $childRecord=[pscustomobject]@{pid=$child.Id;started_at=$child.StartTime.ToUniversalTime().ToString('o');exe=$child.Path}
 $roundTrip=$record | ConvertTo-Json | ConvertFrom-Json
 if(-not(Get-SPONGERecordedProcess $roundTrip)){throw 'JSON round-trip identity rejected'}
 $stale=[pscustomobject]@{pid=$record.pid;started_at=$parent.StartTime.AddSeconds(-1).ToUniversalTime().ToString('o');exe=$record.exe}
 Stop-SPONGERecordedProcess $stale
 if(-not(Get-SPONGERecordedProcess $record)){throw 'Stale timestamp stopped parent'}
 $wrongExe=[pscustomobject]@{pid=$record.pid;started_at=$record.started_at;exe='C:\not-the-owned-executable.exe'}
 Stop-SPONGERecordedProcess $wrongExe
 if(-not(Get-SPONGERecordedProcess $record)){throw 'Wrong executable stopped parent'}
 Stop-SPONGERecordedProcess $roundTrip
 for($i=0;$i -lt 30 -and ((Get-SPONGERecordedProcess $record) -or (Get-SPONGERecordedProcess $childRecord));$i++){Start-Sleep -Milliseconds 100}
 if(Get-SPONGERecordedProcess $record){throw 'Owned parent survived stop'}
 if(Get-SPONGERecordedProcess $childRecord){throw 'Owned child survived stop'}
 $result=@{verified_at=[datetime]::UtcNow.ToString('o');checks=@('JSON timestamp round-trip','stale timestamp preserves live parent','wrong executable preserves live parent','valid record stops parent and child');passed=$true;scope='Disposable Node parent and child; live SPONGE services untouched'}
 $result | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $workspace 'artifacts/verification/process-ownership.json') -Encoding utf8
 $result | ConvertTo-Json -Depth 4
} finally {
 if($childRecord){Stop-SPONGERecordedProcess $childRecord}
 if($parent -and $record){Stop-SPONGERecordedProcess $record}
}
