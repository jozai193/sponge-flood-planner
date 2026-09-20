# Non-destructive recovery for the known inaccessible Windows AF_UNIX socket error.
$ErrorActionPreference='Stop'
$log=Join-Path $env:LOCALAPPDATA 'Docker/log/host/com.docker.backend.exe.log'
& docker info --format '{{.ServerVersion}}' 2>$null
if($LASTEXITCODE -eq 0){Write-Output 'Docker is healthy; no repair needed.';exit 0}
$recentLog=(Get-Content -LiteralPath $log -Tail 500) -join "`n"
# Docker Desktop 4.90 writes the structured error over several physical log lines,
# so matching each line independently misses the guarded failure signature.
$staleSocketPattern='(?is)starting services:.*?(sailor-ingest\.sock|dockerInference|engine\.sock).*?The file cannot be accessed by the system'
if($recentLog -notmatch $staleSocketPattern){throw 'No matching stale-socket failure. Inspect Docker logs; runtime directories were not changed.'}
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$targets=@((Join-Path $env:LOCALAPPDATA 'Docker/run'),(Join-Path $env:LOCALAPPDATA 'docker-secrets-engine'))
foreach($target in $targets){
 $resolved=[IO.Path]::GetFullPath($target)
 if(-not $resolved.StartsWith(([IO.Path]::GetFullPath($env:LOCALAPPDATA)+[IO.Path]::DirectorySeparatorChar),[StringComparison]::OrdinalIgnoreCase)){throw 'Recovery target outside LocalAppData'}
}
# This error occurs before engine readiness. Stop only official Docker binaries.
Get-CimInstance Win32_Process | Where-Object {$_.ExecutablePath -like 'C:\Program Files\Docker\Docker\*'} | ForEach-Object {Stop-Process -Id $_.ProcessId -ErrorAction SilentlyContinue}
foreach($target in $targets){
 if(Test-Path -LiteralPath $target){Move-Item -LiteralPath $target -Destination ($target+'.sponge-recovery-'+$stamp)}
 New-Item -ItemType Directory -Path $target | Out-Null
}
Start-Process -FilePath 'C:\Program Files\Docker\Docker\Docker Desktop.exe' -WindowStyle Hidden
Write-Output 'Runtime socket directories preserved and recreated. No images, containers, volumes or settings were reset. Wait for Docker readiness, then run Start-SPONGE.ps1.'
