"""Small sample client for the sandbox API (the start of B35, the mock RSTN client).

  export PACE_URL=http://127.0.0.1:8090 PACE_KEY=pk_sbx_...
  python3 tools/client.py send testpack/eml/A2-01.eml [--thread a.eml --thread b.eml] [--sync] [--save out.json]
  python3 tools/client.py send testpack/eml/A8-01.form.json --sync           # web form
  python3 tools/client.py get <runId>
  python3 tools/client.py recheck out.json ISSUE-002 REFER_TO_TEAM --team PACE-ADM
"""
import argparse
import base64
import json
import os
import sys
import time
import uuid
from pathlib import Path

import httpx

URL = os.environ.get("PACE_URL", "http://127.0.0.1:8090").rstrip("/")
KEY = os.environ.get("PACE_KEY", "")


def headers():
    if not KEY:
        sys.exit("set PACE_KEY")
    return {"authorization": f"Bearer {KEY}"}


def envelope(path, threads=(), callback=None):
    p = Path(path)
    env = {"requestId": f"cli-{uuid.uuid4().hex[:8]}", "idempotencyKey": uuid.uuid4().hex, "senderRef": f"cli-{p.stem}"}
    if p.name.endswith(".form.json"):
        env.update(channel="WEB_FORM", form=json.loads(p.read_text()))
    else:
        fmt = "msg" if p.suffix.lower() == ".msg" else "eml"
        env.update(channel="EMAIL", email={"format": fmt, "contentBase64": base64.b64encode(p.read_bytes()).decode()})
    if threads:
        env["thread"] = [{"format": "eml", "contentBase64": base64.b64encode(Path(t).read_bytes()).decode()} for t in threads]
    if callback:
        env["callbackUrl"] = callback
    return env


def show(res):
    print(json.dumps(res, indent=1, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("send")
    s.add_argument("file")
    s.add_argument("--thread", action="append", default=[])
    s.add_argument("--sync", action="store_true")
    s.add_argument("--callback")
    s.add_argument("--save", help="save request and result for a later recheck")
    g = sub.add_parser("get")
    g.add_argument("run_id")
    r = sub.add_parser("recheck")
    r.add_argument("saved")
    r.add_argument("issue_id")
    r.add_argument("action", choices=["REPLY_DIRECTLY", "REFER_TO_TEAM", "ASK_CLARIFICATION", "MANUAL_HANDLING"])
    r.add_argument("--team")
    a = ap.parse_args()

    with httpx.Client(timeout=180) as c:
        if a.cmd == "send":
            env = envelope(a.file, a.thread, a.callback)
            resp = c.post(f"{URL}/v0/enquiries" + ("?mode=sync" if a.sync else ""), json=env, headers=headers())
            res = resp.json()
            if resp.status_code == 202:
                while res.get("status") in ("QUEUED", "RUNNING"):
                    time.sleep(1.5)
                    res = c.get(f"{URL}/v0/runs/{res['runId']}", headers=headers()).json()
            show(res)
            if a.save:
                Path(a.save).write_text(json.dumps({"request": env, "result": res}, ensure_ascii=False))
        elif a.cmd == "get":
            show(c.get(f"{URL}/v0/runs/{a.run_id}", headers=headers()).json())
        else:
            saved = json.loads(Path(a.saved).read_text())
            change = {"issueId": a.issue_id, "action": a.action, **({"ownerTeamId": a.team} if a.team else {})}
            body = {"request": saved["request"], "previousResult": saved["result"], "change": change}
            show(c.post(f"{URL}/v0/enquiries/{saved['result']['runId']}/recheck", json=body, headers=headers()).json())


if __name__ == "__main__":
    main()
