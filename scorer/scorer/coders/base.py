"""The Coder interface every backend implements."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..schema import CodeRequest, Codes, CoderName


class CoderUnavailable(RuntimeError):
    """Raised when a backend is not configured or cannot be reached (caller falls back to rules)."""


class Coder(ABC):
    name: CoderName

    def available(self) -> bool:
        """Cheap configuration check (no network)."""
        return True

    @abstractmethod
    def code(self, req: CodeRequest) -> Codes:
        """Return CS codes for one response. May raise CoderUnavailable or any error on failure."""
