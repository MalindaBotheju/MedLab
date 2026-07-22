"""
Database layer — Neon Postgres.

Persistence is optional: if DATABASE_URL isn't set, every function here
becomes a safe no-op so the rest of the app keeps working without a
database (just without history).
"""
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text,
    Boolean,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "")

Base = declarative_base()
_engine = None
_SessionLocal = None

if DATABASE_URL:
    _engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    summary = Column(Text, nullable=True)
    urgent_review_required = Column(Boolean, default=False)
    report_json = Column(Text, nullable=False)
    trace_json = Column(Text, nullable=False)
    guardrail_issues_json = Column(Text, nullable=False)


def is_configured() -> bool:
    return _engine is not None


def init_db() -> None:
    """Create tables if they don't exist yet. No-op if DATABASE_URL isn't set."""
    if not is_configured():
        return
    Base.metadata.create_all(_engine)


def save_report(
    report: Dict[str, Any],
    trace: List[str],
    guardrail_issues: List[str],
) -> Optional[int]:
    """Persist a report. Returns the new row's id, or None if no DB is configured."""
    if not is_configured():
        return None

    urgent = any(
        (f.get("severity") == "urgent")
        for f in report.get("abnormal_findings", [])
    )

    with _SessionLocal() as session:
        row = Report(
            summary=report.get("summary"),
            urgent_review_required=urgent,
            report_json=json.dumps(report),
            trace_json=json.dumps(trace),
            guardrail_issues_json=json.dumps(guardrail_issues),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row.id


def list_reports(limit: int = 50) -> List[Dict[str, Any]]:
    if not is_configured():
        return []
    with _SessionLocal() as session:
        rows = (
            session.query(Report)
            .order_by(Report.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": r.id,
                "created_at": r.created_at.isoformat(),
                "summary": r.summary,
                "urgent_review_required": r.urgent_review_required,
            }
            for r in rows
        ]


def get_report(report_id: int) -> Optional[Dict[str, Any]]:
    if not is_configured():
        return None
    with _SessionLocal() as session:
        row = session.get(Report, report_id)
        if row is None:
            return None
        return {
            "id": row.id,
            "created_at": row.created_at.isoformat(),
            "report": json.loads(row.report_json),
            "trace": json.loads(row.trace_json),
            "guardrail_issues": json.loads(row.guardrail_issues_json),
        }
