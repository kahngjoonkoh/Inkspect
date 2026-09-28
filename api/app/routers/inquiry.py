from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import load_response
from ..models import Response
from ..schemas import FollowupBody, InquiryBody
from ..scorer_client import ScorerClient, ScorerUnavailable, get_scorer
from ..service import response_json

router = APIRouter(prefix="/responses", tags=["inquiry"])

MAX_FOLLOWUPS = 2


def _require_inquiry(r: Response) -> None:
    if r.session.phase != "inquiry":
        raise HTTPException(409, f"Session is in the {r.session.phase} phase")


def _next_followup(r: Response, scorer: ScorerClient) -> str | None:
    asked = [f["prompt"] for f in r.followups or []]
    if len(asked) >= MAX_FOLLOWUPS:
        return None
    try:
        reply = scorer.followup({"card": r.card, "verbatim": r.verbatim, "inquiry": r.explanation,
                                 "asked": asked})
    except ScorerUnavailable:
        return None
    prompt = reply.get("prompt")
    return prompt if prompt and prompt not in asked else None


@router.put("/{response_id}/inquiry")
def save_inquiry(body: InquiryBody, r: Response = Depends(load_response), db: Session = Depends(get_db),
                 scorer: ScorerClient = Depends(get_scorer)) -> dict:
    _require_inquiry(r)
    r.regions = [[[round(min(max(x, 0.0), 1.0), 4), round(min(max(y, 0.0), 1.0), 4)] for x, y in poly]
                 for poly in body.regions if len(poly) >= 3]
    r.whole_card = body.whole_card
    r.explanation = body.explanation.strip()
    r.pending_followup = _next_followup(r, scorer)
    db.commit()
    return {"followup": r.pending_followup, "response": response_json(r)}


@router.post("/{response_id}/followups")
def answer_followup(body: FollowupBody, r: Response = Depends(load_response), db: Session = Depends(get_db),
                    scorer: ScorerClient = Depends(get_scorer)) -> dict:
    _require_inquiry(r)
    r.followups = [*(r.followups or []), {"prompt": body.prompt, "answer": body.answer.strip()}]
    r.pending_followup = _next_followup(r, scorer)
    db.commit()
    return {"followup": r.pending_followup, "response": response_json(r)}


@router.post("/{response_id}/inquiry/done")
def inquiry_done(r: Response = Depends(load_response), db: Session = Depends(get_db)) -> dict:
    _require_inquiry(r)
    if not (r.regions or r.whole_card):
        raise HTTPException(400, "Show where on the card you saw it first")
    if not r.explanation:
        raise HTTPException(400, "Say what makes it look like that first")
    r.inquiry_done = True
    r.pending_followup = None
    db.commit()
    return {"response": response_json(r)}
