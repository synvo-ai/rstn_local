"""Signed results keep the engine stateless: a staff re-check resends the original request and the previous
result, and the signature proves neither was changed (scenario B3)."""
import hashlib
import hmac
import json


def _canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def request_digest(request_dict):
    return hashlib.sha256(_canon(request_dict)).hexdigest()


def sign(secret, result_dict, req_digest):
    body = {k: v for k, v in result_dict.items() if k != "signature"}
    return "v0=" + hmac.new(secret.encode(), _canon({"request": req_digest, "result": body}), hashlib.sha256).hexdigest()


def verify(secret, result_dict, req_digest):
    sig = result_dict.get("signature") or ""
    return hmac.compare_digest(sig, sign(secret, result_dict, req_digest))
