"""HTTP API v0 for the sandbox (protocol §4–5).

POST /v0/enquiries                    submit one email (JSON, or multipart with the .eml as a file); ?mode=sync waits
GET  /v0/runs/{runId}                 status or result
POST /v0/enquiries/{runId}/recheck    staff change to one issue; original request + signed previous result
GET  /v0/health                       up check
"""
import asyncio
import base64
import collections
import hashlib
import hmac
import ipaddress
import json
import logging
import os
import secrets
import socket
import time
import uuid
from urllib.parse import urlparse

import httpx
import yaml
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from . import ENGINE_VERSION, signing
from .config import Settings
from .mime import InputError
from .models import EnquiryRequest, RecheckRequest
from .pipeline import Engine, Tracker
from .store import Store

log = logging.getLogger("pace.api")


def err(status, code, message, field=None, headers=None):
    body = {"error": {"code": code, "message": message, **({"field": field} if field else {})}}
    return JSONResponse(body, status_code=status, headers=headers)


def validation_error(e: ValidationError):
    first = e.errors()[0]
    field = ".".join(str(p) for p in first["loc"]) or None
    return err(400, "INVALID_REQUEST", first["msg"], field)


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def load_keys(path):
    try:
        d = yaml.safe_load(open(path)) or {}
    except FileNotFoundError:
        log.warning("no keys file at %s; every call will be rejected", path)
        return {}
    return {k["sha256"]: k for k in d.get("keys", []) if k.get("active", True)}


def callback_allowed(url, allow_private):
    """Refuse callbacks to private, loopback or link-local addresses (the sandbox must not call into our network)."""
    u = urlparse(url)
    if u.scheme not in ("https", "http") or not u.hostname:
        return False
    if allow_private:
        return True
    if u.scheme != "https":
        return False
    try:
        addrs = {ai[4][0] for ai in socket.getaddrinfo(u.hostname, u.port or 443)}
    except socket.gaierror:
        return False
    return all(ipaddress.ip_address(a).is_global for a in addrs)


def create_app(settings: Settings = None, gateway=None) -> FastAPI:
    settings = settings or Settings()
    if not settings.signing_secret:  # keep one secret across restarts so earlier results can still be re-checked
        path = settings.db_path.parent / "signing.key"
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(secrets.token_urlsafe(32))
            os.chmod(path, 0o600)
        settings.signing_secret = path.read_text().strip()
    if gateway is None:
        from .llm import GeminiGateway
        gateway = GeminiGateway(settings.gemini_api_key, settings.model_timeout_s)
    engine = Engine(settings, gateway)
    store = Store(settings.db_path)
    keys = load_keys(settings.keys_file)
    hits = collections.defaultdict(collections.deque)
    sems = collections.defaultdict(lambda: asyncio.Semaphore(settings.max_running_per_key))
    tasks = set()

    app = FastAPI(title="PaCE enquiry engine — sandbox", version=ENGINE_VERSION, docs_url="/v0/docs", openapi_url="/v0/openapi.json", redoc_url=None)
    app.state.engine, app.state.store, app.state.keys = engine, store, keys

    def auth(request: Request):
        h = request.headers.get("authorization", "")
        token = h[7:].strip() if h.lower().startswith("bearer ") else request.headers.get("x-api-key", "")
        if not token:
            return None
        return keys.get(hashlib.sha256(token.encode()).hexdigest())

    def rate_limited(key_id):
        q, t = hits[key_id], time.time()
        while q and q[0] < t - 3600:
            q.popleft()
        if len(q) >= settings.rate_limit_per_hour:
            return int(q[0] + 3600 - t) + 1
        q.append(t)
        return 0

    def public(result):
        return {k: v for k, v in result.items() if not k.startswith("_")}

    async def deliver(run_id, url, result, key):
        body = json.dumps(result, ensure_ascii=False).encode()
        sig = "sha256=" + hmac.new(key.get("callbackSecret", "").encode(), body, hashlib.sha256).hexdigest()
        headers = {"content-type": "application/json", "x-pace-run-id": run_id, "x-pace-signature": sig}
        for attempt, delay in enumerate((0,) + settings.callback_retry_delays_s, 1):
            await asyncio.sleep(delay)
            if not callback_allowed(url, settings.allow_private_callbacks):
                store.set_callback(run_id, "REFUSED")
                return
            try:
                async with httpx.AsyncClient(timeout=10, follow_redirects=False) as c:
                    r = await c.post(url, content=body, headers=headers)
                if r.status_code < 300:
                    store.set_callback(run_id, f"DELIVERED attempt {attempt}")
                    return
                store.set_callback(run_id, f"HTTP {r.status_code} attempt {attempt}")
            except httpx.HTTPError as e:
                store.set_callback(run_id, f"{type(e).__name__} attempt {attempt}")
        store.set_callback(run_id, "FAILED; result available by polling")

    async def process(run_id, prep, key, received_at, digest):
        async with sems[key["keyId"]]:
            store.set_status(run_id, "RUNNING")
            try:
                result = await engine.run(prep, run_id, received_at)
            except Exception:
                log.exception("run %s crashed", run_id)
                result = engine._result(prep.request, run_id, received_at, Tracker(0), "FAILED",
                                        {"messageType": "ENQUIRY", "emailAction": {"action": "MANUAL_HANDLING", "reason": "The engine could not complete this email; use the fallback acknowledgement."}},
                                        [], {"safety": "NOT_PRODUCED"}, prep.attachments)
        usage = result.get("_usage", {})
        out = public(result)
        out["signature"] = signing.sign(settings.signing_secret, out, digest)
        store.complete(run_id, out, usage)
        log.info("run=%s key=%s health=%s issues=%d in=%s out=%s", run_id, key["keyId"], out["runHealth"], len(out["issues"]), usage.get("input"), usage.get("output"))
        if prep.request.callbackUrl:
            t = asyncio.create_task(deliver(run_id, str(prep.request.callbackUrl), out, key))
            tasks.add(t)
            t.add_done_callback(tasks.discard)
        return out

    async def read_enquiry(request: Request):
        ctype = request.headers.get("content-type", "")
        if int(request.headers.get("content-length") or 0) > settings.max_request_bytes:
            raise InputError("body", "request too large")
        if ctype.startswith("multipart/form-data"):
            form = await request.form()
            env = json.loads(form.get("envelope") or "{}")
            f = form.get("email")
            if f is not None and hasattr(f, "read"):
                raw = await f.read()
                fmt = "msg" if (f.filename or "").lower().endswith(".msg") else "eml"
                env["email"] = {"format": fmt, "contentBase64": base64.b64encode(raw).decode()}
            thread = []
            for tf in form.getlist("thread"):
                raw = await tf.read()
                thread.append({"format": "msg" if (tf.filename or "").lower().endswith(".msg") else "eml", "contentBase64": base64.b64encode(raw).decode()})
            if thread:
                env["thread"] = thread
            return env
        return json.loads(await request.body() or b"{}")

    @app.get("/v0/health")
    async def health():
        return {"status": "ok", "engineVersion": ENGINE_VERSION, "knowledgeVersion": engine.kb.version, "configVersion": engine.config_version, "sandbox": settings.sandbox}

    @app.post("/v0/enquiries")
    async def submit(request: Request, mode: str = "async"):
        key = auth(request)
        if key is None:
            return err(401, "UNAUTHORIZED", "missing or invalid API key")
        wait = rate_limited(key["keyId"])
        if wait:
            return err(429, "RATE_LIMITED", f"over {settings.rate_limit_per_hour} requests per hour", headers={"retry-after": str(wait)})
        try:
            body = await read_enquiry(request)
            req = EnquiryRequest.model_validate(body)
            if req.callbackUrl and not callback_allowed(str(req.callbackUrl), settings.allow_private_callbacks):
                return err(400, "INVALID_REQUEST", "callbackUrl must be a public https address", "callbackUrl")
            prev = store.find_idem(key["keyId"], req.idempotencyKey)
            if prev is not None:
                return JSONResponse(json.loads(prev["result"]) if prev["result"] else {"runId": prev["run_id"], "requestId": prev["request_id"], "status": prev["status"]},
                                    status_code=200, headers={"x-idempotent-replay": "true"})
            prep = engine.prepare(req)
        except ValidationError as e:
            return validation_error(e)
        except InputError as e:
            return err(400, "INVALID_REQUEST", str(e), e.field)
        except json.JSONDecodeError:
            return err(400, "INVALID_REQUEST", "body is not valid JSON")
        run_id = "run_" + uuid.uuid4().hex[:20]
        if not store.create(run_id, key["keyId"], req.requestId, req.idempotencyKey, "enquiry", str(req.callbackUrl) if req.callbackUrl else None):
            prev = store.find_idem(key["keyId"], req.idempotencyKey)
            return JSONResponse({"runId": prev["run_id"], "requestId": prev["request_id"], "status": prev["status"]}, headers={"x-idempotent-replay": "true"})
        digest = signing.request_digest(req.model_dump(mode="json"))
        received = now_iso()
        if mode == "sync":
            return JSONResponse(await process(run_id, prep, key, received, digest))
        t = asyncio.create_task(process(run_id, prep, key, received, digest))
        tasks.add(t)
        t.add_done_callback(tasks.discard)
        return JSONResponse({"runId": run_id, "requestId": req.requestId, "status": "QUEUED", "poll": f"/v0/runs/{run_id}"}, status_code=202)

    @app.get("/v0/runs/{run_id}")
    async def get_run(run_id: str, request: Request):
        key = auth(request)
        if key is None:
            return err(401, "UNAUTHORIZED", "missing or invalid API key")
        row = store.get(run_id)
        if row is None or row["key_id"] != key["keyId"]:
            return err(404, "NOT_FOUND", "no such run for this key")
        if row["result"]:
            out = json.loads(row["result"])
            return JSONResponse(out, headers={"x-callback-status": row["callback_status"] or "none"})
        return {"runId": run_id, "requestId": row["request_id"], "status": row["status"]}

    @app.post("/v0/enquiries/{run_id}/recheck")
    async def recheck(run_id: str, request: Request):
        key = auth(request)
        if key is None:
            return err(401, "UNAUTHORIZED", "missing or invalid API key")
        wait = rate_limited(key["keyId"])
        if wait:
            return err(429, "RATE_LIMITED", f"over {settings.rate_limit_per_hour} requests per hour", headers={"retry-after": str(wait)})
        try:
            rr = RecheckRequest.model_validate(json.loads(await request.body() or b"{}"))
        except ValidationError as e:
            return validation_error(e)
        except json.JSONDecodeError:
            return err(400, "INVALID_REQUEST", "body is not valid JSON")
        prev = rr.previousResult
        if prev.get("runId") != run_id:
            return err(400, "INVALID_REQUEST", "previousResult.runId does not match the URL", "previousResult.runId")
        digest = signing.request_digest(rr.request.model_dump(mode="json"))
        if not signing.verify(settings.signing_secret, prev, digest):
            return err(409, "SIGNATURE_MISMATCH", "the previous result or the original request was changed; resend both exactly as they were")
        try:
            prep = engine.prepare(rr.request)
        except InputError as e:
            return err(400, "INVALID_REQUEST", str(e), "request." + e.field)
        new_id = "run_" + uuid.uuid4().hex[:20]
        store.create(new_id, key["keyId"], rr.request.requestId, None, "recheck", None)
        async with sems[key["keyId"]]:
            result = await engine.recheck(prep, prev, rr.change, new_id, now_iso())
        usage = result.pop("_usage", {})
        out = public(result)
        out["signature"] = signing.sign(settings.signing_secret, out, digest)
        store.complete(new_id, out, usage)
        return JSONResponse(out)

    return app
