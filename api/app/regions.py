"""Region maps: seeded from regions/card_<n>.json, edited through the admin API."""

import json

from sqlalchemy.orm import Session

from .config import settings
from .models import RegionMap


def load_file(card: int) -> dict:
    path = settings.regions_dir / f"card_{card}.json"
    return json.loads(path.read_text())


def seed(db: Session) -> None:
    for card in range(1, 11):
        if db.get(RegionMap, card) is None:
            db.add(RegionMap(card=card, data=load_file(card)))
    db.commit()


def get_map(db: Session, card: int) -> dict:
    row = db.get(RegionMap, card)
    if row is None:
        data = load_file(card)
        db.add(RegionMap(card=card, data=data))
        db.commit()
        return data
    return row.data
