"""Session state, scoring and results assembly shared by the routers."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from . import fq as fq_lookup
from .interpretation import interpret
from .overview import overview
from .location import map_location, mentions_space
from .models import ExamSession, Response
from .regions import get_map
from .scorer_client import ScorerClient
from .scoring import build_protocol, inquiry_text
from .summary import structural_summary


def response_json(r: Response) -> dict:
    return {
        "id": r.id,
        "card": r.card,
        "number": 0,
        "verbatim": r.verbatim,
        "orientation": r.orientation,
        "reaction_ms": r.reaction_ms,
        "inquiry": {
            "regions": r.regions or [],
            "whole_card": r.whole_card,
            "explanation": r.explanation or "",
            "followups": r.followups or [],
            "done": r.inquiry_done,
        },
    }


def ordered(session: ExamSession) -> list[Response]:
    return sorted(session.active_responses, key=lambda r: (r.card, r.id))


def session_state(session: ExamSession) -> dict:
    responses = ordered(session)
    items = []
    for n, r in enumerate(responses, start=1):
        item = response_json(r)
        item["number"] = n
        items.append(item)
    pending = next((i for i, r in enumerate(responses) if not r.inquiry_done), len(responses))
    return {
        "id": str(session.id),
        "phase": session.phase,
        "current_card": session.current_card,
        "administration": session.administration,
        "total_responses": len(responses),
        "responses": items,
        "inquiry_index": pending,
    }


def scorer_request(r: Response) -> dict:
    """The fields the scorer codes a response from; also the training-export format."""
    return {
        "card": r.card,
        "orientation": r.orientation,
        "verbatim": r.verbatim,
        "inquiry": r.explanation or "",
        "followups": r.followups or [],
        "location": {k: r.location[k] for k in ("code", "number", "space", "label")} if r.location else None,
    }


def score_response(db: Session, r: Response, scorer: ScorerClient) -> None:
    text = inquiry_text(r.explanation, r.followups)
    region_map = get_map(db, r.card)
    r.location = map_location(region_map, r.regions or [], r.whole_card, mentions_space(r.verbatim, text))
    match = fq_lookup.lookup(r.card, r.location["label"], r.orientation, r.verbatim, text)
    r.fq_match = match.as_dict() if match else None
    r.codes = scorer.code(scorer_request(r) | {
        "fq_hint": {"item": match.item, "content": match.content, "fq": match.fq} if match else None,
        "coder": None,
    })


def score_session(db: Session, session: ExamSession, scorer: ScorerClient) -> None:
    for r in session.active_responses:
        score_response(db, r, scorer)
    session.phase = "complete"
    session.scored_at = datetime.now(timezone.utc)
    db.commit()


def results(db: Session, session: ExamSession, include_raw: bool = False) -> dict:
    rows = build_protocol(session.active_responses, include_raw=include_raw)
    # Unserious, gibberish, refusal and off-task answers stay in the protocol for review, but their
    # codes mean nothing, so they are left out of the structural summary.
    genuine = [row for row in rows if row["validity"] == "genuine"]
    variables, summary = structural_summary(genuine)
    placeholder = any(row["location"].get("placeholder") for row in rows)
    warnings = []
    excluded = len(rows) - len(genuine)
    if excluded:
        warnings.append(f"{excluded} of {len(rows)} responses did not look like sincere answers (unserious, "
                        "gibberish, refusal or off-task) and were left out of the summary. A reviewer can "
                        "mark them genuine.")
    if len(rows) and excluded / len(rows) >= 0.25:
        warnings.append("A quarter or more of the answers were not sincere, so this record should not be "
                        "interpreted.")
    if not variables["valid"]:
        warnings.append(f"Only {variables['R']} responses: CS requires at least 14 for a valid record.")
    if placeholder:
        warnings.append("Region maps are placeholders, not the Exner location areas: location, Form Quality, "
                        "Popular and Z scores are approximate until real maps are drawn.")
    coders = {row["coder"] for row in rows}
    if coders == {"rule"}:
        warnings.append("Responses were coded by the baseline rule coder, which misses many determinants "
                        "and special scores. Treat the codes as a draft for review.")
    return {
        "session_id": str(session.id),
        "valid": variables["valid"],
        "warnings": warnings,
        "protocol": rows,
        "overview": overview(variables),
        "summary": summary,
        "interpretation": interpret(variables, summary["constellations"], placeholder),
    }
