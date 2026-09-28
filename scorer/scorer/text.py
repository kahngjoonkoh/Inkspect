"""Tiny tokenizer and lexicon matcher (no NLP dependencies).

Instead of a real lemmatizer, `candidates()` yields plausible base forms of a
word (plural, -ing, -ed stripping with consonant/e restoration) and the
lexicon lookup accepts the first candidate it knows.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

_WORD = re.compile(r"[a-z]+(?:[-'][a-z]+)*")

IRREGULAR = {
    "people": "person", "men": "man", "women": "woman", "children": "child",
    "feet": "foot", "teeth": "tooth", "mice": "mouse", "geese": "goose",
    "wolves": "wolf", "leaves": "leaf", "knives": "knife", "lives": "life",
    "halves": "half", "calves": "calf", "hooves": "hoof", "elves": "elf",
    "dwarves": "dwarf", "scarves": "scarf", "oxen": "ox", "lice": "louse",
    "fish": "fish", "sheep": "sheep", "deer": "deer", "moose": "moose",
    "bison": "bison", "species": "species", "antennae": "antenna",
    "lying": "lie", "dying": "die", "tying": "tie", "flew": "fly", "flown": "fly",
    "ran": "run", "sat": "sit", "stood": "stand", "fought": "fight", "hung": "hang",
    "held": "hold", "ate": "eat", "fell": "fall", "swam": "swim", "sang": "sing",
    "blew": "blow", "threw": "throw", "torn": "tear", "tore": "tear", "broke": "break",
    "broken": "break", "bitten": "bite", "shot": "shoot", "killed": "kill",
    "burnt": "burn", "spread": "spread", "leapt": "leap", "crept": "creep",
}
# Plural-looking singulars that must not be stripped.
_KEEP_S = {"his", "is", "was", "has", "this", "its", "us", "gas", "yes", "as", "bus", "dress",
           "grass", "glass", "moss", "cross", "chess", "mess", "boss", "princess", "goddess",
           "octopus", "cactus", "walrus", "platypus", "pelvis", "iris", "virus", "fungus",
           "hippopotamus", "rhinoceros", "canvas", "atlas", "circus", "christmas", "less",
           "kiss", "does", "goes", "abyss", "compass", "harness", "mattress", "cyclops"}


def normalize(text: str) -> str:
    text = text.lower()
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = text.replace("colour", "color").replace("grey", "gray").replace("x-ray", "xray")
    return text


def tokens(text: str) -> list[str]:
    return _WORD.findall(normalize(text))


def candidates(word: str) -> list[str]:
    """Possible base forms of `word`, most literal first."""
    w = word.lower()
    out = [w]
    if w in IRREGULAR:
        out.append(IRREGULAR[w])
    if "'" in w:
        out.append(w.split("'")[0])
    if w.endswith("ies") and len(w) > 4:
        out.append(w[:-3] + "y")
    if w.endswith("ves") and len(w) > 4:
        out += [w[:-3] + "f", w[:-3] + "fe"]
    if w.endswith("es") and len(w) > 3:
        out.append(w[:-2])
    if w.endswith("s") and not w.endswith("ss") and w not in _KEEP_S and len(w) > 2:
        out.append(w[:-1])
    for suffix in ("ing", "ed"):
        if w.endswith(suffix) and len(w) > len(suffix) + 2:
            stem = w[: -len(suffix)]
            out += [stem, stem + "e"]
            if len(stem) > 2 and stem[-1] == stem[-2]:
                out.append(stem[:-1])
            if suffix == "ed" and stem.endswith("i"):
                out.append(stem[:-1] + "y")
    return list(dict.fromkeys(out))


def is_plural(word: str, base: str) -> bool:
    w = word.lower()
    if w in IRREGULAR and IRREGULAR[w] == base and w != base:
        return True
    return w != base and w.endswith("s") and not base.endswith("s")


@dataclass(frozen=True)
class Hit:
    """A lexicon match: `value` found as `base` at token index `index` (span = original words)."""

    value: str
    base: str
    index: int
    span: str
    plural: bool = False


def find(toks: list[str], lexicon: Mapping[str, str] | Iterable[str]) -> list[Hit]:
    """Find lexicon entries (single words or multi-word phrases) in a token list.

    `lexicon` maps base form -> value (or is a set of base forms, value = base).
    Multi-word keys are matched against consecutive tokens; each token may use
    any of its candidate forms.
    """
    lex: Mapping[str, str] = lexicon if isinstance(lexicon, Mapping) else {k: k for k in lexicon}
    phrases = sorted((k for k in lex if " " in k), key=lambda k: -len(k.split()))
    hits: list[Hit] = []
    used: set[int] = set()
    for phrase in phrases:
        parts = phrase.split()
        n = len(parts)
        for i in range(len(toks) - n + 1):
            if any(j in used for j in range(i, i + n)):
                continue
            if all(parts[k] in candidates(toks[i + k]) for k in range(n)):
                hits.append(Hit(lex[phrase], phrase, i, " ".join(toks[i:i + n]),
                                is_plural(toks[i + n - 1], parts[-1])))
                used.update(range(i, i + n))
    for i, t in enumerate(toks):
        if i in used:
            continue
        for c in candidates(t):
            if c in lex and " " not in c:
                hits.append(Hit(lex[c], c, i, t, is_plural(t, c)))
                break
    hits.sort(key=lambda h: h.index)
    return hits


def has_phrase(text: str, phrases: Iterable[str]) -> str | None:
    """Return the first phrase (regex-safe literal, word-bounded) found in normalized text."""
    norm = " ".join(tokens(text))
    for p in phrases:
        if re.search(rf"\b{re.escape(p)}\b", norm):
            return p
    return None
