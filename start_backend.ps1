$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $projectRoot "venv\Scripts\python.exe"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Novel2Screen Backend Server" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Project Root: $projectRoot" -ForegroundColor Gray
Write-Host "Python:      $venvPython" -ForegroundColor Gray
Write-Host "Mode:        short (3-10 chapters)" -ForegroundColor Gray
Write-Host "Port:        8000" -ForegroundColor Gray
Write-Host ""
Write-Host "Starting server... (Ctrl+C to stop)" -ForegroundColor Yellow
Write-Host "API docs:    http://localhost:8000/docs" -ForegroundColor Green
Write-Host ""

# Set PYTHONPATH so backend/ is importable as 'backend'
$env:PYTHONPATH = $projectRoot

# Run via module (works with relative imports)
& $venvPython -m backend.main
