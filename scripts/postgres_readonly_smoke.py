"""Read-only smoke check for a configured PostgreSQL database.

Run manually with DATABASE_URL in a secure environment. This script never
creates tables or writes rows; it must not call app.init_db().
"""
import os
import sys

TABLES = ("users", "activities", "teams", "teamMembers",
          "recruitmentPosts", "joinRequests", "notifications")


def main():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is missing; no connection attempted")
    if not url.startswith(("postgresql://", "postgres://")):
        raise SystemExit("Expected PostgreSQL DATABASE_URL")

    import psycopg
    from psycopg.rows import dict_row
    with psycopg.connect(url, row_factory=dict_row, connect_timeout=10,
                         options="-c default_transaction_read_only=on") as con:
        with con.cursor() as cur:
            cur.execute("SELECT current_database() AS name, current_setting('transaction_read_only') AS readonly")
            info = cur.fetchone()
            assert info["readonly"] == "on"
            for table in TABLES:
                cur.execute("SELECT to_regclass(%s) AS relation", (f'careermate."{table}"',))
                if cur.fetchone()["relation"] is None:
                    raise RuntimeError(f"Missing expected table: {table}")
            cur.execute("SELECT count(*) AS count FROM careermate.users")
            users = cur.fetchone()["count"]
            cur.execute("SELECT count(*) AS count FROM careermate.teams")
            teams = cur.fetchone()["count"]
    print(f"Read-only PostgreSQL smoke check passed; users={users}, teams={teams}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Avoid printing connection errors that may embed credentials.
        raise SystemExit(f"Smoke check failed ({type(exc).__name__}); verify database settings") from None
