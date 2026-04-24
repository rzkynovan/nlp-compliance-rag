# AGENTS.md - Compliance Audit RAG Walkthrough

## Project Overview

**Nama Proyek:** Multi-Agent RAG for Compliance Audit
**Teknologi:** FastAPI + Next.js + ChromaDB + BM25 + MLflow + Docker
**Status:** Phase 8 — E2E Testing Complete (28/29 passed)
**Last Updated:** 2026-04-24

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- OpenAI API Key
- LlamaParse API Key

### 1. Setup Environment Variables

```bash
cp docker/.env.example docker/.env
# Edit docker/.env with your API keys
```

Required variables:
```
OPENAI_API_KEY=sk-xxx
LLAMAPARSE_API_KEY=llx-xxx
DATABASE_URL=postgresql://compliance:compliance123@db:5432/compliance_db
REDIS_URL=redis://redis:6379/0
MLFLOW_TRACKING_URI=http://mlflow:5000
```

### 2. Run with Docker (Recommended)

```bash
cd docker
docker-compose up -d

# Services will be available at:
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:8000
# - API Docs: http://localhost:8000/api/v1/docs
# - MLflow: http://localhost:5001
# - Grafana: http://localhost:3001
# - Prometheus: http://localhost:9090
```

### 3. Run Locally (Development)

**Backend:**
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd backend
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
pnpm install
pnpm dev
```

---

## 📁 Project Structure

### Root Directory

```
nlp-compliance-rag/
├── backend/                    # FastAPI Backend (Python)
├── frontend/                   # Next.js Frontend (TypeScript)
├── src/                        # Core RAG Logic (Python)
├── data/                       # Data Storage
├── docker/                     # Docker Configuration
├── monitoring/                 # Grafana Dashboards
├── KebutuhanTA/               # Thesis Documentation
├── AGENTS.md                  # This file
├── PROGRESS.md                # Implementation tracker
├── requirements.txt           # Python dependencies (src/)
├── test_integration.py        # Integration test script
└── .env.example              # Environment template
```

---

## 🐍 Backend Structure (`backend/`)

### Directory Layout

```
backend/
├── app/
│   ├── __init__.py            # App initialization
│   ├── main.py                # FastAPI entry point
│   ├── config.py              # Pydantic Settings
│   │
│   ├── api/v1/                # API Routes
│   │   ├── audit.py          # POST /audit/analyze, /audit/batch
│   │   ├── regulations.py    # GET /regulations, /regulations/search
│   │   ├── experiments.py    # MLflow experiment endpoints
│   │   ├── health.py         # /health, /ready endpoints
│   │   └── usage.py          # /usage, /budget, /cache endpoints
│   │
│   ├── models/                # Pydantic Models
│   │   ├── audit.py          # AuditRequest, AuditResponse, AgentVerdict
│   │   ├── regulation.py     # Regulation models
│   │   └── experiment.py     # Experiment tracking models
│   │
│   ├── core/                  # Core Utilities
│   │   ├── exceptions.py     # ComplianceAuditError hierarchy
│   │   ├── cache.py          # AuditCache (24h TTL)
│   │   ├── cost_tracker.py   # OpenAI cost tracking
│   │   └── rate_limiter.py   # API rate limiting
│   │
│   ├── services/              # Business Logic
│   │   ├── audit_service.py  # Audit orchestration (placeholder)
│   │   ├── rag_service.py    # Multi-agent RAG service ⭐
│   │   └── regulation_service.py
│   │
│   ├── pipeline/              # Data Pipeline
│   │   ├── extractor.py      # PDF extraction (LlamaParse)
│   │   ├── parser.py         # Regulation parser
│   │   └── chunker.py        # Semantic chunker
│   │
│   ├── ml/                    # ML Tracking
│   │   └── tracking.py        # MLflow integration
│   │
│   └── workers/               # Celery Tasks
│       ├── __init__.py
│       └── tasks.py          # Background tasks
│
└── requirements.txt           # Python dependencies
```

### Key Files Explained

#### `app/main.py` - Application Entry
- Creates FastAPI app with middleware
- Registers all routers (`/api/v1/*`)
- Configures CORS, error handlers
- Initializes logging

#### `app/config.py` - Configuration
```python
class Settings(BaseSettings):
    OPENAI_API_KEY: str
    LLAMAPARSE_API_KEY: str
    CHROMADB_PERSIST_DIR: str
    LLM_MODEL: str = "gpt-4o-mini"         # Cost optimized
    EMBEDDING_MODEL: str = "text-embedding-3-large"  # 3072 dim — wajib cocok dengan ChromaDB
    DAILY_BUDGET_LIMIT_USD: float = 5.0
    ALLOWED_ORIGINS: str = "http://localhost:3000"   # Parsed via allowed_origins_list property
```

> ⚠️ **PENTING:** `EMBEDDING_MODEL` harus `text-embedding-3-large` (3072 dimensi). Jika diubah ke
> `text-embedding-3-small` (1536 dim), ChromaDB akan mengembalikan 0 hasil karena dimensi tidak cocok
> dengan collection yang sudah dibangun saat ingest.

#### `app/services/rag_service.py` - RAG Service ⭐
**This is the main service connecting Backend ↔ Multi-agent System**

```python
class RAGAuditService:
    def __init__(self):
        self.chroma_path = settings.CHROMADB_PERSIST_DIR
        self._coordinator = None  # Lazy load
    
    async def analyze_with_rag(self, clause, regulator, top_k):
        # 1. Check ChromaDB availability
        # 2. If available → use multi-agent RAG
        # 3. If not → fallback to LLM-only
        
    async def _analyze_with_multi_agent(self, clause, regulator, top_k):
        coordinator = self._get_coordinator()
        result = await coordinator.audit_clause_async(...)
        return {
            "final_status": result.final_verdict.final_status,
            "bi_verdict": result.bi_verdict,
            "ojk_verdict": result.ojk_verdict,
            "recommendations": result.final_verdict.recommendations,
            "analysis_mode": "multi_agent_rag"
        }
```

**Path Resolution:**
```python
# Add src/ to Python path for imports
_src_paths = [
    "/app/src",  # Docker path
    str(Path(__file__).parent.parent.parent.parent / "src"),  # Local
]
```

#### `app/api/v1/audit.py` - Audit Endpoint
```python
@router.post("/analyze", response_model=AuditResponse)
async def analyze_sop(request: AuditRequest):
    service = get_rag_service()  # Singleton
    result = await service.analyze_with_rag(
        clause=request.clause,
        regulator=request.regulator,
        top_k=request.top_k
    )
    return AuditResponse(...)
```

---

## 🎨 Frontend Structure (`frontend/`)

### Directory Layout

```
frontend/
├── app/                        # Next.js App Router
│   ├── layout.tsx              # Root layout (QueryProvider + Toaster)
│   ├── template.tsx            # Page transitions (Framer Motion)
│   ├── page.tsx                # Dashboard home (/) — stat cards real data
│   ├── audit/page.tsx          # Audit page (/audit) — tab: Input Teks | Upload Dokumen
│   ├── history/page.tsx        # Audit history (/history)
│   ├── experiments/page.tsx    # MLflow experiments (/experiments)
│   ├── settings/page.tsx       # Settings (/settings) — shadcn Select + toast
│   ├── not-found.tsx           # 404 page
│   └── error.tsx               # Error boundary
│
├── components/
│   ├── ui/                     # shadcn/ui primitives
│   │   ├── button.tsx          # Primary variant: bg-[hsl(var(--primary))] (ITS Blue)
│   │   ├── input.tsx
│   │   ├── textarea.tsx
│   │   ├── form.tsx
│   │   ├── select.tsx
│   │   ├── card.tsx
│   │   ├── switch.tsx
│   │   ├── skeleton.tsx
│   │   └── loading-spinner.tsx
│   │
│   ├── layout/                 # Layout components
│   │   ├── Sidebar.tsx         # Collapsible nav (state di Zustand ui-store)
│   │   └── DashboardLayout.tsx # Animated layout, margin responsif ke sidebar
│   │
│   ├── providers/              # Context providers
│   │   ├── QueryProvider.tsx   # TanStack Query v5 setup
│   │   └── LenisProvider.tsx   # Lenis smooth scroll
│   │
│   ├── motion/                 # Animasi komponen
│   │   ├── FadeIn.tsx
│   │   ├── MagneticButton.tsx
│   │   └── TextReveal.tsx
│   │
│   ├── common/                 # Shared components
│   │   └── ErrorBoundary.tsx   # Error handling
│   │
│   └── audit/                  # Audit feature components
│       ├── AuditForm.tsx       # SOP text input form (react-hook-form + zod)
│       ├── FileUploadZone.tsx  # Drag & drop PDF/TXT/MD upload → ekstrak klausa ⭐
│       └── ResultCard.tsx      # Audit result (6 status, AgentVerdictCard, evidence trail)
│
├── lib/
│   ├── api.ts                  # API functions: analyzeCompliance, uploadDocument, getUsageStats
│   ├── api/
│   │   ├── client.ts           # ky instance (timeout: 120_000ms)
│   │   ├── query-keys.ts       # TanStack Query keys
│   │   └── index.ts
│   ├── query-client.ts         # QueryClient config
│   ├── stores/
│   │   └── ui-store.ts         # Zustand: sidebar collapse state
│   └── utils.ts                # Utilities (cn, etc.)
│
├── package.json
├── tailwind.config.ts
├── tsconfig.json
├── postcss.config.js
└── .env.local
```

---

## 🔬 Core RAG Logic (`src/`)

### Directory Layout

```
src/
├── agents/                     # Multi-agent System
│   ├── __init__.py
│   ├── base_agent.py          # Base agent class (hybrid_retriever + query_analyzer fields)
│   ├── bi_specialist.py      # BI regulation specialist (hybrid routing)
│   ├── ojk_specialist.py     # OJK regulation specialist (hybrid routing)
│   ├── conflict_resolver.py  # Conflict resolution
│   ├── coordinator.py        # Multi-agent orchestrator ⭐
│   └── run_audit.py          # CLI entry point
│
├── retrieval/                  # Hybrid Retrieval System (Phase 7)
│   ├── __init__.py            # Export semua modul retrieval
│   ├── metadata_extractor.py # Ekstrak regulation_code, pasal_number, ayat_number dari chunk
│   ├── query_analyzer.py     # Deteksi intent → QueryIntent (is_specific, sparse_boost)
│   ├── bm25_retriever.py     # BM25Okapi sparse retriever, persist ke disk per-collection
│   └── hybrid_retriever.py   # RRF Fusion: dense (ChromaDB) + sparse (BM25)
│
├── ingest.py                  # PDF→ChromaDB+BM25 pipeline (diperkaya metadata)
├── llama_cache.py            # LlamaParse caching
├── audit.py                   # Single-agent audit
├── batch_audit.py            # Batch processing
└── evaluation.py              # Metrics calculation
```

### Agent Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Coordinator Agent                       │
│                    (coordinator.py)                          │
│                                                              │
│  ┌──────────────────┐          ┌──────────────────┐       │
│  │   BI Specialist   │          │  OJK Specialist   │       │
│  │ (bi_specialist.py)│          │(ojk_specialist.py)│       │
│  │                   │          │                   │       │
│  │  - ChromaDB BI    │          │  - ChromaDB OJK   │       │
│  │  - RAG Retrieval  │          │  - RAG Retrieval  │       │
│  │  - LLM Analysis   │          │  - LLM Analysis   │       │
│  └────────┬─────────┘          └────────┬─────────┘       │
│           │                              │                  │
│           └──────────────┬───────────────┘                  │
│                          │                                  │
│                          ▼                                  │
│              ┌───────────────────────┐                       │
│              │   Conflict Resolver   │                       │
│              │(conflict_resolver.py) │                       │
│              │                       │                       │
│              │ - Reg. Hierarchy      │                       │
│              │ - Priority Rules      │                       │
│              │ - Final Verdict       │                       │
│              └───────────────────────┘                       │
└─────────────────────────────────────────────────────────────┘
```

### Key Files Explained

#### `src/agents/coordinator.py` - Multi-agent Orchestrator

```python
class CoordinatorAgent:
    def __init__(self):
        self.bi_agent = BISpecialistAgent()
        self.ojk_agent = OJKSpecialistAgent()
        self.resolver = ConflictResolverAgent()
    
    def initialize(self, api_key, chroma_path):
        self.bi_agent.initialize(api_key, chroma_path)
        self.ojk_agent.initialize(api_key, chroma_path)
    
    async def audit_clause_async(self, clause, clause_id, context):
        # 1. Run BI and OJK agents in parallel
        bi_task = asyncio.create_task(self._analyze_with_bi(clause))
        ojk_task = asyncio.create_task(self._analyze_with_ojk(clause))
        bi_verdict, ojk_verdict = await asyncio.gather(bi_task, ojk_task)
        
        # 2. Resolve conflicts via ConflictResolverAgent
        final_verdict = self.resolver.resolve(bi_verdict, ojk_verdict, ...)
        
        return AuditResult(...)
```

#### `src/agents/bi_specialist.py` - BI Regulation Agent

```python
class BISpecialistAgent(BaseAgent):
    def initialize(self, api_key, chroma_path):
        # 1. Initialize OpenAI LLM
        self.llm = OpenAI(model="gpt-4o-mini")
        # 2. Load ChromaDB collection
        self.collection = chromadb.get_collection("bi_regulations")
        # 3. Setup embedding model — WAJIB text-embedding-3-large (3072 dim)
        self.embed_model = OpenAIEmbedding(model="text-embedding-3-large")
        # 4. Load BM25 index jika tersedia (Phase 7)
        bm25 = BM25Retriever(index_path=BM25_INDEX_DIR / "bi_regulations")
        if bm25.load_index():
            self.hybrid_retriever = HybridRetriever(self.index, bm25)
            self.query_analyzer   = QueryAnalyzer()
    
    def retrieve_relevant_articles(self, query, top_k=5):
        intent = self.query_analyzer.analyze(query)
        if self.hybrid_retriever and intent.is_specific:
            # Query mengandung nomor pasal/kode regulasi → hybrid (BM25 dominan, alpha=0.7)
            return self.hybrid_retriever.retrieve(query, intent, top_k)
        # Query semantik biasa → dense-only ChromaDB
        return self._dense_retrieve(query, top_k)
```

#### `src/retrieval/hybrid_retriever.py` - Hybrid Retrieval (Phase 7) ⭐

```python
class HybridRetriever:
    def retrieve(self, query, intent, top_k=5):
        dense_results  = self._dense_retrieve(query, top_k * 2)   # ChromaDB cosine
        sparse_results = self.bm25.retrieve(query, top_k * 2)     # BM25Okapi
        fused = self._rrf_fusion(dense_results, sparse_results,
                                  alpha=intent.sparse_boost)       # 0.7 jika specific
        return fused[:top_k]

    def _rrf_fusion(self, dense, sparse, alpha=0.5, k=60):
        # score(d) = alpha * 1/(k+rank_sparse) + (1-alpha) * 1/(k+rank_dense)
        ...
```

**Routing logic:**
```
Query "Pasal 160 ayat 2 batas saldo"
    → QueryAnalyzer: is_specific=True, sparse_boost=0.7
    → HybridRetriever: dense + BM25 → RRF Fusion

Query "apa aturan tentang pengaduan konsumen"
    → QueryAnalyzer: is_specific=False, sparse_boost=0.3
    → Dense-only (ChromaDB cosine similarity)
```

#### `src/agents/conflict_resolver.py` - Conflict Resolution

```python
class ConflictResolverAgent:
    RESOLUTION_PRINCIPLES = {
        "CONSUMER_PROTECTION": {"priority": "OJK over BI"},
        "FINANCIAL_STABILITY": {"priority": "BI over OJK"},
        "STRICTER_STANDARD":   {"priority": "Apply stricter standard"}
    }
    
    def resolve(self, bi_verdict, ojk_verdict, clause_category):
        # 1. Determine conflict type
        # 2. Apply resolution principles
        # 3. Generate final verdict with 6-class output
        return FinalVerdict(...)
```

---

## 🔗 Cross-Folder References

### Backend ↔ Core RAG (`src/`)

```
backend/app/services/rag_service.py
    ↓ imports
src/agents/coordinator.py
    ↓ imports
src/agents/bi_specialist.py
src/agents/ojk_specialist.py
src/agents/conflict_resolver.py
```

**How it works:**
1. `rag_service.py` adds `/app/src` or `../src` to `sys.path`
2. Imports `CoordinatorAgent` from `agents.coordinator`
3. Coordinator runs BI + OJK agents in parallel
4. Returns combined verdict to API endpoint

### Backend ↔ Frontend

```
frontend/lib/api.ts
    ↓ HTTP requests
backend/app/api/v1/audit.py
    ↓ calls
backend/app/services/rag_service.py
```

**API Contract:**
```typescript
// Frontend request — single audit
interface AuditRequest {
  clause: string;
  regulator: "all" | "BI" | "OJK";
  top_k?: number;
  clause_id?: string;
}

// Backend response — 6 status class
type ComplianceStatus =
  | "COMPLIANT" | "NON_COMPLIANT" | "PARTIALLY_COMPLIANT"
  | "NEEDS_REVIEW" | "NOT_ADDRESSED" | "UNCLEAR";

interface AuditResponse {
  request_id: string;
  final_status: ComplianceStatus;
  overall_confidence: number;  // 0.0–1.0
  risk_score: number;          // 0.0–1.0
  bi_verdict: AgentVerdict;
  ojk_verdict: AgentVerdict;
  violations: string[];
  recommendations: string[];
  evidence_references: string[];
  latency_ms: number;
  analysis_mode: "multi_agent_rag" | "llm_only";
  retrieval_mode: "hybrid" | "dense";  // Phase 7
}

// Document upload → clause extraction
interface UploadDocumentResult {
  filename: string;
  file_size_kb: number;
  text: string;
  clauses: string[];
  clause_count: number;
}
```

### Core RAG ↔ ChromaDB

```
src/agents/bi_specialist.py
    ↓ queries
data/processed/chroma_db/
├── bi_regulations/      # 1,590 vectors
├── ojk_regulations/     # 1,031 vectors  
└── chroma.sqlite3       # SQLite metadata
```

### Docker Volume Mappings

```yaml
# docker/docker-compose.yml
services:
  backend:
    volumes:
      - ../data:/app/data          # ChromaDB data (environment-specific)
      # src/ is BAKED into the image via COPY src/ /app/src/
      # This makes the image self-contained — no repo clone needed to run
```

---

## 🔧 API Endpoints

### Health Check

```bash
GET /api/v1/health
GET /api/v1/ready
```

### Audit

```bash
# Single clause audit
POST /api/v1/audit/analyze
{
  "clause": "Saldo maksimal untuk akun unverified adalah Rp 10.000.000",
  "top_k": 5,
  "regulator": "all"
}

# Response:
{
  "request_id": "uuid",
  "final_status": "NON_COMPLIANT",
  "overall_confidence": 0.9,
  "risk_score": 0.85,
  "bi_verdict": {
    "status": "NON_COMPLIANT",
    "confidence": 0.95,
    "violations": ["Pasal 160 Ayat 1 — batas saldo unverified Rp 2.000.000"],
    "reasoning": "..."
  },
  "ojk_verdict": {...},
  "violations": ["..."],
  "recommendations": ["..."],
  "evidence_references": ["PBI 23/6/2021 Pasal 160 Ayat 1"],
  "latency_ms": 3500,
  "analysis_mode": "multi_agent_rag",
  "retrieval_mode": "hybrid"
}

# Batch audit (multiple clauses)
POST /api/v1/audit/batch
{
  "clauses": ["klausa 1...", "klausa 2...", "klausa 3..."],
  "regulator": "all"
}

# Document upload → extract clauses
POST /api/v1/audit/upload
Content-Type: multipart/form-data
file: <PDF|TXT|MD file, max 10MB>

# Response:
{
  "filename": "SOP_EWallet.pdf",
  "file_size_kb": 245.3,
  "text": "...",
  "clauses": ["klausa 1...", "klausa 2...", ...],
  "clause_count": 12
}
```

### Cost Tracking

```bash
GET /api/v1/usage          # Today's usage stats + monthly + cache_stats
GET /api/v1/budget         # Remaining budget
GET /api/v1/cache/stats    # Cache hit rate
```

---

## 🧪 Testing

### Unit Tests (pytest)

```bash
cd backend
pip install -r requirements.txt
python -m pytest tests/ -v
```

**Test files:**

| File | Coverage |
|------|----------|
| `tests/test_exceptions.py` | Custom exception hierarchy (11 classes) |
| `tests/test_cache.py` | AuditCache get/set/TTL/clear/disk |
| `tests/test_cost_tracker.py` | CostTracker pricing, budget, record |
| `tests/test_models.py` | Pydantic model validation & boundaries |
| `tests/test_audit_api.py` | FastAPI endpoints via TestClient |
| `tests/test_rag_service.py` | RAGAuditService with mocked OpenAI |

**Result:** 175 tests, 175 passed ✅

### Manual Testing

```bash
# Test multi-agent RAG
curl -X POST http://localhost:8000/api/v1/audit/analyze \
  -H "Content-Type: application/json" \
  -d '{"clause": "Batas transaksi harian untuk akun unverified adalah Rp 20.000.000", "regulator": "BI"}'

# Test health
curl http://localhost:8000/api/v1/health
```

### Integration Test

```bash
# Run integration test
cd nlp-compliance-rag
source venv/bin/activate
python test_integration.py
```

---

## 📊 Monitoring

### Services

| Service | Port | Purpose |
|---------|------|---------|
| Frontend | 3000 | Next.js App |
| Backend | 8000 | FastAPI |
| ChromaDB | 8001 | Vector DB |
| PostgreSQL | 5432 | Metadata |
| Redis | 6379 | Cache/Queue |
| MLflow | 5001 | Experiments |
| Grafana | 3001 | Dashboards |
| Prometheus | 9090 | Metrics |

---

## 🐛 Troubleshooting

### ChromaDB Empty Error

```bash
# Check ChromaDB status
docker exec backend python -c "
import chromadb
client = chromadb.PersistentClient(path='/app/data/processed/chroma_db')
for c in client.list_collections():
    print(f'{c.name}: {c.count()} vectors')
"

# Re-ingest if needed
python src/ingest.py --force
```

### Module Not Found: 'agents'

```bash
# Check Python path
docker exec backend python -c "import sys; print(sys.path)"

# Expected paths:
# /app/src
# /app/app
# ...
```

### Docker Container Issues

```bash
# Rebuild backend
cd docker
docker-compose build --no-cache backend
docker-compose up -d backend

# Check logs
docker-compose logs -f backend
```

---

## 📝 Architecture Summary

```
┌──────────────────────────────────────────────────────────────────────┐
│                      Frontend (Next.js 14)                           │
│                    http://localhost:3000                              │
│                                                                      │
│  ┌──────────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ AuditForm        │  │ ResultCard   │  │ History/Experiments   │  │
│  │ /audit           │  │ (6 statuses) │  │ /history /experiments │  │
│  │ ├─ Tab Teks      │  │ AgentVerdict │  └───────────────────────┘  │
│  │ └─ FileUploadZone│  │ EvidenceTrail│                              │
│  └──────┬───────────┘  └──────────────┘                              │
│         │ HTTP (ky, timeout 120s)                                    │
└─────────┼────────────────────────────────────────────────────────────┘
          │
          ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                               │
│                    http://localhost:8000                              │
│                                                                      │
│  POST /audit/analyze   POST /audit/batch   POST /audit/upload        │
│              │                │                    │                 │
│              └────────────────┴────────────────────┘                 │
│                               ↓                                      │
│         app/services/rag_service.py  ←── Cache (24h) + Cost Tracker │
│                               ↓                                      │
│              src/agents/coordinator.py                               │
│                ├── bi_specialist.py  ← HybridRetriever (Phase 7)    │
│                ├── ojk_specialist.py ← HybridRetriever (Phase 7)    │
│                └── conflict_resolver.py → final verdict (6 kelas)   │
│                                                                      │
└──────────┬───────────────────────────────────────┬───────────────────┘
           │                                       │
           ▼                                       ▼
┌──────────────────────┐             ┌─────────────────────────┐
│   ChromaDB + BM25    │             │     OpenAI API          │
│   (Hybrid Retrieval) │             │  LLM: gpt-4o-mini       │
│                      │             │  Embeddings:            │
│ BI:  1,590 vectors   │             │  text-embedding-3-large │
│ OJK: 1,031 vectors   │             │  (3072 dim) ⚠️           │
│ BM25 BI:  1,590 idx  │             └─────────────────────────┘
│ BM25 OJK: 1,031 idx  │
└──────────────────────┘
```

---

## 📚 Key Concepts

### Multi-Agent RAG Flow

1. **Request** → API receives clause (text input / hasil upload dokumen)
2. **Check Cache** → Return cached result if exists (24h TTL)
3. **Check Budget** → Reject if over daily limit
4. **Query Analysis** → `QueryAnalyzer` deteksi intent (nomor pasal/kode regulasi?)
5. **Retrieve** → `HybridRetriever`: BM25+Dense jika specific, Dense-only jika semantik
6. **Analyze** → `BISpecialistAgent` + `OJKSpecialistAgent` berjalan paralel
7. **Resolve** → `ConflictResolverAgent` gabungkan verdik → 6-class output
8. **Cache Result** → Store for 24 hours
9. **Return** → Response dengan `retrieval_mode`, `analysis_mode`, evidence trail

### Cost Optimization

- **Caching**: 24-hour TTL untuk query identik
- **Model Selection**: gpt-4o-mini (lebih ekonomis dari gpt-4o)
- **Embeddings**: text-embedding-3-large (wajib cocok dengan ChromaDB — jangan diganti)
- **Budget Tracking**: Daily limit enforcement via `CostTracker`
- **Rate Limiting**: API protection via `RateLimiter`
- **LlamaParse Cache**: PDF parsing di-cache untuk menghindari biaya re-parse

### Performa Sistem (dari E2E Test Phase 8)

| Metrik | Nilai |
|--------|-------|
| Single audit latency | ~3.5–5.6 detik |
| Batch 3 klausul | ~12 detik total |
| Cost per 6 API calls | $0.0012 |
| ChromaDB BI vectors | 1,590 |
| ChromaDB OJK vectors | 1,031 |
| BM25 BI index | 1,590 chunks |
| Unit tests | 175/175 ✅ |
| E2E tests | 28/29 ✅ |

---

## 👥 Authors

- **Nama Mahasiswa** - NRP: XXXXXXXXXX
- **Pembimbing:** [Nama Dosen Pembimbing]

---

*Last updated: 2026-04-24*