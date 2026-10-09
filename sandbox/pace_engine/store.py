"""Sandbox run store (SQLite). Keeps results for polling during the testing window; token usage is kept
in its own column for our cost reports and never returned. Production keeps no email content (B20)."""
import json
import sqlite3
import threading
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY,
  key_id TEXT NOT NULL,
  request_id TEXT NOT NULL,
  idem_key TEXT,
  kind TEXT NOT NULL,              -- enquiry | recheck
  status TEXT NOT NULL,            -- QUEUED | RUNNING | COMPLETED
  created_at REAL NOT NULL,
  result TEXT,
  usage TEXT,
  callback_url TEXT,
  callback_status TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS runs_idem ON runs(key_id, idem_key) WHERE idem_key IS NOT NULL;
"""


class Store:
    def __init__(self, path: Path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._db.executescript(SCHEMA)

    def _exec(self, sql, args=()):
        with self._lock:
            cur = self._db.execute(sql, args)
            self._db.commit()
            return cur

    def find_idem(self, key_id, idem_key):
        if not idem_key:
            return None
        return self._exec("SELECT * FROM runs WHERE key_id=? AND idem_key=?", (key_id, idem_key)).fetchone()

    def create(self, run_id, key_id, request_id, idem_key, kind, callback_url):
        try:
            self._exec("INSERT INTO runs(run_id,key_id,request_id,idem_key,kind,status,created_at,callback_url) VALUES (?,?,?,?,?,?,?,?)",
                       (run_id, key_id, request_id, idem_key, kind, "QUEUED", time.time(), callback_url))
            return True
        except sqlite3.IntegrityError:
            return False

    def set_status(self, run_id, status):
        self._exec("UPDATE runs SET status=? WHERE run_id=?", (status, run_id))

    def complete(self, run_id, result, usage):
        self._exec("UPDATE runs SET status='COMPLETED', result=?, usage=? WHERE run_id=?", (json.dumps(result, ensure_ascii=False), json.dumps(usage), run_id))

    def set_callback(self, run_id, status):
        self._exec("UPDATE runs SET callback_status=? WHERE run_id=?", (status, run_id))

    def get(self, run_id):
        return self._exec("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()

    def reset(self, key_id):
        return self._exec("DELETE FROM runs WHERE key_id=?", (key_id,)).rowcount
