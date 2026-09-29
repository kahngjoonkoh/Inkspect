"""Form Quality lookup in the Exner FQ table (data/fq_tables.db, not in git).

Only an entry at the same card and location gives an FQ value. An entry for the
same object elsewhere on the card still gives the content code as a hint.
"""

import logging
import sqlite3
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .config import settings
from .text import word_set, words

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class FQEntry:
    card: int
    loc: str
    orientation: str  # "^" when the table gives none
    item: str
    head: tuple[str, ...]
    qualifier: frozenset[str]
    content: str
    fq: str


def _orientation(v: str | None) -> str:
    return {"v": "v", "V": "v", "<": "<", ">": ">"}.get(v or "", "^")


@lru_cache(maxsize=2)
def load_table(path: Path = settings.fq_db_path) -> tuple[FQEntry, ...]:
    if not path.is_file():
        log.warning("No FQ table at %s; FQ falls back to the coder's u/- estimate", path)
        return ()
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        rows = con.execute("SELECT Card, Loc, v, Item, Cont, FQ FROM FQ_tables").fetchall()
    finally:
        con.close()
    entries = []
    for card, loc, v, item, cont, fq in rows:
        if fq not in ("o", "u", "-") or not item:
            continue  # '***' marks a cross-reference row
        head_text, _, qual = item.partition("(")
        head = tuple(words(head_text))
        if not head:
            continue
        entries.append(FQEntry(int(card), loc.strip(), _orientation(v), item.strip(), head,
                               frozenset(words(qual)), cont.strip(), fq))
    return tuple(entries)


@dataclass(frozen=True)
class FQMatch:
    item: str
    content: str
    fq: str
    loc: str
    location_match: bool

    def as_dict(self) -> dict:
        return {"item": self.item, "content": self.content, "fq": self.fq, "loc": self.loc,
                "location_match": self.location_match}


def lookup(card: int, location_label: str, orientation: str, verbatim: str, inquiry: str = "",
           table: tuple[FQEntry, ...] | None = None) -> FQMatch | None:
    """Best table entry for the object named in the response.

    The object must be named in the response itself. Parts mentioned only in
    the inquiry ("here is the head") are not the scored object; the inquiry
    only helps choose between qualified entries.
    """
    table = table if table is not None else load_table()
    named = word_set(verbatim)
    vocab = named | word_set(inquiry)
    best, best_score = None, 0.0
    for e in table:
        if e.card != card or not all(h in named for h in e.head):
            continue
        score = 10.0 * len(e.head)
        loc_match = e.loc == location_label
        if loc_match:
            score += 5
        if e.orientation == orientation:
            score += 1
        overlap = len(e.qualifier & vocab)
        score += 0.5 * overlap - (0.1 * len(e.qualifier) if not overlap else 0)
        if score > best_score:
            best, best_score = FQMatch(e.item, e.content, e.fq, e.loc, loc_match), score
    return best


_PART_WORDS = {"head", "ear", "eye", "wing", "leg", "arm", "hand", "foot", "tail", "body", "nose", "mouth",
               "antenna", "claw", "feeler", "horn", "beak", "neck", "shoulder", "hair", "face", "finger",
               "paw", "chest", "back", "belly", "fin", "hat", "coat", "skirt", "shoe", "boot"}


def articulation(text: str) -> int:
    """Number of distinct object parts named — used for the FQ '+' upgrade."""
    return len(set(words(text)) & _PART_WORDS)
