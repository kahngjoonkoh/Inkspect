"""HTTP client for the scorer service."""

import httpx

from .config import settings


class ScorerUnavailable(RuntimeError):
    pass


class ScorerClient:
    def __init__(self, base_url: str = settings.scorer_url, transport: httpx.BaseTransport | None = None):
        self._client = httpx.Client(base_url=base_url, timeout=httpx.Timeout(90.0, connect=3.0),
                                    transport=transport)

    def _post(self, path: str, body: dict) -> dict:
        try:
            r = self._client.post(path, json=body)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPError as exc:
            raise ScorerUnavailable(str(exc)) from exc

    def code(self, body: dict) -> dict:
        return self._post("/code", body)

    def followup(self, body: dict) -> dict:
        return self._post("/followup", body)

    def health(self) -> bool:
        try:
            return self._client.get("/health", timeout=2.0).status_code == 200
        except httpx.HTTPError:
            return False


_client: ScorerClient | None = None


def get_scorer() -> ScorerClient:
    global _client
    if _client is None:
        _client = ScorerClient()
    return _client
