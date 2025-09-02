# backend/backup_cases.py
import os, csv
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./app.db"
engine = create_engine(DATABASE_URL, future=True)

OUT = os.getenv("OUT", "cases_export.csv")

SQL = """
SELECT id, patient_name, species, sex, age_info,
       chief_complaint, history, exam_findings,
       analysis, treatment, prognosis, created_at
FROM cases
ORDER BY id DESC
"""

with engine.connect() as conn, open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["id","patient_name","species","sex","age_info",
                "chief_complaint","history","exam_findings",
                "analysis","treatment","prognosis","created_at"])
    for row in conn.execute(text(SQL)):
        w.writerow(list(row))
print(f"Exported to {OUT}")
