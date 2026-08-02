Write-Output "=== 按私有内存(Commit)排序 Top 15 进程 ==="
Get-Process | Sort-Object PrivateMemorySize64 -Descending | Select-Object -First 15 `
  @{N='Name';E={$_.ProcessName}}, `
  @{N='PrivateMB';E={[math]::Round($_.PrivateMemorySize64 / 1MB)}}, `
  @{N='WorkingSetMB';E={[math]::Round($_.WorkingSet64 / 1MB)}} |
  Format-Table -AutoSize

Write-Output "=== 工作集远大于私有内存的进程(共享/文件映射占用) ==="
Get-Process | Where-Object { $_.WorkingSet64 -gt ($_.PrivateMemorySize64 + 200MB) } |
  Select-Object -First 10 `
  @{N='Name';E={$_.ProcessName}}, `
  @{N='PrivateMB';E={[math]::Round($_.PrivateMemorySize64 / 1MB)}}, `
  @{N='WorkingSetMB';E={[math]::Round($_.WorkingSet64 / 1MB)}} |
  Format-Table -AutoSize

Write-Output "=== 页面文件使用情况 ==="
Get-CimInstance Win32_PageFileUsage | Select-Object Name, AllocatedBaseSize, CurrentUsage, PeakUsage | Format-Table -AutoSize

Write-Output "=== 进程总数 ==="
Write-Output ("进程数: {0}" -f (Get-Process).Count)
