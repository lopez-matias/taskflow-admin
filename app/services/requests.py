from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.errors import BusinessError
from app.models import Comment, Department, Request, RequestCategory, RequestHistory, RequestStatus, User
from app.schemas import CommentCreate, RequestCreate, RequestDetailOut, RequestOut, RequestUpdate

OPEN_STATUSES = {RequestStatus.NEW, RequestStatus.ASSIGNED, RequestStatus.IN_PROGRESS, RequestStatus.BLOCKED}
TRANSITIONS = {
    RequestStatus.NEW: {RequestStatus.ASSIGNED, RequestStatus.CLOSED},
    RequestStatus.ASSIGNED: {RequestStatus.NEW, RequestStatus.IN_PROGRESS, RequestStatus.BLOCKED, RequestStatus.RESOLVED},
    RequestStatus.IN_PROGRESS: {RequestStatus.ASSIGNED, RequestStatus.BLOCKED, RequestStatus.RESOLVED},
    RequestStatus.BLOCKED: {RequestStatus.ASSIGNED, RequestStatus.IN_PROGRESS, RequestStatus.RESOLVED},
    RequestStatus.RESOLVED: {RequestStatus.IN_PROGRESS, RequestStatus.CLOSED},
    RequestStatus.CLOSED: {RequestStatus.IN_PROGRESS},
}

REQUEST_LOADS = (
    selectinload(Request.category),
    selectinload(Request.requesting_department),
    selectinload(Request.assigned_user).selectinload(User.department),
    selectinload(Request.comments).selectinload(Comment.author).selectinload(User.department),
    selectinload(Request.history).selectinload(RequestHistory.actor).selectinload(User.department),
)


def utc_now() -> datetime:
    return datetime.now(UTC)


def as_aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def get_request_or_404(db: Session, request_id: int) -> Request:
    request = db.scalar(select(Request).where(Request.id == request_id).options(*REQUEST_LOADS))
    if request is None:
        raise BusinessError("La solicitud indicada no existe.", 404, "request_not_found")
    return request


def serialize_request(request: Request, *, detail: bool = False) -> RequestOut | RequestDetailOut:
    payload: dict[str, Any] = {
        "id": request.id,
        "title": request.title,
        "description": request.description,
        "priority": request.priority,
        "status": request.status,
        "due_at": request.due_at,
        "created_at": request.created_at,
        "updated_at": request.updated_at,
        "resolved_at": request.resolved_at,
        "category": request.category,
        "requesting_department": request.requesting_department,
        "assigned_user": request.assigned_user,
        "comments_count": len(request.comments),
        "is_overdue": bool(
            request.due_at
            and as_aware(request.due_at) < utc_now()
            and request.status in OPEN_STATUSES
        ),
    }
    if detail:
        payload["comments"] = request.comments
        payload["history"] = list(reversed(request.history))
        return RequestDetailOut.model_validate(payload)
    return RequestOut.model_validate(payload)


def ensure_reference(db: Session, model: type, value: int | None, label: str) -> None:
    if value is None:
        return
    entity = db.get(model, value)
    if entity is None or not getattr(entity, "is_active", True):
        raise BusinessError(f"{label} no existe o no está disponible.", 422, "invalid_reference")


def ensure_references(
    db: Session,
    *,
    category_id: int | None = None,
    department_id: int | None = None,
    user_id: int | None = None,
    actor_id: int | None = None,
) -> None:
    ensure_reference(db, RequestCategory, category_id, "La categoría seleccionada")
    ensure_reference(db, Department, department_id, "El departamento seleccionado")
    ensure_reference(db, User, user_id, "El responsable seleccionado")
    ensure_reference(db, User, actor_id, "El usuario que realiza la acción")


def printable(value: Any) -> str | None:
    if value is None:
        return None
    return value.value if hasattr(value, "value") else str(value)


def add_history(
    db: Session,
    request_id: int,
    actor_id: int | None,
    action: str,
    field: str | None = None,
    old_value: Any = None,
    new_value: Any = None,
) -> None:
    db.add(RequestHistory(
        request_id=request_id,
        actor_id=actor_id,
        action=action,
        field=field,
        old_value=printable(old_value),
        new_value=printable(new_value),
    ))


def create_request(db: Session, data: RequestCreate) -> Request:
    ensure_references(
        db,
        category_id=data.category_id,
        department_id=data.requesting_department_id,
        user_id=data.assigned_user_id,
        actor_id=data.actor_id,
    )
    values = data.model_dump(exclude={"actor_id"})
    values["status"] = RequestStatus.ASSIGNED if data.assigned_user_id else RequestStatus.NEW
    request = Request(**values)
    db.add(request)
    db.flush()
    add_history(db, request.id, data.actor_id, "created", new_value="Solicitud creada")
    if request.assigned_user_id:
        add_history(db, request.id, data.actor_id, "assigned", "assigned_user_id", None, request.assigned_user_id)
    db.commit()
    db.expire_all()
    return get_request_or_404(db, request.id)


def update_request(db: Session, request: Request, data: RequestUpdate) -> Request:
    changes = data.model_dump(exclude_unset=True, exclude={"actor_id"})
    ensure_references(
        db,
        category_id=changes.get("category_id"),
        department_id=changes.get("requesting_department_id"),
        user_id=changes.get("assigned_user_id"),
        actor_id=data.actor_id,
    )

    new_status = changes.get("status")
    if new_status is not None and new_status != request.status:
        if new_status not in TRANSITIONS[request.status]:
            raise BusinessError(
                f"No se admite el cambio de {request.status.value} a {new_status.value}.",
                409,
                "invalid_status_transition",
            )
        future_assignee = changes.get("assigned_user_id", request.assigned_user_id)
        if new_status in {RequestStatus.ASSIGNED, RequestStatus.IN_PROGRESS} and not future_assignee:
            raise BusinessError("La solicitud necesita un responsable para avanzar.", 409, "assignee_required")

    if "assigned_user_id" in changes and changes["assigned_user_id"] and request.status == RequestStatus.NEW and "status" not in changes:
        changes["status"] = RequestStatus.ASSIGNED
    if "assigned_user_id" in changes and changes["assigned_user_id"] is None and "status" not in changes:
        if request.status == RequestStatus.ASSIGNED:
            changes["status"] = RequestStatus.NEW
        elif request.status in {RequestStatus.IN_PROGRESS, RequestStatus.BLOCKED}:
            raise BusinessError("No podés quitar el responsable de una solicitud en trabajo.", 409, "assignee_required")

    changed = False
    for field, new_value in changes.items():
        old_value = getattr(request, field)
        if old_value == new_value:
            continue
        changed = True
        setattr(request, field, new_value)
        action = {
            "assigned_user_id": "assigned",
            "priority": "priority_changed",
            "status": "status_changed",
        }.get(field, "updated")
        add_history(db, request.id, data.actor_id, action, field, old_value, new_value)
        if field == "status":
            if new_value in {RequestStatus.RESOLVED, RequestStatus.CLOSED}:
                request.resolved_at = request.resolved_at or utc_now()
            elif old_value in {RequestStatus.RESOLVED, RequestStatus.CLOSED}:
                request.resolved_at = None

    if not changed:
        raise BusinessError("Los valores enviados no generan ningún cambio.", 409, "no_changes")
    db.commit()
    db.expire_all()
    return get_request_or_404(db, request.id)


def create_comment(db: Session, request: Request, data: CommentCreate) -> Comment:
    ensure_reference(db, User, data.author_id, "El autor")
    comment = Comment(request_id=request.id, author_id=data.author_id, body=data.body)
    db.add(comment)
    db.flush()
    add_history(db, request.id, data.author_id, "commented", new_value="Comentario agregado")
    comment_id = comment.id
    db.commit()
    return db.scalar(
        select(Comment)
        .where(Comment.id == comment_id)
        .options(selectinload(Comment.author).selectinload(User.department))
    )
