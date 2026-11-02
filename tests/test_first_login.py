import os
import tempfile
import unittest
from werkzeug.security import generate_password_hash

os.environ.pop('DATABASE_URL', None)
os.environ.pop('ENABLE_DEMO_DATA', None)
from app import app, init_db

class FirstLoginTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        app.config.update(TESTING=True, SECRET_KEY='test-only')
        import app as module
        self.module = module
        self.original = module.DB_PATH
        module.DB_PATH = os.path.join(self.tmp.name, 'app.db')
        init_db()
        con = module.db()
        con.execute('INSERT INTO users(loginId,passwordHash,role,name,mustChangePassword,createdAt) VALUES(?,?,?,?,?,?)',
                    ('ks2610101', generate_password_hash('Temporary-Pass-123!'), 'STUDENT', '테스트학생', 1, module.now()))
        con.commit()
        con.close()
        self.client = app.test_client()

    def tearDown(self):
        self.module.DB_PATH = self.original
        self.tmp.cleanup()

    def test_password_change_required(self):
        login = self.client.post('/api/login', json={'loginId':'ks2610101','password':'Temporary-Pass-123!'})
        self.assertEqual(login.status_code, 200)
        self.assertTrue(login.json['mustChangePassword'])
        blocked = self.client.get('/api/my-teams')
        self.assertEqual(blocked.status_code, 403)
        self.assertEqual(self.client.post('/api/change-password', json={'currentPassword':'wrong','newPassword':'New-Password-12345!'}).status_code,403)
        changed = self.client.post('/api/change-password',json={'currentPassword':'Temporary-Pass-123!','newPassword':'New-Password-12345!'})
        self.assertEqual(changed.status_code, 200)
        self.assertFalse(self.client.get('/api/me').json['mustChangePassword'])
        self.client.post('/api/logout')
        self.assertEqual(self.client.post('/api/login',json={'loginId':'ks2610101','password':'Temporary-Pass-123!'}).status_code,400)
        self.assertEqual(self.client.post('/api/login',json={'loginId':'ks2610101','password':'New-Password-12345!'}).status_code,200)

if __name__ == '__main__': unittest.main()
