from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import Priority, RequestStatus


class DepartmentOut(BaseModel):
    id: int
    name: str
    color: str
    model_config = ConfigDict(from_attributes=True)


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    avatar_color: str
    department_id: int
    department: DepartmentOut
    model_config = ConfigDict(from_attributes=True)


class CategoryOut(BaseModel):
    id: int
    name: str
    icon: str
    description: str | None
    model_config = ConfigDict(from_attributes=True)


class RequestCreate(BaseModel):
    title: str = Field(min_length=4, max_length=180)
    description: str = Field(min_length=10, max_length=5000)
    category_id: int = Field(gt=0)
    requesting_department_id: int = Field(gt=0)
    assigned_user_id: int | None = Field(default=None, gt=0)
    priority: Priority = Priority.MEDIUM
    due_at: datetime | None = None
    actor_id: int | None = Field(default=None, gt=0)

    @field_validator("title", "description")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        result = value.strip()
        if not result:
            raise ValueError("El contenido no puede estar vacío")
        return result


class RequestUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=4, max_length=180)
    description: str | None = Field(default=None, min_length=10, max_length=5000)
    category_id: int | None = Field(default=None, gt=0)
    requesting_department_id: int | None = Field(default=None, gt=0)
    assigned_user_id: int | None = Field(default=None, gt=0)
    priority: Priority | None = None
    status: RequestStatus | None = None
    due_at: datetime | None = None
    actor_id: int = Field(gt=0)

    @field_validator("title", "description")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def require_change(self):
        if not (self.model_fields_set - {"actor_id"}):
            raise ValueError("Debés enviar al menos un cambio")
        return self


class CommentCreate(BaseModel):
    author_id: int = Field(gt=0)
    body: str = Field(min_length=2, max_length=3000)

    @field_validator("body")
    @classmethod
    def clean_body(cls, value: str) -> str:
        return value.strip()


class CommentOut(BaseModel):
    id: int
    body: str
    created_at: datetime
    author: UserOut
    model_config = ConfigDict(from_attributes=True)


class HistoryOut(BaseModel):
    id: int
    request_id: int
    action: str
    field: str | None
    old_value: str | None
    new_value: str | None
    created_at: datetime
    actor: UserOut | None
    model_config = ConfigDict(from_attributes=True)


class RequestOut(BaseModel):
    id: int
    title: str
    description: str
    priority: Priority
    status: RequestStatus
    due_at: datetime | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    category: CategoryOut
    requesting_department: DepartmentOut
    assigned_user: UserOut | None
    comments_count: int = 0
    is_overdue: bool = False
    model_config = ConfigDict(from_attributes=True)


class RequestDetailOut(RequestOut):
    comments: list[CommentOut]
    history: list[HistoryOut]


class PaginatedRequests(BaseModel):
    items: list[RequestOut]
    total: int
    page: int
    page_size: int
    pages: int


class ChartItem(BaseModel):
    key: str
    label: str
    value: int
    color: str


class DepartmentChartItem(BaseModel):
    id: int
    name: str
    value: int
    color: str


class DashboardOut(BaseModel):
    open_requests: int
    overdue_requests: int
    resolved_this_month: int
    average_open_hours: float
    by_status: list[ChartItem]
    by_priority: list[ChartItem]
    by_department: list[DepartmentChartItem]
    recent_requests: list[RequestOut]
    recent_activity: list[HistoryOut]
