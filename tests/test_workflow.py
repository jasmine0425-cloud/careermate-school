"""Run with python -m unittest discover -s tests.

CAREERMATE_TEST_DATABASE_URL optionally selects an EMPTY local PostgreSQL DB.
Never point tests at the production database.
"""
import io
import os
import tempfile
import unittest
from urllib.parse import urlsplit

test_url = os.environ.get('CAREERMATE_TEST_DATABASE_URL', '')
if test_url and urlsplit(test_url).hostname not in ('localhost', '127.0.0.1', '::1'):
    raise RuntimeError('테스트는 로컬 DB에만 실행할 수 있습니다.')
_tmp = tempfile.TemporaryDirectory()
os.environ.update(APP_ENV='production', SECRET_KEY='temporary-test-secret-' * 3,
                  ADMIN_PASSWORD='temporary-test-password!', SEED_DEMO='false',
                  DB_PATH=_tmp.name + '/data/test.db',
                  DATABASE_URL=os.environ.get('CAREERMATE_TEST_DATABASE_URL', ''))
import app as application


class SchoolWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        application.init_db()
        application.app.testing = True

    def test_team_matching_and_persistence(self):
        admin = application.app.test_client()
        login = admin.post('/api/login', json={'loginId': 'admin',
                            'password': os.environ['ADMIN_PASSWORD']})
        self.assertEqual(login.status_code, 200)
        self.assertIn('Secure', login.headers['Set-Cookie'])
        self.assertNotIn('데모 계정', admin.get('/').text)
        self.assertEqual(admin.get('/api/admin/stats').json['students'], 0)
        activity = admin.post('/api/activities', json={
            'title': '진로 융합 테스트', 'minMembers': 2, 'maxMembers': 2}).json['id']
        clients = {}
        for username in ('first', 'second', 'third'):
            response = admin.post('/api/admin/students', json={
                'loginId': username, 'name': username, 'password': 'test-password',
                'careerCategory': 'AI', 'interests': ['Python'],
                'preferredRoles': ['개발']})
            self.assertEqual(response.status_code, 200)
            client = application.app.test_client()
            self.assertEqual(client.post('/api/login', json={
                'loginId': username, 'password': 'test-password'}).status_code, 200)
            clients[username] = client
        # Duplicate errors must not abort subsequent CSV rows in PostgreSQL.
        csv = b'loginId,name,password\nfirst,duplicate,test-password\nfourth,fourth,test-password\n'
        imported = admin.post('/api/admin/students/import-csv', data={
            'file': (io.BytesIO(csv), 'students.csv')})
        self.assertEqual(imported.status_code, 200)
        self.assertEqual(imported.json['added'], 1, imported.json)
        self.assertEqual(len(imported.json['skipped']), 1)
        students = admin.get('/api/admin/students').json
        second = next(s['id'] for s in students if s['loginId'] == 'second')
        third = next(s['id'] for s in students if s['loginId'] == 'third')
        team = clients['first'].post('/api/teams', json={
            'activityId': activity, 'teamName': '함께하는 팀',
            'inviteUserIds': [second]}).json['teamId']
        # Reinviting exercises recovery from the unique membership constraint.
        self.assertEqual(clients['first'].post(f'/api/teams/{team}/invite',
                         json={'userId': second}).status_code, 200)
        self.assertEqual(clients['first'].post(f'/api/teams/{team}/recruitment',
                         json={'requiredFields': ['AI'], 'requiredRoles': ['개발']}).status_code, 200)
        self.assertEqual(clients['first'].post(f'/api/teams/{team}/recruitment',
                         json={'description': '수정한 모집글'}).status_code, 200)
        self.assertIsInstance(clients['first'].get(f'/api/recommendations/team/{team}').json, list)
        membership = next(m['membershipId'] for m in
                          clients['second'].get(f'/api/teams/{team}').json['members']
                          if m['id'] == second)
        self.assertEqual(clients['second'].post(
            f'/api/memberships/{membership}/respond', json={'accept': True}).status_code, 200)
        self.assertEqual(clients['first'].get(f'/api/teams/{team}').json['status'], 'COMPLETE')
        self.assertEqual(clients['first'].post(f'/api/teams/{team}/invite',
                         json={'userId': third}).status_code, 400)
        self.assertEqual(clients['second'].post('/api/teams', json={
            'activityId': activity, 'teamName': '중복 가입'}).status_code, 400)
        self.assertEqual(clients['second'].get('/api/admin/stats').status_code, 403)
        self.assertEqual(application.app.test_client().get('/api/activities').status_code, 401)
        application.init_db()
        self.assertEqual(admin.get('/api/admin/stats').json['students'], 4)
        self.assertEqual(admin.get('/api/admin/stats').json['teams'], 1)
        self.assertEqual(admin.get('/healthz').status_code, 200)


if __name__ == '__main__':
    unittest.main()
