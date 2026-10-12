"""Persistent reservations on isolated SQLite, including thread contention."""
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from uuid import uuid4
import unittest
from test_speech_transcription import SpeechFixture, db, models, budget, provider


class BudgetTests(SpeechFixture):
    def reserve(self, rid=None):
        return budget.reserve(rid or uuid4().hex, self.owner_id, self.binding, "f" * 64, 1)

    def test_same_request_concurrent_claim_and_restart(self):
        rid = uuid4().hex
        def run(_):
            try: self.reserve(rid); return "sent"
            except provider.SpeechError as e: return e.code
        with ThreadPoolExecutor(max_workers=8) as pool: results = list(pool.map(run, range(16)))
        self.assertEqual(results.count("sent"), 1)
        db.engine.dispose()
        self.assertEqual(budget.budget_status()["attempts"], 1)
        with self.assertRaises(provider.SpeechError): self.reserve(rid)

    def test_one_hundred_cap_concurrently_and_after_restart(self):
        def run(_):
            try: self.reserve(); return True
            except provider.SpeechError: return False
        with ThreadPoolExecutor(max_workers=8) as pool: results = list(pool.map(run, range(110)))
        self.assertEqual(sum(results), 100)
        db.engine.dispose(); self.assertEqual(budget.budget_status()["reserved_fen"], 100)
        with self.assertRaises(provider.SpeechError) as raised: self.reserve()
        self.assertEqual(raised.exception.code, "batch_budget_exhausted")

    def test_missing_invalid_or_holey_ledger_never_auto_initializes(self):
        self.reserve(); self.reserve()
        with db.SessionLocal() as session:
            row = session.get(models.AuditLog, budget.key("anchor")); row.extra_data = {}; session.commit()
        with self.assertRaises(provider.SpeechError): self.reserve()
        with db.SessionLocal() as session:
            row = session.get(models.AuditLog, budget.key("anchor")); row.extra_data = budget.POLICY
            entry = session.query(models.AuditLog).filter_by(event_type="speech_reserve").first(); session.delete(entry); session.commit()
        with self.assertRaises(provider.SpeechError): self.reserve()
        with self.assertRaises(provider.SpeechError): budget.initialize_ledger()
        with db.SessionLocal() as session:
            session.delete(session.get(models.AuditLog, budget.key("anchor"))); session.commit()
        with self.assertRaises(provider.SpeechError): self.reserve()

    def test_failure_keeps_spent_attempt_and_cannot_finish_twice(self):
        rid = uuid4().hex; self.reserve(rid)
        budget.finish(rid, self.owner_id, "result_unknown")
        with self.assertRaises(provider.SpeechError): budget.finish(rid, self.owner_id, "recognized")
        self.assertEqual(budget.budget_status()["attempts"], 1)


if __name__ == "__main__": unittest.main(verbosity=2)
