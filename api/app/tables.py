"""Comprehensive System reference tables: Popular responses, Z values, Zest."""

from .text import word_set

# Card -> (ZW, ZA adjacent, ZD distant, ZS white space)
Z_VALUES: dict[int, tuple[float, float, float, float]] = {
    1: (1.0, 4.0, 6.0, 3.5),
    2: (4.5, 3.0, 5.5, 4.5),
    3: (5.5, 3.0, 4.0, 4.5),
    4: (2.0, 4.0, 3.5, 5.0),
    5: (1.0, 2.5, 5.0, 4.0),
    6: (2.5, 2.5, 6.0, 6.5),
    7: (2.5, 1.0, 3.0, 4.0),
    8: (4.5, 3.0, 3.0, 4.0),
    9: (5.5, 2.5, 4.5, 5.0),
    10: (5.5, 4.0, 4.5, 6.0),
}

# Zf -> expected ZSum (Zest)
ZEST: dict[int, float] = {
    1: 0.0, 2: 2.5, 3: 6.0, 4: 10.0, 5: 13.5, 6: 17.0, 7: 20.5, 8: 24.0, 9: 27.5, 10: 31.0,
    11: 34.5, 12: 38.0, 13: 41.5, 14: 45.5, 15: 49.0, 16: 52.5, 17: 56.0, 18: 59.5, 19: 63.0,
    20: 66.5, 21: 70.0, 22: 73.5, 23: 77.0, 24: 81.0, 25: 84.5, 26: 88.0, 27: 91.5, 28: 95.0,
    29: 98.5, 30: 102.5, 31: 105.5, 32: 109.5, 33: 112.5, 34: 116.5, 35: 120.0, 36: 123.5,
    37: 127.0, 38: 130.5, 39: 134.0, 40: 137.5, 41: 141.0, 42: 144.5, 43: 148.0, 44: 152.0,
    45: 155.5, 46: 159.0, 47: 162.5, 48: 166.0, 49: 169.5, 50: 173.0,
}

ROMAN = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI", 7: "VII", 8: "VIII", 9: "IX", 10: "X"}

CHROMATIC_CARDS = {2, 3, 8, 9, 10}

_HUMAN = {"human", "person", "man", "woman", "people", "lady", "figure", "child", "girl", "boy", "waiter",
          "dancer", "doll", "clown", "cartoon", "puppet"}
_GIANT = _HUMAN | {"giant", "monster", "ogre", "gorilla", "bigfoot", "yeti", "creature", "troll", "alien", "beast"}
_WITCH = _HUMAN | {"witch", "wizard", "giant", "monster", "alien", "creature", "clown", "ghost"}

# Card -> (location labels, words naming the Popular object)
POPULARS: dict[int, tuple[set[str], set[str]]] = {
    1: ({"W"}, {"bat", "butterfly"}),
    2: ({"D1"}, {"bear", "dog", "elephant", "lamb", "animal"}),
    3: ({"D9", "D1"}, _HUMAN),
    4: ({"W", "D7"}, _GIANT),
    5: ({"W"}, {"bat", "butterfly"}),
    6: ({"W", "D1"}, {"skin", "hide", "rug", "pelt", "fur"}),
    7: ({"D1", "D2", "D9"}, {"head", "face"}),
    8: ({"D1"}, {"animal", "dog", "cat", "wolf", "bear", "rat", "mouse", "lion", "tiger", "leopard",
                 "panther", "fox", "rodent", "chameleon", "lizard", "beaver", "squirrel", "pig", "cougar"}),
    9: ({"D3"}, _WITCH),
    10: ({"D1"}, {"crab", "lobster", "spider"}),
}


def is_popular(card: int, location_label: str, text: str) -> bool:
    locs, accepted = POPULARS[card]
    base = location_label.replace("S", "") if location_label.startswith("W") else location_label
    if base not in locs:
        return False
    vocab = word_set(text)
    if card == 7:  # human heads or faces
        return bool(vocab & {"head", "face"}) and bool(vocab & (_HUMAN | {"girl", "woman", "child", "indian"}))
    return bool(vocab & accepted)


def z_value(card: int, loc_code: str, dq: str, space: bool, region_count: int, has_form: bool,
            space_only: bool = False) -> float | None:
    """Organisational activity (Z). The highest applicable value is used.

    Adjacent vs distant detail cannot be read from placeholder maps, so a
    single drawn region counts as adjacent and several as distant.
    """
    if not has_form:
        return None
    zw, za, zd, zs = Z_VALUES[card]
    candidates = []
    if loc_code == "W" and dq != "v":
        candidates.append(zw)
    if loc_code != "W" and dq in ("+", "v/+"):
        candidates.append(za if region_count <= 1 else zd)
    if space and not space_only:
        candidates.append(zs)
    return max(candidates) if candidates else None


def zest(zf: int) -> float | None:
    if zf < 1:
        return None
    return ZEST[min(zf, 50)]
