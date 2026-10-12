# CareerMate — Supabase PostgreSQL deployment

This feature branch is a **draft**, not yet tested against the live Supabase
instance. It does not migrate any data from the original SQLite file.

## Render Environment Variables

- `DATABASE_URL`: Supabase's Session pooler connection URI, including a
  URL-encoded database password. Do not put it in GitHub or screenshots.
- `SECRET_KEY`: a long random Flask session signing key (different from the
  database password).
- `ADMIN_PASSWORD`: a unique, long administrator password for the initial
  administrator account.

The PostgreSQL version refuses to start unless all three are present.
On first startup, it creates empty tables and one administrator account.
It does not create demo students with known passwords.

## Testing before merging

1. Add `SECRET_KEY` and `ADMIN_PASSWORD` as private Render environment
   variables. Do not share their values.
2. Test the draft branch on an isolated preview/staging service or temporary
   PostgreSQL database before merging into `main`.
3. Verify server startup, admin login, adding a test student, creating an
   activity, team invitation, team signup, and page refresh persistence.
4. Existing SQLite data is **not automatically transferred**; back up and
   migrate separately if it must be retained.
5. Do not enter real students' personal information until credentials have
   been rotated and access controls/security have been reviewed.

## Notes

This is a compatibility adapter for the existing SQLite-flavored SQL.
A future refactor should use SQLAlchemy or explicit PostgreSQL statements,
a migration system, pooled connections and production WSGI configuration.
