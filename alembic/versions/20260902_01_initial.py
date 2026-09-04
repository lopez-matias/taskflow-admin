"""Initial OrangeFlow schema.

Revision ID: 20260902_01
Revises:
Create Date: 2026-09-02 00:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260902_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


priority_enum = sa.Enum("low", "medium", "high", "critical", name="priority_enum", native_enum=False, create_constraint=True)
status_enum = sa.Enum("new", "assigned", "in_progress", "blocked", "resolved", "closed", name="request_status_enum", native_enum=False, create_constraint=True)


def upgrade() -> None:
    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("color", sa.String(7), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_departments_name", "departments", ["name"], unique=True)
    op.create_index("ix_departments_is_active", "departments", ["is_active"])

    op.create_table(
        "request_categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("icon", sa.String(30), nullable=False),
        sa.Column("description", sa.String(280)),
        sa.Column("is_active", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_request_categories_name", "request_categories", ["name"], unique=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", sa.String(80), nullable=False),
        sa.Column("avatar_color", sa.String(7), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="RESTRICT"),
    )
    for column in ("name", "email", "is_active", "department_id"):
        op.create_index(f"ix_users_{column}", "users", [column], unique=column == "email")

    op.create_table(
        "requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("requesting_department_id", sa.Integer(), nullable=False),
        sa.Column("assigned_user_id", sa.Integer()),
        sa.Column("priority", priority_enum, nullable=False),
        sa.Column("status", status_enum, nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["category_id"], ["request_categories.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["requesting_department_id"], ["departments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["assigned_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    for column in ("title", "category_id", "requesting_department_id", "assigned_user_id", "priority", "status", "due_at", "created_at"):
        op.create_index(f"ix_requests_{column}", "requests", [column])
    op.create_index("ix_requests_status_priority", "requests", ["status", "priority"])

    op.create_table(
        "comments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["request_id"], ["requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="RESTRICT"),
    )
    for column in ("request_id", "author_id", "created_at"):
        op.create_index(f"ix_comments_{column}", "comments", [column])

    op.create_table(
        "request_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer()),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("field", sa.String(60)),
        sa.Column("old_value", sa.Text()),
        sa.Column("new_value", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["request_id"], ["requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
    )
    for column in ("request_id", "actor_id", "created_at"):
        op.create_index(f"ix_request_history_{column}", "request_history", [column])


def downgrade() -> None:
    op.drop_table("request_history")
    op.drop_table("comments")
    op.drop_table("requests")
    op.drop_table("users")
    op.drop_table("request_categories")
    op.drop_table("departments")
