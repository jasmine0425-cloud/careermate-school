import unittest
from student_ids import make_student_login_id, parse_student_login_id

class StudentIdTests(unittest.TestCase):
    def test_examples(self):
        self.assertEqual(make_student_login_id(2026, 1, 1, 1), "ks2610101")
        self.assertEqual(make_student_login_id(2026, 1, 10, 1), "ks2611001")
        self.assertEqual(make_student_login_id(2025, 2, 1, 1), "ks2520101")
        self.assertEqual(make_student_login_id(2024, 3, 10, 35), "ks2431035")

    def test_ordering(self):
        ids = [make_student_login_id(2026, 1, c, n)
               for c in range(1, 11) for n in range(1, 31)]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(len(ids), len(set(ids)))

    def test_roundtrip(self):
        self.assertEqual(parse_student_login_id("ks2610101"), {
            "admission_year": 2026, "grade": 1,
            "class_number": 1, "student_number": 1
        })

    def test_invalid(self):
        for args in [(2026,1,0,1), (2026,1,11,1), (2026,1,1,0), (2026,4,1,1)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                make_student_login_id(*args)
        for value in ["ks2611101", "ks2610100", "ks2610001", "ks261010", "admin"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_student_login_id(value)

if __name__ == "__main__":
    unittest.main()
