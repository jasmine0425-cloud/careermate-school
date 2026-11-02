"""CareerMate student login ID convention.

ks + admission year (YY) + grade (1-3) + class (01-10) + number (01-40).
No accounts are created by this module.
"""
import re

_PATTERN = re.compile(r"^ks(\d{2})([123])(0[1-9]|10)(0[1-9]|[1-3]\d|40)$")


def make_student_login_id(admission_year, grade, class_number, student_number):
    if not all(isinstance(x, int) and not isinstance(x, bool)
               for x in (admission_year, grade, class_number, student_number)):
        raise ValueError("Student ID fields must be integers")
    if not (2000 <= admission_year <= 2099 and 1 <= grade <= 3
            and 1 <= class_number <= 10 and 1 <= student_number <= 40):
        raise ValueError("Student ID fields are out of range")
    return f"ks{admission_year % 100:02d}{grade}{class_number:02d}{student_number:02d}"


def parse_student_login_id(login_id):
    match = _PATTERN.fullmatch(login_id) if isinstance(login_id, str) else None
    if not match:
        raise ValueError("Invalid CareerMate student login ID")
    year, grade, class_number, student_number = map(int, match.groups())
    return {"admission_year": 2000 + year, "grade": grade,
            "class_number": class_number, "student_number": student_number}


def validate_student_login_id(login_id, admission_year=None):
    parsed = parse_student_login_id(login_id)
    if admission_year is not None and parsed["admission_year"] != admission_year:
        raise ValueError("Admission year mismatch")
    return parsed
