# API reference

The interactive OpenAPI documentation is available at `/docs` while the application is running. ReDoc is available at `/redoc`.

## Conventions

- Base path: `/api`
- Media type: `application/json`
- Dates: ISO 8601
- Pagination starts at page `1`
- Validation failures return `422 Unprocessable Entity`
- Business-rule conflicts return `409 Conflict`

Domain errors use a stable shape:

```json
{
  "detail": "Human-readable explanation",
  "code": "stable_error_code"
}
```

## Health

### `GET /api/health`

Returns the service state and configured environment.

```json
{
  "status": "ok",
  "environment": "development"
}
```

## Dashboard

### `GET /api/dashboard`

Returns headline metrics, grouped status and priority data, department workload, recent requests, and recent history entries.

## Requests

### `GET /api/requests`

Available query parameters:

| Parameter | Type | Description |
|---|---|---|
| `search` | string | Case-insensitive title and description search |
| `department_id` | integer | Requesting department |
| `status` | repeated enum | One or more request statuses |
| `priority` | repeated enum | One or more priorities |
| `user_id` | integer | Assigned user |
| `overdue` | boolean | Include overdue or non-overdue requests |
| `page` | integer | Page number, minimum `1` |
| `page_size` | integer | Items per page, between `1` and `100` |

Example:

```bash
curl "http://localhost:8000/api/requests?status=in_progress&priority=high&overdue=true"
```

### `POST /api/requests`

Creates a request and its initial history record.

```json
{
  "title": "Provision analytics access",
  "description": "Grant read access before the monthly reporting cycle begins.",
  "category_id": 1,
  "requesting_department_id": 5,
  "assigned_user_id": 2,
  "priority": "high",
  "due_at": "2026-09-10T18:00:00Z",
  "actor_id": 1
}
```

`actor_id` is optional during creation because requests may originate from an integration. When supplied, it must identify an active user.

### `GET /api/requests/{request_id}`

Returns request details, comments, and reverse-chronological history.

### `PATCH /api/requests/{request_id}`

Updates one or more fields. `actor_id` is required so the change can be audited.

```bash
curl -X PATCH "http://localhost:8000/api/requests/1" \
  -H "Content-Type: application/json" \
  -d '{"status":"in_progress","priority":"critical","actor_id":1}'
```

Supported fields are `title`, `description`, `category_id`, `requesting_department_id`, `assigned_user_id`, `priority`, `status`, and `due_at`.

### `POST /api/requests/{request_id}/comments`

Adds a comment and a corresponding history entry.

```json
{
  "author_id": 1,
  "body": "The access request is being reviewed by the platform team."
}
```

## Catalogs

- `GET /api/catalogs/departments`
- `GET /api/catalogs/users`
- `GET /api/catalogs/categories`

Catalog endpoints return active records ordered by name.

## Enumerations

Priorities:

```text
low | medium | high | critical
```

Statuses:

```text
new | assigned | in_progress | blocked | resolved | closed
```

## Authentication notice

The portfolio version does not implement authentication or authorization. Do not expose it to untrusted networks or use it with sensitive data without adding an identity and permission layer.
