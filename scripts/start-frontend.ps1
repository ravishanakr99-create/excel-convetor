# Start PDF Extractor Frontend
Set-Location $PSScriptRoot\..\frontend
if (-not (Test-Path node_modules)) {
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    npm install
}
Write-Host "Starting frontend on http://localhost:5173" -ForegroundColor Green
npm run dev
