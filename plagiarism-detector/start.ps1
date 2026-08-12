# start.ps1
# Starts both backend (Flask) and frontend (Vite) in separate windows
# Run from the plagiarism-detector folder:
#   .\start.ps1

Write-Host ""
Write-Host "Starting Plagiarism Detection System..." -ForegroundColor Cyan
Write-Host ""

# ── Backend ───────────────────────────────────────────────────────────────────
Write-Host "Starting Flask backend on http://localhost:5000 ..." -ForegroundColor Yellow

$backendPath = Join-Path $PSScriptRoot "backend"
$pythonExe   = Join-Path $backendPath "venv\Scripts\python.exe"

# Fall back to system python if venv not present
if (-not (Test-Path $pythonExe)) {
    $pythonExe = "python"
    Write-Host "  (using system Python — run setup_windows.ps1 first for venv)" -ForegroundColor Gray
}

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$backendPath'; `$env:TESSERACT_CMD='C:\Program Files\Tesseract-OCR\tesseract.exe'; & '$pythonExe' app.py"
) -WindowStyle Normal

Start-Sleep -Seconds 2

# ── Frontend ──────────────────────────────────────────────────────────────────
Write-Host "Starting React frontend on http://localhost:3000 ..." -ForegroundColor Yellow

$frontendPath = Join-Path $PSScriptRoot "frontend"

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$frontendPath'; npm run dev"
) -WindowStyle Normal

Start-Sleep -Seconds 3

# ── Open browser ──────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Opening browser..." -ForegroundColor Green
Start-Process "http://localhost:3000"

Write-Host ""
Write-Host "Both servers are running in separate windows." -ForegroundColor Green
Write-Host "Close those windows to stop the servers." -ForegroundColor Gray
Write-Host ""
