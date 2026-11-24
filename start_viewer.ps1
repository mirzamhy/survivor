param(
    [int]$Port = 8080
)

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Url = "http://localhost:$Port/viewer/index.html"

Write-Host "Starting Low-Poly Survivor vs Mutants & Zombies 3D Battle Arena..." -ForegroundColor Cyan
Write-Host "Server directory : $Root" -ForegroundColor Gray
Write-Host "Open in browser  : $Url" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop the server." -ForegroundColor Yellow

Start-Process $Url
python -m http.server $Port --directory $Root
