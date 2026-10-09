"""Issue a sandbox API key for one tester. The key is printed once; only its hash is stored.

Run: python3 tools/issue_key.py <keyId> "<tester name>"   (writes var/keys.yaml, or $PACE_KEYS_FILE)
"""
import hashlib
import os
import secrets
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    key_id, tester = sys.argv[1], sys.argv[2]
    path = Path(os.environ.get("PACE_KEYS_FILE", ROOT / "var" / "keys.yaml"))
    path.parent.mkdir(parents=True, exist_ok=True)
    data = yaml.safe_load(path.read_text()) if path.exists() else None
    data = data or {"keys": []}
    if any(k["keyId"] == key_id for k in data["keys"]):
        sys.exit(f"keyId {key_id} already exists")
    key = "pk_sbx_" + secrets.token_urlsafe(24)
    cb = "cbs_" + secrets.token_urlsafe(24)
    data["keys"].append({"keyId": key_id, "tester": tester, "sha256": hashlib.sha256(key.encode()).hexdigest(), "callbackSecret": cb, "active": True})
    path.write_text(yaml.safe_dump(data, sort_keys=False))
    os.chmod(path, 0o600)
    print(f"keyId:          {key_id}\napiKey:         {key}\ncallbackSecret: {cb}\n(stored in {path}; the API key is not shown again)")


if __name__ == "__main__":
    main()
