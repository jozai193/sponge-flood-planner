function Get-SPONGERecordedProcess {
 param($Record)
 $process=Get-Process -Id $Record.pid -ErrorAction SilentlyContinue
 if(-not $process){return $null}
 try {
  # ConvertFrom-Json may produce a DateTime rather than the original ISO string.
  if($process.StartTime.ToUniversalTime() -ne ([datetime]$Record.started_at).ToUniversalTime()){return $null}
  if($Record.exe -and $process.Path -ne $Record.exe){return $null}
  return $process
 } catch {return $null}
}

function Stop-SPONGERecordedProcess {
 param($Record)
 $root=Get-SPONGERecordedProcess $Record
 if(-not $root){return}
 $all=@(Get-CimInstance Win32_Process)
 $targets=[System.Collections.Generic.List[object]]::new()
 function Add-Descendants($parentId,$created){
  foreach($child in $all | Where-Object {$_.ParentProcessId -eq $parentId -and $_.CreationDate -ge $created}){
   Add-Descendants $child.ProcessId $child.CreationDate
   $targets.Add($child)
  }
 }
 Add-Descendants $root.Id $root.StartTime
 foreach($target in $targets){
  $live=Get-Process -Id $target.ProcessId -ErrorAction SilentlyContinue
  if($live -and $live.StartTime.ToUniversalTime() -eq $target.CreationDate.ToUniversalTime()){
   Stop-Process -Id $live.Id -ErrorAction SilentlyContinue
  }
 }
 # Recheck identity immediately before stopping the parent.
 $root=Get-SPONGERecordedProcess $Record
 if($root){Stop-Process -Id $root.Id -ErrorAction SilentlyContinue}
}
