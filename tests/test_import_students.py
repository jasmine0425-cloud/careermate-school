"""Non-production checks for private roster importer. No student data stored here."""
import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

class ImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        path=Path(__file__).resolve().parents[1]/'scripts'/'import_students.py'
        spec=importlib.util.spec_from_file_location('private_import',path)
        self.mod=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)
        self.csv=Path(self.tmp.name)/'roster.csv'
        rows=[]
        for grade,count in [(1,304),(2,275),(3,218)]:
            for n in range(count):
                klass=n//40+1;number=n%40+1
                rows.append({'학년':str(grade),'반':str(klass),'번호':str(number),'이름':f'가상학생{grade}-{n}','로그인ID':f'ks{27-grade:02d}{grade}{klass:02d}{number:02d}'})
        with self.csv.open('w',encoding='utf-8',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=['학년','반','번호','이름','로그인ID']);writer.writeheader();writer.writerows(rows)

    def tearDown(self): self.tmp.cleanup()

    def test_797_unique_ids(self):
        rows=self.mod.load(self.csv)
        self.assertEqual(len(rows),797)
        self.assertEqual(len({r['로그인ID'] for r in rows}),797)

    def test_duplicate_rejected(self):
        with self.csv.open('r',encoding='utf-8',newline='') as f: rows=list(csv.DictReader(f))
        rows[1]['로그인ID']=rows[0]['로그인ID']
        with self.csv.open('w',encoding='utf-8',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)
        with self.assertRaises(ValueError):self.mod.load(self.csv)

if __name__=='__main__': unittest.main()
