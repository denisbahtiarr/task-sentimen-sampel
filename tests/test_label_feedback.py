import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from label_feedback import (  # noqa: E402
    build_escalation_email,
    classify_severity,
    classify_sentiment,
    classify_topic,
    label_rows,
    write_log,
)


class ClassificationTests(unittest.TestCase):
    def test_critical_severity_on_login_outage(self):
        text = "I cannot log in at all, this is the third outage this month."
        self.assertEqual(classify_severity(text), "critical")

    def test_high_severity_on_billing_issue(self):
        text = "I was charged twice for my subscription and it put me over its limit."
        self.assertEqual(classify_severity(text), "high")

    def test_medium_severity_on_recurring_bug(self):
        text = "The filter resets when I switch tabs, found a workaround though."
        self.assertEqual(classify_severity(text), "medium")

    def test_low_severity_default(self):
        text = "Great app overall, wish there was a dark mode."
        self.assertEqual(classify_severity(text), "low")

    def test_positive_sentiment(self):
        text = "I love this product, thank you for the great support."
        self.assertEqual(classify_sentiment(text), "positive")

    def test_negative_sentiment(self):
        text = "This is unacceptable, the app keeps crashing and I am frustrated."
        self.assertEqual(classify_sentiment(text), "negative")

    def test_neutral_sentiment_on_plain_question(self):
        text = "Does the Pro plan include the team workspace feature?"
        self.assertEqual(classify_sentiment(text), "neutral")

    def test_topic_priority_privacy_over_generic(self):
        text = "I could see another customer's invoices, a serious privacy problem."
        self.assertEqual(classify_topic(text), "privacy_security")

    def test_topic_billing(self):
        text = "My payment keeps failing so I am stuck on monthly."
        self.assertEqual(classify_topic(text), "billing_payment")

    def test_topic_unmatched_falls_back_to_other(self):
        self.assertEqual(classify_topic("Just saying hello, nothing else."), "other")


class LabelRowsTests(unittest.TestCase):
    def test_label_rows_adds_expected_fields(self):
        rows = [{
            "id": "1",
            "date": "2026-01-01",
            "name": "Test User",
            "email": "test@example.com",
            "channel": "email",
            "message": "I cannot log in at all, please help now.",
        }]
        labeled = label_rows(rows)
        self.assertEqual(len(labeled), 1)
        self.assertEqual(labeled[0]["severity"], "critical")
        self.assertEqual(labeled[0]["topic"], "authentication")
        self.assertIn("sentiment", labeled[0])


class EscalationEmailTests(unittest.TestCase):
    def setUp(self):
        self.rows = label_rows([
            {
                "id": "1", "date": "2026-01-01", "name": "Escalated User",
                "email": "escalated@example.com", "channel": "email",
                "message": "I cannot log in at all, please help now.",
            },
        ])

    def test_email_lists_every_escalation_row(self):
        subject, body = build_escalation_email(self.rows, "lead@example.com")
        self.assertIn("1", subject)
        self.assertIn("Escalated User", body)
        self.assertIn("escalated@example.com", body)
        self.assertIn("CRITICAL", body)

    def test_email_handles_no_escalations(self):
        subject, body = build_escalation_email([], "lead@example.com")
        self.assertIn("0", subject)
        self.assertIn("No high or critical", body)


class WriteLogTests(unittest.TestCase):
    def test_write_log_creates_one_line_per_row(self, tmp_path=None):
        import tempfile
        rows = label_rows([
            {
                "id": "1", "date": "2026-01-01", "name": "A",
                "email": "a@example.com", "channel": "email",
                "message": "Great app overall, wish there was a dark mode.",
            },
            {
                "id": "2", "date": "2026-01-02", "name": "B",
                "email": "b@example.com", "channel": "chat",
                "message": "The filter resets, found a workaround though.",
            },
        ])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "feedback_log.txt"
            write_log(rows, path)
            content = path.read_text(encoding="utf-8")
            data_lines = [
                line for line in content.splitlines()
                if line and not line.startswith("#")
            ]
            self.assertEqual(len(data_lines), 2)
            self.assertIn("id=1", data_lines[0])
            self.assertIn("id=2", data_lines[1])


if __name__ == "__main__":
    unittest.main()
