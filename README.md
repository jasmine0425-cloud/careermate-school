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
