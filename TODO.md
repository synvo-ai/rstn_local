# NTU PaCE / RSTN — TODO

Tracks open questions for RSTN/NTU and Synvo's own work. Context: `requirements-summary.md`,
`draft-solution.md`, `unit-cost.html`.

Status: `[ ]` open · `[~]` in progress · `[x]` done · `[-]` dropped
Owners are suggestions; adjust after Lisa consolidates scope.

---

## A. Questions for RSTN / NTU

### Knowledge and data sources
- [ ] **A1. Knowledge base access.** Where does approved knowledge live on RSTN's on-prem server, and what
      interface do we get: query API, versioned snapshot export, or a vector index? Who approves and revokes
      content, and how are versions exposed? *(We propose syncing a versioned copy to our hosted index; live query API as fallback.)*
- [ ] **A2. Acceptance of the proposed setup** (hosted engine + privacy connector in RSTN's network). Does NTU policy
      allow masked text to leave NTU for processing in Singapore, nothing retained? Can RSTN host the connector?
      Internal: approved model providers and region still to settle; do not raise model/provider on the 2026-10-08 call.
- [ ] **A3. Programme registry.** Does an authoritative list of programmes, aliases, status and owning teams
      exist, or must it be built? Customer said no master directory exists today. Who maintains it?
- [ ] **A4. Routing/ownership directory.** Owner per programme × intent (admission, fees, credit transfer…),
      with team inboxes. Read access for us?
- [ ] **A5. Sample emails.** NTU will not share historical emails for pre-training (confirmed 2026-10-05), but
      sample emails are available for reference. Ask for a few hundred, de-identified, covering main programmes,
      multi-question, follow-ups and attachments, each with how PaCE handled it (answered / forwarded to whom /
      asked for details). Who de-identifies, and who confirms our labels?
- [ ] **A6. Other approved sources.** FAQs, policies, fee tables, intake calendars: which, where, how current.
      Confirm NTU public programme pages are an approved source (the POC cites them).
- [ ] **A7. Institutional state.** Any authorised read interface for payment, application or TMS status? If
      not, confirm these stay Manual handling for phase 1.

### Integration contract
- [ ] **A8. XML input contract.** Schema or sample payloads; how thread/reply links are identified;
      attachments inline (base64) or by reference; size limits; web-form fields.
- [ ] **A9. Output consumption.** Which result fields RSTN's UI will show; XML or JSON back; sync response or
      callback.
- [ ] **A10. Staff overrides.** Will RSTN call us to validate a staff change of handling (slide 6 behaviour),
      or handle it on their side?
- [ ] **A11. Failure policy.** What RSTN does on `FAILED` / `BLOCKED` runs; who owns the static fallback
      acknowledgement wording.
- [ ] **A12. Volume and latency.** Peak emails per hour, acceptable latency per email, sync vs async,
      expected concurrency. (Round A median is ~13 s sequential.)

### Multimodal
- [ ] **A13. Sample screenshots/attachments** (10–30, redacted). Mix of receipts, certificates, portal
      screenshots, error dialogs? Share of emails that carry them. Decides OCR vs vision and attachment cost.

### Governance and commercial
- [ ] **A14. Retention and audit.** How long we may keep raw email, traces and logs; redaction rules;
      audit export format for "decision audit and service reporting".
- [ ] **A15. RSTN architecture diagram.** Request theirs (Faye's suggestion) and reconcile with ours.
- [ ] **A16. Acceptance criteria.** Which success measures (routing accuracy, first-contact resolution,
      handling time) define phase-1 acceptance, and the target numbers.
- [ ] **A18. Data protection terms.** NTU's PDPA requirements for a data intermediary, DPA template, retention limits,
      security assessment they need from us (questionnaire, pen test).
- [ ] **A17. Environments.** Test/UAT access, sandbox data, go-live date, who supports in production.

## B. Synvo internal work

### Now (this week)
- [~] **B1. Requirement summary and draft solution** — `requirements-summary.md`, `draft-solution.md` (Guowei). Revised after reviewing images.
- [~] **B2. Workflow + architecture diagram and cost-per-email draft** — customer version `workflow-and-architecture.html`, internal cost `unit-cost.html`
      (Guowei → Lisa for the 1-pager).
- [~] **B3. Send question list to RSTN before the technical call on Thu 2026-10-08 10:00** — `questions-for-rstn.md`
      (Part 1: our understanding to confirm; Part 2: questions with our proposals). Share the Workflow and Architecture
      page with RSTN at the same time. Commercial 1-pager goes separately (Saim → Steven).
- [ ] **B22. Prepare for the call**: draft request/response field list to walk through (`draft-solution.md` §7);
      agree internally who answers what (Guowei: engine/API; Li-kai: models/data; Lisa: scope/commercial).
- [ ] **B4. Re-price Round A token usage at current provider rates** (Li-kai). The Round A price snapshot was
      not retained; record the dated price source this time.
- [ ] **B5. Self-Learning phase-2 one-pager** — feedback loop as in LoadStone diagram, scoped and priced
      separately (Faye / Saim).

### Engine (after A1–A3, A8 answers)
- [ ] **B6. Extract headless engine** from the POC: drop UI, case lifecycle, persistence, execution adapters.
      Do **not** carry over content tables (`Message.body`, `AiCapabilityRun.structuredOutput`, `ReliabilityRun.result`);
      trace keeps stage/status/tokens/latency/versions/masked-input hash only (deployment-options.md G2).
- [ ] **B7. XML request/response contract** + XSD + versioning; contract tests.
- [ ] **B8. Override validation API** (slide 6 behaviour as a service).
- [ ] **B9. Indexed retrieval** against RSTN's store (replace POC full-load retriever); evidence carries URL,
      version, authority.
- [ ] **B10. Registry adapter** for programme/owner resolution; handle `AMBIGUOUS` aliases.
- [ ] **B11. Attachment reader** (OCR first; vision where samples require). Tag output `SENDER_PROVIDED`.
      Note: POC image reading is a fixture (`IMAGE_FIXTURE`); this is new build, not productionising.
- [ ] **B12. Per-stage cost/latency telemetry** in every result trace (tokens, model, cost, ms).
- [ ] **B13. Hosted engine deployment** (Singapore region, per-client isolation); hosted-only fallback if RSTN cannot run the connector; on-prem licence package only if A2 says no.
- [ ] **B27. Multi-tenant from day one**: `tenantId` on keys/config/knowledge/traces, per-tenant config and test set; PaCE as dedicated cell (hosting-and-scaling.md §3).
- [ ] **B28. Infra template + sizing**: Terraform for one GCP `asia-southeast1` cell per hosting-and-scaling.md §2.2; price in GCP calculator (Li-kai).
- [ ] **B29. Knowledge sync + withdrawal webhook** with RSTN; second-call pattern for institutional data (phase 2).
- [ ] **B30. Provider region check**: Singapore + ZDR for the selected model; evaluate Vertex AI (`asia-southeast1`) on the test set as alternative.
- [ ] **B23. Model provider zero-data-retention approval in writing**; list provider + region as sub-processor (deployment-options.md G7).
- [ ] **B24. Privacy connector — core of the proposed setup** (runs in RSTN's network): local OCR, masking, image
      redaction, in-memory placeholder map, name restore in reply/summaries/handoff notes. Signed container image,
      CPU only, version check against the engine, no business logic. Measure masking miss rate on the sample set.
- [ ] **B25. Stateless override contract**: resend original request + signed previous result (G1); drop sender address/To/CC from request (G3).
- [ ] **B26. No-payload logging**: scrub logger, disable APM body capture, test that fails if a body hits logs (G6).
- [ ] **B19. Masking quality**: shared masking library for the connector and the hosted-only fallback; re-run test set with masking on.
- [ ] **B20. Stateless processing + trace without email text**; opt-in masked debug capture with auto-delete.
- [ ] **B21. Security pack for RSTN/NTU**: data flow, sub-processors, retention, access control, incident process; DPA draft with Lisa.

### Sample emails (after A5)
- [-] ~~B14. Historical-email curation pipeline~~ — dropped: NTU will not share historical emails.
- [ ] **B14b. Label sample emails** (expected programme, owner, treatment, reply points) with PaCE confirming.
- [ ] **B15. Test set + accuracy report** for routing, treatment and reply, on the labelled samples; extend the
      POC evaluation harness. Re-run after every prompt/model/knowledge change.
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
