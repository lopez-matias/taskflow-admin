from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Department, RequestCategory, User
from app.schemas import CategoryOut, DepartmentOut, UserOut

router = APIRouter(prefix="/catalogs", tags=["Catalogs"])


@router.get("/departments", response_model=list[DepartmentOut])
def departments(db: Session = Depends(get_db)):
    return db.scalars(select(Department).where(Department.is_active.is_(True)).order_by(Department.name)).all()


@router.get("/users", response_model=list[UserOut])
def users(db: Session = Depends(get_db)):
    return db.scalars(
        select(User).where(User.is_active.is_(True)).options(selectinload(User.department)).order_by(User.name)
    ).all()


@router.get("/categories", response_model=list[CategoryOut])
def categories(db: Session = Depends(get_db)):
    return db.scalars(
        select(RequestCategory).where(RequestCategory.is_active.is_(True)).order_by(RequestCategory.name)
    ).all()
