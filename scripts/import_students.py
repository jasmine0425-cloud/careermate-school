"""Private student provisioning. Do not commit student rosters or passwords.
Dry run by default; --execute needs DATABASE_URL and a private handoff path.
"""
import argparse,csv,datetime,os,secrets,string
from collections import Counter
from pathlib import Path

EXPECTED=797
ALPHABET=string.ascii_letters+string.digits+'!@#$%&*'

def load(path):
    with open(path,encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
    if len(rows)!=EXPECTED: raise ValueError(f'Expected {EXPECTED} rows, got {len(rows)}')
    ids=set()
    for row in rows:
        login=row['로그인ID'].strip();grade=int(row['학년']);klass=int(row['반']);num=int(row['번호'])
        if not row['이름'].strip() or row['이름'].startswith('예비'):raise ValueError('Invalid student name')
        if not (1<=grade<=3 and 1<=klass<=10 and 1<=num<=40):raise ValueError('Invalid grade/class/number')
        if login!=f'ks{27-grade:02d}{grade}{klass:02d}{num:02d}' or login in ids:raise ValueError('Invalid or duplicate student ID')
        ids.add(login)
    return rows

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--csv',required=True)
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--handoff',help='Private local credentials file, never commit')
    args=parser.parse_args();rows=load(args.csv)
    print('Validated',len(rows),'students',dict(Counter(r['학년'] for r in rows)))
    if not args.execute:
        print('Dry run: no passwords created and no database writes');return
    if not args.handoff or not os.environ.get('DATABASE_URL'):
        parser.error('Execution requires --handoff and DATABASE_URL')
    from werkzeug.security import generate_password_hash
    import psycopg
    from psycopg.rows import dict_row
    dest=Path(args.handoff).resolve()
    if dest.exists():raise FileExistsError('Credential file already exists')
    credentials=[];passwords=set()
    for row in rows:
        password=''.join(secrets.choice(ALPHABET) for _ in range(20))
        while password in passwords:password=''.join(secrets.choice(ALPHABET) for _ in range(20))
        passwords.add(password);credentials.append((row,password,generate_password_hash(password)))
    with psycopg.connect(os.environ['DATABASE_URL'],row_factory=dict_row,connect_timeout=10) as con:
        with con.cursor() as cur:
            cur.execute('SELECT "loginId" FROM careermate.users WHERE "loginId"=ANY(%s)',([r['로그인ID'] for r in rows],))
            if cur.fetchone():raise RuntimeError('Existing account detected; nothing inserted')
            for row,password,hashed in credentials:
                cur.execute('''INSERT INTO careermate.users ("loginId","passwordHash","role","name","studentNumber","grade","classNumber","number","mustChangePassword","createdAt") VALUES (%s,%s,'STUDENT',%s,%s,%s,%s,%s,1,%s)''',
                    (row['로그인ID'],hashed,row['이름'],row['로그인ID'],int(row['학년']),int(row['반']),int(row['번호']),datetime.datetime.now(datetime.timezone.utc).isoformat()))
            fd=os.open(dest,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            try:
                with os.fdopen(fd,'w',encoding='utf-8-sig',newline='') as output:
                    writer=csv.writer(output);writer.writerow(['로그인ID','이름','임시비밀번호'])
                    writer.writerows((row['로그인ID'],row['이름'],pw) for row,pw,_ in credentials)
                con.commit()
            except BaseException:
                dest.unlink(missing_ok=True)
                raise
    print('Inserted',len(rows),'student accounts')

if __name__=='__main__':main()
