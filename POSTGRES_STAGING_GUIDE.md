# PostgreSQL integration (staging only)

This branch builds on PR #3 and uses a single token-aware adapter (`database.py`) from PR #1, with adjustments for PostgreSQL integrity errors and SQLite's double-quoted `"ACTIVE"` literal. PR #2's regex-based adapter is not included.

## Existing Supabase project
- Project: `careermate-school` (`vywwyjyhtsetohnjflqr`)
- Schema: `careermate`
- Verified read-only query on 2026-11-02: `careermate.users` and `careermate.teams` each contain zero rows.
- No data was inserted, deleted, or migrated.

## Local verification
Run `python -m unittest discover -s tests -v` after `pip install -r requirements.txt`.
Unit tests cover SQL token conversion and SQLite API workflows; they do **not** establish successful remote psycopg connectivity.

## Safe staging configuration
Set `DATABASE_URL` to a PostgreSQL connection URL **only in a controlled staging environment**. Use a TLS-enabled Supabase connection string from the Connect panel; never commit it. Set `SECRET_KEY` to a stable secret, `FLASK_ENV=production`, and `ADMIN_PASSWORD` to a unique password at least 12 characters long. Leave `ENABLE_DEMO_DATA` unset.

The existing application calls `init_db()` only when run as `python app.py`; WSGI deployments need an explicit, reviewed initialization procedure. Never switch the existing Render production service to PostgreSQL until backups, migration and full end-to-end testing are complete.

## Outstanding blockers
- Test a genuine PostgreSQL connection in an isolated environment, including CRUD, uniqueness, FK behavior, CSV partial failures, team invitation and acceptance, and role permissions.
- Review adapter SQL compatibility across all routes and transactions. SQL translation tests are not a substitute for database integration tests.
- Confirm that existing SQLite production data is backed up and whether any data migration is necessary.
- Implement CSRF protection and login rate limiting before production release.
