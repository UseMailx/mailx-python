import sys
import os
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mailx_sdk import MailXClient, MailXError


def fake_response(status_code, json_body=None, headers=None, ok=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.ok = ok if ok is not None else 200 <= status_code < 300
    resp.headers = headers or {}
    resp.content = b"1" if json_body is not None else b""
    resp.json.return_value = json_body or {}
    resp.reason = "error"
    return resp


class TestMailXClient(unittest.TestCase):
    def test_send_email_success(self):
        session = MagicMock()
        session.request.return_value = fake_response(
            202, {"id": "m1", "from": "a@x.com", "to": ["b@x.com"], "subject": "s", "status": "queued"}
        )
        client = MailXClient(api_key="mx_test", base_url="https://x/v1", session=session)
        email = client.send_email("a@x.com", ["b@x.com"], subject="s", text="t")
        self.assertEqual(email["id"], "m1")
        args, kwargs = session.request.call_args
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer mx_test")
        self.assertEqual(args[1], "https://x/v1/emails")

    def test_retries_on_429_then_succeeds(self):
        session = MagicMock()
        session.request.side_effect = [
            fake_response(429, {"error": {"type": "rate_limited", "code": "x", "message": "m"}}, headers={"Retry-After": "0"}),
            fake_response(202, {"id": "m2"}),
        ]
        client = MailXClient(api_key="mx_test", base_url="https://x/v1", session=session)
        result = client.get_email("m2")
        self.assertEqual(result["id"], "m2")
        self.assertEqual(session.request.call_count, 2)

    def test_raises_mailx_error_on_422(self):
        session = MagicMock()
        session.request.return_value = fake_response(
            422, {"error": {"type": "validation_error", "code": "missing_from", "message": "from is required"}}
        )
        client = MailXClient(api_key="mx_test", base_url="https://x/v1", session=session)
        with self.assertRaises(MailXError) as ctx:
            client.send_email("", [])
        self.assertEqual(ctx.exception.status, 422)
        self.assertEqual(ctx.exception.code, "missing_from")

    def test_requires_api_key(self):
        with self.assertRaises(ValueError):
            MailXClient(api_key="")

    def test_new_methods_hit_the_expected_route_and_method(self):
        cases = [
            ("whoami", lambda c: c.whoami(), "GET", "https://x/v1/whoami"),
            ("get_email_events", lambda c: c.get_email_events("em1"), "GET", "https://x/v1/emails/em1/events"),
            (
                "preview_template",
                lambda c: c.preview_template("t1", {"name": "Ada"}),
                "POST",
                "https://x/v1/templates/t1/preview",
            ),
            (
                "preview_broadcast",
                lambda c: c.preview_broadcast("a1", "t1"),
                "POST",
                "https://x/v1/broadcasts/preview",
            ),
            ("get_suppression", lambda c: c.get_suppression("s1"), "GET", "https://x/v1/suppressions/s1"),
        ]
        for name, call, method, url in cases:
            with self.subTest(name):
                session = MagicMock()
                session.request.return_value = fake_response(200, {})
                client = MailXClient(api_key="mx_test", base_url="https://x/v1", session=session)
                call(client)
                args, kwargs = session.request.call_args
                self.assertEqual(args[0], method)
                self.assertEqual(args[1], url)


if __name__ == "__main__":
    unittest.main()
