# Real Estate Listings Platform API

FastAPI + SQLite backend for editor-submitted real-estate listings, admin review, and public approved-listing search.

## Project layout

```text
app/
├── api/v1/endpoints/    # Thin HTTP handlers and versioned routers
├── core/                # Settings, security, logging, constants
├── db/                  # SQLAlchemy base, engine/session, migration reference
├── models/              # ORM entities
├── schemas/             # Request/response contracts
├── repositories/        # Database access only
├── services/            # Business workflows
├── middleware/          # Request logging and login-rate guard
├── exceptions/          # Domain exceptions and FastAPI handlers
└── main.py              # Application factory/assembly
alembic/                 # Migration environment and initial migration
tests/                   # Service-level automated tests
```

The root [`main.py`](main.py) is intentionally only a compatibility ASGI entrypoint. Application code belongs under `app/`.

## Local setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
cp .env.example .env
```

Set a strong `JWT_SECRET_KEY` and `ADMIN_PASSWORD` in `.env` (or export them in your shell), then initialize the schema and seed the single admin account:

```bash
.venv/bin/alembic upgrade head
.venv/bin/python -m app.cli seed-admin \
  --email admin@example.com \
  --password 'a-strong-admin-password' \
  --phone +923001234567
.venv/bin/uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for interactive documentation. API routes are versioned below `/api/v1` by default.

Import [`postman/Zamin.postman_collection.json`](postman/Zamin.postman_collection.json) into Postman for ready-made requests, token-saving login scripts, and admin/editor/public workflows. Paste local demo passwords from ignored `credentials.txt` into the collection variables after import.

For quick local development, `AUTO_CREATE_SCHEMA=true` creates a fresh schema at app startup. Use Alembic (`alembic upgrade head`) in deployed environments and set `AUTO_CREATE_SCHEMA=false`.

## Core workflow

1. Admin logs in at `POST /api/v1/auth/login` and creates supported cities.
2. Admin creates city-scoped editors at `POST /api/v1/admin/editors`; the initial password is returned only once.
3. Editors submit `POST /api/v1/editor/listings` and upload JPEG, PNG, or WEBP images. Admin can also use every editor-listing endpoint, with access to all listings; editors remain limited to their own.
4. Admin reviews pending listings at `GET /api/v1/admin/listings?status=pending` and approves or rejects them.
5. Visitors browse `GET /api/v1/listings` and `GET /api/v1/listings/{id}` anonymously.

Rejected-listing edits resubmit the same listing as pending. Every status transition is captured in `listing_status_history`.

## Search and contacts

`GET /api/v1/listings` supports exact `city`/`city_id` filtering and title/address search with `search_mode=contains`, `regex`, or `fuzzy`. Fuzzy matching is intentionally capped at 2,000 candidates for SQLite; PostgreSQL with `pg_trgm` is the recommended scale-up path.

The public contact number resolves as: listing override → submitting editor → admin.

## Validation and checks

```bash
.venv/bin/pytest
.venv/bin/ruff check app tests
```

The test suite covers admin authentication, editor provisioning, and the rejected → resubmitted → approved listing workflow.

## Realistic demo data

Seed generated—but realistic—Pakistani development data with:

```bash
.venv/bin/python seed.py
```

It creates real Pakistani city and area names such as Lahore/DHA/Gulberg, Karachi/DHA/Bahria Town, and Islamabad/Bahria Enclave; prices and descriptions are realistic but generated. On a fresh database it creates one admin, 20 cities, 10 editors, 200 listings (10 approved and 10 pending per editor), 20 editor-city assignments, 20 cover images, and 300 audit-history rows.

The script writes local credentials to `credentials.txt`, which is ignored by Git. Do not run it against production data.

## Docker

After creating `.env`, run:

```bash
docker compose up --build
```

The container runs Alembic before starting Uvicorn and persists the SQLite database and local image media in named volumes.
