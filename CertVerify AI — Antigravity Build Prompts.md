# CertVerify AI — Antigravity Build Prompts

*Production SaaS · AI-Powered Universal Certificate Verification & Forgery Detection*

---

## Eppadi Use Pannanum

1. **New Antigravity session → Master Context first paste pannu** (every time)
2. **One phase at a time** — rendu phase oru saare paste pannaathe
3. **Acceptance Criteria ✓** ellam check pannitu next phase ku poo
4. Session timeout → new session + Master Context + continue from same phase
5. Agent stuck → last section Recovery Tips paaru

---

## Final Tech Stack

| Layer | Technology |
| --- | --- |
| Backend | Python 3.11 · FastAPI · SQLAlchemy 2.0 async · Alembic |
| Queue | Celery · Redis 7 |
| Database | PostgreSQL 16 |
| Frontend | React 18 + TypeScript · Vite · Tailwind CSS v3 · Shadcn/UI |
| State | Zustand (auth) · TanStack Query v5 (server) |
| OCR | PaddleOCR |
| Image AI | OpenCV-headless · PyTorch · scikit-learn |
| Doc Processing | PyMuPDF · imagehash · pyzbar · sentence-transformers |
| Storage | Cloudinary |
| Reports | ReportLab |
| Auth | JWT (python-jose) + passlib\[bcrypt\] |
| Infrastructure | Docker · Docker Compose · Nginx |

> Original stack-la **TypeScript, Shadcn/UI, Celery+Redis, Docker, Alembic, sentence-transformers, pyzbar, ReportLab** add pannirukken — all production-essential.

---

## MASTER CONTEXT PROMPT

> Every new Antigravity session-la **idhai first paste pannu — skip pannaathe**

```
You are building "CertVerify AI" — a production SaaS platform for AI-powered certificate verification.

STRICT RULES:
- TypeScript for all frontend (no `any` types)
- Python type hints throughout backend
- Real implementations only — no mock/placeholder functions unless I say STUB
- Full error handling on every function and API endpoint
- Loading states for all async UI operations
- Never ask clarifying questions — follow the specification exactly
- All secrets via environment variables only

TECH STACK:
Backend: Python 3.11 | FastAPI | SQLAlchemy 2.0 async | Alembic | Celery | Redis | PostgreSQL 16
Frontend: React 18 + TypeScript | Vite | Tailwind CSS | Shadcn/UI | TanStack Query v5 | Zustand | Recharts
AI/ML: PaddleOCR | OpenCV-headless | PyTorch | scikit-learn | sentence-transformers | imagehash | PyMuPDF | pyzbar
Storage: Cloudinary | Reports: ReportLab | Infrastructure: Docker + Nginx

PROJECT STRUCTURE:
certverify/
├── backend/app/
│   ├── api/v1/endpoints/
│   ├── core/              (config.py, database.py, security.py, celery_app.py)
│   ├── models/
│   ├── schemas/
│   ├── services/ai/       (ocr, forensics, classifier, entities, logo)
│   ├── services/verification/ (company, qr, duplicate, risk)
│   ├── services/report/
│   ├── tasks/
│   └── main.py
├── frontend/src/
│   ├── components/
│   ├── pages/
│   ├── store/ api/ types/
├── docker-compose.yml
└── nginx/
```

---

## Phase 1: Foundation & Infrastructure

```
CERTVERIFY AI — PHASE 1: Foundation & Docker Infrastructure

TASK 1 — Docker Setup:
certverify/docker-compose.yml:
  postgres: postgres:16-alpine, POSTGRES_DB=certverify, POSTGRES_USER=certverify,
    POSTGRES_PASSWORD=${POSTGRES_PASSWORD}, port 5432:5432, volume postgres_data
  redis: redis:7-alpine, port 6379:6379, command: redis-server --requirepass ${REDIS_PASSWORD}
  backend: build ./docker/backend, port 8000:8000, env_file .env,
    volumes ./backend:/app, command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload,
    depends_on: [postgres, redis]
  celery_worker: same build as backend,
    command: celery -A app.tasks.celery_app worker --loglevel=info --concurrency=2,
    env_file .env, depends_on: [postgres, redis]
  flower: mher/flower, port 5555:5555, env CELERY_BROKER_URL=${CELERY_BROKER_URL}
  frontend: build ./docker/frontend, port 3000:3000, volumes ./frontend:/app

docker/backend/Dockerfile:
  FROM python:3.11-slim
  RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev libzbar0 libmagic1
  WORKDIR /app
  COPY requirements.txt .; RUN pip install --no-cache-dir -r requirements.txt; COPY . .

docker/frontend/Dockerfile:
  FROM node:20-alpine; WORKDIR /app; COPY package*.json .; RUN npm install; COPY . .
  CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

.env.example:
  DATABASE_URL=postgresql+asyncpg://certverify:password@postgres:5432/certverify
  REDIS_URL=redis://:password@redis:6379/0
  CELERY_BROKER_URL=redis://:password@redis:6379/1
  CELERY_RESULT_BACKEND=redis://:password@redis:6379/2
  SECRET_KEY=change-this-to-a-32-char-minimum-secret
  ACCESS_TOKEN_EXPIRE_MINUTES=10080
  CLOUDINARY_CLOUD_NAME=your_cloud_name
  CLOUDINARY_API_KEY=your_api_key
  CLOUDINARY_API_SECRET=your_api_secret
  POSTGRES_PASSWORD=strongdbpassword123
  REDIS_PASSWORD=strongredispassword123
  ALLOWED_ORIGINS=http://localhost:3000
  MAX_FILE_SIZE_MB=10
  VITE_API_URL=http://localhost:8000

TASK 2 — Backend Core:
backend/requirements.txt:
  fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg alembic celery[redis] redis
  pydantic-settings python-jose[cryptography] passlib[bcrypt] python-multipart
  httpx aiofiles cloudinary Pillow opencv-python-headless PyMuPDF imagehash
  reportlab pyzbar scikit-learn sentence-transformers paddleocr torch torchvision
  python-magic slowapi python-dotenv

core/config.py: pydantic-settings BaseSettings loading .env, all vars typed,
  ALLOWED_ORIGINS as List[str]. Singleton: settings = Settings() at bottom.

core/database.py: async SQLAlchemy engine (asyncpg driver),
  AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False),
  class Base(DeclarativeBase): pass,
  async def get_db() async generator dependency.

core/celery_app.py:
  celery_app = Celery("certverify",
    broker=settings.celery_broker_url, backend=settings.celery_result_backend)
  celery_app.autodiscover_tasks(["app.tasks"])

app/main.py: FastAPI(title="CertVerify AI", version="1.0.0"),
  CORSMiddleware(allowed_origins=settings.allowed_origins),
  include api_router at prefix /api/v1,
  GET /health → {"status":"ok","version":"1.0.0"},
  @app.on_event("startup"): test DB + Redis connections, log results.

TASK 3 — SQLAlchemy Models:
models/users.py → User:
  id UUID PK gen_random_uuid(), email str UNIQUE INDEXED, password_hash str,
  full_name str, role Enum(USER/ADMIN/HR_VERIFIER) default USER,
  is_active bool True, created_at datetime utcnow, updated_at datetime onupdate

models/certificates.py → Certificate:
  id UUID PK, user_id UUID FK→users.id, original_filename str(255),
  file_url str, cloudinary_public_id str, file_type str(10),
  file_size_bytes int, mime_type str, is_deleted bool False, created_at datetime

models/verification.py → four models:
  VerificationJob: id UUID PK, certificate_id UUID FK→certificates.id,
    status Enum(PENDING/PROCESSING/COMPLETED/FAILED) default PENDING,
    progress_percentage int default 0, current_step str nullable,
    error_message str nullable, started_at datetime nullable,
    completed_at datetime nullable, created_at datetime

  VerificationResult: id UUID PK, job_id UUID FK→verification_jobs.id,
    module_name str(50), status Enum(PASS/FAIL/WARNING/SKIPPED/ERROR),
    finding_summary str, details JSON, confidence_score float nullable, created_at datetime

  RiskAssessment: id UUID PK, job_id UUID FK UNIQUE→verification_jobs.id,
    risk_score int, risk_level Enum(LOW/MEDIUM/HIGH),
    final_verdict Enum(VERIFIED/SUSPICIOUS/UNABLE_TO_VERIFY),
    reasoning text, report_url str nullable, created_at datetime

  CertificateFingerprint: id UUID PK, certificate_id UUID FK UNIQUE→certificates.id,
    phash str(16), dhash str(16), text_hash str(64), created_at datetime

models/__init__.py imports all models.
alembic init backend/alembic; update env.py for async engine + all models imported.
Create: alembic revision --autogenerate -m "initial_tables"

TASK 4 — Frontend Skeleton:
Vite React+TypeScript in certverify/frontend/.
Install: tailwindcss postcss autoprefixer,
  shadcn/ui (init: zinc theme, CSS variables, src/components/ui),
  react-router-dom@6, @tanstack/react-query@5, zustand@4, axios, recharts, lucide-react, date-fns
Shadcn add: button card input label badge dialog progress select textarea table tabs alert sheet tooltip separator skeleton

src/types/index.ts interfaces:
  User { id, email, full_name, role: 'USER'|'ADMIN'|'HR_VERIFIER', is_active, created_at }
  Certificate { id, original_filename, file_url, file_type, file_size_bytes, created_at }
  VerificationJob { id, certificate_id, status: 'PENDING'|'PROCESSING'|'COMPLETED'|'FAILED',
    progress_percentage: number, current_step: string|null }
  VerificationResult { id, module_name,
    status: 'PASS'|'FAIL'|'WARNING'|'SKIPPED'|'ERROR',
    finding_summary: string, details: Record<string,unknown>, confidence_score: number|null }
  RiskAssessment { risk_score: number, risk_level: 'LOW'|'MEDIUM'|'HIGH',
    final_verdict: 'VERIFIED'|'SUSPICIOUS'|'UNABLE_TO_VERIFY',
    reasoning: string, report_url: string|null }
  PaginatedResponse<T> { items: T[], total: number, page: number, size: number }
  UploadResponse { certificate_id, job_id, filename, status }

src/api/client.ts:
  axios instance, baseURL = import.meta.env.VITE_API_URL
  Request interceptor: add Authorization Bearer from authStore token
  Response interceptor: on 401 → clearAuth() + window.location = '/login'

src/store/authStore.ts (Zustand):
  State: user: User|null, token: string|null, isAuthenticated: boolean
  setAuth(token, user), clearAuth()
  Persist to localStorage key 'certverify_auth'

src/components/auth/ProtectedRoute.tsx:
  !isAuthenticated → <Navigate to="/login" replace />
  AdminRoute: role not ADMIN|HR_VERIFIER → <Navigate to="/dashboard" replace />

src/components/layout/AppLayout.tsx:
  Left sidebar, nav links with icons:
    LayoutDashboard→/dashboard, Upload→/upload, History→/history,
    Shield→/admin (only for ADMIN|HR_VERIFIER)
  Top header: "CertVerify AI" + user full_name + role Badge + LogOut button
  Main: <Outlet />

src/App.tsx: BrowserRouter, Routes:
  Public: /login → LoginPage, /register → RegisterPage
  Protected (ProtectedRoute→AppLayout): /dashboard, /upload, /verify/:jobId, /history
  Admin (AdminRoute→AppLayout): /admin
  / → redirect /dashboard
  Create stub placeholder components for all 5 pages.

ACCEPTANCE CRITERIA:
✓ docker-compose up → all 6 services run without errors
✓ GET localhost:8000/health → {"status":"ok","version":"1.0.0"}
✓ GET localhost:5555 → Flower monitoring dashboard
✓ localhost:3000 → React app loads with sidebar
✓ /dashboard redirects to /login when not authenticated
✓ alembic upgrade head → all 4 tables created in PostgreSQL
✓ npx tsc --noEmit → zero TypeScript errors
```

---

## Phase 2: Authentication System

```
CERTVERIFY AI — PHASE 2: Complete Authentication

BACKEND:
core/security.py:
  create_access_token(data: dict, expires_delta: timedelta|None) → str [JWT HS256]
  decode_token(token: str) → dict [raise HTTP 401 on invalid/expired]
  get_password_hash(password: str) → str [bcrypt]
  verify_password(plain: str, hashed: str) → bool
  OAuth2PasswordBearer scheme pointing to /api/v1/auth/login
  async get_current_user(token, db) → User [raise 401 if not found/inactive]
  async require_admin(current_user) → User [raise 403 if not ADMIN]
  async require_staff(current_user) → User [raise 403 if not ADMIN or HR_VERIFIER]

schemas/auth.py:
  RegisterRequest(email: EmailStr, password: str min=8, full_name: str min=2)
  UserResponse(id, email, full_name, role, is_active, created_at)
  TokenResponse(access_token: str, token_type: str = "bearer", user: UserResponse)
  UpdateProfileRequest(full_name?: str, current_password?: str, new_password?: str min=8)

api/v1/endpoints/auth.py:
  POST /api/v1/auth/register
    Check email unique → HTTP 409 if exists
    Hash password, create User(role=USER), commit
    Return TokenResponse with new JWT

  POST /api/v1/auth/login (OAuth2PasswordRequestForm: username=email)
    Find by email → HTTP 401 if not found
    verify_password → HTTP 401 "Invalid credentials" if wrong
    HTTP 403 "Account deactivated" if not is_active
    Return TokenResponse

  GET /api/v1/auth/me (Depends get_current_user) → UserResponse

  PUT /api/v1/auth/me (get_current_user, body: UpdateProfileRequest)
    If new_password: verify current_password first → 400 if wrong
    Update full_name and/or password_hash → Return UserResponse

api/v1/api.py:
  api_router = APIRouter()
  Include auth at /auth, certificates at /certificates,
    verify at /verify, dashboard at /dashboard, admin at /admin

FRONTEND:
src/pages/LoginPage.tsx:
  Centered Shadcn Card (max-w-md)
  Logo + "CertVerify AI" heading + "Sign in" subheading
  Email Input + Label, Password Input with show/hide Eye/EyeOff toggle
  Login Button (Loader2 spin loading state)
  "Don't have an account? Register →" link
  On submit: POST /api/v1/auth/login with FormData (username=email, password)
  On success: authStore.setAuth(token, user) → navigate('/dashboard')
  On error: toast({ variant:"destructive", title: error.response.data.detail })

src/pages/RegisterPage.tsx:
  full_name + email + password + confirm_password inputs
  Validate before submit: match, ≥8 chars
  On success: navigate('/login') with success toast
  On error: destructive toast

src/api/auth.ts: typed login(), register(), getMe(), updateProfile()

Update AppLayout header:
  user full_name, role Badge (ADMIN=purple, HR_VERIFIER=blue, USER=gray)
  LogOut: clearAuth() → navigate('/login')

ACCEPTANCE CRITERIA:
✓ Register new account end-to-end works
✓ Login returns JWT stored in localStorage via Zustand
✓ Sidebar shows user name + role badge
✓ Wrong password → error toast
✓ Any protected route → redirects /login when not authenticated
✓ GET /api/v1/auth/me returns current user JSON
```

---

## Phase 3: Certificate Upload System

```
CERTVERIFY AI — PHASE 3: Upload, Storage & Verification Job Queue

BACKEND:
services/storage_service.py:
  Configure cloudinary at module import using settings
  async upload_certificate(file_bytes, filename, user_id) → StorageResult(url, public_id, bytes, format)
    folder = f"certverify/certificates/{user_id}", resource_type="auto"
  async delete_file(public_id: str) → bool
    cloudinary.uploader.destroy(public_id, resource_type="raw")

api/v1/endpoints/certificates.py:
  POST /api/v1/certificates/upload (Form + File, auth required):
    If file is None → HTTP 400
    content = await file.read()
    If len(content) > MAX_FILE_SIZE_MB*1024*1024 → HTTP 413 "File too large"
    Verify MIME via python-magic: magic.from_buffer(content, mime=True)
    If MIME not in [pdf, jpeg, png] → HTTP 415
    upload_certificate(content, file.filename, str(user.id))
    Create Certificate row
    Create VerificationJob(status=PENDING)
    await db.commit()
    run_verification.apply_async(args=[str(job.id), str(cert.id)], countdown=2)
    Return UploadResponse(certificate_id, job_id, filename, status)

  GET /api/v1/certificates/ (auth, page=1, size=10, status=None):
    Join Certificate→latest VerificationJob→RiskAssessment for current user
    Filter is_deleted=False, paginate → PaginatedCerts

  DELETE /api/v1/certificates/{id} (auth):
    Verify ownership → 403 otherwise
    delete_file(cloudinary_public_id)
    cert.is_deleted=True; commit → 204

  GET /api/v1/verify/{job_id}/status (auth, verify ownership):
    Return JobStatusResponse(job_id, status, progress_percentage, current_step)

  GET /api/v1/verify/{job_id}/results (auth, verify ownership):
    Return ResultsResponse(job, results: list, risk_assessment)

tasks/verification_task.py:
  Use SYNCHRONOUS SQLAlchemy Session for Celery (not async):
    sync_engine = create_engine(settings.database_url.replace("+asyncpg",""))

  @celery_app.task(bind=True, name="run_verification", max_retries=2)
  def run_verification(self, job_id: str, certificate_id: str):
    with Session(sync_engine) as db:
      job = db.get(VerificationJob, job_id)
      job.status='PROCESSING'; job.started_at=datetime.utcnow(); db.commit()
      try:
        # STUB — replace progressively in Phases 4-9
        time.sleep(3)
        job.progress_percentage=100; job.status='COMPLETED'
        job.completed_at=datetime.utcnow(); db.commit()
      except Exception as exc:
        job.status='FAILED'; job.error_message=str(exc); db.commit()
        raise self.retry(exc=exc, countdown=30)

FRONTEND:
src/pages/UploadPage.tsx:
  Centered Shadcn Card with 280px drag-drop zone:
    CSS: border-2 border-dashed rounded-xl, flex col, items-center, cursor-pointer
    Hidden <input type="file" accept=".pdf,.jpg,.jpeg,.png" ref={inputRef} />
    onClick: inputRef.current?.click()
    onDragOver: e.preventDefault(); isDragging=true (border-blue-500 bg-blue-50)
    onDragLeave/onDrop: isDragging=false; handle e.dataTransfer.files[0]
  UploadCloud icon 48px + "Drag & drop certificate here" + "or click to browse"
  After select: show preview
    PDF: FileText icon + filename + size
    Image: <img src={URL.createObjectURL(file)} className="max-h-32 object-contain" />
    X button to clear
  Upload Button (disabled if no file, Loader2 spin while uploading):
    const form = new FormData(); form.append('file', selectedFile)
    POST /api/v1/certificates/upload
    Show Shadcn Progress 0→90% animated, jump to 100 on response
    Success: toast "Verification started!" → navigate(`/verify/${response.job_id}`)
    Error: destructive toast with API error message
  Footer: "PDF, JPG, PNG • Max 10MB"

src/pages/HistoryPage.tsx:
  Shadcn Table: File / Type / Uploaded / Status / Risk / Actions
  Status Badge: PENDING|PROCESSING=yellow, COMPLETED=green, FAILED=red
  Risk Badge: VERIFIED=green, SUSPICIOUS=orange, UNABLE_TO_VERIFY=gray
  Actions: View Button→/verify/{job_id}, Trash2 icon→AlertDialog→DELETE→refetch
  Pagination (Previous/Next, "Page N of M")
  Empty state: UploadCloud + "No certificates yet" + Upload button
  Auto-refresh setInterval 10s while any row is PENDING|PROCESSING

src/pages/VerificationResultPage.tsx (skeleton only — full UI Phase 9):
  const { jobId } = useParams()
  Poll GET /verify/{jobId}/status every 3s while PENDING|PROCESSING
  Stop polling on COMPLETED|FAILED
  Animated step list (map progress 0-100 to step index):
    steps = ["Document Classification","OCR Extraction","Company Verification",
             "Document Forensics","Duplicate Detection","Risk Assessment"]
    gray circle=pending, Loader2 spin=active, CheckCircle2 green=done
  Shadcn Progress bar showing progress_percentage
  COMPLETED → green banner "✓ Verification Complete" (results come Phase 9)
  FAILED → red banner with error_message

src/api/certificates.ts: uploadCertificate, getCertificates,
  deleteCertificate, getJobStatus, getResults (all typed)

ACCEPTANCE CRITERIA:
✓ Drag-drop + click-browse work for PDF/JPG/PNG
✓ >10MB files rejected with error toast
✓ Non-certificate files (.docx, .exe) rejected with 415 error
✓ Upload → file appears in Cloudinary console
✓ Certificate + VerificationJob rows created in DB
✓ Celery task appears in Flower (:5555) as SUCCESS
✓ History page shows uploads with correct status/risk badges
✓ Delete removes from Cloudinary + sets is_deleted=True
✓ VerificationResultPage polls and shows animated step progress
```

---

## Phase 4: OCR & Certificate Classification

```
CERTVERIFY AI — PHASE 4: OCR Engine & AI Classification

BACKEND:
services/ai/ocr_service.py:
  _paddle_ocr = None  # module-level singleton (lazy init)

  def get_ocr():
    global _paddle_ocr
    if not _paddle_ocr:
      from paddleocr import PaddleOCR
      _paddle_ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
    return _paddle_ocr

  def extract_text(file_path: str) → OCRResult(full_text, avg_confidence, block_count):
    If ends .pdf:
      doc = fitz.open(file_path); text = doc[0].get_text()
      if len(text.strip()) >= 50:
        return OCRResult(full_text=text, avg_confidence=0.99, block_count=len(text.split('\n')))
      pix = doc[0].get_pixmap(matrix=fitz.Matrix(2,2))
      tmp = file_path.replace('.pdf','_tmp.png'); pix.save(tmp)
      result = _run_paddle(tmp); os.remove(tmp); return result
    Else: return _run_paddle(file_path)

  def _run_paddle(path) → OCRResult:
    res = get_ocr().ocr(path, cls=True)
    if not res or not res[0]: return OCRResult('', 0.0, 0)
    texts=[l[1][0] for l in res[0]]; confs=[l[1][1] for l in res[0]]
    return OCRResult('\n'.join(texts), sum(confs)/len(confs), len(texts))

services/ai/classifier_service.py:
  KEYWORDS = {
    "EDUCATIONAL": ["university","college","degree","bachelor","master",
      "board of education","marks","cgpa","semester","school","diploma"],
    "EMPLOYMENT": ["experience certificate","employed","designation",
      "relieving","worked with us","service period"],
    "INTERNSHIP": ["internship","intern","training program","completion of training"],
    "GOVERNMENT": ["government of","district","revenue","income certificate",
      "community certificate","nativity","birth certificate"],
    "PROFESSIONAL": ["aws certified","microsoft certified","cisco","oracle",
      "comptia","google certified","credential id","pearson vue"],
    "ISO": ["iso 9001","iso 14001","iso 27001","certification body","accredited","iaf"],
    "PARTICIPATION": ["participated in","participation","attended","workshop","seminar"]
  }

  def classify(text: str) → ClassificationResult(cert_type, confidence, all_scores):
    t = text.lower()
    scores = {ct: sum(1 for kw in kws if kw in t)/len(kws) for ct,kws in KEYWORDS.items()}
    best = max(scores, key=scores.get); conf = scores[best]
    if conf == 0: best = "UNKNOWN"
    return ClassificationResult(cert_type=best, confidence=round(conf,3), all_scores=scores)

services/ai/entity_extractor.py:
  def extract(text: str) → dict:
    result = {}
    for pat in [r"certify that ([A-Z][a-z]+(?: [A-Z][a-z]+)+)",
                r"Mr\.?s?\.?\s+([A-Z][a-z]+(?: [A-Z][a-z]+)+)"]:
      m = re.search(pat, text)
      if m: result['candidate_name'] = m.group(1); break
    lines=[l.strip() for l in text.split('\n') if l.strip()]
    org_kws=['Ltd','Inc','Technologies','University','College','Institute',
             'School','Pvt','Corp','Academy','Services']
    result['organization_name']=next(
      (l for l in lines[:5] if any(k in l for k in org_kws)), lines[0] if lines else None)
    for pat in [r"\d{2}[-/]\d{2}[-/]\d{4}",r"[A-Z][a-z]+ \d{1,2},? \d{4}",
                r"\d{1,2}(?:st|nd|rd|th)? [A-Z][a-z]+ \d{4}"]:
      m=re.search(pat,text)
      if m: result['issue_date']=m.group(); break
    m=re.search(r"(?:No|Certificate No|Ref|ID|Cert)\.?\s*[:\-]?\s*([A-Z0-9][A-Z0-9/\-]{3,20})",
      text,re.IGNORECASE)
    if m: result['cert_number']=m.group(1)
    m=re.search(r"https?://[\w.\-]+\.\w{2,}",text)
    if m: result['website']=m.group()
    m=re.search(r"[\w.\-]+@[\w.\-]+\.\w{2,}",text)
    if m: result['email']=m.group()
    m=re.search(r"(?:Authorized by|Principal|HR Manager|Director|Registrar)[\s\S]{0,60}?([A-Z][a-z]+(?: [A-Z][a-z]+)+)",text)
    if m: result['signatory']=m.group(1)
    return result

Update tasks/verification_task.py — REPLACE stub with real pipeline:
  STEP 1: Download cert file from cert.file_url using httpx
    file_ext = ".pdf" if mime_type=="application/pdf" else ".jpg"
    file_path = f"/tmp/{certificate_id}{file_ext}"
    r = httpx.get(cert.file_url, timeout=30); open(file_path,'wb').write(r.content)

  STEP 2: ocr_result = ocr_service.extract_text(file_path)
    Save VerificationResult(module_name="OCR_EXTRACTION",
      status='PASS' if avg_conf>0.5 else 'WARNING',
      finding_summary=f"{block_count} text blocks, {avg_conf:.0%} confidence",
      details={"full_text":full_text,"block_count":n,"avg_confidence":c})

  STEP 3: cls = classifier_service.classify(full_text)
    Save VerificationResult(module_name="CLASSIFICATION", status='PASS',
      finding_summary=f"{cls.cert_type} ({cls.confidence:.0%} confidence)",
      confidence_score=cls.confidence, details=cls.__dict__)

  STEP 4: entities = entity_extractor.extract(full_text)
    has_key = bool(entities.get('candidate_name') or entities.get('organization_name'))
    Save VerificationResult(module_name="ENTITY_EXTRACTION",
      status='PASS' if has_key else 'WARNING',
      finding_summary="Entities extracted" if has_key else "Limited text extraction",
      details=entities)

  STEP 5: job.progress_percentage=25; job.current_step="Company Verification"; db.commit()
  STEP 6: Keep as STUB — time.sleep(1), progress=100, COMPLETED (Phases 5-9 replace)
  Cleanup /tmp file in finally block

FRONTEND: Update VerificationResultPage after COMPLETED:
  Call GET /verify/{jobId}/results
  Show Shadcn Card "Extracted Information" with 2-col Table (Field | Value):
    Rows: Certificate Type | Candidate Name | Organization | Issue Date
          Cert Number | Website | Email | Signatory
    Show "—" for null. Cert Type row: confidence % as small Badge.
  Source: result with module_name=="ENTITY_EXTRACTION" → details
  Cert type: module_name=="CLASSIFICATION" → finding_summary

ACCEPTANCE CRITERIA:
✓ Upload PDF → OCR_EXTRACTION VerificationResult created in DB
✓ Certificate type correctly identified (test: edu cert → EDUCATIONAL)
✓ Candidate name + org extracted for standard certificate formats
✓ Extracted info table visible in VerificationResultPage frontend
✓ Job progress = 25 after OCR phase completes
✓ Flower shows Celery task completing with no errors
```

---

## Phase 5: Company Intelligence Verification

```
CERTVERIFY AI — PHASE 5: Online Company Intelligence & ISO Verification

BACKEND:
services/verification/company_intelligence.py:

async def verify_company(org_name: str, website: str|None) → CompanyVerificationResult:
  evidence=[]; online=False; web_active=False; web_match=False; ssl=False; mca=False
  async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
    # DuckDuckGo Instant Answer
    try:
      r=await client.get(f"https://api.duckduckgo.com/?q={org_name}&format=json&no_html=1&skip_disambig=1")
      d=r.json()
      if d.get("AbstractURL"): evidence.append(d["AbstractURL"]); online=True
      if d.get("RelatedTopics"): online=True
      summary=d.get("AbstractText","")[:300]
    except: summary=""
    # Website verification
    if website:
      try:
        r=await client.get(website,timeout=5.0)
        web_active=(r.status_code==200)
        web_match=org_name.lower() in r.text.lower()
        ssl=website.startswith("https")
        if web_active: evidence.append(website)
      except: web_active=False
    # India MCA hint
    try:
      r=await client.get(f"https://api.duckduckgo.com/?q={org_name}+site:mca.gov.in&format=json&no_html=1")
      mca=bool("mca.gov.in" in r.json().get("AbstractURL",""))
    except: pass
  confidence=round((0.4 if online else 0)+(0.3 if web_active else 0)+(0.3 if web_match else 0),2)
  return CompanyVerificationResult(org_name=org_name,website_provided=website,
    website_active=web_active,website_matches_org=web_match,ssl_valid=ssl,
    online_presence_found=online,search_summary=summary,
    mca_hint=mca,confidence_score=confidence,evidence_sources=evidence)

async def verify_iso(org_name: str, ocr_text: str) → ISOVerificationResult:
  ISO_PATTERNS=["iso 9001","iso 14001","iso 27001","iso 45001","iso/iec 27001"]
  found=[p for p in ISO_PATTERNS if p in ocr_text.lower()]
  if not found: return ISOVerificationResult(claimed=False,status="NOT_CLAIMED",standards=[])
  evidence=False
  async with httpx.AsyncClient(timeout=8.0,headers={"User-Agent":"Mozilla/5.0"}) as client:
    try:
      r=await client.get(f"https://api.duckduckgo.com/?q={org_name}+ISO+certification&format=json&no_html=1")
      evidence=bool(r.json().get("AbstractURL") or r.json().get("RelatedTopics"))
    except: pass
  return ISOVerificationResult(claimed=True,
    status="EVIDENCE_FOUND" if evidence else "UNVERIFIED",
    standards=found,evidence_found=evidence)

services/ai/logo_similarity.py:
async def compare_logo(image_path: str, website_url: str|None) → LogoSimilarityResult:
  if not website_url: return LogoSimilarityResult(attempted=False,favicon_found=False,similarity_score=0.0)
  domain=urlparse(website_url).netloc
  async with httpx.AsyncClient(timeout=5.0) as client:
    try:
      r=await client.get(f"https://{domain}/favicon.ico")
      if r.status_code!=200: return LogoSimilarityResult(attempted=True,favicon_found=False,similarity_score=0.0)
      site_img=Image.open(BytesIO(r.content)).resize((64,64)).convert("RGB")
      cert_img=Image.open(image_path).convert("RGB")
      w,h=cert_img.size
      logo=cert_img.crop((0,0,w//4,h//4)).resize((64,64))
      ham=imagehash.phash(logo)-imagehash.phash(site_img)
      return LogoSimilarityResult(attempted=True,favicon_found=True,similarity_score=round(1-ham/64,2))
    except: return LogoSimilarityResult(attempted=True,favicon_found=False,similarity_score=0.0)

Update tasks/verification_task.py — after STEP 5 (progress 25), add:
  STEP 6: Get entities and OCR text from previous VerificationResults
    entity_res=db.query(VerificationResult).filter_by(job_id=job_id,module_name="ENTITY_EXTRACTION").first()
    entities=entity_res.details if entity_res else {}
    ocr_res=db.query(VerificationResult).filter_by(job_id=job_id,module_name="OCR_EXTRACTION").first()
    ocr_text=ocr_res.details.get("full_text","") if ocr_res else ""
    org_name=entities.get("organization_name","")
    website=entities.get("website")

  STEP 7: (use asyncio.run() since Celery is synchronous)
    cv=asyncio.run(verify_company(org_name,website))
    ci_status='PASS' if cv.confidence_score>0.5 else 'WARNING' if cv.confidence_score>0.2 else 'FAIL'
    Save VerificationResult(module_name="COMPANY_INTELLIGENCE",status=ci_status,
      finding_summary=f"Company {'found online' if cv.online_presence_found else 'not found online'}",
      confidence_score=cv.confidence_score,details=cv.__dict__)

  STEP 8: iso=asyncio.run(verify_iso(org_name,ocr_text))
    iso_status='SKIPPED' if not iso.claimed else ('PASS' if iso.evidence_found else 'WARNING')
    Save VerificationResult(module_name="ISO_VERIFICATION",status=iso_status,
      finding_summary=iso.status.replace('_',' '),details=iso.__dict__)

  STEP 9: logo=asyncio.run(compare_logo(file_path,website))
    logo_status='PASS' if logo.similarity_score>0.6 else 'WARNING' if logo.favicon_found else 'SKIPPED'
    Save VerificationResult(module_name="LOGO_SIMILARITY",status=logo_status,
      finding_summary=f"Similarity: {logo.similarity_score:.0%}" if logo.favicon_found else "Favicon not found",
      details=logo.__dict__)

  STEP 10: job.progress_percentage=45; job.current_step="Document Forensics"; db.commit()
  Keep rest STUB: sleep(1), progress=100, COMPLETED

FRONTEND: Add "Company Intelligence" Shadcn Card to VerificationResultPage:
  Find result with module_name==="COMPANY_INTELLIGENCE"
  Rows:
    Organization Name (from ENTITY_EXTRACTION entities)
    Website: URL as link + green ● Active / red ● Inactive badge
    Online Presence: ✓ Found (green) or ✗ Not Found (red)
    India MCA Hint: Found / Not Checked
    ISO Claim: Not Claimed / Evidence Found / Unverified (badge)
    Logo Match: similarity% or "Not checked"
  Evidence Sources: each URL as small <a> link
  Confidence: Shadcn Progress 0–100

ACCEPTANCE CRITERIA:
✓ DuckDuckGo API called with extracted org name (verify in Celery logs)
✓ Website active/inactive correctly detected for real company websites
✓ ISO claim detected when ISO keywords present in certificate text
✓ COMPANY_INTELLIGENCE VerificationResult saved with PASS/WARNING/FAIL
✓ Company card renders in frontend result page
✓ Job progress = 45 after this phase
```

---

## Phase 6: Document Forensics & Forgery Detection

```
CERTVERIFY AI — PHASE 6: AI Document Forensics & Image Manipulation Detection

BACKEND:
services/ai/document_forensics.py:

def analyze_pdf_metadata(file_path: str) → dict:
  doc=fitz.open(file_path); meta=doc.metadata; flags=[]
  if meta.get("modDate") and meta.get("creationDate") and meta["modDate"]>meta["creationDate"]:
    flags.append("Document modified after original creation date")
  page=doc[0]
  fonts=page.get_fonts(full=True)
  unique_families=len(set(f[3] for f in fonts if f[3]))
  if unique_families>4: flags.append(f"Unusual font variety ({unique_families} font families)")
  image_count=len(page.get_images())
  ann_count=len(list(page.annots())) if hasattr(page,'annots') else 0
  if ann_count>0: flags.append(f"{ann_count} annotation(s) found (unusual)")
  confidence=min(len(flags)/3.0,1.0)
  return {"modification_suspected":bool(flags and flags[0].startswith('Document modified')),
    "font_family_count":unique_families,"font_inconsistency":unique_families>4,
    "image_count":image_count,"annotation_count":ann_count,
    "suspicious_flags":flags,"confidence_score":round(confidence,2)}

def perform_ela(image_path: str) → dict:
  original=Image.open(image_path).convert("RGB")
  tmp=tempfile.mktemp(suffix=".jpg")
  original.save(tmp,"JPEG",quality=75)
  resaved=Image.open(tmp).convert("RGB")
  diff=ImageChops.difference(original,resaved)
  diff_arr=np.array(diff,dtype=np.float32)
  ela_mean=float(np.mean(diff_arr))
  ela_suspicious=ela_mean>25.0
  os.remove(tmp)
  return {"ela_mean":round(ela_mean,2),"ela_suspicious":ela_suspicious,"threshold":25.0}

def analyze_exif(image_path: str) → dict:
  EDIT_SW=["photoshop","gimp","adobe","lightroom","pixelmator","affinity"]
  editing_software=None; has_gps=False
  try:
    img=Image.open(image_path); exif=img._getexif() or {}
    for tag_id,val in exif.items():
      if isinstance(val,str):
        for sw in EDIT_SW:
          if sw in val.lower(): editing_software=val; break
    has_gps=34853 in exif
  except: pass
  return {"editing_software_detected":editing_software,"has_gps_data":has_gps}

def create_annotated_image(image_path: str, ela_data: dict, cert_id: str) → str|None:
  if not ela_data["ela_suspicious"]: return None
  original=Image.open(image_path).convert("RGB")
  tmp=tempfile.mktemp(suffix=".jpg")
  original.save(tmp,"JPEG",quality=75)
  resaved=Image.open(tmp).convert("RGB")
  diff_arr=np.array(ImageChops.difference(original,resaved),dtype=np.float32)
  diff_gray=np.mean(diff_arr,axis=2)
  t95=np.percentile(diff_gray,95)
  coords=np.where(diff_gray>t95)
  overlay=original.copy(); draw=ImageDraw.Draw(overlay)
  if coords[0].size>100:
    y0,y1=int(coords[0].min()),int(coords[0].max())
    x0,x1=int(coords[1].min()),int(coords[1].max())
    draw.rectangle([x0,y0,x1,y1],outline="red",width=4)
    draw.text((x0,max(0,y0-20)),"⚠ Suspicious Region",fill="red")
  out=f"/tmp/annotated_{cert_id}.jpg"; overlay.save(out); os.remove(tmp)
  import cloudinary.uploader as cu
  result=cu.upload(out,folder="certverify/forensics",public_id=f"annotated_{cert_id}")
  os.remove(out)
  return result["secure_url"]

Update tasks/verification_task.py — after STEP 10 (progress 45), add:
  STEP 11: PDF forensics (if file is PDF)
    if file_path.endswith('.pdf'):
      pdf_data=document_forensics.analyze_pdf_metadata(file_path)
      pdf_status='FAIL' if pdf_data['confidence_score']>0.5 else 'WARNING' if pdf_data['confidence_score']>0 else 'PASS'
      Save VerificationResult(module_name="PDF_FORENSICS",status=pdf_status,
        finding_summary='; '.join(pdf_data['suspicious_flags']) or "No suspicious metadata",
        details=pdf_data)
    else:
      Save VerificationResult(module_name="PDF_FORENSICS",status='SKIPPED',finding_summary="Not a PDF")

  STEP 12: Convert to image if needed
    if file_path.endswith('.pdf'):
      pix=fitz.open(file_path)[0].get_pixmap(matrix=fitz.Matrix(2,2))
      img_path=file_path.replace('.pdf','_page.png'); pix.save(img_path)
    else: img_path=file_path

  STEP 13: Image forensics
    ela_data=document_forensics.perform_ela(img_path)
    exif_data=document_forensics.analyze_exif(img_path)
    annotated_url=document_forensics.create_annotated_image(img_path,ela_data,certificate_id)
    flags=[]
    if ela_data['ela_suspicious']: flags.append(f"ELA detected potential manipulation (score:{ela_data['ela_mean']:.1f})")
    if exif_data['editing_software_detected']: flags.append(f"Editing software: {exif_data['editing_software_detected']}")
    img_status='FAIL' if(ela_data['ela_suspicious'] and exif_data['editing_software_detected']) else 'WARNING' if flags else 'PASS'
    Save VerificationResult(module_name="IMAGE_FORENSICS",status=img_status,
      finding_summary='; '.join(flags) or "No image manipulation detected",
      details={**ela_data,**exif_data,"annotated_image_url":annotated_url})

  STEP 14: job.progress_percentage=65; job.current_step="QR Verification"; db.commit()
  Keep rest STUB: sleep(1), progress=100, COMPLETED
  Clean up img_path if it was converted from PDF

FRONTEND: Add "Document Forensics" Shadcn Card to VerificationResultPage:
  Find IMAGE_FORENSICS result
  If details.annotated_image_url:
    <img src={url} className="w-full rounded border-2 border-red-300" />
    Caption: "⚠ Suspicious regions highlighted"
  Suspicious flags: each as orange Badge with AlertTriangle icon
  PDF subsection (if PDF_FORENSICS not SKIPPED):
    Rows: Modification Suspected / Font Families / Annotations
  ELA subsection: ela_mean score, ela_suspicious yes/no
  Editing Software: show if detected else "Not detected"
  Card header Badge: CLEAN (green) | MINOR ISSUES (yellow) | SUSPICIOUS (red)

ACCEPTANCE CRITERIA:
✓ PDF metadata modification detection works
✓ ELA analysis runs for image certificates
✓ Annotated image created + uploaded to Cloudinary when ela_suspicious=True
✓ IMAGE_FORENSICS VerificationResult saved with PASS/WARNING/FAIL
✓ Forensics card shows annotated image in frontend
✓ Job progress = 65 after this phase
```

---

## Phase 7: QR Code & Digital Signature

```
CERTVERIFY AI — PHASE 7: QR Code Scanning & Digital Signature Verification

BACKEND:
services/verification/qr_verification.py:

def scan_qr(image_path: str) → list[QRData(type,data)]:
  img=cv2.imread(image_path)
  decoded=pyzbar.decode(img)
  return [QRData(type=d.type,data=d.data.decode()) for d in decoded]

async def verify_qr_url(qr_data: str, org_domain: str|None) → QRURLResult:
  SUSPICIOUS_HOSTS={"bit.ly","tinyurl.com","goo.gl","t.co",
    "wix.com","weebly.com","wordpress.com","blogspot.com"}
  if not qr_data.startswith("http"):
    return QRURLResult(raw_data=qr_data,is_url=False,active=False,
      ssl_ok=False,domain_type="TEXT_DATA",is_suspicious=False)
  parsed=urlparse(qr_data); domain=parsed.netloc
  is_suspicious=domain in SUSPICIOUS_HOSTS
  matches_org=org_domain and org_domain in domain if org_domain else None
  active=False; ssl_ok=qr_data.startswith("https")
  async with httpx.AsyncClient(timeout=5.0,follow_redirects=True) as client:
    try: r=await client.get(qr_data); active=(r.status_code==200)
    except: pass
  domain_type="OFFICIAL" if matches_org else "SUSPICIOUS" if is_suspicious else "THIRD_PARTY"
  return QRURLResult(raw_data=qr_data,is_url=True,domain=domain,
    active=active,ssl_ok=ssl_ok,domain_type=domain_type,is_suspicious=is_suspicious)

services/verification/signature_verifier.py:
def check_pdf_signature(file_path: str) → SignatureResult:
  if not file_path.endswith(".pdf"):
    return SignatureResult(applicable=False)
  doc=fitz.open(file_path); sig_widgets=[]
  for page in doc:
    for w in (page.get_widgets() or []):
      if w.field_type_string=="Signature": sig_widgets.append(w)
  has_field=len(sig_widgets)>0
  is_signed=any(w.field_value for w in sig_widgets)
  signer=sig_widgets[0].field_value if is_signed else None
  return SignatureResult(applicable=True,has_signature_field=has_field,
    is_signed=is_signed,signer_name=signer)

Update tasks/verification_task.py — after STEP 14 (progress 65), add:
  STEP 15: Load image (convert PDF page if needed)
    if file_path.endswith('.pdf'):
      pix=fitz.open(file_path)[0].get_pixmap(matrix=fitz.Matrix(2,2))
      img_path=file_path.replace('.pdf','_qr.png'); pix.save(img_path)
    else: img_path=file_path

  STEP 16: QR scan
    entity_res=db.query(VerificationResult).filter_by(job_id=job_id,module_name="ENTITY_EXTRACTION").first()
    org_website=entity_res.details.get("website","") if entity_res else ""
    org_domain=urlparse(org_website).netloc if org_website else None
    qr_list=qr_verification.scan_qr(img_path)
    if qr_list:
      qr_results=[asyncio.run(verify_qr_url(q.data,org_domain)) for q in qr_list]
      all_suspicious=any(r.is_suspicious for r in qr_results)
      Save VerificationResult(module_name="QR_CODE",
        status='FAIL' if all_suspicious else 'PASS',
        finding_summary=f"{len(qr_list)} QR code(s) found",
        details={"qr_results":[r.__dict__ for r in qr_results]})
    else:
      Save VerificationResult(module_name="QR_CODE",status='SKIPPED',finding_summary="No QR code present")

  STEP 17: PDF signature
    sig=signature_verifier.check_pdf_signature(file_path)
    if sig.applicable:
      sig_status='PASS' if sig.is_signed else 'WARNING'
      Save VerificationResult(module_name="DIGITAL_SIGNATURE",status=sig_status,
        finding_summary="Signed" if sig.is_signed else "Signature field present but unsigned",
        details=sig.__dict__)
    else:
      Save VerificationResult(module_name="DIGITAL_SIGNATURE",status='SKIPPED',
        finding_summary="Not a PDF or no signature field")

  STEP 18: job.progress_percentage=75; job.current_step="Duplicate Detection"; db.commit()
  Keep rest STUB: sleep(1), progress=100, COMPLETED

FRONTEND: Add "QR & Digital Signature" Shadcn Card to VerificationResultPage:
  QR Code section:
    SKIPPED: "Not present" (gray badge)
    PASS: list each QR with URL preview + domain_type badge
      OFFICIAL=green, THIRD_PARTY=blue, SUSPICIOUS=red
  Digital Signature section:
    SKIPPED: "Not applicable" (gray)
    PASS: "Signed ✓" + signer name if available
    WARNING: "Signature field present but unsigned"

ACCEPTANCE CRITERIA:
✓ QR codes detected in test certificates that have them
✓ Suspicious URL patterns flagged (bit.ly etc.) as FAIL
✓ SKIPPED saved when no QR code present
✓ PDF digital signature field detected
✓ QR & Signature card renders correctly in frontend
✓ Job progress = 75 after this phase
```

---

## Phase 8: Duplicate Detection

```
CERTVERIFY AI — PHASE 8: Duplicate Certificate Detection

BACKEND:
services/verification/duplicate_detector.py:
  _st_model=None  # lazy load sentence-transformers
  def get_model():
    global _st_model
    if not _st_model:
      from sentence_transformers import SentenceTransformer
      _st_model=SentenceTransformer("all-MiniLM-L6-v2")
    return _st_model

  def compute_fingerprint(image_path: str, text: str) → FingerprintData(phash,dhash,text_hash):
    img=Image.open(image_path).convert("RGB")
    ph=str(imagehash.phash(img)); dh=str(imagehash.dhash(img))
    text_norm=" ".join(text.lower().split())
    th=hashlib.sha256(text_norm.encode()).hexdigest()
    return FingerprintData(phash=ph,dhash=dh,text_hash=th)

  def find_duplicates(cert_id: str, fp: FingerprintData, cur_text: str, db) → list[DuplicateMatch]:
    all_fps=db.query(CertificateFingerprint).filter(CertificateFingerprint.certificate_id!=cert_id).all()
    matches=[]
    cur_hash=imagehash.hex_to_hash(fp.phash)
    for stored in all_fps:
      stored_hash=imagehash.hex_to_hash(stored.phash)
      hamming=cur_hash-stored_hash
      img_sim=round(1-(hamming/64),3)
      if img_sim<0.70: continue  # skip low similarity
      text_sim=0.0
      stored_ocr=db.query(VerificationResult).filter_by(
        module_name="OCR_EXTRACTION").join(VerificationJob).filter(
        VerificationJob.certificate_id==stored.certificate_id).first()
      if stored_ocr and cur_text:
        stored_text=stored_ocr.details.get("full_text","")[:500]
        model=get_model()
        embs=model.encode([cur_text[:500],stored_text])
        from sklearn.metrics.pairwise import cosine_similarity
        text_sim=float(cosine_similarity([embs[0]],[embs[1]])[0][0])
      match_type="EXACT" if hamming==0 else "NEAR_DUPLICATE" if hamming<10 else "SIMILAR_TEMPLATE"
      cert=db.query(Certificate).get(stored.certificate_id)
      matches.append(DuplicateMatch(certificate_id=str(cert.id),filename=cert.original_filename,
        upload_date=str(cert.created_at),img_similarity=img_sim,
        text_similarity=round(text_sim,3),match_type=match_type))
    return sorted(matches,key=lambda m:m.img_similarity,reverse=True)[:5]

Update tasks/verification_task.py — after STEP 18 (progress 75), add:
  STEP 19: Convert to image if PDF (re-use from forensics or convert again)
    img_path for fingerprinting
  STEP 20: Get OCR text
    ocr_res=db.query(VerificationResult).filter_by(job_id=job_id,module_name="OCR_EXTRACTION").first()
    ocr_text=ocr_res.details.get("full_text","") if ocr_res else ""
  STEP 21: Compute and save fingerprint
    fp=duplicate_detector.compute_fingerprint(img_path,ocr_text)
    db.add(CertificateFingerprint(certificate_id=certificate_id,phash=fp.phash,dhash=fp.dhash,text_hash=fp.text_hash))
    db.commit()
  STEP 22: Find duplicates
    matches=duplicate_detector.find_duplicates(certificate_id,fp,ocr_text,db)
    if matches:
      Save VerificationResult(module_name="DUPLICATE_DETECTION",status='WARNING',
        finding_summary=f"{len(matches)} similar certificate(s) found",
        details={"matches":[m.__dict__ for m in matches]})
    else:
      Save VerificationResult(module_name="DUPLICATE_DETECTION",status='PASS',
        finding_summary="No duplicate certificates found",details={"matches":[]})
  STEP 23: job.progress_percentage=85; job.current_step="Risk Assessment"; db.commit()
  Keep rest STUB: sleep(1), progress=100, COMPLETED

FRONTEND: Add "Duplicate Detection" Shadcn Card to VerificationResultPage:
  PASS: green badge "✓ No duplicate certificates found"
  WARNING: orange badge "⚠ {N} similar certificate(s) found"
    If matches: Shadcn Table with cols: Filename / Upload Date / Visual % / Text % / Type
    Visual match shown as mini Progress bar
    Note below: "Similar template doesn't necessarily indicate fraud. Manual verification recommended."

ACCEPTANCE CRITERIA:
✓ CertificateFingerprint row saved to DB after each upload
✓ Uploading same file twice → EXACT match detected with WARNING status
✓ Duplicate card shows in frontend with similarity scores
✓ sentence-transformers model loads and computes similarity without error
✓ PASS status saved when no similar certificates found
✓ Job progress = 85 after this phase
```

---

## Phase 9: Risk Assessment Engine

```
CERTVERIFY AI — PHASE 9: Risk Score, Final Verdict & Complete Result UI

BACKEND:
services/verification/risk_engine.py:

MODULE_WEIGHTS = {
  "OCR_EXTRACTION":5, "CLASSIFICATION":5, "ENTITY_EXTRACTION":5,
  "COMPANY_INTELLIGENCE":25, "LOGO_SIMILARITY":10, "ISO_VERIFICATION":5,
  "PDF_FORENSICS":20, "IMAGE_FORENSICS":25,
  "QR_CODE":15, "DIGITAL_SIGNATURE":10,
  "DUPLICATE_DETECTION":20
}
STATUS_RISK = {"PASS":0.0, "WARNING":0.5, "FAIL":1.0, "SKIPPED":None, "ERROR":None}

def calculate_risk(results: list[VerificationResult]) → RiskCalc:
  total_w=0; risk_pts=0
  for r in results:
    w=MODULE_WEIGHTS.get(r.module_name,5)
    contrib=STATUS_RISK.get(r.status)
    if contrib is not None: total_w+=w; risk_pts+=w*contrib
  score=int((risk_pts/max(total_w,1))*100)
  level="LOW" if score<=30 else "MEDIUM" if score<=60 else "HIGH"
  # Verdict logic
  forensic_fail=any(r.status=="FAIL" and r.module_name in ["IMAGE_FORENSICS","PDF_FORENSICS"] for r in results)
  company_ok=any(r.module_name=="COMPANY_INTELLIGENCE" and r.status=="PASS" for r in results)
  mostly_skipped=sum(1 for r in results if r.status=="SKIPPED")>len(results)*0.55
  if mostly_skipped: verdict="UNABLE_TO_VERIFY"
  elif forensic_fail or score>60: verdict="SUSPICIOUS"
  elif score<=30 and company_ok: verdict="VERIFIED"
  else: verdict="SUSPICIOUS"
  return RiskCalc(risk_score=score,risk_level=level,final_verdict=verdict,
    module_summary={r.module_name:r.status for r in results})

def generate_reasoning(results, calc: RiskCalc) → str:
  passed=[r for r in results if r.status=="PASS"]
  failed=[r for r in results if r.status in ("FAIL","WARNING")]
  skipped=[r for r in results if r.status=="SKIPPED"]
  t=f"CertVerify AI analyzed this certificate using {len(results)} verification modules. "
  if passed: t+=f"Passed: {', '.join(r.module_name.replace('_',' ').title() for r in passed[:4])}. "
  if failed: t+=f"Issues: {'; '.join(r.finding_summary for r in failed[:3])}. "
  if skipped: t+=f"Could not verify: {', '.join(r.module_name.replace('_',' ').title() for r in skipped[:3])}. "
  t+="Note: This system cannot access official issuing authority databases. "
  t+="Results are based on publicly available information and AI image analysis. "
  t+=f"Final: {calc.final_verdict.replace('_',' ')} (Risk Score: {calc.risk_score}/100)."
  return t

Update tasks/verification_task.py — REPLACE final STUB with real risk assessment:
  STEP 24: (FINAL STEP — replaces all stubs)
    results=db.query(VerificationResult).filter_by(job_id=job_id).all()
    calc=risk_engine.calculate_risk(results)
    reasoning=risk_engine.generate_reasoning(results,calc)
    db.add(RiskAssessment(job_id=job_id,risk_score=calc.risk_score,risk_level=calc.risk_level,
      final_verdict=calc.final_verdict,reasoning=reasoning))
    job.status='COMPLETED'; job.progress_percentage=100
    job.completed_at=datetime.utcnow(); db.commit()

FRONTEND (new components):
src/components/verification/RiskScoreCard.tsx:
  SVG circular arc 220x220px showing risk_score 0-100
  Arc color: score<=30→#27ae60 (green), <=60→#f39c12 (yellow), >60→#e74c3c (red)
  Center text: score number large + "/ 100" small
  Below arc: risk_level Badge (low=green, medium=yellow, high=red)
  Verdict banner below:
    VERIFIED: className="bg-green-100 border border-green-500 text-green-800 p-3 rounded"
    SUSPICIOUS: className="bg-red-100 border border-red-500 text-red-800 p-3 rounded"
    UNABLE_TO_VERIFY: className="bg-gray-100 border border-gray-400 text-gray-700 p-3 rounded"
  Shadcn Collapsible below: show reasoning text when expanded

src/components/verification/ModuleBreakdown.tsx:
  Shadcn Table: Module / Status / Finding / Confidence
  PASS: CheckCircle2 green, WARNING: AlertTriangle yellow, FAIL: XCircle red, SKIPPED: Minus gray
  Row onClick: expand to show JSON.stringify(details, null, 2) in <pre> tag

Update VerificationResultPage:
  After COMPLETED, show in order:
  1. RiskScoreCard (top)
  2. ModuleBreakdown
  3. Extracted Information card (Phase 4)
  4. Company Intelligence card (Phase 5)
  5. Document Forensics card (Phase 6)
  6. QR & Signature card (Phase 7)
  7. Duplicate Detection card (Phase 8)

ACCEPTANCE CRITERIA:
✓ Risk score 0-100 calculated from all module results
✓ VERIFIED: requires PASS company + risk_score≤30
✓ SUSPICIOUS: triggers on any forensics FAIL or score>60
✓ UNABLE_TO_VERIFY: when >55% modules are SKIPPED
✓ SVG circular score shows with correct color
✓ Module breakdown table shows all results with expand
✓ All 7 cards visible in correct order in result page
✓ Reasoning text readable in Collapsible
```

---

## Phase 10: PDF Report Generation

```
CERTVERIFY AI — PHASE 10: Downloadable Verification Report (ReportLab)

BACKEND:
services/report/report_generator.py:

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable, PageBreak
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.colors import HexColor

VERDICT_COLORS = {
  "VERIFIED": HexColor("#27ae60"),
  "SUSPICIOUS": HexColor("#e74c3c"),
  "UNABLE_TO_VERIFY": HexColor("#7f8c8d")
}
STATUS_BG = {"PASS":HexColor("#eafaf1"),"FAIL":HexColor("#fce9e8"),
  "WARNING":HexColor("#fef9e7"),"SKIPPED":HexColor("#f2f3f4"),"ERROR":HexColor("#fce9e8")}
STATUS_MARK = {"PASS":"✓","FAIL":"✗","WARNING":"⚠","SKIPPED":"–","ERROR":"!"}

async def generate_report(job_id: str, db) → str:
  # Fetch all data
  job=await db.get(VerificationJob, job_id)
  cert=await db.get(Certificate, job.certificate_id)
  results=(await db.execute(select(VerificationResult).where(VerificationResult.job_id==job_id))).scalars().all()
  risk=(await db.execute(select(RiskAssessment).where(RiskAssessment.job_id==job_id))).scalar_one()
  entity_res=next((r for r in results if r.module_name=="ENTITY_EXTRACTION"),None)
  entities=entity_res.details if entity_res else {}
  cls_res=next((r for r in results if r.module_name=="CLASSIFICATION"),None)

  buf=BytesIO()
  doc=SimpleDocTemplate(buf,pagesize=A4,topMargin=1.5*cm,bottomMargin=1.5*cm,leftMargin=2*cm,rightMargin=2*cm)
  styles=getSampleStyleSheet()
  story=[]

  # PAGE 1 — Header
  story.append(Paragraph("<b>CertVerify AI</b>",styles["Title"]))
  story.append(Paragraph("Certificate Verification Report",styles["Heading1"]))
  story.append(Paragraph(
    f"Report ID: {job_id[:8].upper()} | Generated: {datetime.utcnow().strftime('%d %b %Y, %H:%M UTC')}",
    styles["Normal"]))
  story.append(HRFlowable(width="100%",thickness=1,color=colors.grey))
  story.append(Spacer(1,0.3*cm))

  # Certificate details table
  cert_type=cls_res.finding_summary if cls_res else "Unknown"
  cert_data=[
    ["Field","Value"],
    ["Certificate Type",cert_type],
    ["Candidate Name",entities.get("candidate_name","—")],
    ["Organization",entities.get("organization_name","—")],
    ["Issue Date",entities.get("issue_date","—")],
    ["Certificate No.",entities.get("cert_number","—")],
    ["Filename",cert.original_filename],
    ["Upload Date",cert.created_at.strftime("%d %b %Y")],
  ]
  ct=Table(cert_data,colWidths=[5*cm,12*cm])
  ct.setStyle(TableStyle([
    ("BACKGROUND",(0,0),(-1,0),colors.lightgrey),
    ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
    ("GRID",(0,0),(-1,-1),0.5,colors.grey)
  ]))
  story.append(ct); story.append(Spacer(1,0.5*cm))

  # Verdict box
  story.append(Paragraph(f"Risk Score: {risk.risk_score} / 100 — {risk.risk_level} RISK",styles["Heading2"]))
  vt=Table([[Paragraph(
    f"<font color='white'><b>{risk.final_verdict.replace('_',' ')}</b></font>",styles["Normal"])]],
    colWidths=[17*cm])
  vt.setStyle(TableStyle([
    ("BACKGROUND",(0,0),(0,0),VERDICT_COLORS[risk.final_verdict]),
    ("ALIGN",(0,0),(0,0),"CENTER"),("TOPPADDING",(0,0),(0,0),10),("BOTTOMPADDING",(0,0),(0,0),10)
  ]))
  story.append(vt); story.append(Spacer(1,0.3*cm))
  story.append(Paragraph(risk.reasoning,styles["Normal"]))
  story.append(PageBreak())

  # PAGE 2 — Module Analysis
  story.append(Paragraph("Verification Module Analysis",styles["Heading2"]))
  mod_data=[["Module","Status","Finding","Confidence"]]
  for r in results:
    conf=f"{r.confidence_score:.0%}" if r.confidence_score else "—"
    mod_data.append([
      r.module_name.replace("_"," ").title(),
      f"{STATUS_MARK.get(r.status,'')} {r.status}",
      r.finding_summary[:55],
      conf
    ])
  mt=Table(mod_data,colWidths=[4.5*cm,3*cm,8*cm,2*cm])
  style_cmds=[
    ("BACKGROUND",(0,0),(-1,0),colors.lightgrey),
    ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
    ("GRID",(0,0),(-1,-1),0.5,colors.grey),
    ("FONTSIZE",(0,0),(-1,-1),9)
  ]
  for i,r in enumerate(results,1):
    style_cmds.append(("BACKGROUND",(0,i),(-1,i),STATUS_BG.get(r.status,colors.white)))
  mt.setStyle(TableStyle(style_cmds))
  story.append(mt); story.append(Spacer(1,0.5*cm))

  # Limitations
  story.append(Paragraph("Important Limitations",styles["Heading3"]))
  story.append(Paragraph(
    "This report is generated by AI-based analysis and does not constitute legal verification. "
    "Official issuing authority databases were not directly accessed. "
    "ELA forensic analysis may produce false positives for JPEG-compressed images. "
    "Always consult the issuing authority for definitive verification.",
    styles["Normal"]))

  def add_page_num(canvas,doc):
    canvas.saveState(); canvas.setFont("Helvetica",8)
    canvas.drawRightString(A4[0]-2*cm,1*cm,f"CertVerify AI | Confidential | Page {doc.page}")
    canvas.restoreState()

  doc.build(story,onFirstPage=add_page_num,onLaterPages=add_page_num)
  buf.seek(0)
  import cloudinary.uploader as cu
  result=cu.upload(buf,resource_type="raw",folder="certverify/reports",
    public_id=f"report_{job_id[:8]}",format="pdf")
  url=result["secure_url"]
  risk.report_url=url; await db.commit()
  return url

api/v1/endpoints/verify.py:
  GET /api/v1/verify/{job_id}/report (auth, verify ownership):
    If job.status!='COMPLETED' → HTTP 400 "Verification not complete"
    risk=await db... get RiskAssessment for job
    If risk.report_url: return {"report_url": risk.report_url}
    url=await generate_report(job_id, db)
    return {"report_url": url}

FRONTEND:
src/components/verification/ReportDownloadButton.tsx:
  Button "Download PDF Report" with Download icon (lucide-react), loading state "Generating..."
  On click: GET /api/v1/verify/{jobId}/report
  On success: window.open(report_url, "_blank")
  On error: destructive toast "Report generation failed"

Add ReportDownloadButton to VerificationResultPage below RiskScoreCard.
Add small Download icon button in HistoryPage Actions column for COMPLETED jobs.

ACCEPTANCE CRITERIA:
✓ PDF generates with all 4 sections (header, cert info, verdict box, module table)
✓ Verdict box colored correctly (green/red/gray)
✓ Report uploaded to Cloudinary certverify/reports/ as a PDF
✓ Download button opens PDF in new browser tab
✓ Module table rows color-coded by status (green/red/yellow/gray)
```

---

## Phase 11: Dashboards & Analytics

```
CERTVERIFY AI — PHASE 11: User Dashboard, Admin Panel & Analytics

BACKEND:
api/v1/endpoints/dashboard.py:

GET /api/v1/dashboard/stats (auth required):
  For current user, using async SQLAlchemy queries:
  total_uploads: count of non-deleted certificates for user
  verified_count: count of VERIFIED final_verdict (join certs→jobs→risk)
  suspicious_count: count of SUSPICIOUS verdicts
  unable_count: count of UNABLE_TO_VERIFY verdicts
  processing_count: jobs with status PENDING or PROCESSING
  avg_risk_score: avg(risk_score) from user's RiskAssessments
  uploads_by_day: last 7 days with COUNT per day (SQL date_trunc or GROUP BY DATE)
    Format: [{"date": "2026-11-01", "count": 3}, ...]
  Return all as DashboardStats schema

GET /api/v1/admin/stats (require_staff):
  total_users: count all users
  total_certificates: count all non-deleted
  verdicts: {VERIFIED: N, SUSPICIOUS: N, UNABLE_TO_VERIFY: N} from all RiskAssessments
  suspicious_this_week: SUSPICIOUS verdicts in last 7 days
  avg_processing_seconds: avg(EXTRACT(EPOCH FROM (completed_at - started_at))) for COMPLETED jobs
  daily_uploads_30d: last 30 days [{date, count}]
  Return AdminStats schema

GET /api/v1/admin/users (require_admin, page, size, search, role):
  Paginated users with upload_count subquery
  search: ILIKE on full_name and email
  Return PaginatedAdminUsers

PUT /api/v1/admin/users/{user_id} (require_admin):
  Accept {role?: str, is_active?: bool}
  Update user, return UserResponse

GET /api/v1/admin/certificates (require_staff, page, size, verdict, date_from, date_to):
  All certs (all users, is_deleted=False), join job+risk
  Include user_email in each row
  Return PaginatedAdminCerts with is_suspicious flag per row

FRONTEND:
src/pages/DashboardPage.tsx:
  Fetch GET /dashboard/stats on mount
  Row 1: 4 StatCards side by side:
    Total Uploads (FileText icon, blue), Verified (✓ CheckCircle2, green),
    Suspicious (⚠ AlertTriangle, orange), In Progress (Clock, yellow)
    Each shows animated count-up number (requestAnimationFrame 0→value in 1s)
  Row 2: BarChart "Uploads — Last 7 Days"
    Recharts ResponsiveContainer→BarChart, Bar dataKey="count" fill="#3b82f6" radius={[4,4,0,0]}
    XAxis: formatted dates ("Nov 01"), YAxis: integers only, Tooltip with count
  Row 3: "Recent Uploads" compact list (last 5 certs)
    filename, status badge, relative time ("2 hours ago" via date-fns formatDistance)
    View button → /verify/{job_id}
  Top right corner: prominent Button "Upload Certificate →" → /upload

src/pages/AdminPage.tsx:
  Redirect to /dashboard if role not ADMIN|HR_VERIFIER with toast "Access denied"
  Fetch GET /admin/stats on mount
  Shadcn Tabs with 3 tabs:

  Tab 1 "Overview":
    4 stat cards: total_users, total_certificates, suspicious_this_week, avg_processing_seconds
    LineChart "Daily Uploads (30 days)" using Recharts Line, responsive, smooth curve

  Tab 2 "Users":
    Debounced Search Input (300ms) + Role Select filter
    Shadcn Table: Name | Email | Role Badge | Status | Uploads | Joined | Actions
    Actions:
      Select dropdown for role (onChange: PUT /admin/users/{id} with {role})
      Shadcn Switch for is_active (onChange: PUT /admin/users/{id} with {is_active})
    Pagination

  Tab 3 "Certificates":
    Date range inputs (from/to) + Verdict Select filter
    Shadcn Table: Filename | Owner | Uploaded | Risk Score | Verdict | Actions
    Suspicious rows: className="bg-red-50 border-l-4 border-l-red-400"
    Actions: View button → /verify/{job_id}
    Pagination

src/components/dashboard/StatCard.tsx:
  Props: title, value: number, icon: LucideIcon, colorClass, subtitle?
  Shadcn Card, animated count-up, icon top-left, subtitle below value

src/components/dashboard/UploadsChart.tsx:
  Recharts BarChart wrapped in ResponsiveContainer height={200}
  Accept data: Array<{date: string, count: number}>

ACCEPTANCE CRITERIA:
✓ Dashboard shows correct per-user stats
✓ Bar chart renders with real upload data from last 7 days
✓ Admin panel only accessible to ADMIN|HR_VERIFIER
✓ Admin can change user role via dropdown
✓ Admin can toggle user is_active via Switch
✓ All certificates visible in admin Certificates tab
✓ Suspicious rows highlighted red in admin view
```

---

## Phase 12: Security & Production Deployment

```
CERTVERIFY AI — PHASE 12: Security Hardening & Production Deployment

BACKEND SECURITY:
1. Rate Limiting (slowapi):
   In main.py:
     from slowapi import Limiter, _rate_limit_exceeded_handler
     from slowapi.util import get_remote_address
     from slowapi.errors import RateLimitExceeded
     limiter=Limiter(key_func=get_remote_address)
     app.state.limiter=limiter
     app.add_exception_handler(RateLimitExceeded,_rate_limit_exceeded_handler)
   Apply decorators:
     @limiter.limit("5/minute") on POST /api/v1/auth/login
     @limiter.limit("3/minute") on POST /api/v1/auth/register
     @limiter.limit("10/hour") on POST /api/v1/certificates/upload
       (key by user_id: key_func=lambda req: str(req.state.user_id))

2. Security Headers Middleware (middleware/security_headers.py):
   class SecurityHeadersMiddleware(BaseHTTPMiddleware):
     async def dispatch(self, request, call_next):
       response=await call_next(request)
       response.headers["X-Content-Type-Options"]="nosniff"
       response.headers["X-Frame-Options"]="DENY"
       response.headers["X-XSS-Protection"]="1; mode=block"
       response.headers["Referrer-Policy"]="strict-origin-when-cross-origin"
       return response
   Add: app.add_middleware(SecurityHeadersMiddleware) in main.py

3. Audit Logging (models/audit_log.py + services/audit_service.py):
   AuditLog model: id UUID PK, user_id UUID nullable, action str, resource_type str,
     resource_id str nullable, ip_address str, user_agent str, created_at datetime
   async def log_action(db, user_id, action, resource_type, resource_id, request: Request):
     Create AuditLog; ip=request.client.host; ua=request.headers.get("user-agent","")
   Add log_action calls to:
     POST /auth/login → action="LOGIN"
     POST /auth/register → action="REGISTER"
     POST /certificates/upload → action="UPLOAD", resource_id=cert_id
     DELETE /certificates/{id} → action="DELETE", resource_id=cert_id
     GET /verify/{id}/report → action="DOWNLOAD_REPORT", resource_id=job_id
     PUT /admin/users/{id} → action="ADMIN_UPDATE_USER", resource_id=user_id
   Add alembic migration for audit_logs table
   Add GET /api/v1/admin/audit-logs (require_admin, page, size, user_id filter)

4. Startup Validation (core/startup.py):
   async def validate_startup():
     If settings.secret_key.startswith("change-this"): logger.warning("SECRET_KEY is default!")
     Test DB: await db.execute(text("SELECT 1"))
     Test Redis: redis_client.ping()
     logger.info("All startup checks passed")
   Call in @app.on_event("startup")

PRODUCTION DOCKER:
docker-compose.prod.yml:
  postgres: no exposed ports, restart: unless-stopped
  redis: same
  backend: image certverify-backend:latest,
    command: gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000,
    restart: unless-stopped, env_file .env.prod
  celery_worker: --concurrency=4, restart: unless-stopped
  nginx: nginx:alpine, ports 80:80 443:443,
    volumes ./nginx/nginx.conf:/etc/nginx/nginx.conf, restart: unless-stopped
  frontend: build from Dockerfile.prod, restart: unless-stopped

docker/backend/Dockerfile.prod (multi-stage):
  Stage 1 builder: python:3.11-slim, install all requirements
  Stage 2 runtime: python:3.11-slim, copy from builder,
    RUN adduser --disabled-password --no-create-home certverify
    USER certverify, WORKDIR /app
    CMD ["gunicorn","app.main:app","-w","4","-k","uvicorn.workers.UvicornWorker","--bind","0.0.0.0:8000"]

docker/frontend/Dockerfile.prod (multi-stage):
  Stage 1: node:20-alpine, npm run build → /app/dist
  Stage 2: nginx:alpine, COPY --from=stage1 /app/dist /usr/share/nginx/html
    COPY nginx-spa.conf /etc/nginx/conf.d/default.conf
  nginx-spa.conf: try_files $uri $uri/ /index.html; gzip on;
    gzip_types text/css application/javascript application/json;

nginx/nginx.conf:
  events { worker_connections 1024; }
  http {
    upstream backend { server backend:8000; }
    upstream frontend { server frontend:80; }
    server {
      listen 80; client_max_body_size 11M; gzip on;
      location /api/ {
        proxy_pass http://backend;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $host;
        proxy_read_timeout 120s;
      }
      location /health { proxy_pass http://backend; }
      location / { proxy_pass http://frontend; }
    }
  }

deploy.sh:
  #!/bin/bash
  set -e
  git pull origin main
  docker-compose -f docker-compose.prod.yml build
  docker-compose -f docker-compose.prod.yml run --rm backend alembic upgrade head
  docker-compose -f docker-compose.prod.yml up -d
  sleep 15
  curl -f http://localhost/health && echo "✓ Deployment successful" || (echo "✗ Failed" && exit 1)

FRONTEND:
src/components/ErrorBoundary.tsx (React class component):
  Catches unhandled JS errors
  Renders "Something went wrong" card with Retry button (window.location.reload())
Wrap <App> in <ErrorBoundary> in main.tsx.

ACCEPTANCE CRITERIA:
✓ 6th POST /auth/login in 1 minute → HTTP 429 response
✓ All API responses include X-Frame-Options: DENY header
✓ AuditLog rows created for login, upload, delete, report download
✓ docker-compose.prod.yml builds all images successfully
✓ Nginx serves /api/ → backend and / → frontend on port 80
✓ GET http://localhost/health through Nginx → {"status":"ok"}
✓ Production Docker containers run as non-root user
✓ Refresh on /dashboard in browser → app loads (SPA routing works)
```

---

## Recovery Tips

**Phase stuck / incomplete:** Quote the specific blocked task name and add: `"Continue implementing only: [TASK NAME] from Phase N"`

**TypeScript errors:** `"Fix all TypeScript errors. Do not change any business logic, only add correct type annotations."`

**Celery not running / no tasks in Flower:** `"Check Flower at localhost:5555. If no worker connected, debug the celery_worker Docker service. Check CELERY_BROKER_URL in .env."`

**Database migration conflict:**

```
docker-compose exec backend alembic stamp head
docker-compose exec backend alembic revision --autogenerate -m "fix"
docker-compose exec backend alembic upgrade head
```

**PaddleOCR download fails (first run):** Add to Dockerfile: `RUN python -c "from paddleocr import PaddleOCR; PaddleOCR(use_angle_cls=True, lang='en')"` to pre-download models during build.

**New session, continuing from Phase N:** Paste Master Context, then: `"CertVerify AI is already built through Phase [N-1]. All previous phases are complete. Implement Phase N starting from [specific TASK number]."`

**Agent produces generic/incomplete code:** Add to your prompt: `"Do NOT use placeholder comments like # TODO or pass. Write the full implementation for every function."`
