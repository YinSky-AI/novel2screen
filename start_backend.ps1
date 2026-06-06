param([int]$Port = 8000)
Write-Host "Starting Novel2Screen Backend on port $Port..." -ForegroundColor Cyan
uvicorn backend.main:app --host 0.0.0.0 --port $Port --reload
