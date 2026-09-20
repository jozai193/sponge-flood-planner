$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
& .venv/Scripts/python.exe -m scripts.doctor
$runtimeResult=$LASTEXITCODE
docker compose -f infra/compose/compose.yaml ps
if($runtimeResult -ne 0 -or $LASTEXITCODE -ne 0){exit 1}
