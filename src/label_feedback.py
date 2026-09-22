#!/usr/bin/env python3
"""Label customer feedback with sentiment, topic, and severity, then split
out the high/critical rows for triage.

Usage:
    python src/label_feedback.py [--input data/feedback.csv] [--outdir output]
"""

import argparse
import csv
import sys
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="data/feedback.csv", type=Path)
    parser.add_argument("--outdir", default="output", type=Path)
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

    print(f"Labeled {len(labeled)} rows.")
    print(f"  high/critical: {len(urgent)} -> {args.outdir / 'high_critical_feedback.csv'}")
    print(f"  low/medium:    {len(rest)} -> {args.outdir / 'other_feedback.csv'}")
    print(f"  all rows:      {args.outdir / 'labeled_feedback.csv'}")


if __name__ == "__main__":
    main()
