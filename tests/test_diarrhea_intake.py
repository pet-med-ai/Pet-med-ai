"""M7: disposable SQLite/auth routes; exact originals, no external model calls."""
import unittest
from copy import deepcopy
from unittest.mock import patch
import test_consult_update_preview as fixture
import diarrhea_intake as d

main, db, models = fixture.main, fixture.db, fixture.models

def request(species="dog", **answers):
    t = d.get_template(species)
    return {"version": t["version"], "fingerprint": t["fingerprint"], "species": species, "answers": answers}


class DiarrheaIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ConsultUpdatePreviewTests.setUpClass()
        for name in ["client", "owner_headers", "other_headers", "owner_id"]:
            setattr(cls, name, getattr(fixture.ConsultUpdatePreviewTests, name))

    @classmethod
    def tearDownClass(cls):
        fixture.ConsultUpdatePreviewTests.tearDownClass()

    def test_dog_cat_templates_defaults_are_not_normal_or_zero(self):
        for species in ("dog", "cat"):
            t = d.get_template(species)
            self.assertEqual(t["review_status"], "clinical_draft")
            s = d.build_snapshot(request(species))
            self.assertEqual(d.validate_snapshot(s), s)
            self.assertEqual(len(s["sections"][0]["answers"]), 18)
            self.assertTrue(all(a["answer_type"].startswith("diarrhea:unfilled:") for a in s["sections"][0]["answers"]))
            self.assertEqual(d.ai_context(s), "")
            self.assertNotIn("正常", main._structured_snapshot_text(s))
        with self.assertRaises(d.DiarrheaIntakeError): d.get_template("other")

    def test_all_states_remain_distinct_and_text_questions_refuse_absent(self):
        for state in d.STATES:
            s = d.build_snapshot(request(blood={"state": state, "text": "未见便血；来源为医生🐾"}))
            row = next(a for a in s["sections"][0]["answers"] if a["key"] == "blood")
            self.assertIn("状态：" + d.STATES[state], row["answer"])
        for state, text in [("absent", ""), ("observed", " \t\n"), ("normal", "有")]:
            with self.assertRaises(d.DiarrheaIntakeError): d.build_snapshot(request(onset={"state": state, "text": text}))

    def test_inactive_branch_keeps_exact_original_but_cannot_influence_ai(self):
        raw = "  不确定，原分支🐾\r\n<5 & >2 {{literal}}\t尾部  \n"
        r = request(vomiting={"state": "observed", "text": ""}, vomiting_detail={"state": "observed", "text": raw})
        active = d.build_snapshot(r); self.assertIn(raw, d.ai_context(active))
        r["answers"]["vomiting"]["state"] = "absent"
        inactive = d.build_snapshot(r)
        row = next(a for a in inactive["sections"][0]["answers"] if a["key"] == "vomiting_detail")
        self.assertTrue(row["answer"].endswith(raw)); self.assertEqual(row["answer_type"], "diarrhea:observed:0")
        self.assertEqual(d.ai_context(inactive), "")
        self.assertIn("当前不适用", main._structured_snapshot_text(inactive))

    def test_tampering_version_labels_states_flags_and_bounds_are_rejected(self):
        s = d.build_snapshot(request())
        for edit in [lambda x: x.update(version="diarrhea-intake-v0+old"),
                     lambda x: x.update(label="机器确认正常"), lambda x: x.update(category="other"),
                     lambda x: x["sections"][0]["answers"][0].update(answer_type="diarrhea:unfilled:0"),
                     lambda x: x["sections"][0]["answers"][0].update(label="假题目"),
                     lambda x: x["sections"][0]["answers"].pop()]:
            changed = deepcopy(s); edit(changed)
            with self.assertRaises(d.DiarrheaIntakeError): d.validate_snapshot(changed)
        for answers in [{"unknown": {"state": "unfilled", "text": ""}}, {"notes": {"state": "observed", "text": "x"*6001}},
                        {q["key"]: {"state": "uncertain", "text": "x"*3000} for q in d.get_template("dog")["questions"]}]:
            with self.assertRaises(d.DiarrheaIntakeError): d.build_snapshot(request(**answers))
        self.assertFalse(d.is_diarrhea({}))

    def test_template_and_preview_require_auth_and_do_not_write(self):
        with db.SessionLocal() as session: before = session.query(models.ConsultSession).count()
        for headers, status in [({}, 401), (self.owner_headers, 200)]:
            self.assertEqual(self.client.get("/api/ai/consult/intake/diarrhea?species=dog", headers=headers).status_code, status)
            self.assertEqual(self.client.post("/api/ai/consult/intake/diarrhea/preview", headers=headers, json=request()).status_code, status)
        with db.SessionLocal() as session: self.assertEqual(session.query(models.ConsultSession).count(), before)
        old = request(); old["fingerprint"] = "0"*64
        self.assertEqual(self.client.post("/api/ai/consult/intake/diarrhea/preview", headers=self.owner_headers, json=old).status_code, 409)

    def test_create_routes_use_only_current_observations_for_ai_and_retain_all_states(self):
        s = d.build_snapshot(request(notes={"state": "observed", "text": "医生原文 <5 & {{literal}}🐾"},
                                     vomiting={"state": "absent", "text": "未见"}, blood={"state": "unobservable", "text": "未能观察"}))
        with patch.object(main, "run_agent", return_value={"risk_level": "low"}) as agent:
            response = self.client.post("/api/ai/consult/session", headers=self.owner_headers,
                json={"text": "合成犬腹泻", "species": "dog", "structured_intake_answers": s})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("医生原文", agent.call_args.args[0]); self.assertNotIn("呕吐", agent.call_args.args[0]); self.assertNotIn("便血", agent.call_args.args[0])
        payload = response.json(); self.assertEqual(main._stored_structured_snapshot(payload["answers"][0]), s)
        self.assertEqual(payload["text"], "物种：dog\n合成犬腹泻")
        url = "/api/ai/consult/session/" + payload["session_id"]
        self.assertEqual(self.client.get(url, headers=self.other_headers).status_code, 404)

    def test_invalid_species_and_anonymous_create_fail_before_ai_or_writes(self):
        s = d.build_snapshot(request())
        with patch.object(main, "run_agent") as agent:
            for headers, species, status in [({}, "dog", 401), (self.owner_headers, "cat", 409), (self.owner_headers, "other", 409)]:
                r = self.client.post("/api/ai/consult/session", headers=headers, json={"text": "合成资料", "species": species, "structured_intake_answers": s})
                self.assertEqual(r.status_code, status, r.text)
            agent.assert_not_called()

    def test_ai_failure_never_writes_a_session_and_manual_history_still_saves(self):
        s = d.build_snapshot(request("cat", notes={"state": "observed", "text": "  合成猫原文🐾\n尾部  "}))
        with db.SessionLocal() as session: before = session.query(models.ConsultSession).count()
        with patch.object(main, "run_agent", side_effect=RuntimeError("synthetic AI unavailable")):
            with fixture.TestClient(main.app, raise_server_exceptions=False) as client:
                self.assertEqual(client.post("/api/ai/consult/session", headers=self.owner_headers,
                    json={"text": "合成猫", "species": "cat", "structured_intake_answers": s}).status_code, 500)
        body = {"patient_name": "M7离线合成猫", "species": "cat", "chief_complaint": "原主诉", "history": "原病史\n\n"+main._structured_snapshot_text(s)}
        r = self.client.post("/api/cases", headers=self.owner_headers, json=body)
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual(self.client.get("/api/cases/"+str(r.json()["id"]), headers=self.owner_headers).json()["history"], body["history"])
        with db.SessionLocal() as session: self.assertEqual(session.query(models.ConsultSession).count(), before)

    def test_historical_version_remains_readable_without_new_interpretation(self):
        s = d.build_snapshot(request()); s["version"] = "diarrhea-intake-v0+historic"
        import json
        self.assertEqual(main._stored_structured_snapshot({main.STRUCTURED_SNAPSHOT_KEY: json.dumps(s)}), s)
        self.assertEqual(d.ai_context(s), "")
        with self.assertRaises(fixture.HTTPException if hasattr(fixture, "HTTPException") else Exception): main._clean_structured_snapshot(s)

if __name__ == "__main__": unittest.main()
