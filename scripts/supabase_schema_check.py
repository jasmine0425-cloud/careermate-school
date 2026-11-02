"""Compare an existing PostgreSQL schema without modifying any records or DDL.

Usage: DATABASE_URL=<private PostgreSQL URL> python scripts/supabase_schema_check.py
Do not commit DATABASE_URL or paste it in an issue.
"""
import os
import sys

EXPECTED = {
    "users": {"id", "loginId", "passwordHash", "role", "name", "studentNumber", "grade", "classNumber", "number", "careerCategory", "desiredMajor", "desiredJob", "interests", "keywords", "preferredRoles", "accountStatus", "createdAt"},
    "activities": {"id", "title", "description", "startDate", "endDate", "minMembers", "maxMembers", "recommendedFields", "recruitmentDeadline", "createdAt"},
    "teams": {"id", "activityId", "teamName", "topic", "description", "leaderId", "maxMembers", "status", "createdAt"},
    "teamMembers": {"id", "teamId", "userId", "role", "status", "createdAt"},
    "recruitmentPosts": {"id", "teamId", "requiredFields", "requiredRoles", "recruitCount", "keywords", "description", "deadline", "status", "createdAt"},
    "joinRequests": {"id", "teamId", "userId", "requestType", "status", "message", "createdAt"},
    "notifications": {"id", "userId", "type", "title", "message", "relatedTeamId", "isRead", "createdAt"},
}

def main():
    url = os.environ.get("DATABASE_URL")
    if not url or not url.startswith(("postgres://", "postgresql://")):
        raise RuntimeError("A PostgreSQL DATABASE_URL is required")
    import psycopg
    with psycopg.connect(url, connect_timeout=10, sslmode="require",
                         options="-c default_transaction_read_only=on") as con:
        with con.cursor() as cur:
            cur.execute("SELECT table_name, column_name FROM information_schema.columns WHERE table_schema = %s", ("careermate",))
            actual = {}
            for table, column in cur.fetchall():
                actual.setdefault(table, set()).add(column)
            errors = []
            for table, required in EXPECTED.items():
                missing = required - actual.get(table, set())
                if missing:
                    errors.append(f"{table}: missing {', '.join(sorted(missing))}")
            cur.execute("SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = %s", ("careermate",))
            rls = dict(cur.fetchall())
            for table in EXPECTED:
                if not rls.get(table):
                    errors.append(f"{table}: row-level security is disabled")
            if errors:
                raise RuntimeError("; ".join(errors))
    print(f"PASS: {len(EXPECTED)} tables, expected columns, RLS enabled (read-only)")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Schema check failed ({type(exc).__name__}); check schema/permissions privately", file=sys.stderr)
        sys.exit(1)
