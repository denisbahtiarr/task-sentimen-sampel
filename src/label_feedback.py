#!/usr/bin/env python3
"""Label customer feedback with sentiment, topic, and severity, then split
out the high/critical rows for triage: draft an escalation reply for the
support lead and log the remaining rows to a file.

Usage:
    python src/label_feedback.py [--input data/feedback.csv] [--outdir output]
        [--recipient support-lead@example.com]
"""

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

# --- Sentiment -------------------------------------------------------------

POSITIVE_WORDS = [
    "love", "great", "fantastic", "thank you", "thanks", "appreciate",
    "nice", "kind", "cherry on top", "snappier", "keep up the great work",
]

NEGATIVE_WORDS = [
    "unacceptable", "cannot", "can not", "disappeared", "just gone",
    "cancelling", "cancel our", "disappointed", "confusing", "frustrating",
    "frustrated", "crashes", "panicking", "blocking", "stuck on",
    "fails", "failing", "lost", "losing", "bug", "annoying", "too many",
    "a bit thin", "gave up", "not match", "serious",
]


def classify_sentiment(text: str) -> str:
    lowered = text.lower()
    pos = sum(1 for w in POSITIVE_WORDS if w in lowered)
    neg = sum(1 for w in NEGATIVE_WORDS if w in lowered)
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"


# --- Topic -------------------------------------------------------------
# Ordered from most specific/urgent to most generic. First match wins.

TOPIC_RULES = [
    ("privacy_security", [
        "another customer", "privacy problem", "delete all of my personal data",
        "under the new regulations",
    ]),
    ("data_loss", ["disappeared", "just gone", "recover them"]),
    ("authentication", ["cannot log in", "invalid session"]),
    ("reliability_outage", ["outage", "cannot run our business"]),
    ("billing_payment", [
        "charged twice", "over its limit", "payment keeps failing",
        "stuck on monthly", "duplicate charge", "refund",
    ]),
    ("data_accuracy", ["do not match", "trust these figures"]),
    ("bug_crash", ["crashes", "there is a bug"]),
    ("support_response", [
        "support ticket", "nobody has replied", "response time", "support agent",
    ]),
    ("performance", ["seconds to load", "speed improvements", "snappier", "slow"]),
    ("export_reporting", ["exporting to pdf", "cuts off"]),
    ("notifications", ["email notifications"]),
    ("mobile", ["mobile app", "on android", "on ios"]),
    ("onboarding", ["onboarding", "invite my teammates", "walkthrough", "trial"]),
    ("pricing", ["pricing page", "pro plan", "business plan"]),
    ("ui_ux", ["confusing", "could not find", "typo"]),
    ("documentation", ["api docs", "webhook section", "example payload"]),
    ("feature_request", [
        "would love to see", "integration with", "suggestion would be",
        "wish there was", "widget for the home screen", "keyboard shortcuts",
    ]),
]


def classify_topic(text: str) -> str:
    lowered = text.lower()
    for topic, keywords in TOPIC_RULES:
        if any(kw in lowered for kw in keywords):
            return topic
    return "other"


# --- Severity -------------------------------------------------------------
# Checked top-down; first tier whose keywords appear wins.

CRITICAL_KEYWORDS = [
    "cannot log in", "another customer", "privacy problem", "disappeared",
    "just gone", "cancelling our", "moving to a competitor", "third outage",
    "panicking",
]

HIGH_KEYWORDS = [
    "charged twice", "over its limit", "payment keeps failing",
    "stuck on monthly", "delete all of my personal data", "do not match",
    "crashes every time", "blocking my work", "more than ten times",
]

MEDIUM_KEYWORDS = [
    "four days", "nobody has replied", "resets", "workaround",
    "logging me out", "too many email", "thirty seconds",
]


def classify_severity(text: str) -> str:
    lowered = text.lower()
    if any(kw in lowered for kw in CRITICAL_KEYWORDS):
        return "critical"
    if any(kw in lowered for kw in HIGH_KEYWORDS):
        return "high"
    if any(kw in lowered for kw in MEDIUM_KEYWORDS):
        return "medium"
    return "low"


def label_rows(rows):
    labeled = []
    for row in rows:
        message = row.get("message", "")
        row = dict(row)
        row["sentiment"] = classify_sentiment(message)
        row["topic"] = classify_topic(message)
        row["severity"] = classify_severity(message)
        labeled.append(row)
    return labeled


def write_csv(path: Path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# --- Escalation email -------------------------------------------------------

def build_escalation_email(rows, recipient: str) -> tuple[str, str]:
    """Draft a reply summarizing high/critical rows for the support lead.

    Returns (subject, body). Does not send anything itself.
    """
    subject = f"[Action needed] {len(rows)} high/critical feedback escalation(s)"

    if not rows:
        body = (
            f"Hi,\n\nNo high or critical severity feedback was found in this "
            f"batch. No action needed.\n\n-- Automated feedback triage"
        )
        return subject, body

    lines = [
        "Hi,",
        "",
        f"{len(rows)} feedback item(s) came in at high or critical severity "
        "and need support follow-up:",
        "",
    ]
    for row in rows:
        lines.append(
            f"- [{row['severity'].upper()}] {row.get('name', 'Unknown')} "
            f"({row.get('date', 'n/a')}, {row.get('channel', 'n/a')}) "
            f"- topic: {row.get('topic', 'n/a')}, sentiment: {row.get('sentiment', 'n/a')}"
        )
        lines.append(f"  \"{row.get('message', '')}\"")
        lines.append(f"  reply-to: {row.get('email', 'n/a')}")
        lines.append("")

    lines.append("Please prioritize the critical items first.")
    lines.append("")
    lines.append("-- Automated feedback triage")
    body = "\n".join(lines)
    return subject, body


def draft_escalation_email(rows, recipient: str, outdir: Path) -> Path:
    subject, body = build_escalation_email(rows, recipient)
    path = outdir / "escalation_email.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write(f"To: {recipient}\n")
        f.write(f"Subject: {subject}\n")
        f.write("\n")
        f.write(body)
        f.write("\n")
    return path


# --- Logging ----------------------------------------------------------------

def write_log(rows, path: Path):
    """Log the non-escalation (low/medium severity) rows to a plain-text file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with path.open("w", encoding="utf-8") as f:
        f.write(f"# Feedback log generated {timestamp}\n")
        f.write(f"# {len(rows)} low/medium severity row(s)\n\n")
        for row in rows:
            f.write(
                f"[{row['severity']}] id={row.get('id', 'n/a')} "
                f"topic={row['topic']} sentiment={row['sentiment']} "
                f"date={row.get('date', 'n/a')} channel={row.get('channel', 'n/a')} "
                f"message=\"{row.get('message', '')}\"\n"
            )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="data/feedback.csv", type=Path)
    parser.add_argument("--outdir", default="output", type=Path)
    parser.add_argument(
        "--recipient", default="support-lead@example.com",
        help="Support lead email address the escalation draft is addressed to.",
    )
    args = parser.parse_args()

    if not args.input.exists():
        sys.exit(f"Input file not found: {args.input}")

    with args.input.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    labeled = label_rows(rows)
    fieldnames = list(reader.fieldnames) + ["sentiment", "topic", "severity"]

    urgent = [r for r in labeled if r["severity"] in ("high", "critical")]
    rest = [r for r in labeled if r["severity"] not in ("high", "critical")]

    write_csv(args.outdir / "labeled_feedback.csv", labeled, fieldnames)
    write_csv(args.outdir / "high_critical_feedback.csv", urgent, fieldnames)
    write_csv(args.outdir / "other_feedback.csv", rest, fieldnames)

    email_path = draft_escalation_email(urgent, args.recipient, args.outdir)
    log_path = args.outdir / "feedback_log.txt"
    write_log(rest, log_path)

    print(f"Labeled {len(labeled)} rows.")
    print(f"  high/critical: {len(urgent)} -> {args.outdir / 'high_critical_feedback.csv'}")
    print(f"  low/medium:    {len(rest)} -> {args.outdir / 'other_feedback.csv'}")
    print(f"  all rows:      {args.outdir / 'labeled_feedback.csv'}")
    print(f"  escalation email draft ({len(urgent)} item(s)) -> {email_path}")
    print(f"  low/medium log ({len(rest)} item(s)) -> {log_path}")


if __name__ == "__main__":
    main()
