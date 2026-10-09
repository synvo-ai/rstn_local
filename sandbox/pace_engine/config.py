"""Settings from environment variables. Model names live here only; they never appear in API output."""
import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _env(name, default=None):
    return os.environ.get(name, default)


@dataclass
class Settings:
    data_dir: Path = field(default_factory=lambda: Path(_env("PACE_DATA_DIR", ROOT / "data")))
    db_path: Path = field(default_factory=lambda: Path(_env("PACE_DB", ROOT / "var" / "sandbox.db")))
    keys_file: Path = field(default_factory=lambda: Path(_env("PACE_KEYS_FILE", ROOT / "var" / "keys.yaml")))
    signing_secret: str = field(default_factory=lambda: _env("PACE_SIGNING_SECRET", ""))
    gemini_api_key: str = field(default_factory=lambda: _env("GEMINI_API_KEY", ""))
    # One model per stage, so a cheaper model can take the simpler steps.
    model_understand: str = field(default_factory=lambda: _env("PACE_MODEL_UNDERSTAND", "gemini-3.8-flash"))
    model_draft: str = field(default_factory=lambda: _env("PACE_MODEL_DRAFT", "gemini-3.8-flash"))
    model_verify: str = field(default_factory=lambda: _env("PACE_MODEL_VERIFY", "gemini-3.8-flash"))
    model_timeout_s: float = float(_env("PACE_MODEL_TIMEOUT_S", "60"))
    # B39: per-email token budget; over budget degrades to Manual handling instead of overspending.
    max_input_tokens_per_email: int = int(_env("PACE_MAX_INPUT_TOKENS", "60000"))
    max_thread_messages: int = int(_env("PACE_MAX_THREAD_MESSAGES", "10"))
    max_chars_per_thread_message: int = int(_env("PACE_MAX_THREAD_CHARS", "2000"))
    max_body_chars: int = int(_env("PACE_MAX_BODY_CHARS", "12000"))
    max_attachment_bytes: int = int(_env("PACE_MAX_ATTACHMENT_BYTES", str(10 * 1024 * 1024)))
    max_request_bytes: int = int(_env("PACE_MAX_REQUEST_BYTES", str(40 * 1024 * 1024)))
    # Sandbox access limits per key (protocol §4).
    rate_limit_per_hour: int = int(_env("PACE_RATE_PER_HOUR", "60"))
    max_running_per_key: int = int(_env("PACE_MAX_RUNNING_PER_KEY", "2"))
    callback_retry_delays_s: tuple = tuple(float(x) for x in _env("PACE_CALLBACK_RETRIES", "2,10,60").split(","))
    # Callbacks to private or loopback addresses are refused unless this is set (local testing only).
    allow_private_callbacks: bool = _env("PACE_ALLOW_PRIVATE_CALLBACKS", "0") == "1"
    sandbox: bool = _env("PACE_SANDBOX", "1") == "1"


settings = Settings()
