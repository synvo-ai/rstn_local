# NTU PaCE / RSTN — TODO

Tracks open questions for RSTN/NTU and Synvo's own work. Context: `01-requirements-summary.md`,
`02-draft-solution.md`, `03-architecture-and-unit-cost.html`.

Status: `[ ]` open · `[~]` in progress · `[x]` done · `[-]` dropped
Owners are suggestions; adjust after Lisa consolidates scope.

---

## A. Questions for RSTN / NTU

### Knowledge and data sources
- [ ] **A1. Knowledge base access.** Where does approved knowledge live on RSTN's on-prem server, and what
      interface do we get: query API, versioned snapshot export, or a vector index? Who approves and revokes
      content, and how are versions exposed? *(Biggest technical unknown; decides topology and cost.)*
- [ ] **A2. Where may processing run?** May retrieved excerpts be sent to a cloud model provider (option A),
      or must everything stay inside NTU's network (B/C)? Approved providers and data residency rules.
- [ ] **A3. Programme registry.** Does an authoritative list of programmes, aliases, status and owning teams
      exist, or must it be built? Customer said no master directory exists today. Who maintains it?
- [ ] **A4. Routing/ownership directory.** Owner per programme × intent (admission, fees, credit transfer…),
      with team inboxes. Read access for us?
- [ ] **A5. Historical correspondence (Prof Boh).** Which emails NTU is authorised to let us use (date range,
      mailboxes, programmes), export format, volume, and who approves the curated set.
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
- [ ] **A17. Environments.** Test/UAT access, sandbox data, go-live date, who supports in production.

## B. Synvo internal work

### Now (this week)
- [~] **B1. Requirement summary and draft solution** — `01-…`, `02-…` (Guowei). Revised after reviewing images.
- [~] **B2. Workflow + architecture diagram and cost-per-email draft** — `03-architecture-and-unit-cost.html`
      (Guowei → Lisa for the 1-pager).
- [ ] **B3. Send question list (section A) to RSTN** (Lisa), together with the commercial 1-pager (Saim → Steven).
- [ ] **B4. Re-price Round A token usage at current provider rates** (Li-kai). The Round A price snapshot was
      not retained; record the dated price source this time.
- [ ] **B5. Self-Learning phase-2 one-pager** — feedback loop as in LoadStone diagram, scoped and priced
      separately (Faye / Saim).

### Engine (after A1–A3, A8 answers)
- [ ] **B6. Extract headless engine** from the POC: drop UI, case lifecycle, persistence, execution adapters.
- [ ] **B7. XML request/response contract** + XSD + versioning; contract tests.
- [ ] **B8. Override validation API** (slide 6 behaviour as a service).
- [ ] **B9. Indexed retrieval** against RSTN's store (replace POC full-load retriever); evidence carries URL,
      version, authority.
- [ ] **B10. Registry adapter** for programme/owner resolution; handle `AMBIGUOUS` aliases.
- [ ] **B11. Attachment reader** (OCR first; vision where samples require). Tag output `SENDER_PROVIDED`.
- [ ] **B12. Per-stage cost/latency telemetry** in every result trace (tokens, model, cost, ms).
- [ ] **B13. Deployment package** for the chosen topology (A/B/C); retrieval service if it must sit on-prem.

### Historical knowledge (after A5)
- [ ] **B14. Curation pipeline**: de-identify → de-duplicate → extract Q&A → tag → drop obsolete/conflicting
      → NTU review → versioned publish.
- [ ] **B15. Evaluation set** from curated historical Q&A; accuracy report for routing, treatment and reply.

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
| 2026-09-28 | GPT-5.6 Luna default model for next POC stage (Round A) | Synvo |
