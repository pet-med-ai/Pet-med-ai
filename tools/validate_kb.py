import json, sys, pathlib
from jsonschema import validate, Draft202012Validator

root = pathlib.Path(__file__).resolve().parents[1]
schema = json.load(open(root/"knowledge-base/schema/symptom_kb.schema.json"))

def check(p):
    data = json.load(open(p))
    Draft202012Validator.check_schema(schema)
    validate(data, schema)
    print(f"OK: {p}")

if __name__ == "__main__":
    files = [
        root/"knowledge-base/dermatology/pruritus.json",
        root/"knowledge-base/gastroenterology/diarrhea.json",
        root/"knowledge-base/respiratory/cough.json",
    ]
    for f in files:
        check(f)

