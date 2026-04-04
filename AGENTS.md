# AGENTS.md - Compliance Audit RAG Walkthrough

## Project Overview

**Nama Proyek:** Multi-Agent RAG for Compliance Audit
**Teknologi:** FastAPI + Next.js + ChromaDB + MLflow + Docker
**Status:** Development

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
    LLM_MODEL: str = "gpt-4o-mini"      # Cost optimized
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    DAILY_BUDGET_LIMIT_USD: float = 5.0
```

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
│   ├── layout.tsx              # Root layout (QueryProvider)
│   ├── page.tsx                # Dashboard home (/)
│   ├── audit/page.tsx          # Audit form page (/audit)
│   ├── history/page.tsx        # Audit history (/history)
│   ├── experiments/page.tsx    # MLflow experiments (/experiments)
│   ├── settings/page.tsx       # Settings (/settings)
│   ├── not-found.tsx           # 404 page
│   ├── error.tsx               # Error boundary
│   └── template.tsx            # Page transitions
│
├── components/
│   ├── ui/                     # shadcn/ui primitives
│   │   ├── button.tsx
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
│   │   ├── Sidebar.tsx         # Collapsible navigation
│   │   ├── DashboardLayout.tsx # Animated layout wrapper
│   │   └── index.ts
│   │
│   ├── providers/              # Context providers
│   │   ├── QueryProvider.tsx   # React Query setup
│   │   └── index.ts
│   │
│   ├── common/                 # Shared components
│   │   └── ErrorBoundary.tsx   # Error handling
│   │
│   └── audit/                  # Audit components
│       ├── AuditForm.tsx       # SOP input form
│       └── ResultCard.tsx      # Audit result display
│
├── lib/
│   ├── api.ts                  # Axios client
│   ├── api/                    # API utilities
│   │   ├── client.ts           # Axios instance
│   │   ├── query-keys.ts       # React Query keys
│   │   └── index.ts
│   ├── stores/
│   │   └── ui-store.ts         # Zustand store
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
│   ├── base_agent.py          # Base agent class
│   ├── bi_specialist.py      # BI regulation specialist
│   ├── ojk_specialist.py     # OJK regulation specialist
│   ├── conflict_resolver.py  # Conflict resolution
│   ├── coordinator.py        # Multi-agent orchestrator ⭐
│   └── run_audit.py          # CLI entry point
│
├── ingest.py                  # PDF→ChromaDB pipeline
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
        
        # 2. Resolve conflicts
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
        # 3. Setup embedding model
        self.embed_model = OpenAIEmbedding(model="text-embedding-3-small")
    
    def analyze(self, clause):
        # 1. Retrieve relevant articles from ChromaDB
        evidence = self._retrieve_evidence(clause, top_k=5)
        # 2. Build prompt with evidence
        prompt = self._build_prompt(clause, evidence)
        # 3. Get LLM verdict
        response = self.llm.complete(prompt)
        return self._parse_verdict(response, evidence)
```

#### `src/agents/conflict_resolver.py` - Conflict Resolution

```python
class ConflictResolverAgent:
    RESOLUTION_PRINCIPLES = {
        "CONSUMER_PROTECTION": {"priority": "OJK over BI"},
        "FINANCIAL_STABILITY": {"priority": "BI over OJK"},
        "STRICHER_STANDARD": {"priority": "Apply stricter standard"}
    }
    
    def resolve(self, bi_verdict, ojk_verdict, clause_category):
        # 1. Determine conflict type
        # 2. Apply resolution principles
        # 3. Generate final verdict
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
// Frontend request
interface AuditRequest {
  clause: string;
  regulator: "all" | "BI" | "OJK";
  top_k?: number;
  clause_id?: string;
}

// Backend response
interface AuditResponse {
  request_id: string;
  final_status: ComplianceStatus;
  overall_confidence: number;
  bi_verdict: AgentVerdict;
  ojk_verdict: AgentVerdict;
  violations: string[];
  recommendations: string[];
  latency_ms: number;
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
      - ../data:/app/data          # ChromaDB data
      - ../src:/app/src            # Core RAG logic
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
  "risk_score": 0.1,
  "bi_verdict": {
    "status": "NON_COMPLIANT",
    "confidence": 0.95,
    "violations": ["Pasal 160 Ayat 1"],
    "reasoning": "..."
  },
  "ojk_verdict": {...},
  "violations": ["..."],
  "recommendations": ["..."],
  "latency_ms": 15953,
  "analysis_mode": "multi_agent_rag"
}
```

### Cost Tracking

```bash
GET /api/v1/usage          # Today's usage stats
GET /api/v1/budget         # Remaining budget
```

---

## 🧪 Testing

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
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                        │
│                    http://localhost:3000                         │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ AuditForm    │  │ ResultCard   │  │ History/Experiments   │  │
│  │ /audit       │  │ Display      │  │ /history /experiments │  │
│  └──────┬───────┘  └──────────────┘  └───────────────────────┘  │
│         │ HTTP POST                                               │
└─────────┼───────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                           │
│                    http://localhost:8000                         │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ app/api/v1/audit.py                                        │ │
│  │   ↓                                                        │ │
│  │ app/services/rag_service.py  ←── Cache + Cost Tracker     │ │
│  │   ↓                                                        │ │
│  │ src/agents/coordinator.py                                 │ │
│  │   ├── bi_specialist.py                                    │ │
│  │   ├── ojk_specialist.py                                   │ │
│  │   └── conflict_resolver.py                                │ │
│  └────────────────────────────────────────────────────────────┘ │
│         │                      │                                 │
└─────────┼──────────────────────┼─────────────────────────────────┘
          │                      │
          ▼                      ▼
┌──────────────────┐   ┌───────────────────┐
│   ChromaDB        │   │   OpenAI API      │
│ (Vector Store)    │   │   (LLM/GPT-4o)    │
│                   │   │                   │
│ BI: 1,590 vectors │   │ Embeddings:       │
│ OJK: 1,031 vectors│   │ text-embedding-   │
│                   │   │ 3-small            │
└──────────────────┘   └───────────────────┘
```

---

## 📚 Key Concepts

### Multi-Agent RAG Flow

1. **Request** → API receives clause
2. **Check Cache** → Return cached result if exists
3. **Check Budget** → Reject if over limit
4. **Retrieve** → Query ChromaDB for relevant articles
5. **Analyze** → Run BI and OJK agents in parallel
6. **Resolve** → Combine verdicts with conflict resolver
7. **Cache Result** → Store for 24 hours
8. **Return** → Send verdict to frontend

### Cost Optimization

- **Caching**: 24-hour TTL for identical queries
- **Model Selection**: gpt-4o-mini (17x cheaper than gpt-4o)
- **Embeddings**: text-embedding-3-small (6x cheaper than large)
- **Budget Tracking**: Daily limit enforcement
- **Rate Limiting**: Prevent abuse

---

## 👥 Authors

- **Nama Mahasiswa** - NRP: XXXXXXXXXX
- **Pembimbing:** [Nama Dosen Pembimbing]

---

*Last updated: 2025-04-05*