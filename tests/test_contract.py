import os
import sys
import unittest
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mailx_sdk import MailXClient

BASE_URL = os.environ.get("MAILX_SDK_TEST_BASE_URL")
API_KEY = os.environ.get("MAILX_SDK_TEST_API_KEY")


@unittest.skipUnless(BASE_URL and API_KEY, "MAILX_SDK_TEST_BASE_URL/MAILX_SDK_TEST_API_KEY not set")
class TestContract(unittest.TestCase):
    def test_send_email_against_real_server(self):
        client = MailXClient(api_key=API_KEY, base_url=BASE_URL)
        email = client.send_email(
            os.environ.get("MAILX_SDK_TEST_FROM", "a@example.com"),
            ["bob@example.com"],
            subject="sdk contract test",
            text="hello",
        )
        self.assertTrue(email["id"])
        self.assertEqual(email["status"], "queued")

    def test_new_methods_against_real_server(self):
        client = MailXClient(api_key=API_KEY, base_url=BASE_URL)
        run = uuid.uuid4().hex[:12]

        who = client.whoami()
        self.assertIn("organization", who)

        domain = client.create_domain(name=f"py-contract-{run}.example.com")
        client.verify_domain(domain["id"])
        client.get_domain_dkim(domain["id"])

        tmpl = client.create_template(name=f"py-contract-{run}", subject="Hi {{name}}", text="Hello {{name}}")
        preview = client.preview_template(tmpl["id"], {"name": "Ada"})
        self.assertEqual(preview["subject"], "Hi Ada")

        contact = client.create_contact(email=f"py-contract-member-{run}@example.com")
        audience = client.create_audience(name=f"py-contract-audience-{run}")
        client.update_audience(audience["id"], name=f"py-contract-audience-{run}-renamed")
        client.add_audience_contact(audience["id"], contact_id=contact["id"])
        members = client.list_audience_contacts(audience["id"])
        self.assertEqual(len(members["data"]), 1)

        broadcast_preview = client.preview_broadcast(audience["id"], tmpl["id"])
        self.assertIn("recipients", broadcast_preview)

        client.remove_audience_contact(audience["id"], contact["id"])

        supp = client.create_suppression(email=f"py-contract-suppress-{run}@example.com")
        client.get_suppression(supp["id"])

        webhook = client.create_webhook(url="https://example.com/hook", events=["email.delivered"])
        client.list_webhook_deliveries(webhook["id"])
        client.rotate_webhook_secret(webhook["id"])

        from_addr = os.environ.get("MAILX_SDK_TEST_FROM") or f"hello@{os.environ.get('MAILX_SDK_TEST_VERIFIED_DOMAIN', 'example.com')}"
        email = client.send_email(from_addr, ["dest@example.invalid"], subject="contract", text="hi")
        client.get_email_events(email["id"])


if __name__ == "__main__":
    unittest.main()
