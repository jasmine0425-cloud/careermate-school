import os, json, csv, io, sqlite3
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify, session, render_template, Response
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'school_team_match.db')

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-this-secret-key-before-deploy')
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax')

CAREER_CATEGORIES = ['컴퓨터 / IT','AI','소프트웨어','전자공학','반도체','기계공학','생명과학','화학','의학 / 보건','경영 / 경제','심리 / 사회','교육','미디어','디자인','건축','인문','법학','기타']
ROLE_OPTIONS = ['팀장','기획','자료조사','개발','디자인','발표','PPT 제작','보고서 작성','실험','데이터 분석','하드웨어 제작','영상 제작','기타']


def now():
    return datetime.now().isoformat(timespec='seconds')


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def jdump(v):
    if v is None: return '[]'
    if isinstance(v, str):
        try: json.loads(v); return v
        except Exception: return json.dumps([x.strip() for x in v.split(',') if x.strip()], ensure_ascii=False)
    return json.dumps(v, ensure_ascii=False)


def jload(v):
    try: return json.loads(v or '[]')
    except Exception: return []


def user_public(r):
    return {
        'id': r['id'], 'name': r['name'], 'studentNumber': r['studentNumber'],
        'grade': r['grade'], 'classNumber': r['classNumber'], 'number': r['number'],
        'careerCategory': r['careerCategory'], 'desiredMajor': r['desiredMajor'],
        'desiredJob': r['desiredJob'], 'interests': jload(r['interests']),
        'keywords': jload(r['keywords']), 'preferredRoles': jload(r['preferredRoles'])
    }


def init_db():
    con = db()
    con.executescript('''
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      loginId TEXT UNIQUE NOT NULL,
      passwordHash TEXT NOT NULL,
      role TEXT NOT NULL CHECK(role IN ('ADMIN','STUDENT')),
      name TEXT NOT NULL,
      studentNumber TEXT,
      grade INTEGER,
      classNumber INTEGER,
      number INTEGER,
      careerCategory TEXT DEFAULT '',
      desiredMajor TEXT DEFAULT '',
      desiredJob TEXT DEFAULT '',
      interests TEXT DEFAULT '[]',
      keywords TEXT DEFAULT '[]',
      preferredRoles TEXT DEFAULT '[]',
      accountStatus TEXT DEFAULT 'ACTIVE',
      createdAt TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS activities (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      description TEXT DEFAULT '',
      startDate TEXT,
      endDate TEXT,
      minMembers INTEGER DEFAULT 2,
      maxMembers INTEGER DEFAULT 5,
      recommendedFields TEXT DEFAULT '[]',
      recruitmentDeadline TEXT,
      createdAt TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS teams (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      activityId INTEGER NOT NULL,
      teamName TEXT NOT NULL,
      topic TEXT DEFAULT '',
      description TEXT DEFAULT '',
      leaderId INTEGER NOT NULL,
      maxMembers INTEGER NOT NULL,
      status TEXT DEFAULT 'RECRUITING',
      createdAt TEXT NOT NULL,
      FOREIGN KEY(activityId) REFERENCES activities(id) ON DELETE CASCADE,
      FOREIGN KEY(leaderId) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS teamMembers (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      teamId INTEGER NOT NULL,
      userId INTEGER NOT NULL,
      role TEXT DEFAULT '',
      status TEXT NOT NULL DEFAULT 'waiting',
      createdAt TEXT NOT NULL,
      UNIQUE(teamId,userId),
      FOREIGN KEY(teamId) REFERENCES teams(id) ON DELETE CASCADE,
      FOREIGN KEY(userId) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS recruitmentPosts (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      teamId INTEGER UNIQUE NOT NULL,
      requiredFields TEXT DEFAULT '[]',
      requiredRoles TEXT DEFAULT '[]',
      recruitCount INTEGER DEFAULT 1,
      keywords TEXT DEFAULT '[]',
      description TEXT DEFAULT '',
      deadline TEXT,
      status TEXT DEFAULT 'OPEN',
      createdAt TEXT NOT NULL,
      FOREIGN KEY(teamId) REFERENCES teams(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS joinRequests (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      teamId INTEGER NOT NULL,
      userId INTEGER NOT NULL,
      requestType TEXT NOT NULL,
      status TEXT DEFAULT 'pending',
      message TEXT DEFAULT '',
      createdAt TEXT NOT NULL,
      UNIQUE(teamId,userId,status),
      FOREIGN KEY(teamId) REFERENCES teams(id) ON DELETE CASCADE,
      FOREIGN KEY(userId) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS notifications (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      userId INTEGER NOT NULL,
      type TEXT NOT NULL,
      title TEXT NOT NULL,
      message TEXT NOT NULL,
      relatedTeamId INTEGER,
      isRead INTEGER DEFAULT 0,
      createdAt TEXT NOT NULL,
      FOREIGN KEY(userId) REFERENCES users(id) ON DELETE CASCADE
    );
    ''')
    if not con.execute("SELECT id FROM users WHERE loginId='admin'").fetchone():
        con.execute('INSERT INTO users(loginId,passwordHash,role,name,createdAt) VALUES(?,?,?,?,?)',
                    ('admin', generate_password_hash('Admin123!'), 'ADMIN', '학교 관리자', now()))
    sample_students = [
      ('20261001','김하늘',1,1,1,'kimsky','AI','컴퓨터공학','AI 개발자',['AI','웹 개발','앱 개발'],['Python','Flask','데이터'],['개발','데이터 분석']),
      ('20261002','박서연',1,1,2,'parksy','디자인','산업디자인','UX 디자이너',['디자인','UI/UX','영상'],['Figma','UI','브랜딩'],['디자인','PPT 제작']),
      ('20261003','이준호',1,2,3,'leejh','전자공학','전자공학','임베디드 엔지니어',['로봇','반도체','Arduino'],['센서','Arduino','회로'],['하드웨어 제작','실험']),
      ('20261004','최민지',1,2,4,'choimj','경영 / 경제','경영학','서비스 기획자',['마케팅','사회문제','창업'],['기획','시장조사','발표'],['기획','발표']),
      ('20261005','정다은',1,3,5,'jungde','생명과학','생명공학','연구원',['바이오','의료','환경'],['실험','바이오','환경'],['실험','자료조사']),
    ]
    for s in sample_students:
        if not con.execute('SELECT id FROM users WHERE loginId=?',(s[5],)).fetchone():
            con.execute('''INSERT INTO users(studentNumber,name,grade,classNumber,number,loginId,passwordHash,role,careerCategory,desiredMajor,desiredJob,interests,keywords,preferredRoles,createdAt)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                        (s[0],s[1],s[2],s[3],s[4],s[5],generate_password_hash('student123'),'STUDENT',s[6],s[7],s[8],jdump(s[9]),jdump(s[10]),jdump(s[11]),now()))
    if not con.execute('SELECT id FROM activities').fetchone():
        con.execute('''INSERT INTO activities(title,description,startDate,endDate,minMembers,maxMembers,recommendedFields,recruitmentDeadline,createdAt)
                       VALUES(?,?,?,?,?,?,?,?,?)''',
                    ('AI 융합 캠프','진로 융합형 프로젝트 팀 활동','2026-09-20','2026-10-10',2,5,jdump(['AI','소프트웨어','디자인','전자공학']),'2026-09-19',now()))
    con.commit(); con.close()


def login_required(fn):
    @wraps(fn)
    def wrap(*args, **kwargs):
        if not session.get('user_id'): return jsonify({'error':'로그인이 필요합니다.'}), 401
        return fn(*args, **kwargs)
    return wrap


def admin_required(fn):
    @wraps(fn)
    def wrap(*args, **kwargs):
        if not session.get('user_id'): return jsonify({'error':'로그인이 필요합니다.'}), 401
        if session.get('role') != 'ADMIN': return jsonify({'error':'관리자 권한이 필요합니다.'}), 403
        return fn(*args, **kwargs)
    return wrap


def student_required(fn):
    @wraps(fn)
    def wrap(*args, **kwargs):
        if not session.get('user_id'): return jsonify({'error':'로그인이 필요합니다.'}), 401
        if session.get('role') != 'STUDENT': return jsonify({'error':'학생 계정만 사용할 수 있습니다.'}), 403
        return fn(*args, **kwargs)
    return wrap


def notify(con, user_id, typ, title, message, team_id=None):
    con.execute('INSERT INTO notifications(userId,type,title,message,relatedTeamId,createdAt) VALUES(?,?,?,?,?,?)',
                (user_id, typ, title, message, team_id, now()))


def confirmed_in_activity(con, user_id, activity_id, exclude_team=None):
    q='''SELECT tm.teamId FROM teamMembers tm JOIN teams t ON t.id=tm.teamId
         WHERE tm.userId=? AND tm.status='confirmed' AND t.activityId=?'''
    params=[user_id,activity_id]
    if exclude_team:
        q += ' AND tm.teamId<>?'; params.append(exclude_team)
    return con.execute(q, params).fetchone() is not None


def team_count(con, team_id):
    return con.execute("SELECT COUNT(*) c FROM teamMembers WHERE teamId=? AND status='confirmed'",(team_id,)).fetchone()['c']


def auto_team_status(con, team_id):
    t=con.execute('SELECT maxMembers FROM teams WHERE id=?',(team_id,)).fetchone()
    if not t: return
    count=team_count(con,team_id)
    if count >= t['maxMembers']:
        con.execute("UPDATE teams SET status='COMPLETE' WHERE id=?",(team_id,))
        con.execute("UPDATE recruitmentPosts SET status='CLOSED' WHERE teamId=?",(team_id,))
    else:
        con.execute("UPDATE teams SET status=CASE WHEN status='COMPLETE' THEN 'RECRUITING' ELSE status END WHERE id=?",(team_id,))


@app.route('/')
def index(): return render_template('index.html')

@app.post('/api/login')
def login():
    data=request.get_json(force=True); con=db()
    u=con.execute('SELECT * FROM users WHERE loginId=? AND accountStatus="ACTIVE"',(data.get('loginId',''),)).fetchone(); con.close()
    if not u or not check_password_hash(u['passwordHash'],data.get('password','')):
        return jsonify({'error':'아이디 또는 비밀번호가 올바르지 않습니다.'}),400
    session.clear(); session['user_id']=u['id']; session['role']=u['role']
    return jsonify({'ok':True,'role':u['role'],'name':u['name']})

@app.post('/api/logout')
def logout(): session.clear(); return jsonify({'ok':True})

@app.get('/api/me')
@login_required
def me():
    con=db(); u=con.execute('SELECT * FROM users WHERE id=?',(session['user_id'],)).fetchone()
    unread=con.execute('SELECT COUNT(*) c FROM notifications WHERE userId=? AND isRead=0',(u['id'],)).fetchone()['c']; con.close()
    d=user_public(u); d.update({'role':u['role'],'loginId':u['loginId'],'unread':unread}); return jsonify(d)

@app.put('/api/profile')
@student_required
def update_profile():
    data=request.get_json(force=True); con=db()
    con.execute('''UPDATE users SET desiredMajor=?,desiredJob=?,careerCategory=?,interests=?,keywords=?,preferredRoles=? WHERE id=?''',
                (data.get('desiredMajor',''),data.get('desiredJob',''),data.get('careerCategory',''),jdump(data.get('interests',[])),jdump(data.get('keywords',[])),jdump(data.get('preferredRoles',[])),session['user_id']))
    con.commit(); con.close(); return jsonify({'ok':True})

@app.get('/api/admin/students')
@admin_required
def admin_students():
    con=db(); rows=con.execute("SELECT * FROM users WHERE role='STUDENT' ORDER BY grade,classNumber,number,name").fetchall(); con.close()
    return jsonify([dict(user_public(r), loginId=r['loginId'], accountStatus=r['accountStatus']) for r in rows])

@app.post('/api/admin/students')
@admin_required
def admin_add_student():
    d=request.get_json(force=True); con=db()
    try:
        cur=con.execute('''INSERT INTO users(loginId,passwordHash,role,name,studentNumber,grade,classNumber,number,careerCategory,desiredMajor,desiredJob,interests,keywords,preferredRoles,createdAt)
                           VALUES(?,?,'STUDENT',?,?,?,?,?,?,?,?,?,?,?,?)''',
                        (d['loginId'],generate_password_hash(d.get('password','student123')),d['name'],d.get('studentNumber',''),d.get('grade'),d.get('classNumber'),d.get('number'),d.get('careerCategory',''),d.get('desiredMajor',''),d.get('desiredJob',''),jdump(d.get('interests',[])),jdump(d.get('keywords',[])),jdump(d.get('preferredRoles',[])),now()))
        con.commit(); return jsonify({'ok':True,'id':cur.lastrowid})
    except sqlite3.IntegrityError:
        return jsonify({'error':'이미 사용 중인 아이디입니다.'}),400
    finally: con.close()

@app.put('/api/admin/students/<int:uid>')
@admin_required
def admin_update_student(uid):
    d = request.get_json(force=True)
    login_id = str(d.get('loginId', '')).strip()
    name = str(d.get('name', '')).strip()
    if not login_id or not name:
        return jsonify({'error': '이름과 로그인 아이디는 필수입니다.'}), 400

    con = db()
    try:
        exists = con.execute("SELECT id FROM users WHERE id=? AND role='STUDENT'", (uid,)).fetchone()
        if not exists:
            return jsonify({'error': '학생 계정을 찾을 수 없습니다.'}), 404

        con.execute('''UPDATE users SET loginId=?,name=?,studentNumber=?,grade=?,classNumber=?,number=?,careerCategory=?,desiredMajor=?,desiredJob=?,interests=?,keywords=?,preferredRoles=?,accountStatus=?
                       WHERE id=? AND role='STUDENT' ''',
                    (login_id, name, d.get('studentNumber',''), d.get('grade'), d.get('classNumber'), d.get('number'),
                     d.get('careerCategory',''), d.get('desiredMajor',''), d.get('desiredJob',''), jdump(d.get('interests',[])),
                     jdump(d.get('keywords',[])), jdump(d.get('preferredRoles',[])), d.get('accountStatus','ACTIVE'), uid))
        if d.get('password'):
            con.execute('UPDATE users SET passwordHash=? WHERE id=?', (generate_password_hash(d['password']), uid))
        con.commit()
        return jsonify({'ok': True})
    except sqlite3.IntegrityError:
        con.rollback()
        return jsonify({'error': '이미 사용 중인 로그인 아이디입니다.'}), 400
    finally:
        con.close()

@app.post('/api/admin/students/<int:uid>/reset-password')
@admin_required
def admin_reset_student_password(uid):
    d = request.get_json(silent=True) or {}
    new_password = str(d.get('password') or 'student123').strip()
    if len(new_password) < 4:
        return jsonify({'error': '비밀번호는 4자 이상으로 설정해 주세요.'}), 400
    con = db()
    cur = con.execute("UPDATE users SET passwordHash=? WHERE id=? AND role='STUDENT'",
                      (generate_password_hash(new_password), uid))
    con.commit(); con.close()
    if cur.rowcount == 0:
        return jsonify({'error': '학생 계정을 찾을 수 없습니다.'}), 404
    return jsonify({'ok': True, 'temporaryPassword': new_password})

@app.get('/api/admin/students/csv-template')
@admin_required
def download_student_csv_template():
    output = io.StringIO()
    writer = csv.writer(output, lineterminator='\n')
    writer.writerow(['아이디','이름','학번','학년','반','번호','초기비밀번호','진로','희망학과','희망직업','관심분야','관심키워드','선호역할'])
    writer.writerow(['10901','김예시','10901','1','9','1','student123','컴퓨터 / IT','컴퓨터공학과','AI 개발자','AI,웹 개발','Python,AI','개발,발표'])
    data = '\ufeff' + output.getvalue()
    return Response(data, mimetype='text/csv; charset=utf-8', headers={
        'Content-Disposition': 'attachment; filename=student_import_template.csv'
    })

@app.delete('/api/admin/students/<int:uid>')
@admin_required
def admin_delete_student(uid):
    con=db(); con.execute("UPDATE users SET accountStatus='DELETED', loginId='deleted_'||id||'_'||loginId WHERE id=? AND role='STUDENT'",(uid,)); con.execute("UPDATE teamMembers SET status='left' WHERE userId=? AND status!='left'",(uid,)); con.commit(); con.close(); return jsonify({'ok':True})

@app.post('/api/admin/students/import-csv')
@admin_required
def import_students_csv():
    if 'file' not in request.files: return jsonify({'error':'CSV 파일이 필요합니다.'}),400
    f=request.files['file']; text=io.StringIO(f.stream.read().decode('utf-8-sig')); reader=csv.DictReader(text); con=db(); added=0; skipped=[]
    for i,row in enumerate(reader, start=2):
        try:
            login_id=row.get('loginId') or row.get('아이디'); name=row.get('name') or row.get('이름')
            if not login_id or not name: raise ValueError('아이디/이름 누락')
            con.execute('''INSERT INTO users(loginId,passwordHash,role,name,studentNumber,grade,classNumber,number,careerCategory,desiredMajor,desiredJob,interests,keywords,preferredRoles,createdAt)
                           VALUES(?,?,'STUDENT',?,?,?,?,?,?,?,?,?,?,?,?)''',
                        (login_id,generate_password_hash(row.get('password') or row.get('초기비밀번호') or 'student123'),name,row.get('studentNumber') or row.get('학번',''),row.get('grade') or row.get('학년') or None,row.get('classNumber') or row.get('반') or None,row.get('number') or row.get('번호') or None,row.get('careerCategory') or row.get('진로',''),row.get('desiredMajor') or row.get('희망학과',''),row.get('desiredJob') or row.get('희망직업',''),jdump(row.get('interests') or row.get('관심분야','')),jdump(row.get('keywords') or row.get('관심키워드','')),jdump(row.get('preferredRoles') or row.get('선호역할','')),now())); added+=1
        except Exception as e: skipped.append({'row':i,'reason':str(e)})
    con.commit(); con.close(); return jsonify({'ok':True,'added':added,'skipped':skipped})

@app.get('/api/activities')
@login_required
def activities():
    con=db(); rows=con.execute('SELECT * FROM activities ORDER BY startDate DESC,id DESC').fetchall(); con.close()
    return jsonify([dict(r, recommendedFields=jload(r['recommendedFields'])) for r in rows])

@app.post('/api/activities')
@admin_required
def create_activity():
    d=request.get_json(force=True); con=db(); cur=con.execute('''INSERT INTO activities(title,description,startDate,endDate,minMembers,maxMembers,recommendedFields,recruitmentDeadline,createdAt) VALUES(?,?,?,?,?,?,?,?,?)''',(d['title'],d.get('description',''),d.get('startDate'),d.get('endDate'),int(d.get('minMembers',2)),int(d.get('maxMembers',5)),jdump(d.get('recommendedFields',[])),d.get('recruitmentDeadline'),now())); con.commit(); con.close(); return jsonify({'ok':True,'id':cur.lastrowid})

@app.delete('/api/activities/<int:aid>')
@admin_required
def delete_activity(aid):
    con=db(); con.execute('DELETE FROM activities WHERE id=?',(aid,)); con.commit(); con.close(); return jsonify({'ok':True})

@app.get('/api/students')
@student_required
def student_search():
    con=db(); q="SELECT * FROM users WHERE role='STUDENT' AND accountStatus='ACTIVE' AND id<>?"; params=[session['user_id']]
    term=request.args.get('q','').strip(); grade=request.args.get('grade',''); career=request.args.get('career',''); role=request.args.get('role','')
    if term:
        q += " AND (name LIKE ? OR studentNumber LIKE ? OR careerCategory LIKE ? OR desiredMajor LIKE ? OR interests LIKE ? OR keywords LIKE ?)"; like=f'%{term}%'; params += [like]*6
    if grade: q+=' AND grade=?'; params.append(grade)
    if career: q+=' AND careerCategory LIKE ?'; params.append(f'%{career}%')
    if role: q+=' AND preferredRoles LIKE ?'; params.append(f'%{role}%')
    rows=con.execute(q+' ORDER BY grade,classNumber,number,name LIMIT 200',params).fetchall(); con.close(); return jsonify([user_public(r) for r in rows])

@app.post('/api/teams')
@student_required
def create_team():
    d=request.get_json(force=True); con=db(); activity=con.execute('SELECT * FROM activities WHERE id=?',(d['activityId'],)).fetchone()
    if not activity: con.close(); return jsonify({'error':'활동을 찾을 수 없습니다.'}),404
    if confirmed_in_activity(con,session['user_id'],activity['id']): con.close(); return jsonify({'error':'이미 해당 활동의 다른 팀에 참여하고 있습니다.'}),400
    maxm=min(int(d.get('maxMembers') or activity['maxMembers']), int(activity['maxMembers']))
    cur=con.execute('''INSERT INTO teams(activityId,teamName,topic,description,leaderId,maxMembers,status,createdAt) VALUES(?,?,?,?,?,?,'RECRUITING',?)''',(activity['id'],d['teamName'],d.get('topic',''),d.get('description',''),session['user_id'],maxm,now())); tid=cur.lastrowid
    con.execute("INSERT INTO teamMembers(teamId,userId,role,status,createdAt) VALUES(?,?,?,'confirmed',?)",(tid,session['user_id'],d.get('leaderRole','팀장'),now()))
    for uid in d.get('inviteUserIds',[]):
        if int(uid)==session['user_id']: continue
        try:
            con.execute("INSERT INTO teamMembers(teamId,userId,status,createdAt) VALUES(?,?,'waiting',?)",(tid,int(uid),now()))
            notify(con,int(uid),'TEAM_INVITE','팀 참여 확인 요청',f"{d['teamName']} 팀에 함께하기로 한 팀원으로 등록되었습니다.",tid)
        except sqlite3.IntegrityError: pass
    con.commit(); con.close(); return jsonify({'ok':True,'teamId':tid})


def serialize_team(con, t, include_members=True):
    d=dict(t); d['currentMembers']=team_count(con,t['id']);
    if include_members:
        rows=con.execute('''SELECT tm.id membershipId,tm.status,tm.role teamRole,u.* FROM teamMembers tm JOIN users u ON u.id=tm.userId WHERE tm.teamId=? ORDER BY CASE tm.status WHEN 'confirmed' THEN 0 ELSE 1 END,u.name''',(t['id'],)).fetchall()
        d['members']=[dict(user_public(r), membershipId=r['membershipId'], memberStatus=r['status'], teamRole=r['teamRole']) for r in rows]
    return d

@app.get('/api/teams')
@login_required
def list_teams():
    con=db(); rows=con.execute('SELECT t.*,a.title activityTitle FROM teams t JOIN activities a ON a.id=t.activityId ORDER BY t.createdAt DESC').fetchall(); out=[serialize_team(con,r,False) for r in rows]; con.close(); return jsonify(out)

@app.get('/api/my-teams')
@student_required
def my_teams():
    con=db(); rows=con.execute('''SELECT t.*,a.title activityTitle,tm.status myStatus,tm.role myRole FROM teamMembers tm JOIN teams t ON t.id=tm.teamId JOIN activities a ON a.id=t.activityId WHERE tm.userId=? AND tm.status!='left' ORDER BY t.createdAt DESC''',(session['user_id'],)).fetchall(); out=[]
    for r in rows:
        d=serialize_team(con,r); d['myStatus']=r['myStatus']; d['myRole']=r['myRole']; out.append(d)
    con.close(); return jsonify(out)

@app.get('/api/teams/<int:tid>')
@login_required
def team_detail(tid):
    con=db(); t=con.execute('SELECT t.*,a.title activityTitle FROM teams t JOIN activities a ON a.id=t.activityId WHERE t.id=?',(tid,)).fetchone()
    if not t: con.close(); return jsonify({'error':'팀을 찾을 수 없습니다.'}),404
    d=serialize_team(con,t); rec=con.execute('SELECT * FROM recruitmentPosts WHERE teamId=?',(tid,)).fetchone(); d['recruitment']=dict(rec, requiredFields=jload(rec['requiredFields']), requiredRoles=jload(rec['requiredRoles']), keywords=jload(rec['keywords'])) if rec else None; con.close(); return jsonify(d)

@app.post('/api/teams/<int:tid>/invite')
@student_required
def invite_student(tid):
    d=request.get_json(force=True); uid=int(d['userId']); con=db(); t=con.execute('SELECT * FROM teams WHERE id=?',(tid,)).fetchone()
    if not t or t['leaderId']!=session['user_id']: con.close(); return jsonify({'error':'팀장만 초대할 수 있습니다.'}),403
    if confirmed_in_activity(con,uid,t['activityId'],tid): con.close(); return jsonify({'error':'해당 학생은 이미 이 활동의 다른 팀에 참여 중입니다.'}),400
    if team_count(con,tid)>=t['maxMembers']: con.close(); return jsonify({'error':'팀 정원이 가득 찼습니다.'}),400
    try: con.execute("INSERT INTO teamMembers(teamId,userId,role,status,createdAt) VALUES(?,?,?,'waiting',?)",(tid,uid,d.get('role',''),now()))
    except sqlite3.IntegrityError:
        con.execute("UPDATE teamMembers SET status='waiting',role=? WHERE teamId=? AND userId=?",(d.get('role',''),tid,uid))
    notify(con,uid,'TEAM_INVITE','팀 참여 확인 요청',f"{t['teamName']} 팀에 초대되었습니다.",tid); con.commit(); con.close(); return jsonify({'ok':True})

@app.post('/api/memberships/<int:mid>/respond')
@student_required
def respond_invite(mid):
    d=request.get_json(force=True); con=db(); m=con.execute('''SELECT tm.*,t.activityId,t.teamName,t.leaderId,t.maxMembers FROM teamMembers tm JOIN teams t ON t.id=tm.teamId WHERE tm.id=? AND tm.userId=?''',(mid,session['user_id'])).fetchone()
    if not m or m['status']!='waiting': con.close(); return jsonify({'error':'처리할 요청이 없습니다.'}),404
    if d.get('accept'):
        if confirmed_in_activity(con,session['user_id'],m['activityId'],m['teamId']): con.close(); return jsonify({'error':'이미 해당 활동의 다른 팀에 참여하고 있습니다.'}),400
        if team_count(con,m['teamId'])>=m['maxMembers']: con.close(); return jsonify({'error':'팀 정원이 이미 가득 찼습니다.'}),400
        con.execute("UPDATE teamMembers SET status='confirmed' WHERE id=?",(mid,)); notify(con,m['leaderId'],'INVITE_ACCEPTED','초대 수락',f"팀원이 {m['teamName']} 팀 참여를 확인했습니다.",m['teamId']); auto_team_status(con,m['teamId'])
    else:
        con.execute("UPDATE teamMembers SET status='rejected' WHERE id=?",(mid,)); notify(con,m['leaderId'],'INVITE_REJECTED','초대 거절',f"초대가 거절되었습니다.",m['teamId'])
    con.commit(); con.close(); return jsonify({'ok':True})

@app.post('/api/teams/<int:tid>/recruitment')
@student_required
def save_recruitment(tid):
    d=request.get_json(force=True); con=db(); t=con.execute('SELECT * FROM teams WHERE id=?',(tid,)).fetchone()
    if not t or t['leaderId']!=session['user_id']: con.close(); return jsonify({'error':'팀장만 모집글을 관리할 수 있습니다.'}),403
    count=team_count(con,tid)
    if count>=t['maxMembers']: con.close(); return jsonify({'error':'팀 정원이 가득 찼습니다.'}),400
    con.execute('''INSERT INTO recruitmentPosts(teamId,requiredFields,requiredRoles,recruitCount,keywords,description,deadline,status,createdAt)
                   VALUES(?,?,?,?,?,?,?,'OPEN',?) ON CONFLICT(teamId) DO UPDATE SET requiredFields=excluded.requiredFields,requiredRoles=excluded.requiredRoles,recruitCount=excluded.recruitCount,keywords=excluded.keywords,description=excluded.description,deadline=excluded.deadline,status='OPEN' ''',
                (tid,jdump(d.get('requiredFields',[])),jdump(d.get('requiredRoles',[])),int(d.get('recruitCount',max(1,t['maxMembers']-count))),jdump(d.get('keywords',[])),d.get('description',''),d.get('deadline'),now()))
    con.execute("UPDATE teams SET status='RECRUITING' WHERE id=?",(tid,)); con.commit(); con.close(); return jsonify({'ok':True})

@app.post('/api/teams/<int:tid>/recruitment/close')
@student_required
def close_recruitment(tid):
    con=db(); t=con.execute('SELECT * FROM teams WHERE id=?',(tid,)).fetchone()
    if not t or t['leaderId']!=session['user_id']: con.close(); return jsonify({'error':'팀장만 모집을 종료할 수 있습니다.'}),403
    con.execute("UPDATE recruitmentPosts SET status='CLOSED' WHERE teamId=?",(tid,)); con.execute("UPDATE teams SET status='CLOSED' WHERE id=?",(tid,)); con.commit(); con.close(); return jsonify({'ok':True})

@app.get('/api/recruitment')
@student_required
def recruitment_list():
    con=db(); rows=con.execute('''SELECT rp.*,t.teamName,t.topic,t.description teamDescription,t.activityId,t.maxMembers,t.leaderId,a.title activityTitle
                                  FROM recruitmentPosts rp JOIN teams t ON t.id=rp.teamId JOIN activities a ON a.id=t.activityId
                                  WHERE rp.status='OPEN' AND t.status!='COMPLETE' ORDER BY rp.createdAt DESC''').fetchall(); out=[]
    for r in rows:
        d=dict(r); d['requiredFields']=jload(r['requiredFields']); d['requiredRoles']=jload(r['requiredRoles']); d['keywords']=jload(r['keywords']); d['currentMembers']=team_count(con,r['teamId']);
        ms=con.execute('''SELECT u.name,u.careerCategory FROM teamMembers tm JOIN users u ON u.id=tm.userId WHERE tm.teamId=? AND tm.status='confirmed' ''',(r['teamId'],)).fetchall(); d['members']=[dict(x) for x in ms]; out.append(d)
    con.close(); return jsonify(out)

@app.post('/api/recruitment/<int:rid>/apply')
@student_required
def apply_team(rid):
    d=request.get_json(silent=True) or {}; con=db(); rp=con.execute('''SELECT rp.*,t.teamName,t.activityId,t.leaderId,t.maxMembers FROM recruitmentPosts rp JOIN teams t ON t.id=rp.teamId WHERE rp.id=? AND rp.status='OPEN' ''',(rid,)).fetchone()
    if not rp: con.close(); return jsonify({'error':'모집 중인 팀이 아닙니다.'}),404
    if rp['leaderId']==session['user_id']: con.close(); return jsonify({'error':'자신의 팀에는 지원할 수 없습니다.'}),400
    if confirmed_in_activity(con,session['user_id'],rp['activityId'],rp['teamId']): con.close(); return jsonify({'error':'이미 해당 활동의 다른 팀에 참여하고 있습니다.'}),400
    if team_count(con,rp['teamId'])>=rp['maxMembers']: con.close(); return jsonify({'error':'팀 정원이 가득 찼습니다.'}),400
    exists=con.execute("SELECT id FROM joinRequests WHERE teamId=? AND userId=? AND status='pending'",(rp['teamId'],session['user_id'])).fetchone()
    if exists: con.close(); return jsonify({'error':'이미 참여 요청을 보냈습니다.'}),400
    con.execute("INSERT INTO joinRequests(teamId,userId,requestType,status,message,createdAt) VALUES(?,?,?,'pending',?,?)",(rp['teamId'],session['user_id'],'APPLY',d.get('message',''),now()))
    u=con.execute('SELECT name FROM users WHERE id=?',(session['user_id'],)).fetchone(); notify(con,rp['leaderId'],'JOIN_REQUEST','새 팀 지원',f"{u['name']} 학생이 {rp['teamName']} 팀에 참여하고 싶어 합니다.",rp['teamId']); con.commit(); con.close(); return jsonify({'ok':True})

@app.get('/api/join-requests')
@student_required
def join_requests():
    con=db(); rows=con.execute('''SELECT jr.*,u.name,u.grade,u.classNumber,u.careerCategory,u.desiredMajor,u.interests,u.keywords,u.preferredRoles,t.teamName
                                  FROM joinRequests jr JOIN teams t ON t.id=jr.teamId JOIN users u ON u.id=jr.userId
                                  WHERE t.leaderId=? AND jr.status='pending' ORDER BY jr.createdAt DESC''',(session['user_id'],)).fetchall(); out=[]
    for r in rows:
        d=dict(r); d['interests']=jload(r['interests']); d['keywords']=jload(r['keywords']); d['preferredRoles']=jload(r['preferredRoles']); out.append(d)
    con.close(); return jsonify(out)

@app.post('/api/join-requests/<int:jid>/respond')
@student_required
def respond_join(jid):
    d=request.get_json(force=True); con=db(); jr=con.execute('''SELECT jr.*,t.leaderId,t.activityId,t.maxMembers,t.teamName FROM joinRequests jr JOIN teams t ON t.id=jr.teamId WHERE jr.id=?''',(jid,)).fetchone()
    if not jr or jr['leaderId']!=session['user_id'] or jr['status']!='pending': con.close(); return jsonify({'error':'처리할 권한이 없거나 이미 처리된 요청입니다.'}),403
    if d.get('accept'):
        if confirmed_in_activity(con,jr['userId'],jr['activityId'],jr['teamId']): con.close(); return jsonify({'error':'이 학생은 이미 같은 활동의 다른 팀에 참여했습니다.'}),400
        if team_count(con,jr['teamId'])>=jr['maxMembers']: con.close(); return jsonify({'error':'팀 정원이 가득 찼습니다.'}),400
        con.execute("UPDATE joinRequests SET status='accepted' WHERE id=?",(jid,))
        existing=con.execute('SELECT id FROM teamMembers WHERE teamId=? AND userId=?',(jr['teamId'],jr['userId'])).fetchone()
        if existing: con.execute("UPDATE teamMembers SET status='confirmed' WHERE id=?",(existing['id'],))
        else: con.execute("INSERT INTO teamMembers(teamId,userId,status,createdAt) VALUES(?,?,'confirmed',?)",(jr['teamId'],jr['userId'],now()))
        notify(con,jr['userId'],'JOIN_ACCEPTED','팀 지원 수락',f"{jr['teamName']} 팀 참여 요청이 수락되었습니다.",jr['teamId']); auto_team_status(con,jr['teamId'])
    else:
        con.execute("UPDATE joinRequests SET status='rejected' WHERE id=?",(jid,)); notify(con,jr['userId'],'JOIN_REJECTED','팀 지원 결과',f"{jr['teamName']} 팀 참여 요청이 거절되었습니다.",jr['teamId'])
    con.commit(); con.close(); return jsonify({'ok':True})

@app.get('/api/recommendations/team/<int:tid>')
@student_required
def recommendations(tid):
    mode=request.args.get('mode','similar'); con=db(); t=con.execute('SELECT * FROM teams WHERE id=?',(tid,)).fetchone()
    if not t: con.close(); return jsonify({'error':'팀을 찾을 수 없습니다.'}),404
    members=con.execute('''SELECT u.* FROM teamMembers tm JOIN users u ON u.id=tm.userId WHERE tm.teamId=? AND tm.status='confirmed' ''',(tid,)).fetchall()
    post=con.execute('SELECT * FROM recruitmentPosts WHERE teamId=?',(tid,)).fetchone(); required_fields=set(jload(post['requiredFields']) if post else []); required_roles=set(jload(post['requiredRoles']) if post else [])
    member_careers={m['careerCategory'] for m in members if m['careerCategory']}; member_interests=set(sum([jload(m['interests']) for m in members],[])); member_keywords=set(sum([jload(m['keywords']) for m in members],[])); member_roles=set(sum([jload(m['preferredRoles']) for m in members],[]))
    candidates=con.execute("SELECT * FROM users WHERE role='STUDENT' AND accountStatus='ACTIVE' AND id NOT IN (SELECT userId FROM teamMembers WHERE teamId=?)",(tid,)).fetchall(); out=[]
    for u in candidates:
        if confirmed_in_activity(con,u['id'],t['activityId'],tid): continue
        interests=set(jload(u['interests'])); keywords=set(jload(u['keywords'])); roles=set(jload(u['preferredRoles'])); career=u['careerCategory']
        if mode=='fusion':
            career_score = 35 if career and career not in member_careers else 12
            complement = 10 if (required_fields and career in required_fields) or (required_roles & roles) or (career and career not in member_careers) else 3
        else:
            career_score = 35 if career in member_careers else (25 if career in required_fields else 8)
            complement = 10 if (required_roles & roles) else 4
        interest_score=min(25, 8*len((interests|keywords) & (member_interests|member_keywords)))
        role_score=20 if required_roles & roles else (12 if roles & member_roles else 5)
        activity_score=10 if career in required_fields or bool(interests & required_fields) else 5
        score=min(100,career_score+interest_score+role_score+activity_score+complement)
        reasons=[]
        if career in member_careers: reasons.append(f'현재 팀과 {career} 진로가 일치합니다.')
        if career in required_fields: reasons.append(f'팀이 모집 중인 {career} 분야에 해당합니다.')
        if required_roles & roles: reasons.append(f"필요 역할({', '.join(required_roles & roles)})을 희망합니다.")
        if (interests|keywords) & (member_interests|member_keywords): reasons.append('팀원들과 관심 키워드가 겹칩니다.')
        if mode=='fusion' and career and career not in member_careers: reasons.append(f'현재 팀에 없는 {career} 분야를 보완할 수 있습니다.')
        out.append(dict(user_public(u),score=score,reasons=reasons[:4]))
    con.close(); out.sort(key=lambda x:x['score'],reverse=True); return jsonify(out[:30])

@app.get('/api/notifications')
@login_required
def notifications():
    con=db(); rows=con.execute('SELECT * FROM notifications WHERE userId=? ORDER BY createdAt DESC LIMIT 100',(session['user_id'],)).fetchall(); con.close(); return jsonify([dict(r) for r in rows])

@app.post('/api/notifications/<int:nid>/read')
@login_required
def read_notification(nid):
    con=db(); con.execute('UPDATE notifications SET isRead=1 WHERE id=? AND userId=?',(nid,session['user_id'])); con.commit(); con.close(); return jsonify({'ok':True})

@app.get('/api/admin/stats')
@admin_required
def stats():
    con=db(); d={
      'students': con.execute("SELECT COUNT(*) c FROM users WHERE role='STUDENT' AND accountStatus='ACTIVE'").fetchone()['c'],
      'activities': con.execute('SELECT COUNT(*) c FROM activities').fetchone()['c'],
      'teams': con.execute('SELECT COUNT(*) c FROM teams').fetchone()['c'],
      'recruiting': con.execute("SELECT COUNT(*) c FROM recruitmentPosts WHERE status='OPEN'").fetchone()['c'],
    }; con.close(); return jsonify(d)

@app.get('/api/options')
def options(): return jsonify({'careerCategories':CAREER_CATEGORIES,'roles':ROLE_OPTIONS})

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)), debug=True)
