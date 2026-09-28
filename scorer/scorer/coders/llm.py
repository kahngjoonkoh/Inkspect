"""Hosted-LLM coder (Claude via the official `anthropic` SDK).

The model gets the CS coding rules and the allowed vocabularies, and must
answer with JSON matching a strict schema (structured outputs). Anything that
fails validation raises, and the service falls back to the RuleCoder.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from ..schema import CONTENTS, DETERMINANTS, SPECIAL_SCORES, CodeRequest, Codes, state_text
from .base import Coder, CoderUnavailable

log = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-opus-5"

SYSTEM_PROMPT = f"""You code Rorschach responses with the Exner Comprehensive System (CS).
You receive one response: the card, its orientation, the location the person drew (already coded),
what they said in the response phase, and what they said in the inquiry (plus answers to follow-up questions).

Code only what the person actually said; do not infer determinants they did not report.
- Developmental Quality (dq): "+" two or more objects described as related, at least one with specific form;
  "o" one object with specific form; "v/+" two or more related objects, none with specific form; "v" no specific form.
- Determinants (a blend is several): M (human movement or human experience), FM (animal movement), m (inanimate movement),
  each with a/p/a-p superscript, e.g. "Ma", "FMp", "ma-p". Chromatic colour: FC (form primary), CF (colour primary),
  C (pure colour), Cn (colour naming). Achromatic: FC', C'F, C'. Texture: FT, TF, T. Vista: FV, VF, V.
  Diffuse shading: FY, YF, Y. Reflection: Fr, rF. Form dimension: FD. Use "F" only when nothing else applies.
  Colour used only to locate an area ("the red part") is not a determinant. On achromatic cards (I, IV, V, VI, VII)
  a reported chromatic colour is the special score CP, not a colour determinant.
- pair: true for "(2)": two identical objects based on symmetry (not with reflection).
- contents: CS content codes, primary first.
- special_scores: DV/INC/DR/FAB level 1 or 2, ALOG, CONTAM, AB, AG, COP, MOR, PER, CP.
- fq_fallback: "u" if the object is easily seen in that area, "-" if it distorts the area; "none" if no form is used.
- evidence: for each code you assign, the exact words from the response or inquiry it rests on.
- confidence: your confidence in each code, 0 to 1.

Allowed determinants: {", ".join(DETERMINANTS)}
Allowed contents: {", ".join(CONTENTS)}
Allowed special scores: {", ".join(SPECIAL_SCORES)}"""

OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "dq": {"type": "string", "enum": ["+", "o", "v/+", "v"]},
        "determinants": {"type": "array", "items": {"type": "string", "enum": list(DETERMINANTS)}},
        "pair": {"type": "boolean"},
        "contents": {"type": "array", "items": {"type": "string", "enum": list(CONTENTS)}},
        "special_scores": {"type": "array", "items": {"type": "string", "enum": list(SPECIAL_SCORES)}},
        "fq_fallback": {"type": "string", "enum": ["u", "-", "none"]},
        "evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"code": {"type": "string"}, "span": {"type": "string"}},
                "required": ["code", "span"],
                "additionalProperties": False,
            },
        },
        "confidence": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"code": {"type": "string"}, "value": {"type": "number"}},
                "required": ["code", "value"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["dq", "determinants", "pair", "contents", "special_scores", "fq_fallback", "evidence",
                 "confidence"],
    "additionalProperties": False,
}


def user_message(req: CodeRequest) -> str:
    hint = ""
    if req.fq_hint is not None:
        hint = (f"\nExner FQ table match for this area: {req.fq_hint.item} "
                f"(content {req.fq_hint.content}, FQ {req.fq_hint.fq})")
    return state_text(req) + hint


def parse_output(data: dict[str, Any]) -> Codes:
    fq = data.get("fq_fallback")
    return Codes(
        dq=data["dq"],
        determinants=data["determinants"] or ["F"],
        pair=bool(data["pair"]),
        contents=data["contents"] or ["Id"],
        special_scores=data["special_scores"],
        fq_fallback=None if fq in (None, "none") else fq,
        evidence={e["code"]: e["span"] for e in data.get("evidence", [])},
        confidence={c["code"]: c["value"] for c in data.get("confidence", [])},
        coder="llm",
    )


class LLMCoder(Coder):
    name = "llm"

    def __init__(self, client: Any = None, model: str | None = None) -> None:
        self._client = client
        self.model = model or os.environ.get("LLM_MODEL") or DEFAULT_MODEL
        self.effort = os.environ.get("LLM_EFFORT", "low")

    def available(self) -> bool:
        return self._client is not None or bool(os.environ.get("ANTHROPIC_API_KEY"))

    def _get_client(self) -> Any:
        if self._client is None:
            if not os.environ.get("ANTHROPIC_API_KEY"):
                raise CoderUnavailable("ANTHROPIC_API_KEY is not set")
            import anthropic

            self._client = anthropic.Anthropic(max_retries=2, timeout=60.0)
        return self._client

    def code(self, req: CodeRequest) -> Codes:
        client = self._get_client()
        response = client.beta.messages.create(
            model=self.model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message(req)}],
            output_config={"effort": self.effort, "format": {"type": "json_schema", "schema": OUTPUT_SCHEMA}},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        if response.stop_reason == "refusal":
            raise RuntimeError("model declined to code this response")
        if response.stop_reason == "max_tokens":
            raise RuntimeError("model output was truncated")
        text = next((b.text for b in response.content if getattr(b, "type", None) == "text"), None)
        if text is None:
            raise RuntimeError("model returned no text block")
        return parse_output(json.loads(text))
