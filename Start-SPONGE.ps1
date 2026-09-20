param([switch]$SkipInfrastructure)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'scripts/process-record.ps1')
Set-Location -LiteralPath $PSScriptRoot
if(-not(Test-Path -LiteralPath '.venv/Scripts/python.exe')){throw 'Run Setup-SPONGE.ps1 first.'}
& .venv/Scripts/python.exe -m scripts.doctor
if($LASTEXITCODE -ne 0){throw 'Runtime dependency check failed. See artifacts/verification/doctor.json. Resolve missing or policy-blocked dependencies before starting services.'}
if(-not $SkipInfrastructure){docker compose -f infra/compose/compose.yaml up -d --wait;if($LASTEXITCODE -ne 0){throw 'Start Docker Desktop, then retry.'}}
& .venv/Scripts/python.exe -m alembic upgrade head
if($LASTEXITCODE -ne 0){throw 'Database migration failed.'}
New-Item -ItemType Directory -Path '.runtime' -Force | Out-Null
$definitions=@(
 @{name='api';exe=(Join-Path $PSScriptRoot '.venv/Scripts/python.exe');args=@('-m','uvicorn','services.api.main:app','--host','127.0.0.1','--port','8787','--no-proxy-headers')},
 @{name='worker';exe=(Join-Path $PSScriptRoot '.venv/Scripts/python.exe');args=@('-m','scripts.worker')},
 @{name='maintenance';exe=(Join-Path $PSScriptRoot '.venv/Scripts/python.exe');args=@('-m','scripts.maintenance')},
 @{name='web';exe=(Get-Command node).Source;args=@('node_modules/vite/bin/vite.js','--config','apps/web/vite.config.ts','--host','127.0.0.1','--strictPort')}
)
foreach($definition in $definitions){
 $record=Join-Path $PSScriptRoot ('.runtime/'+$definition.name+'.json')
 if(Test-Path -LiteralPath $record){$saved=Get-Content -LiteralPath $record -Raw | ConvertFrom-Json;if(Get-SPONGERecordedProcess $saved){continue}}
 $port=if($definition.name -eq 'api'){8787}elseif($definition.name -eq 'web'){5173}else{0}
 if($port -and (Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue)){throw "Port $port is already occupied by an unrecorded process. Inspect it before starting another $($definition.name)."}
 $process=Start-Process -FilePath $definition.exe -ArgumentList $definition.args -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput ('.runtime/'+$definition.name+'.out.log') -RedirectStandardError ('.runtime/'+$definition.name+'.err.log')
 @{pid=$process.Id;started_at=$process.StartTime.ToUniversalTime().ToString('o');name=$definition.name;exe=$process.Path} | ConvertTo-Json | Set-Content -LiteralPath $record
}
$ready=$false
for($attempt=0;$attempt -lt 30;$attempt++){
 foreach($definition in $definitions){
  $saved=Get-Content -LiteralPath (Join-Path $PSScriptRoot ('.runtime/'+$definition.name+'.json')) -Raw | ConvertFrom-Json
  if(-not (Get-SPONGERecordedProcess $saved)){throw "$($definition.name) exited during startup. Inspect .runtime/$($definition.name).err.log."}
 }
 try{$health=Invoke-RestMethod 'http://127.0.0.1:8787/api/v1/ready' -TimeoutSec 2;$web=Invoke-WebRequest 'http://127.0.0.1:5173/' -TimeoutSec 2;if($health.database -eq 'ready' -and $web.StatusCode -eq 200){$ready=$true;break}}catch{}
 Start-Sleep -Milliseconds 500
}
if(-not $ready){throw 'SPONGE services did not become ready. Inspect .runtime logs.'}
Write-Output 'SPONGE: http://127.0.0.1:5173 — logs in .runtime'
