import os

os.environ["ORANGEFLOW_DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["ORANGEFLOW_ENVIRONMENT"] = "test"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Department, RequestCategory, User


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    with TestingSession() as db:
        technology = Department(name="Tecnología", color="#ff9d00")
        finance = Department(name="Finanzas", color="#111111")
        db.add_all([technology, finance])
        db.flush()
        db.add_all([
            User(name="Ana Admin", email="ana@example.test", role="Administradora", department=technology, avatar_color="#ff9d00"),
            User(name="Bruno IT", email="bruno@example.test", role="Soporte", department=technology, avatar_color="#111111"),
        ])
        db.add_all([
            RequestCategory(name="Sistemas", icon="key", description="Accesos y soporte"),
            RequestCategory(name="Compras", icon="bag", description="Adquisiciones"),
        ])
        db.commit()

    def override_db():
        with TestingSession() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def ids(client: TestClient) -> dict[str, int]:
    departments = client.get("/api/catalogs/departments").json()
    users = client.get("/api/catalogs/users").json()
    categories = client.get("/api/catalogs/categories").json()
    return {
        "department": departments[0]["id"],
        "other_department": departments[1]["id"],
        "actor": users[0]["id"],
        "assignee": users[1]["id"],
        "category": categories[0]["id"],
    }


def create_request(client: TestClient, **changes):
    catalog = ids(client)
    body = {
        "title": "Acceso al sistema financiero",
        "description": "Necesitamos habilitar el acceso antes del cierre mensual.",
        "category_id": catalog["category"],
        "requesting_department_id": catalog["department"],
        "priority": "high",
        "actor_id": catalog["actor"],
    }
    body.update(changes)
    response = client.post("/api/requests", json=body)
    assert response.status_code == 201, response.text
    return response.json(), catalog
