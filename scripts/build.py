"""Validate data/opportunities.yaml and build the static site into _site/.

Usage:
    python scripts/build.py            # build into _site/
    python scripts/build.py --check    # validate only
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "opportunities.yaml"
WEB = ROOT / "web"
OUT = ROOT / "_site"

REQUIRED = ("id", "title", "funder", "url", "deadline", "domain", "keywords")


def load(path: Path = DATA) -> list[dict]:
    items = yaml.safe_load(path.read_text()) or []
    if not isinstance(items, list):
        sys.exit(f"{path}: top level must be a list")

    errors, seen = [], set()
    for i, it in enumerate(items):
        tag = f"entry {i} ({it.get('id', '?')})"
        for key in REQUIRED:
            if it.get(key) in (None, "", []):
                errors.append(f"{tag}: missing '{key}'")
        if it.get("id") in seen:
            errors.append(f"{tag}: duplicate id")
        seen.add(it.get("id"))

        d = it.get("deadline")
        if isinstance(d, str):
            try:
                d = dt.date.fromisoformat(d)
            except ValueError:
                errors.append(f"{tag}: deadline must be YYYY-MM-DD")
        if isinstance(d, dt.date):
            it["deadline"] = d.isoformat()

        if not str(it.get("url", "")).startswith(("http://", "https://")):
            errors.append(f"{tag}: url must start with http(s)://")
        if not isinstance(it.get("keywords", []), list):
            errors.append(f"{tag}: keywords must be a list")
        for k in ("amount_min", "amount_max"):
            if k in it and not isinstance(it[k], (int, float)):
                errors.append(f"{tag}: {k} must be a number")
        if it.get("timezone"):
            try:
                ZoneInfo(it["timezone"])
            except Exception:
                errors.append(f"{tag}: unknown timezone {it['timezone']!r}")
        it.setdefault("currency", "USD")

    if errors:
        sys.exit("Validation failed:\n  " + "\n  ".join(errors))
    return sorted(items, key=lambda x: x["deadline"])


def _ics_escape(s: str) -> str:
    return (
        str(s).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")
    )


def to_ics(items: list[dict]) -> str:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//funding-tracker//EN",
        "CALSCALE:GREGORIAN",
        "X-WR-CALNAME:Funding deadlines",
    ]
    for it in items:
        day = dt.date.fromisoformat(it["deadline"])
        lines += ["BEGIN:VEVENT", f"UID:{it['id']}@funding-tracker", f"DTSTAMP:{stamp}"]
        if it.get("deadline_time"):
            h, m = map(int, str(it["deadline_time"]).split(":"))
            tz = ZoneInfo(it.get("timezone") or "UTC")
            start = dt.datetime.combine(day, dt.time(h, m), tz).astimezone(dt.timezone.utc)
            lines.append(f"DTSTART:{start:%Y%m%dT%H%M%SZ}")
            lines.append(f"DTEND:{start + dt.timedelta(minutes=30):%Y%m%dT%H%M%SZ}")
        else:
            lines.append(f"DTSTART;VALUE=DATE:{day:%Y%m%d}")
            lines.append(f"DTEND;VALUE=DATE:{day + dt.timedelta(days=1):%Y%m%d}")
        lines += [
            f"SUMMARY:{_ics_escape('Deadline: ' + it['title'])}",
            f"DESCRIPTION:{_ics_escape(it['funder'] + ' - ' + it['url'])}",
            f"URL:{it['url']}",
            "BEGIN:VALARM",
            "TRIGGER:-P14D",
            "ACTION:DISPLAY",
            f"DESCRIPTION:{_ics_escape('2 weeks to ' + it['title'])}",
            "END:VALARM",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def build(items: list[dict]) -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(WEB, OUT)
    payload = {
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "opportunities": items,
    }
    (OUT / "data.json").write_text(json.dumps(payload, indent=2))
    (OUT / "deadlines.ics").write_text(to_ics(items), newline="")
    (OUT / ".nojekyll").touch()
    print(f"Built {len(items)} opportunities -> {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="validate only")
    args = ap.parse_args()
    data = load()
    if args.check:
        print(f"OK: {len(data)} opportunities")
    else:
        build(data)
