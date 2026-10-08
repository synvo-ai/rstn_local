# NTU PaCE / RSTN — TODO

Tracks open questions for RSTN/NTU and Synvo's own work. Context: `requirements-summary.md`, `draft-solution.md`, `unit-cost.html`.

Status: `[ ]` open · `[~]` in progress · `[x]` done · `[-]` dropped Owners are suggestions; adjust after Lisa consolidates scope.

---

## 0. Plan after the 2026-10-08 call

**Where we are:** the technical call is done. Most questions ended without an answer. RSTN has no sample emails, reply templates, knowledge base or timeline from NTU yet. So we build the whole POC on our side with **mock data**, and give RSTN a **sandbox and a testing protocol** so they can try it. Self-learning is not part of the POC.

**Goal:** finish the POC on our side in **3 weeks: Thu 8 Oct – Wed 28 Oct 2026**, with RSTN able to call a sandbox from 21 Oct and a full sandbox handed over on 28 Oct. The protocol itself is a few days of writing; the 3 weeks are for building what it tests.

### Dates committed to RSTN

| When | RSTN gets |
|---|---|
| Wed 14 Oct | Sandbox testing protocol (draft) and API specification (draft), sent together |
| Wed 21 Oct | Sandbox v1: engine only, mock emails and knowledge, API key per tester |
| Wed 28 Oct | Sandbox v2: adds the privacy connector and attachment reading; protocol final; demo; short results report |
| 28 Oct – ~4 Nov | RSTN testing window (1 week; RSTN may extend) with a check-in mid-week |
| ~Thu 5 Nov | Joint review and pilot plan |

Results on mock data show the engine works end to end; they are not an accuracy figure for NTU.

### Phase 1 — POC on our side (3 weeks)

| Week | Dates | Focus | Done when |
|---|---|---|---|
| 1 | 8–14 Oct | Foundations, mock data, documents for RSTN | Engine runs headless behind API v0 on our GPU server; mock knowledge, registry, templates and 50 mock emails exist; S2 decided; protocol and API spec drafts sent on 14 Oct |
| 2 | 15–21 Oct | Sandbox v1, connector | Sandbox v1 reachable by RSTN on 21 Oct with keys and access control; connector v0 masks, reads attachments and restores names; staff-change re-check works; first evaluation on the mock set |
| 3 | 22–28 Oct | Sandbox v2, evaluation, handover | Connector in the sandbox; mock set at ~150 emails with an accuracy, cost and latency report; data-handling note; protocol final; demo and handover on 28 Oct |

**Week 1 (8–14 Oct)**
- [ ] **Mon 12 Oct:** decide where the sandbox runs (S2). It must be reachable from outside with access control; the GPU router today is internal with no auth.
- [ ] B6 headless engine extracted from the POC; B7 API v0 (our own JSON schema plus an XML adapter, since RSTN has no schema yet) firm enough to publish; B31 local model gateway.
- [ ] M1–M4 mock data (50 emails); M5 started.
- [ ] **Wed 14 Oct:** send S1 protocol draft (`sandbox-testing-protocol.md`) and the API spec draft to RSTN.

**Week 2 (15–21 Oct)**
- [ ] S2 sandbox v1 deployed (engine only, mock data, keys, rate limits, reset); S3 access sent to RSTN on **Wed 21 Oct**.
- [ ] B24 / B19 connector v0: masking, attachment tiers (B11: text extraction, classic OCR, optional GLM-OCR), restore.
- [ ] B8 / B25 staff-change re-check; B12 / B26 trace and no-payload logging; B27 tenant IDs.
- [ ] B35 mock RSTN client (XML in, callback out).
- [ ] B15 evaluation harness pointed at the mock set; first run.

**Week 3 (22–28 Oct)**
- [ ] Sandbox v2: connector and attachment reading added; M5 attachments in the test pack.
- [ ] M4 mock set grown to ~150 emails; B15 accuracy report; B32 / B33 cost and latency per email type, including attachments.
- [ ] B36 demo; S1 protocol final; S4 feedback channel live.
- [ ] Data-handling note for RSTN (cut-down B21: data flow, retention, masking).
- [ ] Handover to RSTN on **Wed 28 Oct**.

### Phase 1b — RSTN testing (28 Oct – ~4 Nov)
- [ ] RSTN runs the protocol scenarios through their own system; we fix and redeploy the sandbox during the week.
- [ ] Mid-week check-in; joint review ~Thu 5 Nov with a pilot plan and the list of NTU inputs it needs.

**Out of scope for the 3-week POC:** self-learning (B5), real NTU data and knowledge, cloud production deployment (B13, B28), DPA and security assessment (B21 full, B23), shadow run (B16), institutional data (A7, B29), final pricing (B17).

### Phase 2 — Pilot with NTU data (after the POC; dates depend on NTU)
- Swap mock data for real: sample emails (A5), approved knowledge (A1, A6), programme registry and routing (A3, A4), templates.
- RSTN's real XML schema (A8) replaces our v0.
- Singapore cloud deployment (B13, B28, B30, B37); provider approval (B23); security pack and DPA (B21, A18).
- Accuracy on labelled NTU samples (B14b, B15), then a 1–2 week shadow run (B16); acceptance targets (A16).
- Pricing (B4, B17).

### Phase 3 — Later
- Self-learning from staff feedback (B5).
- Institutional data via RSTN lookups (A7, B29).
- Further customers on the same engine (B27, hosting-and-scaling.md §3).

### M. Mock data (we build it, because RSTN has none)
- [ ] **M1. Mock knowledge base** from public NTU PaCE pages (programme pages, FAQs, fee and intake information): crawl, version, index. Mark every item as mock; NTU still has to approve real sources (A6).
- [ ] **M2. Mock programme registry and routing table**: programmes, aliases, owning teams, made-up team inboxes, owner by question type.
- [ ] **M3. Mock reply templates and style**: greeting, sign-off, acknowledgement, the fallback acknowledgement, handoff note format.
- [ ] **M4. Mock email set**: 50 in week 1, ~150 by week 3, each labelled with expected issues, programme, owner, action and reply points. Cover single and multi-question, follow-ups, referrals, ambiguous programmes, out-of-scope, payment and status questions, and web-form enquiries. Made-up people only.
- [ ] **M5. Mock attachments**: text PDFs, scanned PDFs, receipts, certificates, portal screenshots, logos; made-up personal details so masking can be tested.

### S. Sandbox for RSTN
- [ ] **S1. Sandbox testing protocol** (`sandbox-testing-protocol.md`): draft to RSTN 14 Oct, final 28 Oct. What RSTN can test, how to call the API, scenarios and expected results, how to report issues, what the sandbox does not do.
- [ ] **S2. Sandbox environment**: decide where it runs (our GPU server behind a gateway, or a small cloud test environment calling the local or a hosted model); mock data only; API keys per tester; rate limits; reset button.
- [ ] **S3. Access for RSTN**: endpoint, keys, mock RSTN client, sample requests.
- [ ] **S4. Feedback loop**: issue template (in the protocol) and a mid-week check-in during the testing window.

---

## A. Questions for RSTN / NTU

**After the 2026-10-08 call:** mostly unanswered. RSTN has no sample emails, templates, knowledge base or NTU timeline. Items below stay open for phase 2; for the POC we mock them (section 0, M1–M5).

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


### Before the 8 Oct call
- [~] **B1. Requirement summary and draft solution** — `requirements-summary.md`, `draft-solution.md` (Guowei). Revised after reviewing images.
- [~] **B2. Workflow + architecture diagram and cost-per-email draft** — customer version `workflow-and-architecture.html`, internal cost `unit-cost.html` (Guowei → Lisa for the 1-pager).
- [x] **B3. Send question list to RSTN before the technical call on Thu 2026-10-08 10:00** — `questions-for-rstn.md` (Part 1: our understanding to confirm; Part 2: questions with our proposals). Whether to share the Workflow and Architecture PDF is a separate business decision (not yet). Commercial 1-pager goes separately (Saim → Steven). Also send `response-to-rstn.md`: answers to RSTN's 16 questions, with questions back R1–R14.
- [x] **B22. Prepare for the call**: draft request/response field list to walk through (`draft-solution.md` §7); agree internally who answers what (Guowei: engine/API; Li-kai: models/data; Lisa: scope/commercial).
- [ ] **B4. Re-price Round A token usage at current provider rates** (Li-kai). The Round A price snapshot was not retained; record the dated price source this time.
- [-] **B5. Self-Learning phase-2 one-pager** — not required in the POC (2026-10-08); phase 3. — feedback loop as in LoadStone diagram, scoped and priced separately (Faye / Saim).

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
| 2026-10-08 | After the call: build the POC on our side in 3 weeks (8–28 Oct) with mock data; hand RSTN a sandbox and testing protocol; self-learning not required in the POC | Group |
| 2026-10-08 | Dates for RSTN: protocol and API spec drafts 14 Oct, sandbox v1 21 Oct, sandbox v2 and handover 28 Oct, 1-week testing window, review ~5 Nov | Guowei |
| 2026-10-07 | `response-to-rstn.md` kept high level (no step list, call counts, field names or sizing); technical detail only on the call if asked | Group |
| 2026-10-07 | Engine build owned by Guowei, with Li-kai; our GPU server (local llama.cpp router, GLM-OCR, Qwen VL) is the dev/test environment before cloud deployment | Guowei |
| 2026-10-07 | Promote option C first: hosted engine + privacy connector in RSTN's network; hosted-only and on-prem licence as fallbacks | Group |
| 2026-10-07 | Do not disclose cloud model use or model names in the 2026-10-08 call | Group |
| 2026-10-07 | Send `workflow-and-architecture.html` to RSTN as a saved PDF (A4 landscape print styles), not a hosted page; internal cost page stays HTML | Group |
| 2026-10-07 | Workflow and Architecture PDF not shared with RSTN for now (business decision); `response-to-rstn.md` and `questions-for-rstn.md` no longer reference it | Group |
| 2026-10-06 | Knowledge synced (no per-email NTU query); institutional data looked up by RSTN, passed in a second call; build multi-tenant | Synvo (proposed) |
| 2026-10-06 | Hosted API stays default; offer on-prem privacy connector; binary SDK only as priced licence (deployment-options.md) | Synvo (proposed) |
| 2026-10-06 | Propose async API with callback (TBC with RSTN, question A4) | Synvo |
| 2026-10-05 | Push Synvo-hosted API as the delivery model; on-prem only as priced licence | Group |
| 2026-10-05 | Client data safety measures on our side: masking, stateless, zero-retention provider, DPA | Group |
| 2026-10-05 | No historical emails for pre-training; sample emails for reference → used as test set, gap list, reply style only | NTU (via group) |
| 2026-09-28 | GPT-5.6 Luna default model for next POC stage (Round A) | Synvo |
