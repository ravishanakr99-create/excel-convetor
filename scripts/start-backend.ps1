# Start PDF Extractor Backend
Set-Location $PSScriptRoot\..\backend
if (-not (Test-Path venv)) {
    Write-Host "Creating venv..." -ForegroundColor Yellow
    python -m venv venv
}
& .\venv\Scripts\Activate.ps1
pip install -r requirements.txt -q 2>$null
Write-Host "Starting backend on http://localhost:8000" -ForegroundColor Green
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
