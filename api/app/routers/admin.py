import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import load_response, require_admin
from ..location import parse_label
from ..models import ExamSession, RegionMap, Response
from ..schemas import CodesOverride, RegionMapBody
from ..scoring import effective_codes, inquiry_text
from ..service import results

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/sessions")
def list_sessions(db: Session = Depends(get_db)) -> list[dict]:
    sessions = db.scalars(select(ExamSession).order_by(ExamSession.created_at.desc()).limit(200)).all()
    return [{"id": str(s.id), "created_at": s.created_at.isoformat(), "phase": s.phase,
             "total_responses": len(s.active_responses)} for s in sessions]


def _scored_session(session_id: uuid.UUID, db: Session) -> ExamSession:
    session = db.get(ExamSession, session_id)
    if session is None:
        raise HTTPException(404, "Session not found")
    if session.phase != "complete":
        raise HTTPException(409, "Session has not been scored yet")
    return session


@router.get("/sessions/{session_id}")
def session_detail(session_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    return results(db, _scored_session(session_id, db), include_raw=True)


@router.put("/responses/{response_id}/codes")
def override_codes(body: CodesOverride, r: Response = Depends(load_response), db: Session = Depends(get_db)) -> dict:
    if r.session.phase != "complete":
        raise HTTPException(409, "Session has not been scored yet")
    override = body.model_dump(exclude_none=True, exclude={"location_label"})
    if body.location_label:
        try:
            override["location"] = parse_label(body.location_label)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
    r.override = override
    r.overridden_at = datetime.now(timezone.utc)
    db.commit()
    return results(db, r.session, include_raw=True)


@router.delete("/responses/{response_id}/codes")
def clear_override(r: Response = Depends(load_response), db: Session = Depends(get_db)) -> dict:
    r.override = None
    r.overridden_at = None
    db.commit()
    return results(db, r.session, include_raw=True)


@router.put("/regions/{card}")
def save_regions(card: int, body: RegionMapBody, db: Session = Depends(get_db)) -> dict:
    if body.card != card:
        raise HTTPException(400, "Card number mismatch")
    kinds = [r.get("kind") for r in body.regions]
    if kinds.count("W") != 1:
        raise HTTPException(400, "A region map needs exactly one W region")
    for region in body.regions:
        if region.get("kind") not in ("W", "D", "Dd", "S") or not region.get("id"):
            raise HTTPException(400, f"Bad region: {region.get('id')!r}")
    data = body.model_dump(exclude_none=True)
    row = db.get(RegionMap, card)
    if row is None:
        db.add(RegionMap(card=card, data=data))
    else:
        row.data = data
    db.commit()
    return data


def _state_text(r: Response) -> str:
    loc = (r.override or {}).get("location") or r.location or {}
    return (f"Card {r.card}, orientation {r.orientation}, location {loc.get('label', '?')}. "
            f"Response: {r.verbatim} Inquiry: {inquiry_text(r.explanation, r.followups)}")


@router.get("/export/training.jsonl", response_class=PlainTextResponse)
def export_training(db: Session = Depends(get_db)) -> str:
    rows = db.scalars(select(Response).where(Response.override.is_not(None), Response.discarded.is_(False))
                      .order_by(Response.id)).all()
    lines = []
    for r in rows:
        labels = effective_codes(r.codes, r.override)
        if r.override.get("fq"):
            labels["fq"] = r.override["fq"]
        lines.append(json.dumps({"state": _state_text(r), "labels": labels, "source": "override"}))
    return "\n".join(lines) + ("\n" if lines else "")
