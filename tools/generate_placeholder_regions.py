"""Generate PLACEHOLDER location region maps for the ten cards.

These are NOT the Exner Comprehensive System location areas. They are an
automatic segmentation of each card's ink (connected components, colour
clusters, and a centre/sides split with mirror pairs merged), numbered by size.
They exist only so the app runs end to end. Replace them with the real CS areas
in the admin region editor (/admin/regions/<card>), then download the JSON over
regions/card_<n>.json.

Run (from the repo root):
    docker run --rm -v "$PWD":/w -w /w python:3.12-slim sh -c \
      "pip install -q opencv-python-headless==4.* numpy && python tools/generate_placeholder_regions.py"
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
CARDS = ROOT / "web" / "public" / "cards"
OUT = ROOT / "regions"
PREVIEW = Path(sys.argv[1]) if len(sys.argv) > 1 else None

WORK_WIDTH = 480
# Number of colour clusters (including the achromatic ink) for the chromatic cards.
COLOUR_CLUSTERS = {2: 3, 3: 3, 8: 5, 9: 4, 10: 7}
MIN_D_SHARE = 0.02  # a part needs 2% of the ink to become a D area
MIN_DD_SHARE = 0.004
MAX_D = 12


def ink_mask(img: np.ndarray) -> np.ndarray:
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    band = np.concatenate([lab[:8].reshape(-1, 3), lab[-8:].reshape(-1, 3),
                           lab[:, :8].reshape(-1, 3), lab[:, -8:].reshape(-1, 3)])
    bg = np.median(band, axis=0)
    dist = np.linalg.norm(lab - bg, axis=2)
    dist8 = np.clip(dist * 255.0 / max(dist.max(), 1.0), 0, 255).astype(np.uint8)
    otsu, _ = cv2.threshold(dist8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # Otsu alone drops pale colours (e.g. the green and orange on VIII and IX).
    _, mask = cv2.threshold(dist8, 0.6 * otsu, 255, cv2.THRESH_BINARY)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
    keep = np.zeros_like(mask)
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] >= 0.001 * mask.size:
            keep[labels == i] = 255
    return keep


def contours_to_polys(mask: np.ndarray, min_area: float) -> list[np.ndarray]:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    polys = []
    for c in contours:
        if cv2.contourArea(c) < min_area:
            continue
        approx = cv2.approxPolyDP(c, 0.004 * cv2.arcLength(c, True), True)
        if len(approx) >= 3:
            polys.append(approx.reshape(-1, 2))
    return polys


def components(mask: np.ndarray, min_area: float) -> list[np.ndarray]:
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
    return [((labels == i) * 255).astype(np.uint8)
            for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] >= min_area]


def colour_parts(img: np.ndarray, ink: np.ndarray, k: int) -> list[np.ndarray]:
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    ys, xs = np.nonzero(ink)
    samples = lab[ys, xs]
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.5)
    cv2.setRNGSeed(7)
    _, labels, _ = cv2.kmeans(samples, k, None, criteria, 5, cv2.KMEANS_PP_CENTERS)
    parts = []
    for c in range(k):
        m = np.zeros(ink.shape, np.uint8)
        sel = labels.ravel() == c
        m[ys[sel], xs[sel]] = 255
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
        parts.append(m)
    return parts


def split_large(part: np.ndarray, cx: float, ink_w: float) -> list[np.ndarray]:
    """Split a dominant part into a centre column (top/bottom halves) and a pair of sides."""
    h, w = part.shape
    band = 0.12 * ink_w
    xx = np.arange(w)[None, :].repeat(h, axis=0)
    centre = np.where(np.abs(xx - cx) < band, part, 0).astype(np.uint8)
    sides = np.where(np.abs(xx - cx) >= band, part, 0).astype(np.uint8)
    ys = np.nonzero(centre)[0]
    out = [sides]
    if len(ys):
        mid = int(np.median(ys))
        top, bottom = centre.copy(), centre.copy()
        top[mid:] = 0
        bottom[:mid] = 0
        out += [top, bottom]
    return out


def build(card: int) -> tuple[dict, np.ndarray, list]:
    img = cv2.imread(str(CARDS / f"card_{card}.jpg"), cv2.IMREAD_COLOR)
    scale = WORK_WIDTH / img.shape[1]
    img = cv2.resize(img, (WORK_WIDTH, round(img.shape[0] * scale)), interpolation=cv2.INTER_AREA)
    h, w = img.shape[:2]
    ink = ink_mask(img)
    ink_area = float((ink > 0).sum())
    xs = np.nonzero(ink)[1]
    cx, ink_w = (xs.min() + xs.max()) / 2.0, float(xs.max() - xs.min())

    # Candidate parts: colour clusters (chromatic cards) or the ink itself, split into components.
    base = colour_parts(img, ink, COLOUR_CLUSTERS[card]) if card in COLOUR_CLUSTERS else [ink]
    parts: list[np.ndarray] = []
    for b in base:
        for comp in components(b, MIN_DD_SHARE * ink_area):
            if (comp > 0).sum() > 0.35 * ink_area:
                for piece in split_large(comp, cx, ink_w):
                    parts += components(piece, MIN_DD_SHARE * ink_area)
            else:
                parts.append(comp)

    # Merge mirror pairs (left/right halves of the symmetric blot) into one area.
    info = []
    for p in parts:
        m = cv2.moments(p, binaryImage=True)
        info.append({"mask": p, "area": m["m00"], "x": m["m10"] / m["m00"], "y": m["m01"] / m["m00"]})
    used, groups = set(), []
    for i, a in enumerate(info):
        if i in used:
            continue
        group = [a]
        used.add(i)
        for j, b in enumerate(info):
            if j in used:
                continue
            mirrored = abs((2 * cx - a["x"]) - b["x"]) < 0.05 * w and abs(a["y"] - b["y"]) < 0.05 * h
            if mirrored and 0.5 < a["area"] / b["area"] < 2.0 and abs(a["x"] - cx) > 0.03 * w:
                group.append(b)
                used.add(j)
                break
        groups.append(group)
    groups.sort(key=lambda g: -sum(p["area"] for p in g))

    def norm(poly: np.ndarray) -> list[list[float]]:
        return [[round(float(x) / w, 4), round(float(y) / h, 4)] for x, y in poly]

    regions = [{"id": "W", "kind": "W",
                "polygons": [norm(p) for p in contours_to_polys(ink, 0.002 * ink_area)]}]
    d_no, dd_no = 1, 21
    for g in groups:
        share = sum(p["area"] for p in g) / ink_area
        polys = [norm(poly) for p in g for poly in contours_to_polys(p["mask"], 0.3 * p["area"])]
        if not polys:
            continue
        if share >= MIN_D_SHARE and d_no <= MAX_D:
            regions.append({"id": f"D{d_no}", "kind": "D", "polygons": polys})
            d_no += 1
        else:
            regions.append({"id": f"Dd{dd_no}", "kind": "Dd", "polygons": polys})
            dd_no += 1

    # White space: background areas enclosed by the ink.
    inv = cv2.bitwise_not(ink)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(inv)
    s_no = 50
    for i in range(1, n):
        x, y, bw, bh, area = stats[i]
        touches = x == 0 or y == 0 or x + bw >= w or y + bh >= h
        if touches or area < 0.004 * ink_area:
            continue
        polys = [norm(p) for p in contours_to_polys(((labels == i) * 255).astype(np.uint8), 0.5 * area)]
        if polys:
            regions.append({"id": f"DdS{s_no}", "kind": "S", "polygons": polys})
            s_no += 1

    region_map = {
        "card": card,
        "placeholder": True,
        "note": "Auto-generated placeholder areas, NOT the Exner CS location areas. "
                "Replace via /admin/regions/%d." % card,
        "regions": regions,
    }
    return region_map, img, regions


def preview(img: np.ndarray, regions: list, path: Path) -> None:
    h, w = img.shape[:2]
    canvas = img.copy()
    rng = np.random.default_rng(3)
    for r in regions:
        colour = (0, 0, 0) if r["kind"] == "W" else tuple(int(c) for c in rng.integers(40, 230, 3))
        for poly in r["polygons"]:
            pts = np.array([[x * w, y * h] for x, y in poly], np.int32)
            cv2.polylines(canvas, [pts], True, colour, 2 if r["kind"] != "W" else 1)
            m = pts.mean(axis=0).astype(int)
            cv2.putText(canvas, r["id"], tuple(int(v) for v in m), cv2.FONT_HERSHEY_SIMPLEX, 0.4, colour, 1)
    cv2.imwrite(str(path), canvas)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for card in range(1, 11):
        region_map, img, regions = build(card)
        (OUT / f"card_{card}.json").write_text(json.dumps(region_map, indent=1) + "\n")
        kinds = [r["id"] for r in regions]
        print(f"card {card}: {', '.join(kinds)}")
        if PREVIEW:
            PREVIEW.mkdir(parents=True, exist_ok=True)
            preview(img, regions, PREVIEW / f"card_{card}.png")


if __name__ == "__main__":
    main()
