# Render + Supabase deployment readiness (no production changes)

## Verified (2026-11-02)
- Render service `careermate-school` (Singapore) deploys `main` automatically and starts `gunicorn app:app --bind 0.0.0.0:$PORT`.
- `main` still uses SQLite and has older default credential/demo bootstrap behavior.
- Supabase `careermate` has seven expected tables, with PostgreSQL identity IDs and RLS enabled. A read-only query found no accounts.
- GitHub's disposable PostgreSQL CI is distinct from a live Flask-to-Supabase credential connection.

## Release blockers
1. Do not set `DATABASE_URL` on the current `main` deployment: it will not switch the SQLite-only code.
2. Review and land security and database PRs in dependency order, **after** confirming CI, preserving the existing service's data, and taking an SQLite backup. PR #5 targets PR #4; PR #4 targets the security branch, not `main`.
3. The current Render start command imports `app:app` and **does not call `init_db()`**. Existing Supabase tables are already present, but administrator bootstrap requires a separate explicit process. Do not change the start command to invoke database initialization automatically without a reviewed migration/bootstrap plan.
4. In a staging Render service (not the existing production service), configure `FLASK_ENV=production`, stable strong `SECRET_KEY`, private TLS-enabled `DATABASE_URL`, and unique `ADMIN_PASSWORD` (at least 12 chars). Keep `ENABLE_DEMO_DATA=0`. Store credentials only in Render private environment settings.
5. Confirm Supabase connection privileges and direct connection vs pooler requirements, and test schema checker `scripts/supabase_schema_check.py` against the staging credentials. The existing Supabase project has not been tested with app credentials.
6. Test login, student management, teams, role permissions, CSRF, rate limits, restart persistence, and rollback before switching traffic. Do not publicly expose known demo passwords.

## Accounts
- Supabase `careermate.users` currently contains no records. No real student credentials can be supplied.
- Sample student login IDs in source are `kimsky`, `parksy`, `leejh`, `choimj`, and `jungde`; they are **not** active Supabase accounts and only seed when `ENABLE_DEMO_DATA=1`.
- Do not create sample accounts in production or reuse source-code default passwords.
