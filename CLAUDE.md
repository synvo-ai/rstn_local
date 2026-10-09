# rstn_local

Synvo's working repo for the NTU PaCE enquiry project. RSTN builds the system that triages PaCE general-enquiry emails; Synvo supplies the AI engine inside it. Guowei is AI tech lead and works with Li-kai on the build; Lisa handles scope and commercial.

`TODO.md` is the live plan: items (B/M/A/S numbers), owners, dates and the decision log. Read it before planning work and update it when something is decided or done.

## Layout

- `sandbox/`: the sandbox engine (Python, API v0). See `sandbox/README.md`.
- `ntu-pace-correspondence-intelligence/`: the earlier TypeScript POC, a separate git repo. Reference only; the sandbox is a rewrite, not an extraction.
- `sandbox-testing-protocol.md`, `response-to-rstn.md`, `questions-for-rstn.md`: shared with RSTN.
- `deployment-options.md`, `hosting-and-scaling.md`, `draft-solution.md`, `requirements-summary.md`, `cost-bench/`, `unit-cost.html`: internal.
- `workflow-and-architecture.html` and `wa.pdf`: internal. Never shared with RSTN.

## Timeline (POC with mock data, 8–28 Oct 2026)

- S2, where the sandbox is hosted: 12 Oct.
- API spec and testing protocol drafts to RSTN: 14 Oct. The spec comes from `sandbox/pace_engine/models.py`, with internal fields removed.
- Sandbox v1 (engine only): 21 Oct.
- Sandbox v2 (privacy connector and attachment reading), handover and demo: 28 Oct.
- RSTN testing: 28 Oct – about 4 Nov, then review about 5 Nov.

Phase 1 is English only (non-English emails go to Manual handling). Self-learning is not in the POC. The Jeff decision-model spike (B43) is deferred.

## Rules for RSTN-facing content

- Never say the engine uses a cloud model, and never name a model or provider. Model names stay in internal docs, the server log and `tools/evaluate.py` output, never in API responses.
- Keep it high level. Don't mention JEPA, Jeff or a vector database.

## Writing and git

- Markdown: one line per paragraph, no hard wraps. Put a blank line between header fields.
- In this repo, commit and push without asking.
- `GEMINI_API_KEY` is set in `~/.bashrc`. Run anything that needs it through `bash -ic '...'`, and never print the key.
- Don't use the DavidAU/Qwen3.6-27B-Fable-Fus-711 model.

## Sandbox engine: current state (9 Oct 2026, v1)

- Pipeline: language check (no model call), understand (model), registry resolution and routing, rule-based action, draft (model, evidence only, controlled sentences verbatim), rule checks, verify (model). The model reads and writes; rules decide.
- Gemini on all three model steps, set per step by env variables. On the 20 mock cases: 20/20 pass, about 10 s and S$0.003 per email.
- `data/` (knowledge, registry, templates) and `testpack/` are made up. Li-kai's M1/M2 output replaces `data/` in the same YAML format.
- `var/` holds keys, the signing key, the database, logs and evaluation results. It is never committed.

### Attachments and OCR: not built

- Attachments are listed with a status (`NOT_READ`, `TOO_LARGE`, `UNSUPPORTED`, or `IGNORED` for small inline images). The model sees only each file's name and type. An issue that depends on an unread attachment records that in its missing information.
- Planned for v2:
  - B11: the attachment reader.
  - B33: ONNX-based classic OCR on CPU, pip-installable. GLM-OCR is too slow on CPU with the 10-page cap.
  - B40: MinerU for PDFs with complex layouts. Whether it fits in the connector is still open, because it pulls in PyTorch.

### Masking: only partly built

- Done in `mime.py`:
  - sender, To and CC addresses are dropped;
  - web-form contact fields (email, phone, NRIC, address) are dropped;
  - quoted history is cut.
- Logs and traces contain no email text.
- Not done:
  - the email body goes to the model unmasked, so names, phone numbers, NRIC and IDs written in the text pass through;
  - the sender's display name goes into the drafting step's greeting;
  - there is no placeholder map, no restoring of names, and no image redaction.
- This is acceptable only while every email is mock data. Body masking must be in place before any real email goes through.
- Planned for v2, B24/B19: the privacy connector as a Python package that runs in RSTN's network. It parses the email, reads attachments locally, replaces personal details with placeholders and keeps the map in memory, sends only masked text to the engine, and restores the real values in the reply, summaries and handoff notes. M5 (mock attachments with made-up personal details) is needed to measure the masking miss rate.
- The GPU server's model router listens on `0.0.0.0:8080` with no authentication (B31). It must be locked down before any NTU data reaches it.
