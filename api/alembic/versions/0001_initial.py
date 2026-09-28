"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-28
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("phase", sa.String(16), nullable=False),
        sa.Column("current_card", sa.Integer(), nullable=False),
        sa.Column("administration", sa.Integer(), nullable=False),
        sa.Column("card1_prompted", sa.Boolean(), nullable=False),
        sa.Column("empty_prompted_card", sa.Integer(), nullable=True),
        sa.Column("scored_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "responses",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("administration", sa.Integer(), nullable=False),
        sa.Column("card", sa.Integer(), nullable=False),
        sa.Column("verbatim", sa.Text(), nullable=False),
        sa.Column("orientation", sa.String(1), nullable=False),
        sa.Column("reaction_ms", sa.Integer(), nullable=True),
        sa.Column("discarded", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("regions", sa.JSON(), nullable=False),
        sa.Column("whole_card", sa.Boolean(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("followups", sa.JSON(), nullable=False),
        sa.Column("pending_followup", sa.Text(), nullable=True),
        sa.Column("inquiry_done", sa.Boolean(), nullable=False),
        sa.Column("location", sa.JSON(), nullable=True),
        sa.Column("fq_match", sa.JSON(), nullable=True),
        sa.Column("codes", sa.JSON(), nullable=True),
        sa.Column("override", sa.JSON(), nullable=True),
        sa.Column("overridden_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_responses_session_id", "responses", ["session_id"])
    op.create_table(
        "region_maps",
        sa.Column("card", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("region_maps")
    op.drop_index("ix_responses_session_id", table_name="responses")
    op.drop_table("responses")
    op.drop_table("sessions")
