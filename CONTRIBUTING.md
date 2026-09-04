# Contributing

Thank you for considering a contribution to OrangeFlow.

## Before starting

For substantial changes, open an issue first and describe the business problem, proposed behavior, and expected API or interface impact. Small fixes may be submitted directly.

Please keep pull requests focused. Unrelated refactors should be proposed separately.

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
docker compose up -d database
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

Alternatively, use `./scripts/start.sh` when local PostgreSQL binaries are available but Docker is not.

## Quality checks

Run these commands before opening a pull request:

```bash
ruff check .
pytest
```

New business rules and bug fixes should include tests. Do not reduce validation or audit coverage to make a change pass.

## Coding guidelines

- Use English for code, commit messages, and documentation.
- Keep the product interface and end-user error messages in Spanish.
- Keep business rules out of routers and browser code.
- Use SQLAlchemy 2.x query patterns.
- Add schema changes through Alembic migrations.
- Never commit credentials, local databases, or generated runtime files.
- Preserve accessibility and mobile behavior when changing the interface.

## Commit and pull request guidance

Use short, imperative commit subjects, for example:

```text
Add department workload filter
Fix resolved timestamp when reopening requests
```

Pull requests should explain what changed, why it changed, how it was tested, and include screenshots for visible interface changes.
