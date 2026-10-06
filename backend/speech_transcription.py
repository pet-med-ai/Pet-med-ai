"""Bounded Tencent SentenceRecognition adapter. No audio persistence or retries."""
import asyncio
import base64
from datetime import datetime, timezone
import hashlib
import hmac
import io
import json
import os
import time
import wave

import httpx

MAX_AUDIO_BYTES = 2 * 1024 * 1024
MAX_SECONDS = 30
PROVIDER = "tencent-sentence-16k_zh-2019-06-14"
ENDPOINT = "https://asr.tencentcloudapi.com"


class SpeechError(Exception):
    def __init__(self, code, status=503):
        self.code, self.status = code, status
        super().__init__(code)  # Never propagate vendor messages, payloads or secrets.


def ensure_development():
    if os.getenv("ENVIRONMENT") not in {"test", "development"} or os.getenv("RENDER", "").lower() == "true":
        raise SpeechError("development_only")


def ensure_enabled():
    ensure_development()
    if os.getenv("SPEECH_ENABLED") != "1" or os.getenv("SPEECH_SYNTHETIC_ONLY") != "1":
        raise SpeechError("speech_disabled")
    # A price review is explicit; no free-quota assumptions or configurable caps.
    if os.getenv("SPEECH_REVIEWED_CNY_PER_1000") != "3.20":
        raise SpeechError("price_review_required")
    if not all(os.getenv(k) for k in ("TENCENTCLOUD_SECRET_ID", "TENCENTCLOUD_SECRET_KEY")):
        raise SpeechError("credentials_unavailable")


def validate_wav(audio):
    if not 44 <= len(audio) <= MAX_AUDIO_BYTES:
        raise SpeechError("audio_size", 422)
    try:
        if audio[:4] != b"RIFF" or int.from_bytes(audio[4:8], "little") + 8 != len(audio):
            raise ValueError()
        with wave.open(io.BytesIO(audio), "rb") as wav:
            if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getcomptype()) != (1, 2, 16000, "NONE"):
                raise ValueError()
            frames = wav.getnframes()
            if not 1600 <= frames <= MAX_SECONDS * 16000 or len(wav.readframes(frames)) != frames * 2:
                raise ValueError()
        return frames / 16000
    except (wave.Error, EOFError, ValueError):
        raise SpeechError("audio_format_or_duration", 422) from None


def signed_request(audio, request_id, *, timestamp=None):
    """TC3 v3 canonical signing, fixed host/action, body-source audio only."""
    timestamp = int(time.time()) if timestamp is None else timestamp
    body = json.dumps({"ProjectId": 0, "SubServiceType": 2, "EngSerViceType": "16k_zh",
                       "SourceType": 1, "VoiceFormat": "wav", "UsrAudioKey": request_id,
                       "Data": base64.b64encode(audio).decode(), "DataLen": len(audio),
                       "FilterDirty": 0, "FilterModal": 0, "FilterPunc": 0, "ConvertNumMode": 0},
                      separators=(",", ":")).encode()
    host, content_type = "asr.tencentcloudapi.com", "application/json; charset=utf-8"
    signed = "content-type;host;x-tc-action"
    canonical = "POST\n/\n\ncontent-type:" + content_type + "\nhost:" + host + "\nx-tc-action:sentencerecognition\n\n" + signed + "\n" + hashlib.sha256(body).hexdigest()
    day = datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%d")
    scope = day + "/asr/tc3_request"
    to_sign = "TC3-HMAC-SHA256\n" + str(timestamp) + "\n" + scope + "\n" + hashlib.sha256(canonical.encode()).hexdigest()
    key = ("TC3" + os.environ["TENCENTCLOUD_SECRET_KEY"]).encode()
    for part in (day, "asr", "tc3_request"):
        key = hmac.new(key, part.encode(), hashlib.sha256).digest()
    signature = hmac.new(key, to_sign.encode(), hashlib.sha256).hexdigest()
    headers = {"Host": host, "Content-Type": content_type, "X-TC-Action": "SentenceRecognition",
               "X-TC-Version": "2019-06-14", "X-TC-Timestamp": str(timestamp),
               "Authorization": "TC3-HMAC-SHA256 Credential=" + os.environ["TENCENTCLOUD_SECRET_ID"] + "/" + scope + ", SignedHeaders=" + signed + ", Signature=" + signature}
    if os.getenv("TENCENTCLOUD_TOKEN"):
        headers["X-TC-Token"] = os.environ["TENCENTCLOUD_TOKEN"]
    return body, headers


async def recognize(audio, request_id):
    ensure_enabled()
    validate_wav(audio)
    body, headers = signed_request(audio, request_id)
    try:
        # Total deadline also bounds a slow streaming response. Neither redirects
        # nor SDK/proxy retries can repeat a charged request.
        async with asyncio.timeout(45):
            async with httpx.AsyncClient(timeout=40, follow_redirects=False, trust_env=False) as client:
                async with client.stream("POST", ENDPOINT, content=body, headers=headers) as response:
                    if response.status_code != 200:
                        raise SpeechError("provider_unavailable")
                    chunks, size = [], 0
                    async for chunk in response.aiter_bytes():
                        size += len(chunk)
                        if size > 128 * 1024:
                            raise SpeechError("provider_invalid_response")
                        chunks.append(chunk)
                    result = json.loads(b"".join(chunks))["Response"]
        if not isinstance(result, dict):
            raise SpeechError("provider_invalid_response")
        if "Error" in result:
            if not isinstance(result["Error"], dict):
                raise SpeechError("provider_invalid_response")
            code = str(result["Error"].get("Code", ""))
            if code.startswith(("RequestLimitExceeded", "LimitExceeded")):
                raise SpeechError("provider_rate_limit", 429)
            if any(x in code for x in ("NoAmount", "NoFreeAmount", "ServiceIsolate")):
                raise SpeechError("provider_quota_exhausted", 503)
            raise SpeechError("provider_rejected")
        transcript = result.get("Result")
        rid = result.get("RequestId")
        if not isinstance(transcript, str) or not transcript.strip() or len(transcript) > 4000 or not isinstance(rid, str) or len(rid) > 100:
            raise SpeechError("provider_invalid_response")
        return {"text": transcript, "provider_request_id": rid, "provider": PROVIDER}
    except (TimeoutError, httpx.TimeoutException):
        raise SpeechError("provider_timeout_unknown", 504) from None
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        raise SpeechError("provider_result_unknown") from None
    finally:
        audio = body = headers = None
