from collections import Counter
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.database import get_db
from app.models import Department, Priority, Request, RequestHistory, RequestStatus, User
from app.schemas import ChartItem, DashboardOut, DepartmentChartItem, HistoryOut
from app.services.requests import OPEN_STATUSES, REQUEST_LOADS, as_aware, serialize_request

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

STATUS_LABELS = {
    RequestStatus.NEW: ("Nuevas", "#cbd5e1"),
    RequestStatus.ASSIGNED: ("Asignadas", "#93c5fd"),
    RequestStatus.IN_PROGRESS: ("En progreso", "#2563eb"),
    RequestStatus.BLOCKED: ("Bloqueadas", "#64748b"),
    RequestStatus.RESOLVED: ("Resueltas", "#0f766e"),
    RequestStatus.CLOSED: ("Cerradas", "#334155"),
}
PRIORITY_LABELS = {
    Priority.LOW: ("Baja", "#dbeafe"),
    Priority.MEDIUM: ("Media", "#93c5fd"),
    Priority.HIGH: ("Alta", "#2563eb"),
    Priority.CRITICAL: ("Crítica", "#1e3a8a"),
}


@router.get("", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db)):
    now = datetime.now(UTC)
    requests = db.scalars(select(Request).options(*REQUEST_LOADS).order_by(Request.created_at.desc())).all()
    departments = db.scalars(select(Department).where(Department.is_active.is_(True)).order_by(Department.name)).all()
    open_requests = [item for item in requests if item.status in OPEN_STATUSES]
    overdue = [item for item in open_requests if item.due_at and as_aware(item.due_at) < now]
    resolved_month = [
        item for item in requests
        if item.resolved_at
        and as_aware(item.resolved_at).year == now.year
        and as_aware(item.resolved_at).month == now.month
    ]
    average_hours = (
        sum((now - as_aware(item.created_at)).total_seconds() / 3600 for item in open_requests) / len(open_requests)
        if open_requests else 0
    )
    status_counts = Counter(item.status for item in requests)
    priority_counts = Counter(item.priority for item in open_requests)
    department_counts = Counter(item.requesting_department_id for item in open_requests)
    activity = db.scalars(
        select(RequestHistory)
        .options(selectinload(RequestHistory.actor).selectinload(User.department))
        .order_by(RequestHistory.created_at.desc(), RequestHistory.id.desc())
        .limit(get_settings().activity_limit)
    ).all()

    return DashboardOut(
        open_requests=len(open_requests),
        overdue_requests=len(overdue),
        resolved_this_month=len(resolved_month),
        average_open_hours=round(average_hours, 1),
        by_status=[ChartItem(key=key.value, label=label, value=status_counts[key], color=color) for key, (label, color) in STATUS_LABELS.items()],
        by_priority=[ChartItem(key=key.value, label=label, value=priority_counts[key], color=color) for key, (label, color) in PRIORITY_LABELS.items()],
        by_department=[DepartmentChartItem(id=item.id, name=item.name, value=department_counts[item.id], color=item.color) for item in departments],
        recent_requests=[serialize_request(item) for item in requests[:6]],
        recent_activity=[HistoryOut.model_validate(item) for item in activity],
    )
