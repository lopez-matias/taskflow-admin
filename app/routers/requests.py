from datetime import UTC, datetime
from math import ceil

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Priority, Request, RequestStatus
from app.schemas import (
    CommentCreate,
    CommentOut,
    PaginatedRequests,
    RequestCreate,
    RequestDetailOut,
    RequestOut,
    RequestUpdate,
)
from app.services.requests import (
    OPEN_STATUSES,
    REQUEST_LOADS,
    create_comment,
    create_request,
    get_request_or_404,
    serialize_request,
    update_request,
)

router = APIRouter(prefix="/requests", tags=["Requests"])


@router.get("", response_model=PaginatedRequests)
def list_requests(
    search: str | None = Query(default=None, max_length=120),
    department_id: int | None = Query(default=None, gt=0),
    statuses: list[RequestStatus] | None = Query(default=None, alias="status"),
    priorities: list[Priority] | None = Query(default=None, alias="priority"),
    user_id: int | None = Query(default=None, gt=0),
    overdue: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = select(Request)
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        query = query.where(or_(Request.title.ilike(pattern), Request.description.ilike(pattern)))
    if department_id:
        query = query.where(Request.requesting_department_id == department_id)
    if statuses:
        query = query.where(Request.status.in_(statuses))
    if priorities:
        query = query.where(Request.priority.in_(priorities))
    if user_id:
        query = query.where(Request.assigned_user_id == user_id)
    if overdue is not None:
        is_overdue = Request.due_at < datetime.now(UTC)
        is_overdue = is_overdue & Request.status.in_(OPEN_STATUSES)
        query = query.where(is_overdue if overdue else or_(Request.due_at.is_(None), ~is_overdue))

    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    items = db.scalars(
        query.options(*REQUEST_LOADS)
        .order_by(Request.created_at.desc(), Request.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return PaginatedRequests(
        items=[serialize_request(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, ceil(total / page_size)),
    )


@router.post("", response_model=RequestOut, status_code=status.HTTP_201_CREATED)
def add_request(data: RequestCreate, db: Session = Depends(get_db)):
    return serialize_request(create_request(db, data))


@router.get("/{request_id}", response_model=RequestDetailOut)
def request_detail(request_id: int, db: Session = Depends(get_db)):
    return serialize_request(get_request_or_404(db, request_id), detail=True)


@router.patch("/{request_id}", response_model=RequestDetailOut)
def edit_request(request_id: int, data: RequestUpdate, db: Session = Depends(get_db)):
    request = get_request_or_404(db, request_id)
    return serialize_request(update_request(db, request, data), detail=True)


@router.post("/{request_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
def add_comment(request_id: int, data: CommentCreate, db: Session = Depends(get_db)):
    return create_comment(db, get_request_or_404(db, request_id), data)
