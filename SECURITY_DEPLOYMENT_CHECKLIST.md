# CareerMate security deployment checklist

This branch hardens the existing SQLite application. PostgreSQL migration from PR #1/#2 is NOT included yet.

## Required before production
- Set SECRET_KEY to a stable, cryptographically random value (at least 32 bytes of entropy). A random fallback is intended for local development only; without a stable key, sessions reset on restart.
- Set ADMIN_PASSWORD to a unique strong password before the first initialization. Existing admin credentials are not automatically rotated; change them separately.
- Set FLASK_ENV=production and leave FLASK_DEBUG unset.
- Leave ENABLE_DEMO_DATA unset in production.
- Set student passwords explicitly when provisioning accounts. If omitted, the server creates an unknown random password, so the account cannot be used until an administrator sets a new one.
- Back up the SQLite database before migrations.
- Configure CSRF protection, login rate limiting, authorization review, and password rotation before admitting real students.
- Verify the Render environment and Supabase project independently; no live database changes were made by this branch.

## Review warning
This is a first-pass hardening change, not a production security certification. Run the existing login, CSV import, account creation, team matching, and reset-password tests before merging.
