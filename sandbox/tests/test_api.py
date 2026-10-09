"""API behaviour from the testing protocol (scenarios B1–B3, D3, E1–E3, E5, E6), with a scripted model."""
import base64
import hashlib
import json
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from pace_engine.api import create_app
from pace_engine.config import Settings
from pace_engine.llm import ScriptedGateway

ROOT = Path(__file__).resolve().parent.parent
KEY = "pk_test_key"
EML = (ROOT / "testpack" / "eml" / "A2-01.eml").read_bytes()


def understand(_):
    return {"language": "en", "messageType": "ENQUIRY", "issues": [
        {"summary": "The sender asks whether their payment was received.", "topic": "whether your payment was received", "query": "payment received",
         "intent": "PAYMENT_STATUS", "programmeMentions": ["Graduate Certificate in Applied Data Analytics"], "senderFacts": [], "mentionsAttachment": True, "alreadyAnswered": False},
        {"summary": "The sender asks when the January intake starts.", "topic": "the January intake", "query": "January intake start date",
         "intent": "SCHEDULE", "programmeMentions": ["Graduate Certificate in Applied Data Analytics"], "senderFacts": [], "mentionsAttachment": False, "alreadyAnswered": False},
        {"summary": "The sender asks about parking.", "topic": "parking", "query": "parking",
         "intent": "COURSE_INFORMATION", "programmeMentions": ["Graduate Certificate in Applied Data Analytics"], "senderFacts": [], "mentionsAttachment": False, "alreadyAnswered": False},
    ]}


def draft(p):
    """Answer an issue only when its evidence holds an intake date; copy controlled sentences."""
    issues, parts = [], [p["greeting"], p["opening"]]
    for i in p["issues"]:
        if i["action"] == "REPLY_DIRECTLY":
            ev = next((e for e in i["evidence"] if "11 January 2027" in e["text"]), None)
            if ev and "intake" in i["question"]:
                claim = "The January 2027 intake starts on 11 January 2027."
                issues.append({"issueId": i["issueId"], "answered": True, "claims": [{"text": claim, "evidenceIds": [ev["evidenceId"]]}]})
                parts.append(claim)
            else:
                issues.append({"issueId": i["issueId"], "answered": False, "claims": []})
                parts.append(i["fallbackSentence"])
        else:
            issues.append({"issueId": i["issueId"], "answered": False, "claims": []})
            parts.append(i["controlledSentence"])
    parts.append(p["signOff"])
    return {"issues": issues, "replyText": "\n\n".join(parts)}


def verify(_):
    return {"verdict": "SAFE_TO_REVIEW", "findings": []}


@pytest.fixture
def client(tmp_path):
    keys = tmp_path / "keys.yaml"
    keys.write_text(yaml.safe_dump({"keys": [{"keyId": "t1", "tester": "test", "sha256": hashlib.sha256(KEY.encode()).hexdigest(), "callbackSecret": "cbs"}]}))
    s = Settings(db_path=tmp_path / "db.sqlite", keys_file=keys, signing_secret="secret", rate_limit_per_hour=8)
    gw = ScriptedGateway({"understand": understand, "draft": draft, "verify": verify})
    c = TestClient(create_app(s, gw))
    c.headers["authorization"] = f"Bearer {KEY}"
    c.gw = gw
    return c


def envelope(**kw):
    env = {"requestId": "r1", "channel": "EMAIL", "senderRef": "s-1", "email": {"format": "eml", "contentBase64": base64.b64encode(EML).decode()}}
    env.update(kw)
    return env


def test_health(client):
    r = client.get("/v0/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"
    assert "gemini" not in r.text.lower()


def test_sync_run_actions_and_trace(client):
    r = client.post("/v0/enquiries?mode=sync", json=envelope())
    assert r.status_code == 200, r.text
    out = r.json()
    actions = [i["action"] for i in out["issues"]]
    assert actions == ["MANUAL_HANDLING", "REPLY_DIRECTLY", "MANUAL_HANDLING"]
    assert out["reply"]["safety"] == "SAFE_TO_REVIEW"
    assert out["reply"]["coversIssueIds"] == ["ISSUE-002"]
    assert out["attachments"][0]["status"] == "NOT_READ"
    assert out["signature"].startswith("v0=")
    # D3: the trace carries no email text and no model names or token counts
    trace = json.dumps(out["trace"]).lower()
    assert "priya" not in trace and "payment" not in trace and "gemini" not in trace and "token" not in trace
    assert "_usage" not in out


def test_addresses_never_reach_the_model(client):
    client.post("/v0/enquiries?mode=sync", json=envelope())
    sent = json.dumps([p for _, p in client.gw.calls])
    assert "@example.com" not in sent and "pace-mock.example" not in sent


def test_auth(client):  # E3
    r = client.post("/v0/enquiries", json=envelope(), headers={"authorization": "Bearer wrong"})
    assert r.status_code == 401


def test_malformed(client):  # E2
    r = client.post("/v0/enquiries", json={"requestId": "r1", "channel": "EMAIL"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "INVALID_REQUEST"
    r = client.post("/v0/enquiries", json=envelope(senderRef="someone@example.com"))
    assert r.status_code == 400
    r = client.post("/v0/enquiries", json=envelope(email={"format": "eml", "contentBase64": "%%%"}))
    assert r.status_code == 400 and r.json()["error"]["field"] == "email.contentBase64"


def test_idempotency(client):  # E1
    a = client.post("/v0/enquiries?mode=sync", json=envelope(idempotencyKey="k1")).json()
    n = len(client.gw.calls)
    b = client.post("/v0/enquiries?mode=sync", json=envelope(idempotencyKey="k1"))
    assert b.json()["runId"] == a["runId"] and b.headers.get("x-idempotent-replay") == "true"
    assert len(client.gw.calls) == n


def test_poll(client):
    r = client.post("/v0/enquiries", json=envelope())
    assert r.status_code == 202
    run_id = r.json()["runId"]
    got = client.get(f"/v0/runs/{run_id}").json()
    assert got["runId"] == run_id


def test_rate_limit(client):  # E6
    codes = [client.post("/v0/enquiries", json={"bad": 1}).status_code for _ in range(9)]
    assert codes[-1] == 429


def test_private_callback_refused(client):
    r = client.post("/v0/enquiries", json=envelope(callbackUrl="http://127.0.0.1:9000/cb"))
    assert r.status_code == 400 and r.json()["error"]["field"] == "callbackUrl"


def test_simulated_failure(client):  # E5
    out = client.post("/v0/enquiries?mode=sync", json=envelope(options={"simulate": "failure"})).json()
    assert out["runHealth"] == "FAILED" and out["reply"]["safety"] == "NOT_PRODUCED"


def _first(client):
    env = envelope()
    return env, client.post("/v0/enquiries?mode=sync", json=env).json()


def test_recheck_accept_refer(client):  # B1
    env, prev = _first(client)
    r = client.post(f"/v0/enquiries/{prev['runId']}/recheck", json={"request": env, "previousResult": prev,
                    "change": {"issueId": "ISSUE-002", "action": "REFER_TO_TEAM", "ownerTeamId": "PACE-ADM"}})
    out = r.json()
    assert r.status_code == 200 and out["recheck"]["status"] == "ACCEPTED"
    assert out["issues"][1]["action"] == "REFER_TO_TEAM" and out["issues"][1]["owner"]["teamId"] == "PACE-ADM"
    assert "ISSUE-002" not in out["reply"]["coversIssueIds"]
    assert out["handoffNotes"][0]["teamId"] == "PACE-ADM"


def test_recheck_reject_unanswerable(client):  # B2
    env, prev = _first(client)
    r = client.post(f"/v0/enquiries/{prev['runId']}/recheck", json={"request": env, "previousResult": prev,
                    "change": {"issueId": "ISSUE-003", "action": "REPLY_DIRECTLY"}})
    out = r.json()
    assert out["recheck"]["status"] == "REJECTED"
    assert [i["action"] for i in out["issues"]] == [i["action"] for i in prev["issues"]]


def test_recheck_tampered(client):  # B3
    env, prev = _first(client)
    prev["issues"][0]["action"] = "REPLY_DIRECTLY"
    r = client.post(f"/v0/enquiries/{prev['runId']}/recheck", json={"request": env, "previousResult": prev,
                    "change": {"issueId": "ISSUE-002", "action": "MANUAL_HANDLING"}})
    assert r.status_code == 409
    _, prev2 = _first(client)
    r = client.post(f"/v0/enquiries/{prev2['runId']}/recheck", json={"request": envelope(senderRef="other"), "previousResult": prev2,
                    "change": {"issueId": "ISSUE-002", "action": "MANUAL_HANDLING"}})
    assert r.status_code == 409


def test_multipart_eml(client):
    r = client.post("/v0/enquiries?mode=sync", data={"envelope": json.dumps({"requestId": "m1", "channel": "EMAIL"})},
                    files={"email": ("A2-01.eml", EML, "message/rfc822")})
    assert r.status_code == 200, r.text
    assert len(r.json()["issues"]) == 3
