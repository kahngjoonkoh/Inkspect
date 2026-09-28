import secrets
import uuid

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import ExamSession, Response


def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    if not x_admin_token or not secrets.compare_digest(x_admin_token, settings.admin_token):
        raise HTTPException(401, "Admin token required")


def load_session(session_id: uuid.UUID, db: Session = Depends(get_db)) -> ExamSession:
    session = db.get(ExamSession, session_id)
    if session is None:
        raise HTTPException(404, "Session not found")
    return session


def load_response(response_id: int, db: Session = Depends(get_db)) -> Response:
    r = db.get(Response, response_id)
    if r is None or r.discarded:
        raise HTTPException(404, "Response not found")
    return r
