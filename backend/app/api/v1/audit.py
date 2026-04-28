from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Depends
from typing import List
from datetime import datetime
import uuid
import time
import sys
import os
import io
import re

from sqlalchemy.orm import Session
from sqlalchemy import func, case

from app.models.audit import (
    AuditRequest, AuditResponse, BatchAuditRequest, BatchAuditResponse,
    ComplianceStatus, AgentVerdict, EvidenceItem, AuditHistoryItem
)
from app.services.rag_service import get_rag_service
from app.db import get_db, _to_row, _from_row, AuditHistoryRow

router = APIRouter(prefix="/audit", tags=["audit"])

RISK_SCORE_MAP = {"LOW": 0.25, "MEDIUM": 0.5, "HIGH": 0.75}


def _map_status(status: str) -> ComplianceStatus:
    # Normalize: replace hyphen variant (NON-COMPLIANT) → underscore (NON_COMPLIANT)
    normalized = str(status).upper().replace("-", "_").strip()
    status_mapping = {
        "COMPLIANT": ComplianceStatus.COMPLIANT,
        "NON_COMPLIANT": ComplianceStatus.NON_COMPLIANT,
        "PARTIALLY_COMPLIANT": ComplianceStatus.PARTIALLY_COMPLIANT,
        "NEEDS_REVIEW": ComplianceStatus.NEEDS_REVIEW,
        "NOT_ADDRESSED": ComplianceStatus.NOT_ADDRESSED,
        "UNCLEAR": ComplianceStatus.UNCLEAR,
        "NEEDS_HUMAN_REVIEW": ComplianceStatus.NEEDS_REVIEW,
    }
    return status_mapping.get(normalized, ComplianceStatus.UNCLEAR)


def _map_risk_score(risk_score) -> float:
    if isinstance(risk_score, str):
        return RISK_SCORE_MAP.get(risk_score.upper(), 0.5)
    return float(risk_score) if risk_score is not None else 0.5


def _extract_verdict_data(verdict_data, agent_name: str) -> AgentVerdict:
    if not verdict_data:
        return AgentVerdict(
            agent_name=agent_name,
            status=ComplianceStatus.UNCLEAR,
            confidence=0.5,
            violations=[],
            evidence=[],
            reasoning="No verdict available"
        )
    
    # Extract violations - handle both dict and string formats
    raw_violations = verdict_data.get("violations", verdict_data.get("violated_articles", []))
    violations = []
    for v in raw_violations:
        if isinstance(v, dict):
            regulation = v.get("regulation", v.get("reg", ""))
            article    = v.get("article", v.get("pasal", ""))
            detail     = v.get("violation", v.get("violation_detail", v.get("description", "")))
            required   = v.get("required", v.get("required_value", ""))
            actual     = v.get("actual", v.get("actual_value", ""))

            parts = []
            if regulation:
                parts.append(regulation)
            if article:
                parts.append(article)
            prefix = " — ".join(parts) if parts else "Pelanggaran"

            body = detail or ""
            if required and actual:
                body += f" (seharusnya: {required}, aktual: {actual})"
            elif required:
                body += f" (nilai wajib: {required})"

            violations.append(f"{prefix}: {body}" if body else prefix)
        elif isinstance(v, str) and v.strip():
            violations.append(v.strip())
    
    # Extract evidence
    evidence = []
    for e in verdict_data.get("evidence", []):
        if isinstance(e, dict):
            evidence.append(EvidenceItem(
                regulation=e.get("regulation", ""),
                article=e.get("article", ""),
                article_text=e.get("article_text", ""),
                relevance_score=e.get("relevance_score", 0.5)
            ))
    
    return AgentVerdict(
        agent_name=agent_name,
        status=_map_status(verdict_data.get("verdict", verdict_data.get("status", "UNCLEAR"))),
        confidence=verdict_data.get("confidence_score", verdict_data.get("confidence", 0.5)),
        violations=violations,
        evidence=evidence,
        reasoning=verdict_data.get("reasoning_trace", verdict_data.get("reasoning", ""))
    )


@router.post("/analyze", response_model=AuditResponse)
async def analyze_sop(request: AuditRequest):
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    try:
        service = get_rag_service()
        result = await service.analyze_with_rag(
            clause=request.clause,
            regulator=request.regulator,
            top_k=request.top_k,
            clause_id=request.clause_id,
            use_cache=request.use_cache
        )
        
        latency_ms = (time.time() - start_time) * 1000
        
        bi_verdict = _extract_verdict_data(result.get("bi_verdict"), "BI_SPECIALIST")
        ojk_verdict = _extract_verdict_data(result.get("ojk_verdict"), "OJK_SPECIALIST")

        # Aggregate violations from both agents into root field
        all_violations = list(result.get("violations") or [])
        for v in (bi_verdict.violations or []):
            if v and v not in all_violations:
                all_violations.append(v)
        for v in (ojk_verdict.violations or []):
            if v and v not in all_violations:
                all_violations.append(v)

        response = AuditResponse(
            request_id=request_id,
            timestamp=datetime.now(),
            clause=request.clause,
            clause_id=request.clause_id,
            bi_verdict=bi_verdict,
            ojk_verdict=ojk_verdict,
            final_status=_map_status(result.get("final_status", "UNCLEAR")),
            overall_confidence=result.get("overall_confidence", 0.5),
            risk_score=_map_risk_score(result.get("risk_score")),
            violations=all_violations,
            recommendations=result.get("recommendations", []),
            latency_ms=result.get("latency_ms", latency_ms),
            model_used=result.get("model_used", "gpt-5.4-mini"),
            tokens_used=0
        )
        
        # Persist to PostgreSQL
        try:
            from app.db import get_session_factory
            factory = get_session_factory()
            db = factory()
            try:
                db.add(_to_row(response))
                db.commit()
            finally:
                db.close()
        except Exception as db_err:
            import logging
            logging.getLogger(__name__).warning(f"DB write failed (returning response anyway): {db_err}")

        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audit failed: {str(e)}")


@router.post("/batch", response_model=BatchAuditResponse)
async def batch_analyze(request: BatchAuditRequest, background_tasks: BackgroundTasks):
    results = []
    total_tokens = 0
    status_counts = {}
    
    for clause_request in request.clauses:
        response = await analyze_sop(clause_request)
        results.append(response)
        total_tokens += response.tokens_used
        
        status = response.final_status.value
        status_counts[status] = status_counts.get(status, 0) + 1
    
    return BatchAuditResponse(
        request_id=str(uuid.uuid4()),
        timestamp=datetime.now(),
        total_clauses=len(results),
        results=results,
        summary={
            "total_tokens": total_tokens,
            "status_distribution": status_counts,
            "avg_latency_ms": sum(r.latency_ms for r in results) / len(results)
        }
    )


@router.get("/history/stats")
async def get_audit_history_stats():
    """Aggregate stats across ALL audit records — not paginated."""
    from app.db import get_session_factory
    factory = get_session_factory()
    db = factory()
    try:
        total = db.query(func.count(AuditHistoryRow.request_id)).scalar() or 0
        if total == 0:
            return {"total": 0, "compliant": 0, "non_compliant": 0, "partially_compliant": 0,
                    "not_addressed": 0, "unclear": 0, "avg_latency_ms": 0}
        rows = db.query(AuditHistoryRow.final_status, func.count().label("cnt")).group_by(AuditHistoryRow.final_status).all()
        counts = {r.final_status: r.cnt for r in rows}
        avg_latency = db.query(func.avg(AuditHistoryRow.latency_ms)).scalar() or 0
        return {
            "total": total,
            "compliant": counts.get("COMPLIANT", 0),
            "non_compliant": counts.get("NON_COMPLIANT", 0),
            "partially_compliant": counts.get("PARTIALLY_COMPLIANT", 0) + counts.get("NEEDS_REVIEW", 0),
            "not_addressed": counts.get("NOT_ADDRESSED", 0),
            "unclear": counts.get("UNCLEAR", 0),
            "avg_latency_ms": round(avg_latency, 0),
        }
    finally:
        db.close()


@router.get("/history", response_model=List[AuditResponse])
async def get_audit_history(
    skip: int = 0,
    limit: int = 20,
    search: str = "",
    status: str = "",
):
    from app.db import get_session_factory
    factory = get_session_factory()
    db = factory()
    try:
        q = db.query(AuditHistoryRow)
        if status:
            q = q.filter(AuditHistoryRow.final_status == status)
        if search:
            term = f"%{search.lower()}%"
            from sqlalchemy import or_
            q = q.filter(or_(
                func.lower(AuditHistoryRow.clause).like(term),
                func.lower(AuditHistoryRow.request_id).like(term),
            ))
        rows = q.order_by(AuditHistoryRow.timestamp.desc()).offset(skip).limit(limit).all()
        return [_from_row(r, AuditResponse, AgentVerdict, EvidenceItem, ComplianceStatus) for r in rows]
    finally:
        db.close()


@router.get("/{request_id}", response_model=AuditResponse)
async def get_audit_detail(request_id: str):
    from app.db import get_session_factory
    factory = get_session_factory()
    db = factory()
    try:
        row = db.query(AuditHistoryRow).filter(AuditHistoryRow.request_id == request_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Audit request not found")
        return _from_row(row, AuditResponse, AgentVerdict, EvidenceItem, ComplianceStatus)
    finally:
        db.close()


# ── Document Upload ────────────────────────────────────────────────────────────

ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".txt", ".md"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

# Regex untuk strip header/footer browser (timestamp + URL + nomor halaman)
# Contoh: "3/23/26, 3:36 AM Syarat dan Ketentuan GoPay https://... 17/19"
_BROWSER_HEADER_RE = re.compile(
    r'\d{1,2}/\d{1,2}/\d{2,4},?\s+\d{1,2}:\d{2}\s*(?:AM|PM)?\s*.*?https?://\S+\s*\d+/\d+',
    re.IGNORECASE,
)

# Mapping ligature yang rusak akibat encoding PDF → ASCII
_LIGATURE_MAP = [
    ("ﬁ", "fi"),   # ﬁ  (fi ligature)
    ("ﬂ", "fl"),   # ﬂ  (fl ligature)
    ("ﬃ", "ffi"),  # ﬃ
    ("ﬄ", "ffl"),  # ﬄ
    ("ï¬",    "fi"),   # fi ligature salah-decode via latin-1
    ("ï¬‚",   "fl"),   # fl ligature salah-decode
    ("’", "'"),    # right single quotation mark
    ("‘", "'"),    # left single quotation mark
    ("“", '"'),    # left double quotation mark
    ("”", '"'),    # right double quotation mark
    ("–", "-"),    # en dash
    ("—", "--"),   # em dash
]


def _clean_pdf_text(text: str) -> str:
    """Bersihkan artefak umum dari PDF hasil browser print / LlamaParse."""
    # Fix ligature dan karakter khusus
    for bad, good in _LIGATURE_MAP:
        text = text.replace(bad, good)

    # Fix italic spacing dari LlamaParse: "d a t a m i n e" → "data mine"
    # Deteksi: 3+ huruf tunggal berurutan dipisah spasi
    text = re.sub(r'\b([a-zA-Z]) ([a-zA-Z]) ([a-zA-Z])(?: ([a-zA-Z]))*\b',
                  lambda m: m.group(0).replace(" ", ""), text)

    # Strip baris header/footer browser (timestamp + URL + nomor halaman)
    text = _BROWSER_HEADER_RE.sub("", text)
    # Hapus baris yang hanya berisi URL
    text = re.sub(r'^\s*https?://\S+\s*$', '', text, flags=re.MULTILINE)
    # Hapus URL yang muncul di tengah/akhir paragraf (sisa LlamaParse page footer)
    text = re.sub(r'\s*https?://\S+\s*\d+/\d+', '', text)
    # Hapus heading halaman LlamaParse yang muncul di tengah teks
    # Contoh: "# Syarat dan Ketentuan GoPay" atau "Syarat dan Ketentuan GoPay" standalone
    text = re.sub(r'#{1,3}\s+[^\n]{5,60}\n', '', text)
    text = re.sub(r'(?<!\w)(Syarat dan Ketentuan GoPay|Terms and Conditions GoPay)\s*', '', text)

    # Normalise multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


async def _extract_pdf_text_llamaparse(content: bytes, filename: str, use_cache: bool = True) -> tuple[str, bool]:
    """
    Ekstrak teks PDF menggunakan LlamaParse API dengan caching berbasis SHA-256.

    Returns:
        (text, from_cache) — from_cache=True jika hasil diambil dari cache disk.
    """
    import tempfile
    import sys
    from pathlib import Path
    from app.config import settings

    api_key = settings.LLAMA_CLOUD_API_KEY
    if not api_key:
        raise HTTPException(status_code=501, detail="LLAMA_CLOUD_API_KEY tidak dikonfigurasi.")

    try:
        from llama_parse import LlamaParse
    except ImportError:
        raise HTTPException(status_code=501, detail="llama-parse tidak terinstall.")

    # Resolve llama_cache dari src/
    _src_paths = ["/app/src", str(Path(__file__).resolve().parent.parent.parent.parent.parent / "src")]
    for p in _src_paths:
        if Path(p).exists() and p not in sys.path:
            sys.path.insert(0, p)

    import os as _os
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        # ── Cache check ───────────────────────────────────────────────────
        if use_cache:
            try:
                from llama_cache import get_cache
                cache = get_cache()
                cached_docs = cache.get(tmp_path)
                if cached_docs:
                    text = "\n\n".join(d["text"] for d in cached_docs if d.get("text", "").strip())
                    return text, True
            except Exception as cache_err:
                # Cache error non-fatal — lanjut ke parse
                import logging
                logging.getLogger(__name__).warning(f"LlamaParse cache read error: {cache_err}")

        # ── Parse via API ─────────────────────────────────────────────────
        parser = LlamaParse(
            api_key=api_key,
            result_type="markdown",
            language="id",
            verbose=False,
        )
        docs = await parser.aload_data(tmp_path)

        # ── Simpan ke cache ───────────────────────────────────────────────
        if use_cache:
            try:
                from llama_cache import get_cache
                cache = get_cache()
                cache.set(tmp_path, docs, metadata={"source_filename": filename})
            except Exception as cache_err:
                import logging
                logging.getLogger(__name__).warning(f"LlamaParse cache write error: {cache_err}")

        text = "\n\n".join(doc.text for doc in docs if doc.text.strip())
        return text, False

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"LlamaParse gagal memproses PDF: {str(e)}")
    finally:
        if tmp_path:
            try:
                _os.unlink(tmp_path)
            except Exception:
                pass


def _extract_pdf_text_pypdf(content: bytes) -> str:
    """Fallback: ekstrak teks PDF menggunakan pypdf (gratis, lokal)."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(content))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(p.strip() for p in pages if p.strip())
    except ImportError:
        raise HTTPException(status_code=501, detail="Parsing PDF membutuhkan library pypdf.")
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Gagal membaca PDF: {str(e)}")


_CLAUSE_SENTINEL = "§§CLAUSE_SPLIT§§"


def _split_into_clauses(text: str, min_length: int = 80) -> List[str]:
    """
    Split T&C / SOP document into clause-level segments.

    Strategy (applied in order):
    1. Inject a sentinel before each structural marker:
       - Numbered section headings  e.g. "12. Judul Bagian"
       - Lettered sub-clauses       e.g. "a. Anda dapat..."
       - Roman-numeral list items   e.g. "i. ", "ii. ", "iii. "
    2. Split on the sentinel; sub-split any block still > 800 chars on
       blank lines.
    3. Normalise whitespace; merge fragments shorter than min_length into
       the preceding clause.
    """
    text = re.sub(r"\r\n", "\n", text)

    # ── Step 0: handle LlamaParse Markdown headings as clause boundaries ─────
    # LlamaParse menghasilkan "## 28. Hak Kekayaan Intelektual" → ubah ke sentinel
    text = re.sub(
        r"(^|\n)(#{1,3}\s+\d{1,2}\.\s+[^\n]+)",
        lambda m: m.group(1) + _CLAUSE_SENTINEL + m.group(2).lstrip("#").strip() + "\n",
        text,
        flags=re.MULTILINE,
    )

    # ── Step 1: mark structural boundaries ──────────────────────────────────
    def _mark(m: re.Match) -> str:  # type: ignore[type-arg]
        return m.group(1) + _CLAUSE_SENTINEL + "".join(m.groups()[1:])

    # Numbered section heading: "12. Judul" at line start (capital first letter)
    # Tangkap dengan \n di akhir ATAU end-of-string ($) agar tidak bleeding ke klausul sebelumnya
    text = re.sub(
        r"(?<!\d)(\n|^)(\d{1,2}\.\s+)([A-Z][^\n]{0,80})(\n|$)",
        lambda m: m.group(1) + _CLAUSE_SENTINEL + m.group(2) + m.group(3) + "\n",
        text,
        flags=re.MULTILINE,
    )
    # Lettered sub-clause: "a. " or "a) " at line start
    text = re.sub(
        r"(\n)([a-z][.)]\s)",
        _mark,
        text,
        flags=re.MULTILINE,
    )
    # Roman numeral list items: "i. ", "ii. ", "iii. ", "iv. " etc.
    text = re.sub(
        r"(\n)((?:i{1,3}|iv|vi{0,3}|ix|x)[.)]\s)",
        _mark,
        text,
        flags=re.MULTILINE,
    )

    # ── Step 2: split on sentinel; sub-split large blocks on blank lines ────
    raw_blocks: List[str] = []
    for block in text.split(_CLAUSE_SENTINEL):
        block = block.strip()
        if not block:
            continue
        if len(block) > 800:
            sub = re.split(r"\n{2,}", block)
            raw_blocks.extend(s.strip() for s in sub if s.strip())
        else:
            raw_blocks.append(block)

    # ── Step 3: normalise whitespace and merge short fragments ──────────────
    # Pattern untuk strip trailing section title yang bleeding: "33. Judul Berikut" di akhir
    _TRAILING_SECTION_RE = re.compile(r'\s+\d{1,2}\.\s+[A-Z][^\s.]{0,40}$')

    clauses: List[str] = []
    for block in raw_blocks:
        block = re.sub(r"\s+", " ", block).strip()
        # Strip trailing section title dari klausul sebelumnya
        block = _TRAILING_SECTION_RE.sub("", block).strip()
        if len(block) < min_length:
            if clauses:
                clauses[-1] = clauses[-1] + " " + block
            continue
        clauses.append(block)

    return clauses[:150]  # cap at 150 clauses


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    use_llamaparse_cache: bool = True,
):
    """
    Extract text from an uploaded PDF, TXT, or MD document.

    - PDF: LlamaParse (jika API key ada) dengan disk cache berbasis SHA-256 konten file.
           Set use_llamaparse_cache=false untuk memaksa re-parse.
    - TXT/MD: Python decode langsung.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nama file tidak boleh kosong.")

    ext = os.path.splitext(file.filename)[-1].lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Format file tidak didukung ({ext}). Gunakan: {', '.join(sorted(ALLOWED_UPLOAD_EXTENSIONS))}",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Ukuran file maksimal 10 MB.")
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="File tidak boleh kosong.")

    parsed_from_cache = False
    if ext == ".pdf":
        from app.config import settings
        if settings.LLAMA_CLOUD_API_KEY:
            text, parsed_from_cache = await _extract_pdf_text_llamaparse(
                content, file.filename, use_cache=use_llamaparse_cache
            )
        else:
            text = _extract_pdf_text_pypdf(content)
        text = _clean_pdf_text(text)
    else:
        text = content.decode("utf-8", errors="replace")

    if not text.strip():
        raise HTTPException(status_code=422, detail="Dokumen tidak mengandung teks yang dapat dibaca.")

    clauses = _split_into_clauses(text)

    return {
        "filename": file.filename,
        "file_size_kb": round(len(content) / 1024, 1),
        "text": text,
        "clauses": clauses,
        "clause_count": len(clauses),
        "parsed_from_cache": parsed_from_cache,
    }