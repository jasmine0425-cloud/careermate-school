"""Isolated SQLite API regression tests for the CareerMate security branch.

Run: python -m unittest discover -s tests -v
No production database or external service is accessed.
"""
import importlib.util
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("careermate_app_under_test", ROOT / "app.py")
app_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(app_module)


class CareerMateWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp.name) / "test.db")
        self.patchers = [
            patch.object(app_module, "DB_PATH", self.db_path),
            patch.dict(os.environ, {"ADMIN_PASSWORD": "AdminTestPassword!2026", "ENABLE_DEMO_DATA": "0"}, clear=False),
        ]
        for p in self.patchers:
            p.start()
        app_module.init_db()
        app_module.app.config.update(TESTING=True)
        self.client = app_module.app.test_client()

    def tearDown(self):
        for p in reversed(self.patchers):
            p.stop()
        self.temp.cleanup()

    def login(self, user, password):
        return self.client.post("/api/login", json={"loginId": user, "password": password})

    def add_student(self, login_id, password="StudentPassword!2026"):
        return self.client.post("/api/admin/students", json={
            "loginId": login_id, "name": login_id, "password": password,
            "careerCategory": "AI", "preferredRoles": ["개발"]
        })

    def test_login_and_role_protection(self):
        self.assertEqual(self.client.get("/api/admin/students").status_code, 401)
        self.assertEqual(self.login("admin", "wrong").status_code, 400)
        self.assertEqual(self.login("admin", "AdminTestPassword!2026").status_code, 200)
        self.assertEqual(self.client.get("/api/admin/students").status_code, 200)

    def test_student_creation_and_password_validation(self):
        self.login("admin", "AdminTestPassword!2026")
        self.assertEqual(self.add_student("shortpw", "short").status_code, 400)
        self.assertEqual(self.add_student("studentA").status_code, 200)
        self.assertEqual(self.add_student("studentA").status_code, 400)
        self.client.post("/api/logout")
        self.assertEqual(self.login("studentA", "StudentPassword!2026").status_code, 200)
        self.assertEqual(self.client.get("/api/admin/students").status_code, 403)

    def test_csv_import_skips_weak_password(self):
        self.login("admin", "AdminTestPassword!2026")
        csv_data = ("아이디,이름,초기비밀번호\n"
                    "csvgood,Good,StrongPassword!2026\n"
                    "csvbad,Bad,short\n").encode("utf-8")
        res = self.client.post("/api/admin/students/import-csv",
                               data={"file": (io.BytesIO(csv_data), "students.csv")},
                               content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json["added"], 1)
        self.assertEqual(len(res.json["skipped"]), 1)
        self.client.post("/api/logout")
        self.assertEqual(self.login("csvgood", "StrongPassword!2026").status_code, 200)

    def test_team_creation_and_duplicate_membership(self):
        self.login("admin", "AdminTestPassword!2026")
        self.assertEqual(self.add_student("leader").status_code, 200)
        self.assertEqual(self.add_student("member").status_code, 200)
        activity = self.client.post("/api/activities", json={
            "title": "Test Activity", "minMembers": 2, "maxMembers": 3
        })
        self.assertEqual(activity.status_code, 200)
        aid = activity.json["id"]
        self.client.post("/api/logout")
        self.login("leader", "StudentPassword!2026")
        team = self.client.post("/api/teams", json={
            "activityId": aid, "teamName": "Test Team"
        })
        self.assertEqual(team.status_code, 200)
        self.assertEqual(self.client.post("/api/teams", json={
            "activityId": aid, "teamName": "Duplicate Team"
        }).status_code, 400)
        self.assertEqual(self.client.get("/api/teams").status_code, 200)


if __name__ == "__main__":
    unittest.main()
