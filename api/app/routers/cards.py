from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..db import get_db
from ..regions import get_map
from ..scorer_client import ScorerClient, get_scorer
from ..tables import CHROMATIC_CARDS

router = APIRouter(tags=["cards"])

CARD_SIZES = {1: (736, 482), 2: (690, 493), 3: (800, 550), 4: (794, 536), 5: (760, 555),
              6: (772, 570), 7: (800, 547), 8: (689, 600), 9: (754, 699), 10: (890, 711)}


@router.get("/health")
def health(db: Session = Depends(get_db), scorer: ScorerClient = Depends(get_scorer)) -> dict:
    db.execute(text("SELECT 1"))
    return {"status": "ok", "db": "ok", "scorer": "ok" if scorer.health() else "unavailable"}


@router.get("/cards")
def cards() -> list[dict]:
    return [{"card": n, "image": f"/cards/card_{n}.jpg", "width": w, "height": h, "chromatic": n in CHROMATIC_CARDS}
            for n, (w, h) in CARD_SIZES.items()]


@router.get("/regions/{card}")
def regions(card: int, db: Session = Depends(get_db)) -> dict:
    if card not in CARD_SIZES:
        raise HTTPException(404, "No such card")
    return get_map(db, card)
