$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'scripts/process-record.ps1')
foreach($name in @('web','maintenance','worker','api')){
 $record=Join-Path $PSScriptRoot ('.runtime/'+$name+'.json')
 if(Test-Path -LiteralPath $record){
  $saved=Get-Content -LiteralPath $record -Raw | ConvertFrom-Json
  Stop-SPONGERecordedProcess $saved
  Remove-Item -LiteralPath $record
 }
}
Write-Output 'Recorded SPONGE processes stopped. Shared Docker Desktop and persistent data remain available.'
