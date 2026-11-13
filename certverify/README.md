# CertVerify AI — Enterprise Production SaaS

An AI-Powered Universal Certificate Verification & Forgery Detection SaaS platform built with production-grade architecture.

---

## Architecture Overview

- **Backend**: Python 3.11/3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic, Celery, Redis
- **Database**: Supabase PostgreSQL (via asyncpg and connection pooling)
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Lucide React, Zustand, TanStack Query, Recharts
- **AI & Forensics Engine**:
  - **OCR**: PyMuPDF + PaddleOCR
  - **Document Classification**: Multi-category rules & keyword weights (Educational, Employment, Government, Professional, ISO, Internship, Participation)
  - **Entity Extraction**: Regex & structured NLP for Candidate Name, Organization, Issue Date, Cert Number, URL, Email, Signatory
  - **Company Intelligence**: Online footprint corroboration (DuckDuckGo, SSL validation, India MCA registry hint, ISO claim verification)
  - **Brand Corroboration**: Image perceptual hashing (`imagehash.phash`) comparing website favicon with certificate logo region
  - **Document Forensics**: PDF metadata revision audit, Error Level Analysis (ELA) with NumPy/PIL, EXIF manipulation software signatures (Photoshop, GIMP, etc.), and highlighted visual anomaly generation
  - **QR Code & Digital Signatures**: QR decoding with pyzbar/OpenCV, destination domain reputation analysis, cryptographic PDF digital signature validation
  - **Duplicate Detection**: Perceptual visual hash (`phash`, `dhash`), SHA256 text fingerprinting, and semantic cosine similarity with Sentence Transformers (`all-MiniLM-L6-v2`)
  - **Risk Assessment Engine**: Weighted multi-engine synthesis with deterministic thresholds yielding `VERIFIED`, `SUSPICIOUS`, or `UNABLE_TO_VERIFY` with natural language audit reasoning
- **Audit Reports**: Enterprise branded 2-page verification PDF generated via ReportLab
- **Security & Hardening**:
  - JWT HS256 tokens with bcrypt password hashing
  - Role-Based Access Control (`USER`, `ADMIN`, `HR_VERIFIER`)
  - SlowAPI rate limiting (Login: 5/min, Register: 3/min, Upload: 10/hour)
  - HTTP Security Headers (`nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection`, `Referrer-Policy`)
  - Complete database-driven audit logging (`audit_logs` table)
  - Startup integrity validation sequence

---

## Project Structure

```
certverify/
├── backend/
│   ├── alembic/                    # Database migrations
│   ├── app/
│   │   ├── api/v1/endpoints/       # Auth, Certificates, Verify, Dashboard, Admin
│   │   ├── core/                   # Config, Database, Security, Celery, Startup
│   │   ├── middleware/             # Security headers
│   │   ├── models/                 # SQLAlchemy models
│   │   ├── schemas/                # Pydantic schemas
│   │   ├── services/ai/            # OCR, Classifier, Entity, Forensics, Logo
│   │   ├── services/verification/  # Company intelligence, QR, Duplicate, Risk
│   │   ├── services/report/        # ReportLab PDF generator
│   │   ├── tasks/                  # Celery background workers
│   │   └── main.py                 # FastAPI application
│   ├── tests/                      # Automated test suite
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/                    # Typed API client & endpoints
│   │   ├── components/             # UI, Layout, Dashboard, Verification
│   │   ├── pages/                  # Login, Register, Dashboard, Upload, History, Result, Admin
│   │   ├── store/                  # Zustand persistent auth
│   │   ├── types/                  # TypeScript interfaces
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
├── docker/
│   ├── backend/                    # Dev & Prod Dockerfiles
│   └── frontend/                   # Dev & Prod Dockerfiles + Nginx SPA config
├── nginx/                          # Production reverse proxy config
├── docker-compose.yml              # Local container orchestration
├── docker-compose.prod.yml         # Production multi-stage orchestration
├── deploy.sh                       # One-click deployment script
└── .env.example                    # Environment configuration template
```

---

## Supabase PostgreSQL Configuration

In `certverify/.env`, provide your Supabase PostgreSQL credentials:

```bash
# Supabase asyncpg connection (Port 5432 or Supabase Transaction Pooler 6543)
DATABASE_URL=postgresql+asyncpg://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres
DATABASE_SYNC_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres

# Supabase API
SUPABASE_URL=https://[YOUR-PROJECT-REF].supabase.co
SUPABASE_KEY=[YOUR-SUPABASE-ANON-KEY]
SUPABASE_SERVICE_ROLE_KEY=[YOUR-SUPABASE-SERVICE-ROLE-KEY]
```

To run migrations against Supabase:
```bash
cd backend
alembic upgrade head
```

---

## Running Locally

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate   # On Windows (or source venv/bin/activate on Linux/Mac)
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Celery Worker
```bash
cd backend
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=2
```

---

## Production Deployment

```bash
chmod +x deploy.sh
./deploy.sh
```

Nginx proxies:
- `/api/*` -> Backend API (port 8000)
- `/health` -> Health probe (port 8000)
- `/*` -> Optimized React Frontend (port 80)

