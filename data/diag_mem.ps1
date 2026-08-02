$os = Get-CimInstance Win32_OperatingSystem
$totalGB = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
$freeGB  = [math]::Round($os.FreePhysicalMemory / 1MB, 1)
$usedGB  = [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) / 1MB, 1)
Write-Output "=== 总内存 / 空闲 / 已用 (GB) ==="
Write-Output ("Total={0}  Free={1}  Used={2}" -f $totalGB, $freeGB, $usedGB)

Write-Output ""
Write-Output "=== 按工作集内存排序 Top 25 进程 ==="
Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 25 `
  @{N='Name';E={$_.ProcessName}}, `
  @{N='MemMB';E={[math]::Round($_.WorkingSet64 / 1MB)}}, `
  @{N='PrivateMB';E={[math]::Round($_.PrivateMemorySize64 / 1MB)}} |
  Format-Table -AutoSize

Write-Output "=== 按进程名聚合的内存 ==="
Get-Process | Group-Object ProcessName | ForEach-Object {
  $sum = ($_.Group | Measure-Object WorkingSet64 -Sum).Sum
  [PSCustomObject]@{ Name = $_.Name; Count = $_.Count; TotalMB = [math]::Round($sum / 1MB) }
} | Sort-Object TotalMB -Descending | Select-Object -First 15 | Format-Table -AutoSize

Write-Output "=== 系统缓存/待机内存 (Standby) ==="
try {
  $c = (Get-Counter '\Memory\Standby Cache Normal Priority' -ErrorAction Stop).CounterSamples[0].CookedValue
  $m = (Get-Counter '\Memory\Modified Page List Bytes' -ErrorAction Stop).CounterSamples[0].CookedValue
  Write-Output ("Standby Normal = {0} GB, Modified = {1} GB" -f [math]::Round($c / 1GB, 2), [math]::Round($m / 1GB, 2))
} catch {
  Write-Output "无法读取 Standby 计数器: $($_.Exception.Message)"
}

Write-Output "=== 提交内存 (Committed) ==="
$cs = Get-CimInstance Win32_OperatingSystem
Write-Output ("CommitLimit={0} GB  Committed={1} GB" -f [math]::Round($cs.TotalVirtualMemorySize / 1MB, 1), [math]::Round(($cs.TotalVirtualMemorySize - $cs.FreeVirtualMemory) / 1MB, 1))
