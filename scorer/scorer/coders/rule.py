"""Deterministic, lexicon-based CS coder.

This is the default backend and the test baseline. It codes what surface
words reveal (content nouns, movement verbs, colour/shading/texture words,
morbid/aggressive vocabulary) and leaves anything needing real judgement to
the reviewer or a trained backend. Every code carries the words it was based
on (`evidence`) and a rough confidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .. import lexicon as lx
from ..schema import ACHROMATIC_CARDS, CodeRequest, Codes
from ..text import Hit, find, has_phrase, tokens
from .base import Coder

_EMOTIONS = {"sad": "p", "happy": "p", "angry": "a", "furious": "a", "scared": "p", "afraid": "p",
             "depressed": "p", "lonely": "p", "joyful": "p", "jealous": "p", "ashamed": "p", "proud": "p",
             "worried": "p", "anxious": "p", "calm": "p", "peaceful": "p", "surprised": "p", "shocked": "p",
             "frightened": "p", "terrified": "p", "miserable": "p", "unhappy": "p", "grieving": "p"}
_LOOK_DIRECTIONS = {"at", "into", "down", "up", "out", "over", "toward", "towards", "around", "back",
                    "away", "through", "across", "each", "sideways"}
_LOCATION_NOUNS = {"part", "parts", "area", "areas", "space", "spot", "spots", "bit", "bits", "section",
                   "sections", "background", "blob", "blobs", "patch", "patches", "piece", "pieces",
                   "one", "ones", "thing", "things", "region", "stuff"}
_UNNATURAL_COLORS = {"green", "blue", "pink", "purple", "violet", "turquoise", "magenta"}
# Animals that really are these colours, so "blue crab" is not an INCOM.
_NATURALLY_COLORED = {"crab", "jay", "whale", "bird", "flamingo", "frog", "lizard", "parrot", "snake",
                      "caterpillar", "beetle", "fish", "butterfly", "dragonfly", "grasshopper", "chameleon",
                      "iguana", "gecko", "moth", "peacock", "hummingbird", "tree frog", "lobster", "shrimp",
                      "octopus", "jellyfish", "worm", "insect", "bug", "spider", "mantis", "shark"}
_DEPTH_STRONG = {"in the distance", "far away", "from above", "from below", "perspective", "background",
                 "foreground", "looking down", "3d", "three dimensional", "depth", "receding", "far"}
_STATIVE = {"bit", "look", "looks", "looked", "seem", "seems", "seemed", "is", "are", "was", "were", "been",
            "got", "get", "gets", "being", "kind", "sort", "little"}
_INQUIRY_PAIR = ("one on each side", "two of them", "both of them", "twins")


@dataclass
class _Obj:
    """A content hit plus what it refers to."""

    hit: Hit
    code: str
    whole: bool
    source: str  # "v" (verbatim) or "i" (inquiry)


@dataclass
class _Acc:
    evidence: dict[str, str] = field(default_factory=dict)
    confidence: dict[str, float] = field(default_factory=dict)

    def note(self, code: str, span: str, conf: float) -> None:
        self.evidence.setdefault(code, span)
        self.confidence[code] = max(conf, self.confidence.get(code, 0.0))


def _is_part(code: str, base: str) -> bool:
    return code in ("Hd", "(Hd)", "Ad", "(Ad)") or base in lx.SHARED_PARTS


def _content_hits(toks: list[str]) -> list[Hit]:
    hits = []
    for h in find(toks, lx.CONTENT):
        if h.base in lx.NOUN_NEEDS_DETERMINER and not _determined(toks, h.index):
            continue
        hits.append(h)
    taken = {h.index for h in hits}
    for i, t in enumerate(toks):
        if i in taken or t not in lx.NOUN_NEEDS_DETERMINER and t.rstrip("s") not in lx.NOUN_NEEDS_DETERMINER:
            continue
        base = t if t in lx.NOUN_NEEDS_DETERMINER else t.rstrip("s")
        if base in lx.CONTENT or not _determined(toks, i):
            continue
        hits.append(Hit(lx.NOUN_NEEDS_DETERMINER[base], base, i, t, t != base))
    hits.sort(key=lambda h: h.index)
    return hits


def _determined(toks: list[str], i: int) -> bool:
    t = toks[i]
    if t.endswith("ing") or t.endswith("ed"):
        return False
    if i == 0:
        return True
    return any(toks[j] in lx.DETERMINERS for j in range(max(0, i - 3), i))


def _fictional(code: str) -> bool:
    return code.startswith("(")


def _detail_code(whole_code: str) -> str:
    return {"H": "Hd", "(H)": "(Hd)", "A": "Ad", "(A)": "(Ad)"}.get(whole_code, whole_code)


class RuleCoder(Coder):
    name = "rule"

    def code(self, req: CodeRequest) -> Codes:
        acc = _Acc()
        v_toks = tokens(req.verbatim)
        i_toks = tokens(req.inquiry_text())
        full = f"{req.verbatim} {req.inquiry_text()}"

        objects, primary = self._objects(v_toks, i_toks, acc)
        contents = self._contents(objects, primary, v_toks + i_toks, req, acc)

        movement = self._movement(v_toks, i_toks, objects, primary, acc)
        dq = self._dq(objects, v_toks, i_toks, primary, movement, acc)
        base = primary.hit.base if primary else None
        elaborated = any(o.source == "i" and o.hit.base != base for o in objects)
        determinants, special = self._determinants(req, v_toks, i_toks, dq, movement, elaborated, acc)

        reflection = any(d in ("Fr", "rF") for d in determinants)
        pair = False if reflection else self._pair(v_toks, i_toks, primary, acc)
        special += self._special(req, full, v_toks, i_toks, objects, primary, pair, movement, acc)

        if req.fq_hint is not None:
            fq_fallback = None
        elif req.location is not None and req.location.label.startswith("Dd") and req.location.label.endswith("99"):
            fq_fallback = "-"
        else:
            fq_fallback = "u"

        return Codes(
            dq=dq,
            determinants=determinants,
            pair=pair,
            contents=contents,
            special_scores=special,
            fq_fallback=fq_fallback,
            evidence=acc.evidence,
            confidence=acc.confidence,
            coder="rule",
        )

    # --- contents --------------------------------------------------------------------

    def _objects(self, v_toks: list[str], i_toks: list[str], acc: _Acc) -> tuple[list[_Obj], _Obj | None]:
        objs = [_Obj(h, h.value, not _is_part(h.value, h.base), "v") for h in _content_hits(v_toks)]
        objs += [_Obj(h, h.value, not _is_part(h.value, h.base), "i") for h in _content_hits(i_toks)]

        v_objs = [o for o in objs if o.source == "v"]
        # "tusks of an elephant", "animal skin", "dog's head": a part attached to a whole is a detail.
        for k, o in enumerate(v_objs):
            if o.whole:
                continue
            for w in v_objs:
                if not w.whole or w.code not in lx.WHOLE_HUMAN | lx.WHOLE_ANIMAL:
                    continue
                gap = v_toks[o.hit.index + 1: w.hit.index]
                attached_after = w.hit.index < o.hit.index and o.hit.index - w.hit.index <= 2
                if (0 < w.hit.index - o.hit.index <= 4 and "of" in gap) or attached_after:
                    w.code = _detail_code(w.code)
                    w.whole = False
                    o.code = w.code
                    acc.note(w.code, f"{o.hit.span} … {w.hit.span}" if not attached_after
                             else f"{w.hit.span} {o.hit.span}", 0.75)
                    break

        wholes_v = [o for o in v_objs if o.whole]
        primary = wholes_v[0] if wholes_v else None
        if primary is None:
            detail_v = [o for o in v_objs if o.code in ("Hd", "(Hd)", "Ad", "(Ad)")]
            shared_v = [o for o in v_objs if o.hit.base in lx.SHARED_PARTS]
            if detail_v:
                primary = detail_v[0]
            elif shared_v:
                o = shared_v[0]
                animal_context = any(x.code in lx.WHOLE_ANIMAL for x in objs if x.source == "i")
                o.code = "Ad" if animal_context else "Hd"
                primary = o
        if primary is None:
            wholes_i = [o for o in objs if o.source == "i" and o.whole]
            primary = wholes_i[0] if wholes_i else None
        return objs, primary

    def _contents(self, objs: list[_Obj], primary: _Obj | None, all_toks: list[str], req: CodeRequest,
                  acc: _Acc) -> list[str]:
        contents: list[str] = []

        def add(code: str, span: str, conf: float) -> None:
            if code not in contents:
                contents.append(code)
            acc.note(code, span, conf)

        if req.fq_hint is not None and req.fq_hint.content in lx.CONTENT.values():
            add(req.fq_hint.content, req.fq_hint.item, 0.85)
        if primary is not None:
            add(primary.code, primary.hit.span, 0.8 if primary.source == "v" else 0.55)
        for o in objs:
            if o is primary or o.code in contents:
                continue
            if o.source == "v":
                if o.whole or o.code in ("Hd", "(Hd)", "Ad", "(Ad)"):
                    # A detail of the primary object is already covered by the primary's code.
                    if not o.whole and primary is not None and primary.code in lx.HUMAN_CONTENTS | lx.ANIMAL_CONTENTS:
                        continue
                    add(o.code, o.hit.span, 0.7)
            elif o.whole and o.code not in lx.HUMAN_CONTENTS | lx.ANIMAL_CONTENTS:
                # Secondary content first mentioned in the inquiry (blood, clouds, a hat...).
                add(o.code, o.hit.span, 0.5)
        emo = find(all_toks, lx.HUMAN_EXPERIENCE)
        if emo:
            add("Hx", emo[0].span, 0.6)
        if req.fq_hint is not None:
            keep = req.fq_hint.content
            # "Rabbit ears" matches the table's "Rabbit" (A), but the response names a detail (Ad).
            if primary is not None and primary.source == "v" and primary.code == _detail_code(keep):
                keep = primary.code
            fam = ({"H", "(H)", "Hd", "(Hd)"} if keep in lx.HUMAN_CONTENTS
                   else {"A", "(A)", "Ad", "(Ad)"} if keep in lx.ANIMAL_CONTENTS else set())
            contents = [c for c in contents if c == keep or c not in fam]
        if not contents:
            add("Id", req.verbatim.strip()[:40] or "-", 0.3)
        return contents

    # --- developmental quality -----------------------------------------------------------

    def _dq(self, objs: list[_Obj], v_toks: list[str], i_toks: list[str], primary: _Obj | None,
            movement: dict[str, list[tuple[str, int, str, bool]]], acc: _Acc) -> str:
        wholes = [o for o in objs if o.source == "v" and o.whole]
        distinct = list(dict.fromkeys(o.hit.base for o in wholes))
        all_toks = v_toks + i_toks
        relation = find(all_toks, lx.RELATION_WORDS)
        group = find(v_toks, lx.GROUP_WORDS)
        together = find(all_toks, lx.TOGETHER)
        formless = [b for b in distinct if b in lx.FORMLESS]
        all_formless = bool(distinct) and len(formless) == len(distinct)

        if group and primary is not None and primary.hit.plural:
            acc.note("DQ+", f"{group[0].span} … {primary.hit.span}", 0.7)
            return "+"
        if len(distinct) >= 2 and relation:
            code = "v/+" if all_formless else "+"
            acc.note(f"DQ{code}", f"{distinct[0]} {relation[0].span} {distinct[1]}", 0.6)
            return code
        interaction = together or (movement and (find(all_toks, lx.COOPERATIVE_VERBS) or find(all_toks, lx.AGGRESSIVE)))
        if primary is not None and primary.hit.plural and interaction:
            acc.note("DQ+", f"{primary.hit.span} {interaction[0].span}", 0.6)
            return "+"
        if all_formless:
            acc.note("DQv", formless[0], 0.6)
            return "v"
        if primary is None and not distinct:
            acc.note("DQv", "no specific object", 0.3)
            return "v"
        acc.note("DQo", primary.hit.span if primary else distinct[0], 0.6)
        return "o"

    # --- movement ------------------------------------------------------------------

    def _movement(self, v_toks: list[str], i_toks: list[str], objs: list[_Obj], primary: _Obj | None,
                  acc: _Acc) -> dict[str, list[tuple[str, int, str, bool]]]:
        """Return {base: [(a|p, subject_id, span, human_only_by_animal)]} for M / FM / m."""
        found: dict[str, list[tuple[str, int, str, bool]]] = {}
        for source, toks in (("v", v_toks), ("i", i_toks)):
            content_idx = {o.hit.index for o in objs if o.source == source}
            for h in find(toks, lx.MOVEMENT):
                nxt = toks[h.index + 1] if h.index + 1 < len(toks) else ""
                if h.index in content_idx:
                    continue
                if h.base == "look" and nxt not in _LOOK_DIRECTIONS:
                    continue
                if nxt in lx.NON_MOVEMENT_AFTER.get(h.base, ()):
                    continue
                if h.base in lx.CONTENT and _determined(toks, h.index):
                    continue
                prev = toks[h.index - 1] if h.index > 0 else ""
                if prev in _STATIVE and not h.span.endswith("ing"):
                    continue  # "looks a bit burst", "is spread": a state, not movement
                subject = self._subject(objs, source, h.index, primary)
                kind = self._kind(subject)
                human_only = h.base in lx.HUMAN_ONLY_VERBS
                if h.base in lx.INANIMATE_VERBS and kind == "inanimate":
                    base = "m"
                elif kind == "human":
                    base = "M"
                elif kind == "animal":
                    base = "M" if human_only else "FM"
                else:
                    base = "m"
                sid = id(subject) if subject is not None else -1
                found.setdefault(base, []).append((h.value, sid, h.span, kind == "animal" and human_only))
        # Human experience attributed to a figure ("a sad animal") is M in CS.
        for source, toks in (("v", v_toks), ("i", i_toks)):
            for i, t in enumerate(toks):
                if t in _EMOTIONS and primary is not None and self._kind(primary) in ("human", "animal"):
                    found.setdefault("M", []).append((_EMOTIONS[t], id(primary), t, False))
        return found

    @staticmethod
    def _subject(objs: list[_Obj], source: str, index: int, primary: _Obj | None) -> _Obj | None:
        before = [o for o in objs if o.source == source and o.hit.index < index and o.whole]
        return before[-1] if before else primary

    @staticmethod
    def _kind(obj: _Obj | None) -> str:
        if obj is None:
            return "inanimate"
        if obj.code in lx.HUMAN_CONTENTS:
            return "human"
        if obj.code in lx.ANIMAL_CONTENTS:
            return "animal"
        return "inanimate"

    # --- determinants -------------------------------------------------------------------

    def _determinants(self, req: CodeRequest, v_toks: list[str], i_toks: list[str], dq: str,
                      movement: dict[str, list[tuple[str, int, str, bool]]], elaborated: bool,
                      acc: _Acc) -> tuple[list[str], list[str]]:
        dets: list[str] = []
        special: list[str] = []
        all_toks = v_toks + i_toks
        form = dq in ("+", "o")

        for base in ("M", "FM", "m"):
            items = movement.get(base)
            if not items:
                continue
            kinds = {k for k, _, _, _ in items}
            if kinds == {"a", "p"}:
                subjects_a = {s for k, s, _, _ in items if k == "a"}
                subjects_p = {s for k, s, _, _ in items if k == "p"}
                sup = "a-p" if subjects_a != subjects_p else "a"
            else:
                sup = kinds.pop()
            dets.append(f"{base}{sup}")
            acc.note(f"{base}{sup}", ", ".join(dict.fromkeys(span for _, _, span, _ in items)), 0.7)

        def determinant_hits(lexicon: frozenset[str]) -> list[Hit]:
            out = []
            for h in find(all_toks, lexicon):
                nxt = all_toks[h.index + len(h.base.split())] if h.index + len(h.base.split()) < len(all_toks) else ""
                if nxt in _LOCATION_NOUNS:
                    continue  # "the red part" locates; it does not explain the percept
                out.append(h)
            return out

        chroma = determinant_hits(lx.CHROMATIC)
        if chroma:
            if req.card in ACHROMATIC_CARDS:
                special.append("CP")
                acc.note("CP", chroma[0].span, 0.6)
            else:
                only_colors = v_toks and all(t in lx.CHROMATIC or t in {"and", "the", "it", "is", "just", "a",
                                                                      "some", "colors", "all", "of"} for t in v_toks)
                if only_colors:
                    code = "Cn"
                elif form:
                    code = "FC"
                elif elaborated or find(all_toks, lx.FORM_WORDS):
                    code = "CF"
                else:
                    code = "C"
                dets.append(code)
                acc.note(code, chroma[0].span, 0.65)

        def near_shading(h: Hit) -> bool:
            window = all_toks[max(0, h.index - 2): h.index + 3]
            return any(w in ("light", "lighter", "shading", "shade", "shades", "shaded") for w in window)

        def shaded(lexicon: frozenset[str], f_code: str, mid: str, pure: str, conf: float) -> None:
            hits = determinant_hits(lexicon)
            if lexicon is lx.ACHROMATIC:
                hits = [h for h in hits if not near_shading(h)]
            if not hits:
                return
            code = f_code if form else (mid if find(all_toks, lx.FORM_WORDS) else pure)
            dets.append(code)
            acc.note(code, hits[0].span, conf)

        shaded(lx.ACHROMATIC, "FC'", "C'F", "C'", 0.55)
        shaded(frozenset(lx.TEXTURE - {"feel"}), "FT", "TF", "T", 0.6)

        shading = determinant_hits(lx.SHADING)
        depth = find(all_toks, lx.DEPTH)
        if shading and depth:
            code = "FV" if form else "VF"
            dets.append(code)
            acc.note(code, f"{shading[0].span} … {depth[0].span}", 0.5)
        elif shading:
            code = "FY" if form else "YF"
            dets.append(code)
            acc.note(code, shading[0].span, 0.55)
        elif any(h.base in _DEPTH_STRONG for h in depth):
            dets.append("FD")
            acc.note("FD", next(h.span for h in depth if h.base in _DEPTH_STRONG), 0.5)

        refl = find(all_toks, lx.REFLECTION)
        if refl:
            code = "Fr" if form else "rF"
            dets.append(code)
            acc.note(code, refl[0].span, 0.7)

        if not dets:
            dets.append("F")
            acc.note("F", "no other determinant reported", 0.6)
        return dets, special

    # --- pair -------------------------------------------------------------------

    def _pair(self, v_toks: list[str], i_toks: list[str], primary: _Obj | None, acc: _Acc) -> bool:
        # "the two blue spots" only locates; drop number words that precede a location noun.
        kept = [t for k, t in enumerate(v_toks)
                if not (t in ("two", "both") and any(x in _LOCATION_NOUNS for x in v_toks[k + 1:k + 4]))]
        hit = has_phrase(" ".join(kept), [p for p in lx.PAIR_WORDS if p not in ("the sides", "on the sides")])
        if hit is None:
            hit = has_phrase(" ".join(i_toks), _INQUIRY_PAIR)
        if hit is None and primary is not None and primary.source == "v" and primary.whole and primary.hit.plural:
            hit = primary.hit.span
        if hit:
            acc.note("(2)", hit, 0.65)
            return True
        return False

    # --- special scores ------------------------------------------------------------

    def _special(self, req: CodeRequest, full: str, v_toks: list[str], i_toks: list[str], objs: list[_Obj],
                 primary: _Obj | None, pair: bool, movement: dict[str, list[tuple[str, int, str, bool]]],
                 acc: _Acc) -> list[str]:
        out: list[str] = []
        all_toks = v_toks + i_toks

        def add(code: str, span: str, conf: float) -> None:
            if code not in out:
                out.append(code)
            acc.note(code, span, conf)

        dv = has_phrase(full, lx.DEVIANT_VERBALIZATIONS)
        if dv:
            add("DV1", dv, 0.6)

        wholes = [o for o in objs if o.whole]
        animals = [o for o in wholes if o.code in lx.WHOLE_ANIMAL]
        humans = [o for o in wholes if o.code in lx.WHOLE_HUMAN]
        animal_whole = animals or (primary is not None and primary.code in lx.ANIMAL_CONTENTS)
        human_parts = find(all_toks, lx.HUMAN_ONLY_PARTS)
        if animal_whole and not humans and human_parts:
            add("INC1", human_parts[0].span, 0.55)
        if any(o.hit.base in lx.INVERTEBRATES for o in wholes):
            face = [h for h in find(all_toks, {"face"})]
            if face:
                add("INC1", face[0].span, 0.5)
        for o in wholes:
            if (o.code in ("A", "H") and o.source == "v" and o.hit.index > 0
                    and v_toks[o.hit.index - 1] in _UNNATURAL_COLORS and o.hit.base not in _NATURALLY_COLORED):
                add("INC1", f"{v_toks[o.hit.index - 1]} {o.hit.span}", 0.55)

        many_animals = len(animals) >= 2 or (pair and animal_whole) or (primary is not None and primary.hit.plural
                                                                     and primary.code in lx.ANIMAL_CONTENTS)
        if many_animals and any(flag for items in movement.values() for *_, flag in items):
            span = next(s for items in movement.values() for _, _, s, flag in items if flag)
            add("FAB1", span, 0.5)

        mor = find(all_toks, lx.MORBID)
        if mor:
            add("MOR", mor[0].span, 0.7)
        ag = find(all_toks, lx.AGGRESSIVE)
        if ag:
            add("AG", ag[0].span, 0.65)
        coop = find(all_toks, lx.COOPERATIVE_VERBS)
        together = find(all_toks, lx.TOGETHER)
        living = len(animals) + len(humans)
        if coop and not ag and (pair or together or living >= 2) and movement:
            add("COP", coop[0].span, 0.55)
        per = has_phrase(full, lx.PERSONAL)
        if per:
            add("PER", per, 0.6)
        ab = find(all_toks, lx.ABSTRACT)
        if ab:
            add("AB", ab[0].span, 0.5)
        return out
