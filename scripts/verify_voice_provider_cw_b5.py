"""Explicit, synthetic-only live verification. Never used by CI or startup.

Requires pre-existing isolated DB/schema and protected Tencent credentials.
No migrations, accounts, resource purchases or automatic retries are performed.
"""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


async def run(args):
    import speech_transcription as provider
    import speech_budget as budget
    provider.ensure_development()
    url = urlparse(os.environ.get("DATABASE_URL", ""))
    if url.scheme not in {"sqlite", "postgresql"} or (url.scheme == "postgresql" and url.hostname not in {"127.0.0.1", "localhost"}) or "cwb5" not in url.path.lower():
        raise SystemExit("Use a pre-existing local cwb5 synthetic database; no production database is permitted.")
    if not args.synthetic_only:
        raise SystemExit("Explicit --synthetic-only is required.")
    if args.initialize_ledger:
        budget.initialize_ledger()
        print("Initialized fixed CW-B5 ledger once; no ASR request sent.")
        return
    if not args.audio_dir or not args.output:
        raise SystemExit("Supply --audio-dir and --output; only pre-generated fictional WAV fixtures are accepted.")
    provider.ensure_enabled()
    budget.budget_status()  # Missing ledger never initializes automatically.
    cases = json.loads((ROOT / "tests/fixtures/voice_cw_b5_cases.json").read_text())
    out = Path(args.output)
    if out.exists():
        raise SystemExit("Evidence output already exists; inspect it and the ledger before any manual retry.")
    audios = []
    for case in cases:
        audio = (Path(args.audio_dir) / (case["id"] + ".wav")).read_bytes()
        provider.validate_wav(audio); audios.append(audio)
    evidence = {"batch": budget.BATCH, "synthetic_only": True, "results": [], "status": "in_progress"}
    out.parent.mkdir(parents=True, exist_ok=True)
    def checkpoint():
        out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    checkpoint()
    for case, audio in zip(cases, audios):
        # Deterministic fixed fixture key: rerunning this tool cannot resend it.
        rid = hashlib.sha256((budget.BATCH + case["id"]).encode()).hexdigest()[:32]
        binding = {"session_id": "synthetic-live-verification", "fixture": case["id"]}
        entry = {"id": case["id"], "request_id": rid, "reference": case["text"], "condition": case["condition"]}
        start = time.monotonic()
        try:
            budget.reserve(rid, "synthetic-verifier", binding, hashlib.sha256(audio).hexdigest(), provider.validate_wav(audio))
        except provider.SpeechError as error:
            entry["error"] = error.code; evidence["results"].append(entry); evidence["status"] = "stopped_before_egress"; checkpoint(); break
        try:
            result = await provider.recognize(audio, rid)
            budget.finish(rid, "synthetic-verifier", "recognized", transcript_hash=budget.digest(result["text"]))
            entry.update(text=result["text"], provider_request_id=result["provider_request_id"], missing_exact_terms=[word for word in case["terms"] if word not in result["text"]], review="manual_error_classification_required")
        except provider.SpeechError as error:
            budget.finish(rid, "synthetic-verifier", error.code); entry["error"] = error.code
        entry["elapsed_seconds"] = round(time.monotonic() - start, 3)
        entry["reserved_fen"] = 1
        evidence["results"].append(entry); evidence["meter"] = budget.budget_status(); checkpoint()
        if "error" in entry:
            evidence["status"] = "stopped_after_error_no_retry"; checkpoint(); break
    else:
        evidence["status"] = "service_calls_complete_doctor_review_pending"; checkpoint()
    print(json.dumps({"status": evidence["status"], "attempts": len(evidence["results"]), "meter": budget.budget_status()}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic-only", action="store_true")
    parser.add_argument("--initialize-ledger", action="store_true")
    parser.add_argument("--audio-dir")
    parser.add_argument("--output")
    asyncio.run(run(parser.parse_args()))
