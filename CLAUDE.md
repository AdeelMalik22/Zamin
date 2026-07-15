# CLAUDE.md

## Project purpose

This repository is a FastAPI real-estate listings platform. Editors submit city-scoped listings, an admin reviews them, and public visitors see only approved listings.

## Architecture rules

- Keep `app/main.py` limited to application assembly: lifespan, middleware, routers, and static mounts.
- Add HTTP handlers only in `app/api/v1/endpoints/`; handlers validate input, authorize the caller, call a service, and return a schema.
- Keep business rules in `app/services/` and SQLAlchemy query code in `app/repositories/`.
- Put ORM changes in `app/models/` and matching request/response contracts in `app/schemas/`.
- Do not place business logic, database queries, or models back into the root `main.py`.
- Add a new Alembic migration for every persistent model change. Do not edit an applied migration.

## Commands

```bash
# Install development dependencies
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt

# Create/update schema and run the app
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload

# Create a real bootstrap admin
.venv/bin/python -m app.cli seed-admin --email admin@example.com --password 'strong-password' --phone +923001234567

# Seed deterministic local demo data
.venv/bin/python -m app.cli seed-mock-data

# Quality checks
.venv/bin/pytest
.venv/bin/ruff check app tests
```

## API conventions

- Public API routes are versioned under `/api/v1`.
- Use dependency guards from `app/api/dependencies.py` for admin/editor access.
- Use the domain exceptions in `app/exceptions/`, not ad hoc HTTP exceptions inside services.
- Keep response models explicit. Do not expose password hashes, raw ORM objects, or internal-only fields to public routes.
- Listing changes must preserve status history. Rejected editor changes resubmit the listing as pending.

## Mock data

`seed-mock-data` is idempotent and creates a development dataset with one admin, twenty cities, ten editors, 200 listings (100 approved and 100 pending), twenty cover images, twenty editor-city assignments, and audit history. It uses predictable `@mock.local` editor emails and should never be run against a production database.
