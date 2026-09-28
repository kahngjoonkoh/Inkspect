"""Minimal Laya decision server for the `laya` compose profile.

Serves the same request/response shape as Laya's own `laya-serve`
(`POST /v1/systemone`), but pins one checkpoint (a fine-tuned Inkspect
checkpoint, or the public typed-decisions one) instead of routing.

    LAYA_CHECKPOINT  Hugging Face repo id or local path (default convaiinnovations/laya)
    LAYA_SUBFOLDER   subfolder inside the repo (default typed-decisions; empty for a local fine-tune)
    LAYA_DEVICE      cpu | cuda (default cpu)
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import laya
from fastapi import FastAPI
from pydantic import BaseModel

CHECKPOINT = os.environ.get("LAYA_CHECKPOINT", "convaiinnovations/laya")
SUBFOLDER = os.environ.get("LAYA_SUBFOLDER", "typed-decisions")
DEVICE = os.environ.get("LAYA_DEVICE", "cpu")

_agent: Any = None


def agent() -> Any:
    global _agent
    if _agent is None:
        kwargs: dict[str, Any] = {"device": DEVICE}
        if SUBFOLDER:
            kwargs["subfolder"] = SUBFOLDER
        try:
            _agent = laya.load(CHECKPOINT, **kwargs)
        except TypeError:  # older laya releases take no device argument
            kwargs.pop("device")
            _agent = laya.load(CHECKPOINT, **kwargs)
    return _agent


class DecisionRequest(BaseModel):
    state: str | dict[str, Any]
    questions: dict[str, dict[str, Any]]
    model: str | None = None  # accepted for laya-serve compatibility; the pinned checkpoint is always used


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    agent()  # load weights before reporting healthy
    yield


app = FastAPI(title="Inkspect Laya server", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "checkpoint": f"{CHECKPOINT}/{SUBFOLDER}".rstrip("/")}


@app.post("/v1/systemone")
def systemone(req: DecisionRequest) -> dict[str, Any]:
    return agent().predict(req.state, req.questions)
