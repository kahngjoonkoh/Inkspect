"""Tiny text helpers shared by FQ lookup and the Popular rules (no NLP dependencies)."""

import re

_IRREGULAR = {
    "people": "person", "men": "man", "women": "woman", "children": "child", "feet": "foot",
    "teeth": "tooth", "mice": "mouse", "geese": "goose", "wolves": "wolf", "leaves": "leaf",
    "knives": "knife", "halves": "half", "lives": "life", "wives": "wife", "calves": "calf",
    "butterflies": "butterfly", "flies": "fly", "ladies": "lady", "puppies": "puppy",
    "fairies": "fairy", "bodies": "body", "cherries": "cherry", "berries": "berry",
    "dice": "die", "oxen": "ox", "sheep": "sheep", "fish": "fish", "deer": "deer",
}
_KEEP_S = {"glass", "moss", "grass", "dress", "cross", "bus", "octopus", "cactus", "iris", "pelvis",
           "thorax", "virus", "walrus", "hippopotamus", "rhinoceros", "is", "this", "has", "was", "as"}

# Words that name the same thing as an FQ table head word.
SYNONYMS = {
    "person": "human", "man": "human", "woman": "human", "lady": "human", "guy": "human",
    "figure": "human", "girl": "human", "boy": "human", "child": "human", "kid": "human",
    "doggy": "dog", "puppy": "dog", "kitty": "cat", "kitten": "cat", "pelt": "skin", "hide": "skin",
    "rug": "skin", "moth": "butterfly",
}


def lemma(word: str) -> str:
    w = word.lower()
    if w in _IRREGULAR:
        return _IRREGULAR[w]
    if w in _KEEP_S or len(w) <= 3:
        return w
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith(("ches", "shes", "sses", "xes", "zes")):
        return w[:-2]
    if w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def words(text: str) -> list[str]:
    return [lemma(w) for w in re.findall(r"[a-zA-Z]+", text or "")]


def word_set(text: str) -> set[str]:
    ws = words(text)
    return set(ws) | {SYNONYMS[w] for w in ws if w in SYNONYMS}
