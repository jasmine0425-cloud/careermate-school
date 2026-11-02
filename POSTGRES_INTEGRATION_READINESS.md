# PostgreSQL integration readiness — 2026-11-02

## Verified status
- PR #3 GitHub Actions run #2 (41423610342) completed successfully. This validates the current regression suite, not PostgreSQL.
- Supabase project `careermate-school` (ref `vywwyjyhtsetohnjflqr`) is currently INACTIVE. Read-only table inspection failed because the database is inaccessible.
- The production/main branch still uses SQLite. Do not change Render's DATABASE_URL or merge PostgreSQL code before an isolated migration test.

## Compare existing proposals
- PR #1: `database.py`, `migrate_sqlite.py`, `tests/test_workflow.py`, WSGI and setup changes.
- PR #2: `postgres_adapter.py`, `SUPABASE_SETUP.md`, environment checks.
- Both implement overlapping SQLite-style PostgreSQL adapters; choose one, not both.
- Review token conversion around SQL string literals, double-quoted SQLite string constants, mixed-case identifiers, INSERT RETURNING, savepoints, schema search_path, and connection TLS.
- Review transaction behavior and error handling for CSV imports, invite acceptance, team capacity, and duplicate membership.

## Safe execution sequence
1. Restore Supabase project access and verify schema, tables, roles, and backup availability (read-only).
2. Back up the existing SQLite DB. Confirm whether Render data is persistent and identify authoritative records.
3. Create a separate integration branch based on the latest reviewed security changes. Bring in ONE adapter and migration script, with tests.
4. Run local SQLite regression tests plus PostgreSQL integration tests on an isolated database; include migration row counts and foreign keys.
5. Review data-access boundaries. Prefer a private PostgreSQL schema not exposed to Supabase Data API; do not expose student data via anon grants.
6. Set a stable production SECRET_KEY and strong ADMIN_PASSWORD; use TLS for DB connections. Never commit credentials.
7. After passing checks, stage deployment with rollback procedure; merge and deploy only after reviewing results.

## Outstanding application security work
- CSRF protection for cookie-authenticated state-changing routes.
- Login rate limiting, account lifecycle and password rotation.
- Existing demo accounts/credentials on deployed databases require an explicit audit.
- Student data minimization and access authorization review.
