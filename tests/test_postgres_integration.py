"""End-to-end PostgreSQL API tests against an isolated disposable database.

Only runs when CAREERMATE_PG_TEST_URL is set. Never point this at Supabase
or any database containing real records: init_db creates an admin account.
"""
import os
import unittest
from unittest.mock import patch

@unittest.skipUnless(os.environ.get("CAREERMATE_PG_TEST_URL"), "Disposable PostgreSQL URL not configured")
class PostgreSQLWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import app as module
        cls.module = module
        cls.patchers = [
            patch.dict(os.environ, {
                "DATABASE_URL": os.environ["CAREERMATE_PG_TEST_URL"],
                "ADMIN_PASSWORD": "DisposableAdminPassword!2026",
                "ENABLE_DEMO_DATA": "0",
            }),
        ]
        for p in cls.patchers:
            p.start()
        module.init_db()
        module.app.config.update(TESTING=True)

    @classmethod
    def tearDownClass(cls):
        for p in reversed(cls.patchers):
            p.stop()

    def test_login_student_and_team(self):
        client = self.module.app.test_client()
        self.assertEqual(client.post("/api/login", json={
            "loginId": "admin", "password": "DisposableAdminPassword!2026"
        }).status_code, 200)
        response = client.post("/api/admin/students", json={
            "loginId": "pgstudent", "name": "PG Student",
            "password": "DisposableStudentPassword!2026", "careerCategory": "AI"
        })
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        activity = client.post("/api/activities", json={
            "title": "Disposable PostgreSQL Activity", "minMembers": 2, "maxMembers": 3
        })
        self.assertEqual(activity.status_code, 200, activity.get_data(as_text=True))
        aid = activity.json["id"]
        client.post("/api/logout")
        self.assertEqual(client.post("/api/login", json={
            "loginId": "pgstudent", "password": "DisposableStudentPassword!2026"
        }).status_code, 200)
        team = client.post("/api/teams", json={
            "activityId": aid, "teamName": "Disposable PostgreSQL Team"
        })
        self.assertEqual(team.status_code, 200, team.get_data(as_text=True))
        duplicate = client.post("/api/teams", json={
            "activityId": aid, "teamName": "Duplicate Team"
        })
        self.assertEqual(duplicate.status_code, 400, duplicate.get_data(as_text=True))
        self.assertEqual(client.get("/api/teams").status_code, 200)

if __name__ == "__main__":
    unittest.main()
