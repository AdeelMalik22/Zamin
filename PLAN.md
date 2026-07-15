# Project Plan

## Completed

- [x] Layered FastAPI package (`api`, `core`, `db`, `models`, `schemas`, `repositories`, `services`, `middleware`, `exceptions`)
- [x] JWT access/refresh authentication and role-based dependencies
- [x] Admin city and editor management
- [x] Editor listing capture, validation, and local image storage
- [x] Admin review queue with approve/reject audit history
- [x] Public approved-listing browse and contains/regex/fuzzy search
- [x] Initial Alembic migration, Docker scaffolding, and service-level tests
- [x] Idempotent development mock-data seed command

## Current development data

`python -m app.cli seed-mock-data` seeds the following on a fresh database:

| Entity | Records |
| --- | ---: |
| Admin | 1 |
| Cities | 20 |
| Editors | 10 |
| Editor-city assignments | 20 |
| Listings | 200 |
| Approved listings | 100 |
| Pending listings | 100 |
| Listing images | 20 |
| Listing status history | 300 |

Each editor owns 20 listings: 10 approved and 10 pending.

## Next milestones

1. Build the public web UI and internal admin/editor dashboards.
2. Add object-storage support (S3-compatible) behind the existing storage service.
3. Move production search to PostgreSQL + `pg_trgm` once SQLite fuzzy search is no longer sufficient.
4. Replace the in-process login guard with a Redis-backed shared rate limiter.
5. Add CI for migrations, unit tests, linting, and container build.
6. Add thumbnail generation and image-dimension validation.
