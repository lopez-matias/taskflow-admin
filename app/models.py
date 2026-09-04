from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Priority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RequestStatus(StrEnum):
    NEW = "new"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    RESOLVED = "resolved"
    CLOSED = "closed"


def enum_type(enum: type[StrEnum], name: str) -> SAEnum:
    return SAEnum(
        enum,
        name=name,
        values_callable=lambda entries: [entry.value for entry in entries],
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
    )


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    color: Mapped[str] = mapped_column(String(7), default="#ff9d00")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    users: Mapped[list[User]] = relationship(back_populates="department")
    requests: Mapped[list[Request]] = relationship(back_populates="requesting_department")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(80), default="Colaborador")
    avatar_color: Mapped[str] = mapped_column(String(7), default="#171717")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id", ondelete="RESTRICT"), index=True)

    department: Mapped[Department] = relationship(back_populates="users")
    assigned_requests: Mapped[list[Request]] = relationship(back_populates="assigned_user")
    comments: Mapped[list[Comment]] = relationship(back_populates="author")


class RequestCategory(Base):
    __tablename__ = "request_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    icon: Mapped[str] = mapped_column(String(30), default="folder")
    description: Mapped[str | None] = mapped_column(String(280))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    requests: Mapped[list[Request]] = relationship(back_populates="category")


class Request(Base):
    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(180), index=True)
    description: Mapped[str] = mapped_column(Text)
    category_id: Mapped[int] = mapped_column(ForeignKey("request_categories.id", ondelete="RESTRICT"), index=True)
    requesting_department_id: Mapped[int] = mapped_column(ForeignKey("departments.id", ondelete="RESTRICT"), index=True)
    assigned_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    priority: Mapped[Priority] = mapped_column(enum_type(Priority, "priority_enum"), default=Priority.MEDIUM, index=True)
    status: Mapped[RequestStatus] = mapped_column(enum_type(RequestStatus, "request_status_enum"), default=RequestStatus.NEW, index=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    category: Mapped[RequestCategory] = relationship(back_populates="requests")
    requesting_department: Mapped[Department] = relationship(back_populates="requests")
    assigned_user: Mapped[User | None] = relationship(back_populates="assigned_requests")
    comments: Mapped[list[Comment]] = relationship(back_populates="request", cascade="all, delete-orphan", order_by="Comment.created_at")
    history: Mapped[list[RequestHistory]] = relationship(back_populates="request", cascade="all, delete-orphan", order_by="RequestHistory.created_at")

    __table_args__ = (Index("ix_requests_status_priority", "status", "priority"),)


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    request: Mapped[Request] = relationship(back_populates="comments")
    author: Mapped[User] = relationship(back_populates="comments")


class RequestHistory(Base):
    __tablename__ = "request_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"), index=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action: Mapped[str] = mapped_column(String(50))
    field: Mapped[str | None] = mapped_column(String(60))
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    request: Mapped[Request] = relationship(back_populates="history")
    actor: Mapped[User | None] = relationship()
