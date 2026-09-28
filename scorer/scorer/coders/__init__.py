"""Coder registry. All backends implement `Coder.code(CodeRequest) -> Codes`."""

from __future__ import annotations

from .base import Coder, CoderUnavailable
from .laya import LayaCoder
from .llm import LLMCoder
from .rule import RuleCoder

__all__ = ["Coder", "CoderUnavailable", "LLMCoder", "LayaCoder", "RuleCoder", "get_coder"]

_FACTORIES = {"rule": RuleCoder, "llm": LLMCoder, "laya": LayaCoder}


def get_coder(name: str) -> Coder:
    try:
        return _FACTORIES[name]()
    except KeyError:
        raise ValueError(f"unknown coder {name!r}; expected one of {sorted(_FACTORIES)}") from None
