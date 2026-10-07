# NTU PaCE / RSTN — TODO

Tracks open questions for RSTN/NTU and Synvo's own work. Context: `requirements-summary.md`, `draft-solution.md`, `unit-cost.html`.

Status: `[ ]` open · `[~]` in progress · `[x]` done · `[-]` dropped Owners are suggestions; adjust after Lisa consolidates scope.

---

## A. Questions for RSTN / NTU

### Knowledge and data sources
- [ ] **A1. Knowledge base access.** Where does approved knowledge live on RSTN's on-prem server, and what interface do we get: query API, versioned snapshot export, or a vector index? Who approves and revokes content, and how are versions exposed? *(We propose syncing a versioned copy to our hosted index; live query API as fallback.)*
- [ ] **A2. Acceptance of the proposed setup** (hosted engine + privacy connector in RSTN's network). Does NTU policy allow masked text to leave NTU for processing in Singapore, nothing retained? Can RSTN host the connector? Internal: approved model providers and region still to settle; do not raise model/provider on the 2026-10-08 call.
- [ ] **A3. Programme registry.** Does an authoritative list of programmes, aliases, status and owning teams exist, or must it be built? Customer said no master directory exists today. Who maintains it?
- [ ] **A4. Routing/ownership directory.** Owner per programme × intent (admission, fees, credit transfer…), with team inboxes. Read access for us?
- [ ] **A5. Sample emails.** NTU will not share historical emails for pre-training (confirmed 2026-10-05), but sample emails are available for reference. Ask for a few hundred, de-identified, covering main programmes, multi-question, follow-ups and attachments, each with how PaCE handled it (answered / forwarded to whom / asked for details). Who de-identifies, and who confirms our labels?
- [ ] **A6. Other approved sources.** FAQs, policies, fee tables, intake calendars: which, where, how current. Confirm NTU public programme pages are an approved source (the POC cites them).
- [ ] **A7. Institutional state.** Any authorised read interface for payment, application or TMS status? If not, confirm these stay Manual handling for phase 1.

### Integration contract
- [ ] **A8. XML input contract.** Schema or sample payloads; how thread/reply links are identified; attachments inline (base64) or by reference; size limits; web-form fields.
- [ ] **A9. Output consumption.** Which result fields RSTN's UI will show; XML or JSON back; sync response or callback.
- [ ] **A10. Staff overrides.** Will RSTN call us to validate a staff change of handling (slide 6 behaviour), or handle it on their side?
- [ ] **A11. Failure policy.** What RSTN does on `FAILED` / `BLOCKED` runs; who owns the static fallback acknowledgement wording.
- [ ] **A12. Volume and latency.** Peak emails per hour, acceptable latency per email, sync vs async, expected concurrency. (Round A median is ~13 s sequential.)

### Multimodal
- [ ] **A13. Sample screenshots/attachments** (10–30, redacted). Mix of receipts, certificates, portal screenshots, error dialogs? Share of emails that carry them. Decides OCR vs vision and attachment cost.

### Governance and commercial
- [ ] **A14. Retention and audit.** How long we may keep raw email, traces and logs; redaction rules; audit export format for "decision audit and service reporting".
- [ ] **A15. RSTN architecture diagram.** Request theirs (Faye's suggestion) and reconcile with ours.
- [ ] **A16. Acceptance criteria.** Which success measures (routing accuracy, first-contact resolution, handling time) define phase-1 acceptance, and the target numbers.
- [ ] **A18. Data protection terms.** NTU's PDPA requirements for a data intermediary, DPA template, retention limits, security assessment they need from us (questionnaire, pen test).
- [ ] **A17. Environments.** Test/UAT access, sandbox data, go-live date, who supports in production.

## B. Synvo internal work

**Owners:** engine build is owned by Guowei, with Li-kai. Unmarked engine items default to Guowei.

**Dev/test environment (before cloud deployment):** our GPU server (`MICL-LoyCCWS3`, 2 × Quadro RTX 8000 48 GB, 12 CPU, 62 GB RAM). A llama.cpp router (`/etc/systemd/system/llama-router.service`) serves an OpenAI-compatible API on port 8080 (GPU 1, at most 2 models loaded, idle models unload after 5 min). Models are configured in `/home/gwwang/workspace/models/models.ini`:
- OCR: `GLM-OCR` (Q8_0, greedy decoding).
- Vision-language: `unsloth/Qwen3.8-27B` (Q8_0 and Q4_K_M, with `mmproj`), for screenshots that need more than OCR.
- Text: `Qwen/Qwen3.6-35B-A3B` (Q8 and Q4), `unsloth/GLM-4.7-Flash`, `Jackrong/Qwopus3.6`.
- Do not use the uncensored community fine-tune (`DavidAU/Qwen3.6-27B-Fable-Fus-711`) for this project.


### Now (this week)
- [~] **B1. Requirement summary and draft solution** — `requirements-summary.md`, `draft-solution.md` (Guowei). Revised after reviewing images.
- [~] **B2. Workflow + architecture diagram and cost-per-email draft** — customer version `workflow-and-architecture.html`, internal cost `unit-cost.html` (Guowei → Lisa for the 1-pager).
- [~] **B3. Send question list to RSTN before the technical call on Thu 2026-10-08 10:00** — `questions-for-rstn.md` (Part 1: our understanding to confirm; Part 2: questions with our proposals). Share the Workflow and Architecture page with RSTN at the same time. Commercial 1-pager goes separately (Saim → Steven). Also send `response-to-rstn.md`: answers to RSTN's 16 questions, with questions back R1–R14.
- [ ] **B22. Prepare for the call**: draft request/response field list to walk through (`draft-solution.md` §7); agree internally who answers what (Guowei: engine/API; Li-kai: models/data; Lisa: scope/commercial).
- [ ] **B4. Re-price Round A token usage at current provider rates** (Li-kai). The Round A price snapshot was not retained; record the dated price source this time.
- [ ] **B5. Self-Learning phase-2 one-pager** — feedback loop as in LoadStone diagram, scoped and priced separately (Faye / Saim).

### Start now (no RSTN input needed)
- [ ] **B31. Dev environment on the GPU server** (Guowei): point the engine's model gateway at the local router; one config per step (OCR, vision, text). Before any NTU sample data lands: bind the router to localhost or a firewall allow-list and add an API key (it currently listens on `0.0.0.0:8080` without auth).
- [ ] **B32. Open-model baseline** (Guowei): re-run the Round A scenarios and the new test set on the local models; compare quality, latency and calls per email with the hosted model. This also sizes the on-prem licence option (hosting-and-scaling.md §2.4) and gives a fallback if a hosted provider is not approved.
- [ ] **B33. Connector OCR on CPU** (Guowei / Li-kai): we told RSTN the connector needs about 2–4 vCPU, 8 GB and no GPU. Benchmark GLM-OCR (and Tesseract/PaddleOCR as a fallback) on CPU per page, and adjust the sizing we quote if needed. Use the GPU server only as the reference for accuracy. **First measurement (2026-10-07):** GLM-OCR Q8 via llama.cpp, CPU only, 4 threads, one made-up 900×1200 receipt: ~45 s per page once loaded (33 s image encoding, ~11 s decoding), plus ~14 s to load; peak memory ~10.7 GB; text correct apart from one masked digit (`****` read as `*****`). So no GPU is needed at PaCE volume, but 8 GB is too tight: quote 4 vCPU / 16 GB if GLM-OCR stays, or use classic OCR (Tesseract/PaddleOCR, ~1–3 s per page, ~1–2 GB, and gives word boxes needed for image redaction) by default with GLM-OCR as an option.
- [ ] **B34. Synthetic test set** (Guowei): extend the 7 POC scenarios to ~50 made-up emails (several questions, follow-ups, referrals, attachments, ambiguous programmes) until NTU samples arrive (A5). Include made-up receipts and screenshots for B11.
- [ ] **B35. Mock RSTN client** (Li-kai): small caller that sends XML through the connector to the engine and receives the callback; used for the live demo and for RSTN's sandbox.
- [ ] **B36. Live-demo hygiene** (RSTN question 16): hide model or provider names in POC screens (evaluation pages, settings, trace model field); pick 3–4 safe scenarios; no live screenshot tests while image reading is a fixture.
- [ ] **B37. Accounts and budget** (Li-kai): cloud project in Singapore (GCP, and check AWS since RSTN mentioned Bedrock), provider API access with zero retention, budget for test and production environments.
- [ ] **B38. POC plan for RSTN** (Guowei with Li-kai): `response-to-rstn.md` promises a plan after the call. Draft it from the internal 10-week outline (weeks 1–2 contract, samples, knowledge sync; 3–6 integration, connector, labelling; 7–10 UAT, accuracy, shadow run).

Also unblocked now, from the lists below: B6 headless engine, B7 contract draft (semantics), B8/B25 override, B9 retrieval over public NTU pages, B10 registry draft from NTU web pages, B11 attachment reader, B12 telemetry, B24/B19 connector masking and OCR, B26 no-payload logging, B27 tenant IDs, B28 infra template.

### Engine (after A1–A3, A8 answers)
- [ ] **B6. Extract headless engine** from the POC: drop UI, case lifecycle, persistence, execution adapters. Do **not** carry over content tables (`Message.body`, `AiCapabilityRun.structuredOutput`, `ReliabilityRun.result`); trace keeps stage/status/tokens/latency/versions/masked-input hash only (deployment-options.md G2).
- [ ] **B7. XML request/response contract** + XSD + versioning; contract tests.
- [ ] **B8. Override validation API** (slide 6 behaviour as a service).
- [ ] **B9. Indexed retrieval** against RSTN's store (replace POC full-load retriever); evidence carries URL, version, authority.
- [ ] **B10. Registry adapter** for programme/owner resolution; handle `AMBIGUOUS` aliases.
- [ ] **B11. Attachment reader** (OCR first; vision where samples require). Tag output `SENDER_PROVIDED`. Note: POC image reading is a fixture (`IMAGE_FIXTURE`); this is new build, not productionising.
- [ ] **B12. Per-stage cost/latency telemetry** in every result trace (tokens, model, cost, ms).
- [ ] **B13. Hosted engine deployment** (Singapore region, per-client isolation); hosted-only fallback if RSTN cannot run the connector; on-prem licence package only if A2 says no.
- [ ] **B27. Multi-tenant from day one**: `tenantId` on keys/config/knowledge/traces, per-tenant config and test set; PaCE as dedicated cell (hosting-and-scaling.md §3).
- [ ] **B28. Infra template + sizing**: Terraform for one GCP `asia-southeast1` cell per hosting-and-scaling.md §2.2; price in GCP calculator (Li-kai).
- [ ] **B29. Knowledge sync + withdrawal webhook** with RSTN; second-call pattern for institutional data (phase 2).
- [ ] **B30. Provider region check**: Singapore + ZDR for the selected model; evaluate Vertex AI (`asia-southeast1`) on the test set as alternative.
- [ ] **B23. Model provider zero-data-retention approval in writing**; list provider + region as sub-processor (deployment-options.md G7).
- [ ] **B24. Privacy connector — core of the proposed setup** (runs in RSTN's network): local OCR, masking, image redaction, in-memory placeholder map, name restore in reply/summaries/handoff notes. Signed container image, CPU only, version check against the engine, no business logic. Measure masking miss rate on the sample set.
- [ ] **B25. Stateless override contract**: resend original request + signed previous result (G1); drop sender address/To/CC from request (G3).
- [ ] **B26. No-payload logging**: scrub logger, disable APM body capture, test that fails if a body hits logs (G6).
- [ ] **B19. Masking quality**: shared masking library for the connector and the hosted-only fallback; re-run test set with masking on.
- [ ] **B20. Stateless processing + trace without email text**; opt-in masked debug capture with auto-delete.
- [ ] **B21. Security pack for RSTN/NTU**: data flow, sub-processors, retention, access control, incident process; DPA draft with Lisa.

### Sample emails (after A5)
- [-] ~~B14. Historical-email curation pipeline~~ — dropped: NTU will not share historical emails.
- [ ] **B14b. Label sample emails** (expected programme, owner, treatment, reply points) with PaCE confirming.
- [ ] **B15. Test set + accuracy report** for routing, treatment and reply, on the labelled samples; extend the POC evaluation harness. Re-run after every prompt/model/knowledge change.
- [ ] **B15b. Knowledge-gap list** for NTU: sample questions no approved source answers.

### Before commercial commitment
- [ ] **B16. Shadow run** 1–2 weeks on live traffic, nothing sent; cost and latency per email by type.
- [ ] **B17. Final unit-cost table** for the commercial proposal (variable per email + fixed + phase 2).
- [ ] **B18. Model re-check** with production-like context; Luna remains default until then.

## C. Decisions log

| Date | Decision | By |
|---|---|---|
| 2026-10 | Synvo provides an engine via API; UI/demo are reference only | Group |
| 2026-10 | Guowei is AI tech lead, working with Li-kai | Group |
| 2026-10 | "RL" renamed Self-Learning and parked to phase 2 | Saim / Faye |
| 2026-10 | Build internal architecture diagram now, in parallel with requesting RSTN's | Saim |
| 2026-10-07 | `response-to-rstn.md` kept high level (no step list, call counts, field names or sizing); technical detail only on the call if asked | Group |
| 2026-10-07 | Engine build owned by Guowei, with Li-kai; our GPU server (local llama.cpp router, GLM-OCR, Qwen VL) is the dev/test environment before cloud deployment | Guowei |
| 2026-10-07 | Promote option C first: hosted engine + privacy connector in RSTN's network; hosted-only and on-prem licence as fallbacks | Group |
| 2026-10-07 | Do not disclose cloud model use or model names in the 2026-10-08 call | Group |
| 2026-10-07 | Send `workflow-and-architecture.html` to RSTN as a saved PDF (A4 landscape print styles), not a hosted page; internal cost page stays HTML | Group |
| 2026-10-06 | Knowledge synced (no per-email NTU query); institutional data looked up by RSTN, passed in a second call; build multi-tenant | Synvo (proposed) |
| 2026-10-06 | Hosted API stays default; offer on-prem privacy connector; binary SDK only as priced licence (deployment-options.md) | Synvo (proposed) |
| 2026-10-06 | Propose async API with callback (TBC with RSTN, question A4) | Synvo |
| 2026-10-05 | Push Synvo-hosted API as the delivery model; on-prem only as priced licence | Group |
| 2026-10-05 | Client data safety measures on our side: masking, stateless, zero-retention provider, DPA | Group |
| 2026-10-05 | No historical emails for pre-training; sample emails for reference → used as test set, gap list, reply style only | NTU (via group) |
| 2026-09-28 | GPT-5.6 Luna default model for next POC stage (Round A) | Synvo |
