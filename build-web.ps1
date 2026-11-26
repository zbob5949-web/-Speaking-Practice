param([switch]$Install)
$ErrorActionPreference = "Stop"
foreach ($appName in @("frontend", "admin")) {
    Push-Location (Join-Path $PSScriptRoot "app/$appName")
    try {
        if ($Install -or -not (Test-Path "node_modules")) {
            npm.cmd ci --no-audit --no-fund
            if ($LASTEXITCODE -ne 0) { throw "Dependency install failed: $appName" }
        }
        npm.cmd run build
        if ($LASTEXITCODE -ne 0) { throw "Build failed: $appName" }
    } finally { Pop-Location }
}
Write-Host "Built both sites. Start: python run_backend.py"
Write-Host "Student: http://127.0.0.1:8000/"
Write-Host "Admin:   http://127.0.0.1:8000/admin-ui/"
