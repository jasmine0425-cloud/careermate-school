"""Copy a read-only SQLite backup into an empty CareerMate PostgreSQL schema."""
import os
import sqlite3
import sys
from pathlib import Path

from psycopg import sql
from app import SCHEMA
from database import connect_database

TABLES = ('users', 'activities', 'teams', 'teamMembers',
          'recruitmentPosts', 'joinRequests', 'notifications')


def migrate(source_path, database_url):
    if not database_url:
        raise RuntimeError('대상 DATABASE_URL을 환경변수에 설정하세요.')
    path = Path(source_path).resolve(strict=True)
    source = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
    source.row_factory = sqlite3.Row
    target = connect_database('', database_url)
    counts = {}
    try:
        target.executescript(SCHEMA)
        for table in TABLES:
            if target.execute(f'SELECT COUNT(*) c FROM "{table}"').fetchone()['c']:
                raise RuntimeError('대상 DB가 비어 있지 않습니다. 기존 데이터를 덮어쓰지 않습니다.')
        for table in TABLES:
            rows = source.execute(f'SELECT * FROM "{table}" ORDER BY id').fetchall()
            counts[table] = len(rows)
            if rows:
                columns = ','.join('"' + name + '"' for name in rows[0].keys())
                placeholders = ','.join('?' for _ in rows[0].keys())
                for row in rows:
                    target.execute(f'INSERT INTO "{table}" ({columns}) VALUES ({placeholders})', tuple(row))
            target.connection.execute(
                sql.SQL("SELECT setval(pg_get_serial_sequence(%s, 'id'), "
                        "COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM careermate.{}")
                .format(sql.Identifier(table)), (f'careermate."{table}"',))
        target.commit()
        return counts
    except Exception:
        target.rollback()
        raise
    finally:
        target.close()
        source.close()


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('사용법: python migrate_sqlite.py /path/to/backup.db')
    try:
        counts = migrate(sys.argv[1], os.environ.get('DATABASE_URL', ''))
        print('이전 완료:', ', '.join(f'{table}={count}' for table, count in counts.items()))
    except Exception:
        # Connection exceptions may include host details; never print credentials.
        raise SystemExit('이전 실패: 대상 DB가 비어 있는지, 연결 설정과 원본 백업을 확인하세요. 기존 대상 데이터는 변경하지 않았습니다.') from None
