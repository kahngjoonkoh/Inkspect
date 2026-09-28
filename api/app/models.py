import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def now() -> datetime:
    return datetime.now(timezone.utc)


class ExamSession(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    phase: Mapped[str] = mapped_column(String(16), default="response")
    current_card: Mapped[int] = mapped_column(Integer, default=1)
    administration: Mapped[int] = mapped_column(Integer, default=1)
    card1_prompted: Mapped[bool] = mapped_column(Boolean, default=False)
    empty_prompted_card: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    responses: Mapped[list["Response"]] = relationship(
        back_populates="session", order_by="Response.id", cascade="all, delete-orphan"
    )

    @property
    def active_responses(self) -> list["Response"]:
        return [r for r in self.responses if not r.discarded]


class Response(Base):
    __tablename__ = "responses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    administration: Mapped[int] = mapped_column(Integer, default=1)
    card: Mapped[int] = mapped_column(Integer)
    verbatim: Mapped[str] = mapped_column(Text)
    orientation: Mapped[str] = mapped_column(String(1), default="^")
    reaction_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    discarded: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    # Inquiry phase
    regions: Mapped[list[Any]] = mapped_column(JSON, default=list)
    whole_card: Mapped[bool] = mapped_column(Boolean, default=False)
    explanation: Mapped[str] = mapped_column(Text, default="")
    followups: Mapped[list[Any]] = mapped_column(JSON, default=list)
    pending_followup: Mapped[str | None] = mapped_column(Text, nullable=True)
    inquiry_done: Mapped[bool] = mapped_column(Boolean, default=False)

    # Scoring
    location: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    fq_match: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    codes: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    override: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    overridden_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped[ExamSession] = relationship(back_populates="responses")


class RegionMap(Base):
    __tablename__ = "region_maps"

    card: Mapped[int] = mapped_column(Integer, primary_key=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
