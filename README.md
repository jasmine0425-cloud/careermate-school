# CareerMate - 진로 기반 학교 팀 매칭 플랫폼

학교의 캠프·대회·수행평가·프로젝트 등에서 학생들이 진로와 관심 분야에 맞는 팀원을 찾고, 모집팀에 지원할 수 있는 Flask + SQLite 웹앱입니다.

## 주요 기능
- 관리자/학생 로그인 및 역할 분리
- 관리자 학생 계정 추가/삭제, CSV 일괄 등록
- 활동 생성/삭제
- 학생 진로 프로필 수정
- 팀 생성, 기존 약속 팀원 선택 → 참여 확인 요청
- 같은 활동 내 중복 확정 가입 방지
- 팀원 모집글 작성/마감
- 모집 중인 팀에서 `같이하기` 지원
- 팀장 지원 수락/거절
- 진로 유사형 / 진로 융합형 추천 + 추천 이유
- 알림 시스템
- 팀 정원 충족 시 모집 자동 종료
- 반응형 모바일 UI

## 실행 방법
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
python app.py
```
브라우저에서 `http://127.0.0.1:5000` 접속

## 데모 계정
- 관리자: `admin` / `Admin123!`
- 학생: `kimsky` / `student123`
- 추가 샘플 학생: `parksy`, `leejh`, `choimj`, `jungde` / 비밀번호 `student123`

## CSV 일괄 등록 컬럼
권장 헤더:
```csv
loginId,name,studentNumber,grade,classNumber,number,password,careerCategory,desiredMajor,desiredJob,interests,keywords,preferredRoles
```
여러 값은 쉼표로 구분합니다.

## 배포 전 필수 변경
1. `SECRET_KEY` 환경변수를 강한 랜덤 값으로 설정
2. 기본 관리자 비밀번호 변경
3. HTTPS 적용
4. 운영 환경에서는 Flask 개발 서버 대신 Gunicorn/Waitress 등 WSGI 서버 사용
5. 개인정보 처리방침 및 학교 내부 접근권한 정책에 맞게 운영

## 초기화
처음 실행하면 `school_team_match.db`가 자동 생성됩니다. 완전히 초기화하려면 서버를 종료하고 해당 DB 파일을 삭제한 뒤 다시 실행합니다.

## 외부 공개 서버 실행

개발 서버 대신 `gunicorn --workers 1 --bind 0.0.0.0:$PORT wsgi:app`을 사용합니다.
`wsgi.py`는 서버 시작 시 데이터베이스 테이블을 초기화합니다.

운영 환경변수:
- `APP_ENV=production`
- `SECRET_KEY`: 32자 이상 랜덤 문자열 (변경하면 기존 로그인 세션이 해제됩니다)
- `ADMIN_LOGIN`: 최초 관리자 아이디, 기본값 `admin`
- `ADMIN_PASSWORD`: 최초 관리자 비밀번호, 12자 이상
- `SEED_DEMO=false`: 공개된 데모 계정과 샘플 활동 생성을 끕니다
- `DB_PATH`: 영구 저장소 안의 DB 절대 경로

`ADMIN_PASSWORD`는 새 DB의 최초 관리자 생성에만 사용합니다. 기존 DB 관리자 비밀번호를 바꾸지는 않습니다.
운영 서버에는 저장소에 포함된 `school_team_match.db`를 그대로 사용하지 말고,
영구 저장소의 새 DB 경로를 지정하세요. 기존 학생 데이터를 이전해야 한다면 별도 백업/이전이 필요합니다.
`.gitignore`는 이미 Git에 등록된 DB 파일을 제거하지 않습니다.

### Render 설정

- 서비스: Python Web Service
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn --workers 1 --bind 0.0.0.0:$PORT wsgi:app`
- Health Check Path: `/healthz`
- 영구 디스크를 사용하는 경우 Mount Path `/var/data`, `DB_PATH=/var/data/school_team_match.db`

SQLite를 계속 사용하는 경우 데이터 보존에는 영구 디스크가 필요합니다. 디스크 없는 임시 파일시스템에서는
재배포/재시작 시 기록을 잃을 수 있으므로 학교 실사용 용도로 배포하지 마세요.
Render 영구 디스크는 유료 서비스가 필요하므로 비용 확인 후 선택하세요.
공개 주소는 배포 후 Render가 발급하는 `https://서비스이름.onrender.com`입니다.

## 무료 운영: Render + Supabase PostgreSQL

Render 웹 서비스는 기존 Free 플랜을 유지하고, DB만 Supabase Free 프로젝트를 사용합니다.
`DATABASE_URL`이 설정되면 PostgreSQL을 사용하고, 없으면 로컬 개발용 SQLite를 사용합니다.
기존 SQLite 파일이 PostgreSQL로 자동 복사되지는 않습니다.

1. Supabase에서 **Free 조직**에 `careermate-school` 프로젝트를 생성합니다.
2. 프로젝트 **Connect → Session pooler → URI**에서 포트 5432 연결 주소를 확인합니다.
3. Render 서비스 **Environment**에 `DATABASE_URL`을 설정합니다. 비밀번호가 들어 있는
   주소이므로 GitHub 코드/채팅에 쓰지 말고 환경변수에만 저장합니다. 비밀번호의 특수문자는
   연결 URI에 넣을 때 URL 인코딩해야 합니다.
4. `APP_ENV=production`, `SECRET_KEY`(32자 이상), `ADMIN_PASSWORD`(12자 이상),
   `SEED_DEMO=false`를 설정합니다. 새 DB에서 관리자 아이디는 기본 `admin`입니다.
5. Start Command를 `gunicorn --workers 1 --bind 0.0.0.0:$PORT wsgi:app`으로 변경하고
   Health Check Path를 `/healthz`로 설정합니다.
6. 기존 기록을 유지해야 한다면 **전환 전에 기존 SQLite 파일을 백업**하고 아래 이전 명령을
   실행합니다. 준비가 끝나기 전에는 운영 서버를 재배포하지 않습니다.
7. 로그인·팀 생성 후 재배포하고 기록이 유지되는지 확인합니다.

학생 데이터는 별도 `careermate` 스키마에 저장합니다. Supabase Data API에 이 스키마를
노출하지 마세요. 프런트엔드는 기존 Flask API만 이용하며 DB 비밀번호를 받지 않습니다.
Supabase Free는 현재 500MB DB 및 최대 두 개의 활성 프로젝트를 제공합니다.
일주일 정도 사용하지 않으면 일시 정지될 수 있으며 대시보드에서 재개가 필요합니다.
유료 업그레이드나 Render 디스크는 이 구성에 필요하지 않습니다.

참고: https://supabase.com/pricing
연결: https://supabase.com/docs/guides/database/connecting-to-postgres

### 기존 SQLite 데이터 이전

먼저 원본 파일을 백업하고, 쓰기 작업을 멈춘 시점의 SQLite 복사본을 사용하세요.
`DATABASE_URL`과 운영 환경변수가 설정된 터미널에서:

```bash
python migrate_sqlite.py /absolute/path/to/school_team_match.db
```

대상 DB가 비어 있을 때만 실행됩니다. 원본 파일은 읽기 전용으로 열고, 기존 ID와
비밀번호 해시를 보존하며, 실패하면 DB 이전 전체를 롤백합니다. 이미 초기 관리자나
학생이 있는 대상 DB에는 덮어쓰지 않습니다.

### 개발 검증

```bash
python -m unittest discover -s tests -v
```

빈 로컬 PostgreSQL에서도 같은 검증을 수행할 수 있습니다. 운영 DB를 테스트에 사용하지 마세요.
`CAREERMATE_TEST_DATABASE_URL`을 빈 로컬 테스트 DB 주소로 설정합니다.
