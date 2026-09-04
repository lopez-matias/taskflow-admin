from datetime import UTC, datetime, timedelta

from tests.conftest import create_request


def test_create_request_and_initial_history(client):
    request, _ = create_request(client)
    assert request["status"] == "new"
    assert request["assigned_user"] is None
    detail = client.get(f"/api/requests/{request['id']}")
    assert detail.status_code == 200
    assert detail.json()["history"][0]["action"] == "created"


def test_assignment_status_priority_and_resolution_are_audited(client):
    request, catalog = create_request(client)
    assigned = client.patch(
        f"/api/requests/{request['id']}",
        json={"assigned_user_id": catalog["assignee"], "actor_id": catalog["actor"]},
    )
    assert assigned.status_code == 200
    assert assigned.json()["status"] == "assigned"

    working = client.patch(
        f"/api/requests/{request['id']}",
        json={"status": "in_progress", "priority": "critical", "actor_id": catalog["actor"]},
    )
    assert working.status_code == 200
    resolved = client.patch(
        f"/api/requests/{request['id']}",
        json={"status": "resolved", "actor_id": catalog["actor"]},
    )
    payload = resolved.json()
    assert payload["resolved_at"] is not None
    assert {entry["action"] for entry in payload["history"]} >= {"assigned", "status_changed", "priority_changed", "created"}


def test_comment_updates_count_and_history(client):
    request, catalog = create_request(client)
    response = client.post(
        f"/api/requests/{request['id']}/comments",
        json={"author_id": catalog["actor"], "body": "Estoy revisando el caso con el equipo."},
    )
    assert response.status_code == 201
    detail = client.get(f"/api/requests/{request['id']}").json()
    assert detail["comments_count"] == 1
    assert detail["comments"][0]["author"]["name"] == "Ana Admin"
    assert detail["history"][0]["action"] == "commented"


def test_invalid_references_transitions_and_payloads(client):
    request, catalog = create_request(client)
    transition = client.patch(
        f"/api/requests/{request['id']}",
        json={"status": "resolved", "actor_id": catalog["actor"]},
    )
    assert transition.status_code == 409
    assert transition.json()["code"] == "invalid_status_transition"

    invalid_relation = client.post("/api/requests", json={
        "title": "Solicitud inválida",
        "description": "Descripción válida pero referencia inexistente.",
        "category_id": 9999,
        "requesting_department_id": catalog["department"],
    })
    assert invalid_relation.status_code == 422
    assert invalid_relation.json()["code"] == "invalid_reference"

    validation = client.post("/api/requests", json={"title": "x", "description": "corta"})
    assert validation.status_code == 422


def test_search_filters_overdue_and_pagination(client):
    yesterday = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    first, catalog = create_request(client, title="Compra de notebook", priority="critical", assigned_user_id=2, due_at=yesterday)
    create_request(client, title="Revisión de permisos", priority="low")
    response = client.get("/api/requests", params={
        "search": "notebook", "priority": "critical", "department_id": catalog["department"],
        "user_id": catalog["assignee"], "overdue": "true",
    })
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == first["id"]
    assert response.json()["items"][0]["is_overdue"] is True


def test_dashboard_page_health_and_openapi(client):
    create_request(client)
    create_request(client, title="Segunda solicitud interna")
    dashboard = client.get("/api/dashboard")
    assert dashboard.status_code == 200
    data = dashboard.json()
    assert data["open_requests"] == 2
    assert sum(item["value"] for item in data["by_status"]) == 2
    assert len(data["by_department"]) == 2
    assert client.get("/").status_code == 200
    assert "OrangeFlow" in client.get("/").text
    assert client.get("/api/health").json() == {"status": "ok", "environment": "test"}
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/requests" in paths
    assert "/api/dashboard" in paths
