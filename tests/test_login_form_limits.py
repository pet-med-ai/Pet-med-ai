"""Real login/JWT and bounded parser regressions, synthetic SQLite only.

Run in its own process: python tests/test_login_form_limits.py
The shared fixture clears inherited environment and denies network, subprocesses
and any database other than its disposable synthetic SQLite file.
"""
import asyncio
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

import test_consult_update_preview as fixture
import auth_jwt
import login_form_limits as limits
from sqlalchemy import event

main, db = fixture.main, fixture.db
CONTENT_TYPE = (b"content-type", b"application/x-www-form-urlencoded")
LOGIN = {"username": "owner@example.com", "password": "synthetic-test-password"}


def scope(headers, path="/auth/login", method="POST"):
    return {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
            "method": method, "scheme": "http", "path": path,
            "raw_path": path.encode(), "query_string": b"", "root_path": "",
            "headers": [(key.lower(), value) for key, value in headers],
            "client": ("127.0.0.1", 1), "server": ("testserver", 80)}


async def raw_request(chunks, headers=None, *, disconnect=False, delay=0):
    messages, reads = [], 0
    chunks = list(chunks)

    async def receive():
        nonlocal reads
        reads += 1
        if delay:
            await asyncio.sleep(delay)
        if not chunks:
            return {"type": "http.disconnect"}
        part = chunks.pop(0)
        return {"type": "http.request", "body": part,
                "more_body": bool(chunks) or disconnect}

    async def send(message):
        messages.append(message)

    await main.app(scope([CONTENT_TYPE] if headers is None else headers), receive, send)
    starts = [item for item in messages if item["type"] == "http.response.start"]
    assert len(starts) == 1, messages
    body = b"".join(item.get("body", b"") for item in messages if item["type"] == "http.response.body")
    return starts[0]["status"], body, reads


class LoginFormLimitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ConsultUpdatePreviewTests.setUpClass()
        cls.client = fixture.ConsultUpdatePreviewTests.client

    @classmethod
    def tearDownClass(cls):
        fixture.ConsultUpdatePreviewTests.tearDownClass()

    def rejected(self, chunks, expected, **kwargs):
        queries = []

        def track(*args):
            queries.append(True)

        event.listen(db.engine, "before_cursor_execute", track)
        try:
            with patch.object(auth_jwt, "verify_user") as verify:
                result = asyncio.run(raw_request(chunks, **kwargs))
                self.assertEqual(result[0], expected, result[:2])
                verify.assert_not_called()
                self.assertEqual(queries, [], "Rejected form reached the database")
                self.assertNotIn(LOGIN["password"].encode(), result[1])
                return result
        finally:
            event.remove(db.engine, "before_cursor_execute", track)

    def assert_token(self, response):
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(data["token_type"], "bearer")
        response = self.client.get("/api/cases", headers={"Authorization": "Bearer " + data["access_token"]})
        self.assertEqual(response.status_code, 200, response.text)

    def test_urlencoded_login_and_protected_read(self):
        self.assert_token(self.client.post("/auth/login", data=LOGIN))

    def test_browser_multipart_login_and_protected_read(self):
        self.assert_token(self.client.post("/auth/login", files={key: (None, value) for key, value in LOGIN.items()}))

    def test_unicode_and_reserved_password_characters_roundtrip(self):
        data = {"email": "encoded@example.com", "password": "合成+&=% 密码"}
        self.assertEqual(self.client.post("/auth/signup", json=data).status_code, 200)
        login = {"username": data["email"], "password": data["password"]}
        self.assert_token(self.client.post("/auth/login", data=login))
        self.assert_token(self.client.post("/auth/login", files={k: (None, v) for k, v in login.items()}))

    def test_bad_password_remains_401(self):
        for kwargs in ({"data": {**LOGIN, "password": "incorrect"}},
                       {"files": {k: (None, v) for k, v in {**LOGIN, "password": "incorrect"}.items()}}):
            self.assertEqual(self.client.post("/auth/login", **kwargs).status_code, 401)

    def test_missing_required_fields_remain_422(self):
        for body in ({}, {"username": LOGIN["username"]}, {"password": LOGIN["password"]}):
            self.rejected([urlencode(body).encode()], 422)

    def test_six_oauth_fields_and_grant_validation(self):
        data = {**LOGIN, "grant_type": "password", "scope": "read write", "client_id": "synthetic", "client_secret": "synthetic"}
        self.assert_token(self.client.post("/auth/login", data=data))
        self.assert_token(self.client.post("/auth/login", files={k: (None, v) for k, v in data.items()}))
        self.rejected([urlencode({**LOGIN, "grant_type": "bad"}).encode()], 422)

    def test_actual_body_limit_exactly_16_kib(self):
        body = urlencode(LOGIN).encode()
        for index in range(4):
            name = f"x{index}".encode()
            size = min(limits.MAX_LOGIN_FIELD_BYTES - len(name), limits.MAX_LOGIN_BODY_BYTES - len(body) - len(name) - 2)
            body += b"&" + name + b"=" + b"x" * size
        self.assertEqual(len(body), limits.MAX_LOGIN_BODY_BYTES)
        status, _, _ = asyncio.run(raw_request([body]))
        self.assertEqual(status, 200)
        self.rejected([body + b"x"], 413)

    def test_oversized_single_chunk_stops_before_parser(self):
        with patch("starlette.formparsers.FormParser.parse", side_effect=AssertionError("parser reached")):
            result = self.rejected([b"x" * (limits.MAX_LOGIN_BODY_BYTES + 1), b"not consumed"], 413)
            self.assertEqual(result[2], 1)

    def test_oversized_multichunk_stops_at_limit(self):
        chunks = [b"x" * 1024] * 18
        result = self.rejected(chunks, 413)
        self.assertEqual(result[2], 17)

    def test_missing_length_and_many_small_chunks(self):
        body = urlencode(LOGIN).encode()
        status, _, reads = asyncio.run(raw_request([body[i:i + 1] for i in range(len(body))]))
        self.assertEqual(status, 200)
        self.assertEqual(reads, len(body))

    def test_understated_length_cannot_bypass_cap(self):
        self.rejected([b"x" * (limits.MAX_LOGIN_BODY_BYTES + 1)], 413,
                      headers=[CONTENT_TYPE, (b"content-length", b"1")])

    def test_oversized_declared_length_does_not_read(self):
        for value in (b"16385", b"9" * 5000):
            result = self.rejected([b"unused"], 413, headers=[CONTENT_TYPE, (b"content-length", value)])
            self.assertEqual(result[2], 0)

    def test_malformed_and_duplicate_lengths_do_not_read(self):
        for value in (b"-1", b"+4", b"1.0", b"abc", b"", b"1,1", "１２".encode()):
            result = self.rejected([b"unused"], 400, headers=[CONTENT_TYPE, (b"content-length", value)])
            self.assertEqual(result[2], 0)
        result = self.rejected([b"unused"], 400, headers=[CONTENT_TYPE, (b"content-length", b"1"), (b"content-length", b"1")])
        self.assertEqual(result[2], 0)

    def test_inconsistent_bounded_length_is_400(self):
        body = urlencode(LOGIN).encode()
        for length in (len(body) - 1, len(body) + 1):
            self.rejected([body], 400, headers=[CONTENT_TYPE, (b"content-length", str(length).encode())])

    def test_declared_length_matches_and_identity_encoding(self):
        body = urlencode(LOGIN).encode()
        status, _, _ = asyncio.run(raw_request([body], [CONTENT_TYPE, (b"content-length", str(len(body)).encode()),
                                                       (b"content-encoding", b"identity")]))
        self.assertEqual(status, 200)

    def test_unsupported_and_ambiguous_content_type_do_not_read(self):
        for headers in ([], [(b"content-type", b"application/json")], [CONTENT_TYPE, CONTENT_TYPE]):
            self.assertEqual(self.rejected([b"unused"], 415, headers=headers)[2], 0)

    def test_encoded_body_is_rejected_before_read(self):
        for value in (b"gzip", b"br", b"identity, gzip"):
            self.assertEqual(self.rejected([b"unused"], 415, headers=[CONTENT_TYPE, (b"content-encoding", value)])[2], 0)

    def test_urlencoded_excess_fields_with_small_body(self):
        for body in (b"&".join([b"x=v"] * 7), b"&".join([b"x=v"] * 1000)):
            self.rejected([body], 400)

    def test_urlencoded_field_name_and_value_are_bounded(self):
        for body in (b"x=" + b"v" * 4096, b"x" * 4097 + b"=v"):
            self.rejected([body], 400)

    def test_urlencoded_field_exact_size_accepted(self):
        data = {**LOGIN, "scope": "x" * (limits.MAX_LOGIN_FIELD_BYTES - len("scope"))}
        self.assert_token(self.client.post("/auth/login", data=data))

    def test_multipart_field_count_size_and_files(self):
        for files in ([('x', (None, 'v'))] * 7,
                      [("x", (None, "x" * 4097))],
                      [("file", ("synthetic.txt", b"synthetic"))]):
            # Build the multipart body locally, then exercise raw ASGI with DB/verify spies.
            request = self.client.build_request("POST", "/auth/login", files=files)
            self.rejected([request.read()], 400, headers=request.headers.raw)

    def test_multipart_field_exact_size_accepted(self):
        data = {**LOGIN, "scope": "x" * limits.MAX_LOGIN_FIELD_BYTES}
        self.assert_token(self.client.post("/auth/login", files={k: (None, v) for k, v in data.items()}))

    def test_malformed_multipart_is_400_not_500(self):
        for content_type, body in ((b"multipart/form-data", b"abc"),
                                   (b"multipart/form-data; boundary=x", b"invalid")):
            self.rejected([body], 400, headers=[(b"content-type", content_type)])

    def test_incomplete_stream_does_not_authenticate(self):
        self.rejected([urlencode(LOGIN).encode()], 400, disconnect=True)

    def test_slow_body_times_out_without_authentication(self):
        with patch.object(limits, "LOGIN_BODY_TIMEOUT_SECONDS", .01):
            self.rejected([b"x=y"], 408, delay=.05)

    def test_other_routes_and_cors_keep_existing_behavior(self):
        self.assertEqual(self.client.get("/healthz").json(), {"ok": True})
        self.assertEqual(self.client.get("/auth/login").status_code, 405)
        response = self.client.options("/auth/login", headers={"Origin": "http://localhost:5173",
                                        "Access-Control-Request-Method": "POST"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], "http://localhost:5173")
        response = self.client.post("/auth/login", content=b"x" * 16385,
                                    headers={"Content-Type": "application/x-www-form-urlencoded", "Origin": "http://localhost:5173"})
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.headers["access-control-allow-origin"], "http://localhost:5173")

    def test_signup_not_subject_to_login_body_cap(self):
        response = self.client.post("/auth/signup", json={"email": "signup@example.com",
                                    "password": "synthetic-password", "full_name": "x" * 17000})
        self.assertEqual(response.status_code, 200, response.text)

    def test_trailing_slash_redirect_preserved(self):
        response = self.client.post("/auth/login/", data=LOGIN, follow_redirects=False)
        self.assertEqual(response.status_code, 307)
        self.assertTrue(response.headers["location"].endswith("/auth/login"))
        self.assert_token(self.client.post("/auth/login/", data=LOGIN))

    def test_openapi_oauth_contract_preserved(self):
        schema = self.client.get("/openapi.json").json()
        self.assertEqual(schema["components"]["securitySchemes"]["OAuth2PasswordBearer"]["flows"]["password"]["tokenUrl"], "/auth/login")
        content = schema["paths"]["/auth/login"]["post"]["requestBody"]["content"]
        ref = content["application/x-www-form-urlencoded"]["schema"]["$ref"].split("/")[-1]
        self.assertEqual(set(schema["components"]["schemas"][ref]["required"]), {"username", "password"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
