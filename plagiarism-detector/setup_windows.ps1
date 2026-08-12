# setup_windows.ps1
# Run this once to set up everything on Windows
# Open PowerShell in the plagiarism-detector folder and run:
#   .\setup_windows.ps1

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Plagiarism Detector - Windows Setup" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# ── Step 1: Check Python ──────────────────────────────────────────────────────
Write-Host "[1/5] Checking Python..." -ForegroundColor Yellow
try {
    $pyver = python --version 2>&1
    Write-Host "      Found: $pyver" -ForegroundColor Green
} catch {
    Write-Host "      Python not found. Please install from https://python.org" -ForegroundColor Red
    exit 1
}

# ── Step 2: Install Tesseract (Windows installer via winget) ──────────────────
Write-Host ""
Write-Host "[2/5] Installing Tesseract OCR..." -ForegroundColor Yellow
Write-Host "      Trying winget (Windows Package Manager)..." -ForegroundColor Gray

$tesseractPath = "C:\Program Files\Tesseract-OCR\tesseract.exe"

if (Test-Path $tesseractPath) {
    Write-Host "      Tesseract already installed at $tesseractPath" -ForegroundColor Green
} else {
    try {
        winget install --id UB-Mannheim.TesseractOCR -e --silent 2>&1 | Out-Null
        if (Test-Path $tesseractPath) {
            Write-Host "      Tesseract installed successfully!" -ForegroundColor Green
        } else {
            Write-Host "      winget install ran but path not found yet." -ForegroundColor Yellow
            Write-Host "      If OCR fails, manually download from:" -ForegroundColor Yellow
            Write-Host "      https://github.com/UB-Mannheim/tesseract/wiki" -ForegroundColor Cyan
        }
    } catch {
        Write-Host "      winget not available. Download Tesseract manually:" -ForegroundColor Yellow
        Write-Host "      https://github.com/UB-Mannheim/tesseract/wiki" -ForegroundColor Cyan
        Write-Host "      Install to: C:\Program Files\Tesseract-OCR\" -ForegroundColor Cyan
    }
}

# Add Tesseract to PATH for this session
$env:PATH += ";C:\Program Files\Tesseract-OCR"

# ── Step 3: Create virtual environment ───────────────────────────────────────
Write-Host ""
Write-Host "[3/5] Creating Python virtual environment..." -ForegroundColor Yellow
Set-Location backend

if (Test-Path "venv") {
    Write-Host "      venv already exists, skipping." -ForegroundColor Green
} else {
    python -m venv venv
    Write-Host "      venv created." -ForegroundColor Green
}

# ── Step 4: Install Python packages ──────────────────────────────────────────
Write-Host ""
Write-Host "[4/5] Installing Python packages (this may take a few minutes)..." -ForegroundColor Yellow
Write-Host "      Activating venv..." -ForegroundColor Gray

& ".\venv\Scripts\pip.exe" install --upgrade pip -q
& ".\venv\Scripts\pip.exe" install -r requirements.txt -q

Write-Host "      Packages installed." -ForegroundColor Green

# ── Step 5: Install Node / frontend deps ─────────────────────────────────────
Write-Host ""
Write-Host "[5/5] Installing frontend dependencies..." -ForegroundColor Yellow
Set-Location ..\frontend

try {
    $nodeVer = node --version 2>&1
    Write-Host "      Node.js found: $nodeVer" -ForegroundColor Green
    npm install --silent
    Write-Host "      Frontend packages installed." -ForegroundColor Green
} catch {
    Write-Host "      Node.js not found. Install from https://nodejs.org" -ForegroundColor Yellow
    Write-Host "      Then run: cd frontend && npm install" -ForegroundColor Cyan
}

Set-Location ..

# ── Done ──────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "  Setup complete!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "To start the app, run:" -ForegroundColor Cyan
Write-Host "  .\start.ps1" -ForegroundColor White
Write-Host ""
