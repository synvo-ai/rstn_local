"""Build the mock test pack: testpack/cases.yaml → testpack/eml/*.eml (and .form.json for web forms).

Run: python3 tools/make_testpack.py
"""
import io
import json
import re
import sys
from email.message import EmailMessage
from email.utils import format_datetime
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / "testpack"
OUT = PACK / "eml"
DESK = "PaCE General Enquiries <enquiries@pace-mock.example>"
SGT = timezone(timedelta(hours=8))
BASE = datetime(2026, 10, 7, 9, 0, tzinfo=SGT)


def addr(name):
    if name.startswith("PaCE"):
        return DESK
    slug = re.sub(r"[^a-z]+", ".", name.lower()).strip(".") or "sender"
    return f"{name} <{slug}@example.com>"


def receipt_jpg(text_lines):
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (600, 400), "white")
    d = ImageDraw.Draw(img)
    for i, line in enumerate(text_lines):
        d.text((30, 30 + i * 32), line, fill="black")
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=80)
    return buf.getvalue()


def logo_png():
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (120, 40), "#1f6feb")
    ImageDraw.Draw(img).text((10, 12), "CLINIC", fill="white")
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def build(case, when, body=None, subject=None, sender=None, in_reply_to=None, refs=(), part="0"):
    m = EmailMessage()
    m["From"] = addr(sender or case["from"])
    m["To"] = DESK if not (sender or "").startswith("PaCE") else addr(case["from"])
    m["Subject"] = subject if subject is not None else case["subject"]
    m["Date"] = format_datetime(when)
    m["Message-ID"] = f"<{case['id']}.{part}@mock.example>"
    if in_reply_to:
        m["In-Reply-To"] = in_reply_to
        m["References"] = " ".join(refs)
    if case.get("html_only") and body is None:
        m.set_content(case["body_html"], subtype="html")
        if case.get("inline_logo"):
            m.get_payload()  # keep single part, then convert to related for the inline logo
            m.make_related()
            m.add_related(logo_png(), maintype="image", subtype="png", cid="<logo001>", filename="logo.png", disposition="inline")
    else:
        m.set_content(body if body is not None else case["body"])
    return m


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.iterdir():
        old.unlink()
    cases = yaml.safe_load((PACK / "cases.yaml").read_text())["cases"]
    for n, c in enumerate(cases):
        when = BASE + timedelta(minutes=37 * n)
        if c.get("channel") == "WEB_FORM":
            (OUT / f"{c['id']}.form.json").write_text(json.dumps({"fields": c["form"]}, indent=1, ensure_ascii=False))
            continue
        ids, prev_body = [], ""
        for k, t in enumerate(c.get("thread", []), 1):
            tw = when - timedelta(days=len(c["thread"]) - k + 1)
            tm = build(c, tw, body=t["body"], subject=t["subject"], sender=t["from"], in_reply_to=ids[-1] if ids else None, refs=ids, part=f"t{k}")
            ids.append(tm["Message-ID"])
            (OUT / f"{c['id']}.thread-{k}.eml").write_bytes(bytes(tm))
            prev_body = t["body"]
        body = None
        if c.get("quote_thread") and c.get("thread"):
            quoted = "\n".join("> " + l for l in prev_body.splitlines())
            body = c["body"] + f"\nOn {format_datetime(when - timedelta(days=1))}, {DESK} wrote:\n" + quoted + "\n"
        m = build(c, when, body=body, in_reply_to=ids[-1] if ids else None, refs=ids)
        for a in c.get("attachments", []):
            if a["kind"] == "receipt":
                data = receipt_jpg(["Bank transfer receipt (MOCK)", "Date: 02 Oct 2026", "To: NANYANG TECHNOLOGICAL UNIVERSITY", "Amount: SGD 3,924.00", "Reference: PACE-FMIC-2026-08817", "Payer: (made-up)"])
                m.add_attachment(data, maintype="image", subtype="jpeg", filename=a["filename"])
        (OUT / f"{c['id']}.eml").write_bytes(bytes(m))
    print(f"{len(cases)} cases written to {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
