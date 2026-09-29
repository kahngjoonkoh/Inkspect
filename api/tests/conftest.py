import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.db import Base, get_db
from app.main import create_app
from app.models import RegionMap
from app.scorer_client import get_scorer


# The FQ table is not in git; tests that need it run only where a local copy exists.
needs_fq_table = pytest.mark.skipif(not settings.fq_db_path.is_file(), reason="no local copy of the Exner FQ table")


def square(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


@pytest.fixture
def toy_map():
    """A 'card' with ink in the middle band, two D areas, a mirrored pair, and a white-space hole."""
    return {
        "card": 1,
        "placeholder": True,
        "regions": [
            {"id": "W", "kind": "W", "polygons": [square(0.1, 0.2, 0.9, 0.8)]},
            {"id": "D1", "kind": "D", "polygons": [square(0.1, 0.2, 0.3, 0.8), square(0.7, 0.2, 0.9, 0.8)]},
            {"id": "D2", "kind": "D", "polygons": [square(0.3, 0.2, 0.7, 0.4)]},
            {"id": "Dd21", "kind": "Dd", "polygons": [square(0.45, 0.7, 0.55, 0.8)]},
            {"id": "DdS50", "kind": "S", "polygons": [square(0.4, 0.45, 0.6, 0.65)]},
        ],
    }


class FakeScorer:
    """Stands in for the scorer service in API tests."""

    def __init__(self):
        self.code_calls = []
        self.followup_calls = []

    def code(self, body):
        self.code_calls.append(body)
        text = f"{body['verbatim']} {body['inquiry']}".lower()
        dets = ["FMa"] if "flying" in text else ["F"]
        contents = [body["fq_hint"]["content"]] if body.get("fq_hint") else ["A"]
        specials = ["MOR"] if "dead" in text else []
        return {"dq": "o", "determinants": dets, "pair": "two" in text, "contents": contents,
                "special_scores": specials, "fq_fallback": "u", "evidence": {}, "confidence": {}, "coder": "rule"}

    def followup(self, body):
        self.followup_calls.append(body)
        if "pretty" in body["inquiry"].lower() and not body["asked"]:
            return {"prompt": "You said “pretty”. What makes it look pretty?", "keyword": "pretty"}
        return {"prompt": None, "keyword": None}

    def health(self):
        return True


@pytest.fixture
def scorer():
    return FakeScorer()


@pytest.fixture
def client(scorer):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Local = sessionmaker(bind=engine, expire_on_commit=False)
    with Local() as db:
        for card in range(1, 11):
            data = json.loads((settings.regions_dir / f"card_{card}.json").read_text())
            db.add(RegionMap(card=card, data=data))
        db.commit()

    def override_db():
        with Local() as db:
            yield db

    app = create_app(seed_regions=False)
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_scorer] = lambda: scorer
    with TestClient(app) as c:
        yield c


@pytest.fixture
def admin():
    return {"X-Admin-Token": settings.admin_token}

