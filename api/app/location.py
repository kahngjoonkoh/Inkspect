"""Map the test taker's drawn lasso regions onto a card's location areas.

Everything is rasterised onto a fixed grid in normalised card coordinates and
compared by area overlap. No language processing is involved.
"""

import re
from dataclasses import dataclass
from functools import lru_cache
import json

import numpy as np
from PIL import Image, ImageDraw

GRID = 256
W_THRESHOLD = 0.8  # share of the ink a selection must cover to count as W
MATCH_THRESHOLD = 0.55  # F1 needed to accept a numbered D/Dd area

Point = list[float]
Polygon = list[Point]

_SPACE_WORDS = re.compile(r"\b(white|space|spaces|hole|holes|gap|gaps|empty|background|blank|paper)\b", re.I)


def mentions_space(*texts: str) -> bool:
    return any(_SPACE_WORDS.search(t or "") for t in texts)


def rasterise(polygons: list[Polygon]) -> np.ndarray:
    img = Image.new("1", (GRID, GRID), 0)
    draw = ImageDraw.Draw(img)
    for poly in polygons:
        if len(poly) >= 3:
            draw.polygon([(x * GRID, y * GRID) for x, y in poly], fill=1)
    return np.array(img, dtype=bool)


@dataclass(frozen=True)
class Area:
    id: str
    kind: str
    number: int | None
    variants: tuple[np.ndarray, ...]  # each polygon alone, plus their union
    mask: np.ndarray


@dataclass(frozen=True)
class CompiledMap:
    ink: np.ndarray
    areas: tuple[Area, ...]
    placeholder: bool


def _number(region_id: str) -> int | None:
    m = re.search(r"(\d+)$", region_id)
    return int(m.group(1)) if m else None


def compile_map(region_map: dict) -> CompiledMap:
    return _compile(json.dumps(region_map, sort_keys=True))


@lru_cache(maxsize=64)
def _compile(serialised: str) -> CompiledMap:
    region_map = json.loads(serialised)
    whole = np.zeros((GRID, GRID), bool)
    space = np.zeros((GRID, GRID), bool)
    areas = []
    for r in region_map.get("regions", []):
        masks = [rasterise([p]) for p in r.get("polygons", [])]
        if not masks:
            continue
        union = np.logical_or.reduce(masks)
        if r["kind"] == "W":
            whole |= union
            continue
        if r["kind"] == "S":
            space |= union
        variants = tuple(masks) + ((union,) if len(masks) > 1 else ())
        areas.append(Area(r["id"], r["kind"], _number(r["id"]), variants, union))
    ink = whole & ~space
    return CompiledMap(ink, tuple(areas), bool(region_map.get("placeholder", False)))


def label(code: str, space: bool, number: int | None) -> str:
    return f"{code}{'S' if space else ''}{number if number is not None else ''}"


def location_dict(code: str, number: int | None, space: bool, placeholder: bool, match: float,
                  space_only: bool = False) -> dict:
    return {
        "code": code,
        "number": number,
        "space": space,
        "label": label(code, space, number),
        "placeholder": placeholder,
        "match": round(match, 3),
        "space_only": space_only,
    }


def _f1(sel: np.ndarray, area: np.ndarray) -> float:
    inter = float((sel & area).sum())
    if inter == 0:
        return 0.0
    coverage = inter / float(area.sum())
    precision = inter / float(sel.sum())
    return 2 * coverage * precision / (coverage + precision)


def _best(sel: np.ndarray, areas: list[Area]) -> tuple[Area | None, float]:
    best, score = None, 0.0
    for area in areas:
        s = max(_f1(sel, v) for v in area.variants)
        if s > score:
            best, score = area, s
    return best, score


def map_location(region_map: dict, polygons: list[Polygon], whole_card: bool, uses_space: bool = False) -> dict:
    """Return the CS location for a selection.

    `uses_space` says whether the response mentions the white space; S is only
    coded when the space is actually used, not merely enclosed by a loose lasso.
    """
    cm = compile_map(region_map)
    s_areas = [a for a in cm.areas if a.kind == "S"]
    ink_areas = [a for a in cm.areas if a.kind != "S"]

    def space_used(sel: np.ndarray) -> bool:
        return uses_space and any(float((sel & a.mask).sum()) / float(a.mask.sum()) >= 0.3 for a in s_areas)

    if whole_card:
        return location_dict("W", None, uses_space and bool(s_areas), cm.placeholder, 1.0)

    user = rasterise(polygons)
    if not user.any():
        return location_dict("Dd", 99, False, cm.placeholder, 0.0)

    on_ink = user & cm.ink
    on_space = user & np.logical_or.reduce([a.mask for a in s_areas]) if s_areas else np.zeros_like(user)

    # Mostly white space: the response is about a space area itself.
    if on_space.sum() > on_ink.sum() and s_areas:
        area, score = _best(on_space, s_areas)
        if area is not None:
            return location_dict("Dd", area.number, True, cm.placeholder, score, space_only=True)

    if not on_ink.any():
        return location_dict("Dd", 99, False, cm.placeholder, 0.0)

    ink_share = float(on_ink.sum()) / float(cm.ink.sum())
    if ink_share >= W_THRESHOLD:
        return location_dict("W", None, space_used(user), cm.placeholder, ink_share)

    area, score = _best(on_ink, ink_areas)
    if area is not None and score >= MATCH_THRESHOLD:
        return location_dict(area.kind, area.number, space_used(user), cm.placeholder, score)
    return location_dict("Dd", 99, space_used(user), cm.placeholder, score)


def parse_label(text: str) -> dict:
    """Parse a reviewer-entered location label such as 'W', 'WS', 'D1', 'DdS29'."""
    m = re.fullmatch(r"\s*(W|Dd|D)(S?)(\d*)\s*", text)
    if not m:
        raise ValueError(f"Not a location label: {text!r}")
    code, s, num = m.groups()
    return location_dict(code, int(num) if num else None, bool(s), False, 1.0)
