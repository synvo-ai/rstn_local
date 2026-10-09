# PaCE enquiry engine — sandbox v1

Internal. The engine behind the sandbox RSTN gets on 21 October (`../sandbox-testing-protocol.md`). Sandbox v1 is engine only, with mock data. The privacy connector and attachment reading come in v2 (28 October).

Model names and token counts appear only in the server log and in `tools/evaluate.py` output. They are never in API responses.

## Layout

| Path | What |
|---|---|
| `pace_engine/models.py` | API v0 request and result schemas (B7). This is the contract for the API spec draft due 14 Oct. |
| `pace_engine/mime.py` | `.eml` / `.msg` / plain text / web form → one message; drops addresses; HTML to text; cuts quoted history; lists attachments. |
| `pace_engine/language.py` | Phase 1 English-only check before any model call (A10). |
| `pace_engine/registry.py` | Programme resolution (RESOLVED / AMBIGUOUS / UNRESOLVED) and routing by intent (M2 format). |
| `pace_engine/knowledge.py` | Knowledge items and BM25 retrieval, restricted to the resolved programme (M1 format). |
| `pace_engine/prompts.py` | Instructions and JSON schemas for the three model steps: understand, draft, verify. |
| `pace_engine/pipeline.py` | The run: language check → understand → resolve and route → decide action → draft → rule checks → verify. Also the staff re-check. |
| `pace_engine/llm.py` | Gemini gateway (one model per stage, set by env) and a scripted gateway for tests. |
| `pace_engine/api.py` | HTTP API: keys, rate limit, idempotency, sync / poll / callback, signed results, re-check, SSRF guard on callbacks. |
| `pace_engine/store.py` | SQLite run store for polling during the testing window. |
| `data/` | **Mock** registry, knowledge seed and reply templates. Every fact is made up. |
| `testpack/cases.yaml` | Mock emails with expected results (M4 seed, 20 cases). `tools/make_testpack.py` builds `testpack/eml/`. |
| `tools/` | `evaluate.py` (B15 harness), `client.py` (sample client, start of B35), `issue_key.py` (tester keys). |

## How a run decides

The model reads and writes; the application decides.

- **Understand** (model) lists the sender's questions: intent, programme words used, sender facts, and whether each is already answered in the thread. It also gives the language and whether the message is an enquiry at all.
- **Registry** resolves the programme and routes by intent. Each intent has a handling rule:
  - `ANSWER_DESK`: reply from knowledge;
  - `REFER`: the owning team;
  - `INSTITUTIONAL`: needs records → Manual handling;
  - `MANUAL`.
- **Rules** set the action:
  - unclear programme → Ask for clarification;
  - no knowledge found → Manual handling;
  - otherwise Reply directly, pending the draft.
- **Draft** (model) gets only the evidence for each issue. It must copy the controlled sentences (referral, clarification, manual) word for word. If the evidence does not answer the question, it says so, and the issue becomes Manual handling.
- **Rule checks:**
  - every claim appears verbatim in the draft and cites evidence given for that issue;
  - every controlled sentence and the sign-off are present.

  Any failure means **BLOCKED**, and the model verify step is skipped.
- **Verify** (model) acts as a critic. It looks for unsupported facts, statements about the sender's records, answers to non-reply issues, and facts from the wrong programme.
- **Re-check:** the client resends the original request, the signed previous result and the change. Only draft and verify run again. A change to Reply directly is rejected in three cases:
  - the question needs records;
  - the knowledge has no answer;
  - the programme is unclear.

## Run it

```bash
cd sandbox
python3 tools/make_testpack.py                       # build testpack/eml from cases.yaml
python3 -m pytest -q                                 # offline tests (scripted model)
bash -ic 'python3 tools/evaluate.py'                 # test pack against Gemini (GEMINI_API_KEY from ~/.bashrc)
python3 tools/issue_key.py rstn-1 "RSTN tester 1"    # prints the key once; hash in var/keys.yaml
bash -ic 'python3 -m pace_engine --port 8090'        # API; docs at /v0/docs
PACE_KEY=pk_sbx_... python3 tools/client.py send testpack/eml/A2-01.eml --save var/a.json
PACE_KEY=pk_sbx_... python3 tools/client.py recheck var/a.json ISSUE-003 REFER_TO_TEAM --team PACE-ADM
```

Settings are env variables (`pace_engine/config.py`):
- `PACE_MODEL_UNDERSTAND`, `PACE_MODEL_DRAFT`, `PACE_MODEL_VERIFY`
- `PACE_MAX_INPUT_TOKENS` (per-email budget, B39)
- `PACE_RATE_PER_HOUR`, `PACE_MAX_RUNNING_PER_KEY`
- `PACE_ALLOW_PRIVATE_CALLBACKS=1` (local testing only)

`var/` holds the database, keys, signing key, logs and evaluation results. It is not committed.

## First results (9 Oct 2026, gemini-3.8-flash on all three steps)

- **Test pack:** 20 mock cases. 20/20 pass on actions, programme and owner. This came after fixing two wrong expectations and making issue splitting stable (one issue per intent and programme; same-intent issues are merged by rule).
- **Per email:** ~10 s with three sequential model calls, and ~1.7k input / ~0.4k output tokens. At today's price that's about US$0.0026, or S$0.003.
- **Non-English emails and non-enquiries** stop before the expensive steps. Non-English emails make no model call at all.

## Not in v1 (next)

- **Attachments.** They are listed but not read; issues that rely on one note this. Attachment reading and the connector arrive in v2 (B24, B11, B40).
- **Knowledge, registry and templates are a small mock seed.** M1/M2 (Li-kai) replace them in the same YAML format.
- **The test pack has 20 cases.** M4 grows it to 50 by 14 Oct and ~150 by 28 Oct.
- **The sandbox host isn't chosen yet (S2, due 12 Oct).** Today the server binds to 127.0.0.1. Public exposure needs TLS and an IP allowlist in front.
- **`.msg` input needs `pip install extract-msg`** (optional dependency).
