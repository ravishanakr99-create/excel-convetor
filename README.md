# PDF Extractor - AI Document Extraction

Full-stack web application for uploading multiple PDFs, extracting structured data using AI, and exporting results to Excel.

## Features

- **Upload**: Up to 500 PDF files with drag-and-drop, upload progress bar
- **AI Extraction**: Layout-aware section detection, domain-specific field extraction
- **OCR**: Support for scanned PDFs via Tesseract
- **Batch Processing**: Process all files, real-time status updates
- **Excel Export**: One row per PDF, one column per domain field, with confidence scores
- **Dashboard**: Upload panel, processing status, results preview, download button, history

## Tech Stack

| Layer | Stack |
|-------|-------|
| Frontend | React 18, Vite, Tailwind CSS, Axios, React Router, React Dropzone |
| Backend | FastAPI, pdfplumber, PyMuPDF, Tesseract OCR, OpenAI (optional) |
| Data | Pandas, openpyxl |
| Auth | JWT, bcrypt |
| Storage | Local filesystem |

## Prerequisites

- **Python 3.10+** (3.11 recommended; 3.13 may have PyMuPDF wheel issues)
- **Node.js 18+**
- **Tesseract + optional deps** – For OCR of scanned PDFs: `pip install -r requirements-optional.txt` and [install Tesseract](https://github.com/tesseract-ocr/tesseract)
  - Windows: `choco install tesseract`
  - Mac: `brew install tesseract`
  - Ubuntu: `sudo apt install tesseract-ocr`

## Quick Start

**Option A: Use scripts (Windows PowerShell)**
```powershell
# Terminal 1 - Backend
.\scripts\start-backend.ps1

# Terminal 2 - Frontend
.\scripts\start-frontend.ps1
```

**Option B: Manual**

### 1. Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

Create `.env` from example:

```bash
copy .env.example .env   # Windows
# cp .env.example .env  # Mac/Linux
```

Edit `.env` and set:

- `SECRET_KEY` – random string for JWT
- `OPENAI_API_KEY` – optional, for AI extraction (fallback: rule-based)

Run the backend:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

### 3. First Use

1. Register an account on the Login page
2. Go to **Upload** and add PDF files
3. Click **Upload & Process**
4. Wait for processing (status updates automatically)
5. Click **Download Excel** when done

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register user |
| POST | `/api/auth/login` | Login |
| POST | `/api/jobs/upload` | Upload PDFs (multipart) |
| GET | `/api/jobs/status/{job_id}` | Job status |
| GET | `/api/jobs/results/{job_id}` | Extraction results |
| GET | `/api/jobs/download/{job_id}` | Download Excel |
| GET | `/api/jobs/history` | User job history |

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/routes/     # Auth, upload, process, download
│   │   ├── models/         # Pydantic models
│   │   ├── models_db.py    # SQLAlchemy models
│   │   ├── services/       # PDF, OCR, AI, Excel
│   │   ├── config.py
│   │   ├── database.py
│   │   └── main.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/            # Axios client
│   │   ├── components/
│   │   ├── contexts/       # Auth
│   │   └── pages/          # Login, Dashboard, Upload, Results, History
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

## Configuration

### Backend `.env`

| Variable | Description |
|----------|-------------|
| SECRET_KEY | JWT signing key |
| OPENAI_API_KEY | OpenAI API key (optional) |
| UPLOAD_DIR | Upload directory (default: ./uploads) |
| OUTPUT_DIR | Excel output directory (default: ./outputs) |
| DATABASE_URL | SQLite by default |

### AI Extraction

- With `OPENAI_API_KEY`: Uses GPT-4o-mini for structured extraction
- Without: Uses rule-based extraction (regex + heuristics)

## License

MIT
