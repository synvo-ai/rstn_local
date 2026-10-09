"""Run the mock test pack through the engine and compare with the expected results (B15).

Run in-process (no HTTP): bash -ic 'python3 tools/evaluate.py [--case A2-01] [--show] [--concurrency 4]'
Writes var/eval/<time>.json with every result. Token counts are internal and printed for cost tracking.
"""
import argparse
import asyncio
import base64
import json
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pace_engine.config import Settings  # noqa: E402
from pace_engine.llm import GeminiGateway  # noqa: E402
from pace_engine.models import EnquiryRequest  # noqa: E402
from pace_engine.pipeline import Engine  # noqa: E402

PACK = ROOT / "testpack"


def request_for(case):
    eml = PACK / "eml"
    env = {"requestId": f"eval-{case['id']}", "channel": case.get("channel", "EMAIL"), "senderRef": f"mock-{case['id']}"}
    if env["channel"] == "WEB_FORM":
        env["form"] = json.loads((eml / f"{case['id']}.form.json").read_text())
    else:
        env["email"] = {"format": "eml", "contentBase64": base64.b64encode((eml / f"{case['id']}.eml").read_bytes()).decode()}
        thread = []
        for k, t in enumerate(case.get("thread", []), 1):
            raw = (eml / f"{case['id']}.thread-{k}.eml").read_bytes()
            thread.append({"format": "eml", "contentBase64": base64.b64encode(raw).decode(), "sentBy": t.get("sentBy")})
        if thread:
            env["thread"] = thread
    return EnquiryRequest.model_validate(env)


def prog_matches(exp, issue):
    p = issue["programme"]
    if exp in (None, "ANY"):
        return True
    if exp in ("AMBIGUOUS", "UNRESOLVED", "NOT_NEEDED"):
        return p["status"] == exp
    return p.get("programmeId") == exp


def score(case, r):
    exp = case["expected"]
    problems = []
    msg = r.get("message") or {}
    if exp.get("messageType", "ENQUIRY") != msg.get("messageType"):
        problems.append(f"messageType {msg.get('messageType')} (expected {exp.get('messageType', 'ENQUIRY')})")
    if exp.get("languageSupported", True) != msg.get("languageSupported", True):
        problems.append(f"languageSupported {msg.get('languageSupported')}")
    actual = list(r["issues"])
    soft = []
    def ok(e, i):
        return (i["action"] == e["action"] and prog_matches(e.get("programme"), i)
                and (not e.get("owner") or (i.get("owner") or {}).get("teamId") == e["owner"]))

    for e in exp.get("issues", []):
        m = next((i for i in actual if ok(e, i) and i["intent"] == e.get("intent")), None) or next((i for i in actual if ok(e, i)), None)
        if m is None:
            problems.append(f"missing {e['action']} / {e.get('programme')}" + (f" / {e['owner']}" if e.get("owner") else ""))
        else:
            actual.remove(m)
            if e.get("intent") and e["intent"] != m["intent"]:
                soft.append(f"{m['issueId']} intent {m['intent']} (expected {e['intent']})")
    for i in actual:
        problems.append(f"extra {i['issueId']} {i['action']} / {i['programme'].get('programmeId') or i['programme']['status']}")
    if r.get("runHealth") == "FAILED":
        problems.append("run failed")
    return problems, soft


def describe(r):
    out = []
    for i in r["issues"]:
        p = i["programme"].get("programmeId") or i["programme"]["status"]
        out.append(f"{i['action']}:{p}:{i['intent']}")
    return ", ".join(out) or (r.get("message") or {}).get("emailAction", {}).get("reason", "-")


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", action="append")
    ap.add_argument("--show", action="store_true", help="print each full result")
    ap.add_argument("--concurrency", type=int, default=4)
    a = ap.parse_args()
    s = Settings()
    engine = Engine(s, GeminiGateway(s.gemini_api_key, s.model_timeout_s))
    cases = yaml.safe_load((PACK / "cases.yaml").read_text())["cases"]
    if a.case:
        cases = [c for c in cases if c["id"] in a.case]
    sem = asyncio.Semaphore(a.concurrency)

    async def one(c):
        async with sem:
            req = request_for(c)
            t0 = time.time()
            r = await engine.run(engine.prepare(req), f"eval_{c['id']}", time.strftime("%Y-%m-%dT%H:%M:%S%z"))
            return c, r, time.time() - t0

    results = await asyncio.gather(*(one(c) for c in cases))
    rows, passed, tin, tout = [], 0, 0, 0
    for c, r, secs in results:
        problems, soft = score(c, r)
        passed += not problems
        u = r["_usage"]
        tin += u["input"]
        tout += u["output"] + u["thinking"]
        safety = (r.get("reply") or {}).get("safety")
        print(f"{'PASS' if not problems else 'FAIL'} {c['id']:7s} {secs:5.1f}s {r['runHealth']:9s} reply={safety:14s} in={u['input']:6d} out={u['output'] + u['thinking']:5d}  {describe(r)}")
        for p in problems:
            print(f"      ✗ {p}")
        for p in soft:
            print(f"      ~ {p}")
        for f in (r.get("reply") or {}).get("findings", []):
            print(f"      ! {f}")
        if a.show:
            print(json.dumps({k: v for k, v in r.items() if k != "trace"}, indent=1, ensure_ascii=False))
        rows.append({"case": c["id"], "pass": not problems, "problems": problems, "soft": soft, "seconds": round(secs, 1), "result": r})
    n = len(results)
    print(f"\n{passed}/{n} passed · tokens per email: in {tin // max(1, n)}, out {tout // max(1, n)}")
    out = ROOT / "var" / "eval"
    out.mkdir(parents=True, exist_ok=True)
    path = out / time.strftime("%Y%m%d-%H%M%S.json")
    path.write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    print(f"results: {path}")


if __name__ == "__main__":
    asyncio.run(main())
