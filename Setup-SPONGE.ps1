$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
if(-not(Get-Command node -ErrorAction SilentlyContinue)){throw 'Node.js is required.'}
if(-not(Get-Command pnpm -ErrorAction SilentlyContinue)){throw 'pnpm is required.'}
if(-not(Test-Path -LiteralPath '.bootstrap/Scripts/uv.exe')){
 py -3.11 -m venv .bootstrap
 if($LASTEXITCODE -ne 0){throw 'Python 3.11 bootstrap or an installed uv runtime is required.'}
 & .bootstrap/Scripts/python.exe -m pip install uv==0.12.12
 if($LASTEXITCODE -ne 0){throw 'uv installation failed.'}
}
$env:UV_PYTHON_INSTALL_DIR=Join-Path $PSScriptRoot '.runtime/python'
& .bootstrap/Scripts/uv.exe sync --frozen --python 3.12
if($LASTEXITCODE -ne 0){throw 'Python dependency sync failed.'}
pnpm install --frozen-lockfile
if($LASTEXITCODE -ne 0){throw 'JavaScript dependency sync failed.'}
& .venv/Scripts/python.exe -m scripts.export_contracts --check
if($LASTEXITCODE -ne 0){throw 'Schema check failed.'}
Write-Output 'Dependencies ready. Run Start-SPONGE.ps1 to start the local services.'
