"""
db.py — SQLAlchemy database connection + AuditHistory table
"""
import json
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine, Column, String, Float, DateTime, Text, Boolean
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
import bcrypt as _bcrypt_lib

from app.config import settings


def _hash_pw(password: str) -> str:
    return _bcrypt_lib.hashpw(password.encode("utf-8"), _bcrypt_lib.gensalt()).decode("utf-8")

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


class UserRow(Base):
    __tablename__ = "users"

    username        = Column(String, primary_key=True, index=True)
    hashed_password = Column(String, nullable=False)
    role            = Column(String, nullable=False, default="basic")


class AuditHistoryRow(Base):
    __tablename__ = "audit_history"

    request_id         = Column(String, primary_key=True, index=True)
    timestamp          = Column(DateTime, default=datetime.utcnow, index=True)
    clause             = Column(Text)
    clause_id          = Column(String, nullable=True)
    final_status       = Column(String, index=True)
    overall_confidence = Column(Float)
    risk_score         = Column(Float)
    latency_ms         = Column(Float)
    model_used         = Column(String, nullable=True)
    from_cache         = Column(Boolean, default=False)
    analysis_mode      = Column(String, nullable=True)
    query_type         = Column(String, nullable=True)
    retrieval_mode     = Column(String, nullable=True)
    summary            = Column(Text, nullable=True)
    # JSON-serialised fields
    bi_verdict_json    = Column(Text, nullable=True)
    ojk_verdict_json   = Column(Text, nullable=True)
    violations_json    = Column(Text, nullable=True)
    recommendations_json = Column(Text, nullable=True)


# ── Engine & session factory ──────────────────────────────────────────────────

_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        if not settings.DATABASE_URL:
            raise RuntimeError("DATABASE_URL is not configured.")
        _engine = create_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autocommit=False, autoflush=False)
    return _SessionLocal


def init_db():
    """Create tables if they don't exist (idempotent)."""
    try:
        Base.metadata.create_all(bind=get_engine())
        logger.info("Database tables initialised.")
    except Exception as e:
        logger.warning(f"Database init failed (will use in-memory fallback): {e}")


def seed_users():
    """
    Upsert basic and advanced users from env vars.
    Called once at startup — idempotent (won't duplicate).
    """
    try:
        factory = get_session_factory()
        db: Session = factory()
        users_to_seed = [
            (settings.BASIC_USERNAME, settings.BASIC_USER_PASSWORD, "basic"),
            (settings.ADVANCED_USERNAME, settings.ADVANCED_USER_PASSWORD, "advanced"),
        ]
        for username, password, role in users_to_seed:
            existing = db.query(UserRow).filter_by(username=username).first()
            if existing:
                existing.hashed_password = _hash_pw(password)
                existing.role = role
            else:
                db.add(UserRow(
                    username=username,
                    hashed_password=_hash_pw(password),
                    role=role,
                ))
        db.commit()
        db.close()
        logger.info(f"Seeded users: {[u[0] for u in users_to_seed]}")
    except Exception as e:
        logger.warning(f"seed_users failed: {e}")


def get_db() -> Session:
    factory = get_session_factory()
    db = factory()
    try:
        yield db
    finally:
        db.close()


# ── Helpers: AuditResponse ↔ AuditHistoryRow ─────────────────────────────────

def _fix_encoding(text: str) -> str:
    """Fix double-encoded UTF-8 artifacts (e.g. â for em dash —)."""
    if not isinstance(text, str):
        return text
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return text

def _to_row(response) -> AuditHistoryRow:
    """Convert AuditResponse Pydantic model → DB row."""
    def _ser(obj):
        if obj is None:
            return None
        if hasattr(obj, "model_dump"):
            return json.dumps(obj.model_dump(), ensure_ascii=False)
        return json.dumps(obj, ensure_ascii=False)

    return AuditHistoryRow(
        request_id          = response.request_id,
        timestamp           = response.timestamp,
        clause              = response.clause,
        clause_id           = response.clause_id,
        final_status        = response.final_status.value if hasattr(response.final_status, "value") else str(response.final_status),
        overall_confidence  = response.overall_confidence,
        risk_score          = response.risk_score,
        latency_ms          = response.latency_ms,
        model_used          = getattr(response, "model_used", None),
        from_cache          = getattr(response, "from_cache", False),
        analysis_mode       = getattr(response, "analysis_mode", None),
        query_type          = getattr(response, "query_type", None),
        retrieval_mode      = getattr(response, "retrieval_mode", None),
        summary             = getattr(response, "summary", None),
        bi_verdict_json     = _ser(response.bi_verdict),
        ojk_verdict_json    = _ser(response.ojk_verdict),
        violations_json     = json.dumps(response.violations or []),
        recommendations_json= json.dumps(response.recommendations or []),
    )


def _from_row(row: AuditHistoryRow, response_class, verdict_class, evidence_class, status_class):
    """Convert DB row → AuditResponse Pydantic model."""
    def _deser_verdict(raw: Optional[str], agent_name: str):
        if not raw:
            return None
        d = json.loads(raw)
        evidence = [
            evidence_class(**e) if isinstance(e, dict) else e
            for e in d.get("evidence", [])
        ]
        return verdict_class(
            agent_name  = d.get("agent_name", agent_name),
            status      = status_class(d["status"]) if "status" in d else status_class.UNCLEAR,
            confidence  = d.get("confidence", 0.5),
            violations  = d.get("violations", []),
            evidence    = evidence,
            reasoning   = d.get("reasoning", ""),
        )

    return response_class(
        request_id          = row.request_id,
        timestamp           = row.timestamp,
        clause              = row.clause,
        clause_id           = row.clause_id,
        final_status        = status_class(row.final_status),
        overall_confidence  = row.overall_confidence,
        risk_score          = row.risk_score,
        latency_ms          = row.latency_ms,
        model_used          = row.model_used or "gpt-5.4-mini",
        tokens_used         = 0,
        from_cache          = row.from_cache or False,
        analysis_mode       = row.analysis_mode,
        query_type          = row.query_type,
        retrieval_mode      = row.retrieval_mode,
        summary             = row.summary,
        bi_verdict          = _deser_verdict(row.bi_verdict_json, "BI_SPECIALIST"),
        ojk_verdict         = _deser_verdict(row.ojk_verdict_json, "OJK_SPECIALIST"),
        violations          = [_fix_encoding(v) for v in json.loads(row.violations_json or "[]")],
        recommendations     = [_fix_encoding(r) if isinstance(r, str) else r for r in json.loads(row.recommendations_json or "[]")],
    )
