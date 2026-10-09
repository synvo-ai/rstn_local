"""Model gateway: one JSON-in, JSON-out call per stage. Model names and token counts stay in the internal
log; the API result carries neither."""
import asyncio
import json
import logging
import time
from dataclasses import dataclass

log = logging.getLogger("pace.llm")


class ModelError(RuntimeError):
    pass


@dataclass
class Usage:
    input: int = 0
    output: int = 0
    thinking: int = 0

    def add(self, other):
        self.input += other.input
        self.output += other.output
        self.thinking += other.thinking


class GeminiGateway:
    def __init__(self, api_key, timeout_s=60.0, retries=2):
        from google import genai
        if not api_key:
            raise ModelError("GEMINI_API_KEY is not set")
        self._client = genai.Client(api_key=api_key)
        self.timeout_s = timeout_s
        self.retries = retries

    def _config(self, model, system, schema):
        from google.genai import types
        if model.startswith("gemini-2.5"):
            tc = types.ThinkingConfig(thinking_budget=0)
        else:
            tc = types.ThinkingConfig(thinking_level="low")
        return types.GenerateContentConfig(system_instruction=system, response_mime_type="application/json",
                                           response_json_schema=schema, thinking_config=tc, temperature=0.2,
                                           automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True))

    async def json(self, stage, model, system, payload, schema):
        cfg = self._config(model, system, schema)
        contents = json.dumps(payload, ensure_ascii=False)
        last = None
        for attempt in range(self.retries + 1):
            t0 = time.time()
            try:
                r = await asyncio.wait_for(self._client.aio.models.generate_content(model=model, contents=contents, config=cfg), self.timeout_s)
                u = r.usage_metadata
                usage = Usage(u.prompt_token_count or 0, u.candidates_token_count or 0, u.thoughts_token_count or 0)
                log.info("stage=%s model=%s in=%d out=%d think=%d ms=%d", stage, model, usage.input, usage.output, usage.thinking, (time.time() - t0) * 1000)
                if not r.text:
                    raise ModelError(f"{stage}: empty response")
                return json.loads(r.text), usage
            except (asyncio.TimeoutError, json.JSONDecodeError, ModelError) as e:
                last = e
            except Exception as e:  # provider errors; retry the transient ones
                last = e
                if not any(code in str(e) for code in ("429", "500", "503", "UNAVAILABLE", "RESOURCE_EXHAUSTED")):
                    break
            await asyncio.sleep(1.5 * (attempt + 1))
        log.warning("stage=%s model=%s failed: %s", stage, model, type(last).__name__)
        raise ModelError(f"{stage} failed: {type(last).__name__}")


class ScriptedGateway:
    """Test double: `handlers[stage](payload) -> dict`."""

    def __init__(self, handlers):
        self.handlers = handlers
        self.calls = []

    async def json(self, stage, model, system, payload, schema):
        self.calls.append((stage, payload))
        h = self.handlers.get(stage)
        if h is None:
            raise ModelError(f"no handler for {stage}")
        out = h(payload)
        if isinstance(out, Exception):
            raise out
        return out, Usage(len(json.dumps(payload)) // 4, len(json.dumps(out)) // 4, 0)
