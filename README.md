# Plagiarism Detection System

Full-stack plagiarism detection supporting text files, image OCR, and three analysis layers (TF-IDF, N-gram, SentenceBERT).

---

## Windows Setup (Quick Start)

### Step 1 — Install Tesseract OCR (for image support)

Download and run the installer:
**https://github.com/UB-Mannheim/tesseract/wiki**

- Choose the 64-bit installer
- Install to the default path: `C:\Program Files\Tesseract-OCR\`
- Tick "Add to PATH" during install

> Text file analysis works without Tesseract — only image OCR needs it.

---

### Step 2 — Run setup

Open PowerShell in the `plagiarism-detector` folder:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\setup_windows.ps1
```

### Step 3 — Start

```powershell
.\start.ps1
```

Opens browser at http://localhost:3000

---

## Manual Setup

```powershell
# Backend
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python app.py

# Frontend (new terminal)
cd frontend
npm install
npm run dev  
```

---

## Project Structure

```
plagiarism-detector/
├── setup_windows.ps1
├── start.ps1
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   └── core/
│       ├── text_processor.py
│       ├── ocr_engine.py        # Windows Tesseract path auto-detected
│       ├── similarity_engine.py
│       ├── semantic_model.py
│       └── report_generator.py
└── frontend/
    └── src/App.jsx
```

---

## Scoring Weights

| Method | Weight |
|--------|--------|
| SentenceBERT | 50% |
| TF-IDF | 30% |
| N-gram Jaccard | 20% |

Falls back to 60% TF-IDF / 40% N-gram if sentence-transformers is unavailable.

---

## Troubleshooting

**"tesseract is not installed or not in PATH"**
Install from https://github.com/UB-Mannheim/tesseract/wiki

**"No module named flask"**
Run `.\venv\Scripts\activate` before `python app.py`

**Frontend shows network error**
Make sure backend is running on port 5000

**sentence-transformers install fails**
Comment it out in requirements.txt — TF-IDF fallback is automatic
