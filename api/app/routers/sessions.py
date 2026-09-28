from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import examiner
from ..db import get_db
from ..deps import load_session
from ..models import ExamSession, Response
from ..schemas import AddResponse, CreateSession
from ..scorer_client import ScorerClient, ScorerUnavailable, get_scorer
from ..service import response_json, results, score_session, session_state

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _require_phase(session: ExamSession, phase: str) -> None:
    if session.phase != phase:
        raise HTTPException(409, f"Session is in the {session.phase} phase")


@router.post("")
def create_session(body: CreateSession, db: Session = Depends(get_db)) -> dict:
    if not body.consent:
        raise HTTPException(400, "Consent is required to start the test")
    session = ExamSession()
    db.add(session)
    db.commit()
    return session_state(session)


@router.get("/{session_id}")
def get_session(session: ExamSession = Depends(load_session)) -> dict:
    return session_state(session)


@router.post("/{session_id}/responses")
def add_response(body: AddResponse, session: ExamSession = Depends(load_session),
                 db: Session = Depends(get_db)) -> dict:
    _require_phase(session, "response")
    if body.card != session.current_card:
        raise HTTPException(409, f"The current card is {session.current_card}")
    on_card = [r.verbatim for r in session.active_responses if r.card == body.card]
    decision = examiner.decide_add(body.verbatim, on_card)
    if not decision.accepted:
        return {"accepted": False, "response": None, "message": decision.message, "card_full": decision.card_full}
    r = Response(session_id=session.id, administration=session.administration, card=body.card,
                 verbatim=examiner.normalise_spacing(body.verbatim), orientation=body.orientation,
                 reaction_ms=body.reaction_ms if not on_card else None)
    session.responses.append(r)
    session.empty_prompted_card = None
    db.commit()
    item = response_json(r)
    item["number"] = session_state(session)["total_responses"]
    return {"accepted": True, "response": item, "message": decision.message, "card_full": decision.card_full}


@router.delete("/{session_id}/responses/{response_id}")
def delete_response(response_id: int, session: ExamSession = Depends(load_session),
                    db: Session = Depends(get_db)) -> dict:
    _require_phase(session, "response")
    r = next((r for r in session.active_responses if r.id == response_id), None)
    if r is None or r.card != session.current_card:
        raise HTTPException(404, "Response not found on the current card")
    session.responses.remove(r)
    db.commit()
    return session_state(session)


@router.post("/{session_id}/cards/{card}/next")
def next_card(card: int, session: ExamSession = Depends(load_session), db: Session = Depends(get_db)) -> dict:
    _require_phase(session, "response")
    if card != session.current_card:
        raise HTTPException(409, f"The current card is {session.current_card}")
    count = sum(1 for r in session.active_responses if r.card == card)
    decision = examiner.decide_next(card, count, session.card1_prompted, session.empty_prompted_card == card,
                                    len(session.active_responses), session.administration)
    if decision.action == "stay":
        if count == 0:
            session.empty_prompted_card = card
        else:
            session.card1_prompted = True
    elif decision.action == "next_card":
        session.current_card += 1
        session.empty_prompted_card = None
    elif decision.action == "readminister":
        for r in session.active_responses:
            r.discarded = True
        session.administration = 2
        session.current_card = 1
        session.card1_prompted = False
        session.empty_prompted_card = None
    else:
        session.phase = "inquiry"
    db.commit()
    return {"action": decision.action, "message": decision.message, "state": session_state(session)}


@router.post("/{session_id}/finish")
def finish(session: ExamSession = Depends(load_session), db: Session = Depends(get_db),
           scorer: ScorerClient = Depends(get_scorer)) -> dict:
    if session.phase == "complete":
        return results(db, session)
    _require_phase(session, "inquiry")
    if not all(r.inquiry_done for r in session.active_responses):
        raise HTTPException(409, "Some responses still need an inquiry")
    try:
        score_session(db, session, scorer)
    except ScorerUnavailable as exc:
        db.rollback()
        raise HTTPException(503, f"Scoring service unavailable: {exc}") from exc
    return results(db, session)


@router.get("/{session_id}/results")
def get_results(session: ExamSession = Depends(load_session), db: Session = Depends(get_db)) -> dict:
    _require_phase(session, "complete")
    return results(db, session)
