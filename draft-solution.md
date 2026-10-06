# NTU PaCE General Enquiries — Draft Solution (Synvo Correspondence Intelligence Engine)

Audience: Synvo internal + RSTN architecture discussion.
Companion documents: `requirements-summary.md` (what), `TODO.md` (open items),
`workflow-and-architecture.html` (diagram, customer-facing), `unit-cost.html` (cost per email, internal).
Status: **draft.** Anything waiting on RSTN/NTU is marked **ASSUMPTION** and has a matching line in `TODO.md`.

---

## 1. Solution in one paragraph

A **headless Correspondence Intelligence engine** behind an API. RSTN posts an enquiry (XML): current email,
permitted thread context, attachments. The engine returns: the issues in the email, the programme and owner
of each, whether approved knowledge answers it, one treatment per issue (Reply directly / Refer to receiving
team / Ask for clarification / Manual handling), one verified reply covering the answerable issues, and a
full decision trace with cost and latency. **The engine never sends, routes or invents facts.** RSTN
executes; PaCE staff decide. This is slide 2's "Synvo AI" lane, without the UI.

We keep the POC's intelligence core and drop its workflow shell (UI, case lifecycle, database, execution
adapters), which RSTN already owns.

## 2. Boundary with RSTN

| Concern | Owner |
|---|---|
| Mailbox/form intake, attachment storage | RSTN |
| Case and thread identity, case status, dashboard | RSTN |
| Programme registry and approved knowledge (authoring, approval, revocation) | NTU / RSTN |
| Providing sample emails for reference | NTU / PaCE |
| Payment, TMS, application state | NTU systems (manual handling until an authorised interface exists) |
| Staff UI, approval, sending, forwarding, static fallback wording | RSTN / PaCE |
| **Understanding, programme/owner resolution, sufficiency, treatment, grounded reply, verification, override validation, decision trace** | **Synvo** |
| **Labelling sample emails into a test set; knowledge-gap list (offline)** | **Synvo builds, PaCE confirms labels** |

Non-execution semantics stay explicit: **`HANDOFF` ≠ forwarded, `SAFE_TO_REVIEW` ≠ approved,
`MANUAL_REVIEW` ≠ reviewed, candidate reply ≠ sent email.** Run health is separate from business treatment:
`MANUAL_REVIEW + SAFE_TO_REVIEW + SUCCEEDED` is a valid, successful result.

## 3. Architecture

Two paths: an **online path** per email (the API RSTN calls), and an **offline knowledge path** that keeps
the knowledge base current. The diagram version is in `workflow-and-architecture.html`.

```
 ONLINE — per email (async + callback proposed; TBC)          stage code   model call?
 ──────────────────────────────────────────────────────────────────────────────────────
 RSTN ──XML──► [1] Intake & validation                          —           no
                   schema, idempotency key, correlation IDs,
                   keep sender / thread / institutional inputs separate
               [2] Attachment reading (only if attachments)     new         OCR or vision
                   screenshot/receipt → text + fields, tagged SENDER_PROVIDED
               [3] Thread delta (only if follow-up)             P0-F        yes
               [4] Understand: split into issues                P0-A        yes
               [5] Identify programme & owner ◄── Registry      P0-B        only if ambiguous
               [6] Retrieve evidence ◄── Knowledge base          —           embeddings (prod)
               [7] Check information: SUFFICIENT / INSUFFICIENT  P0-C        no (rules)
                   / CONFLICTING / STALE
               [8] Recommend action per issue                    —           no (rules)
                   ANSWER · HANDOFF · CLARIFY · MANUAL_REVIEW
               [9] Draft one reply for answerable issues        P0-D        yes
              [10] Application validation                        —           no (rules)
              [11] Independent verification  PASS / BLOCK        P0-E        yes
              [12] Decision trace + cost/latency per stage       —           no
 RSTN ◄──XML── result

 OVERRIDE — staff change a treatment (slide 6)
 RSTN ──► re-run [8]–[11] for the changed issue with the staff choice as input;
          invalid change → plan unchanged + reason

 OFFLINE — knowledge path (batch, not per email)
 NTU web pages, FAQs, policies ─► crawl/import ─► version ─► index      (the only fact sources)
 PaCE sample emails ─► de-identify ─► label expected owner / action / answer points
   ─► test set (accuracy before go-live and after every change)
   ─► gap list (questions no approved source answers → NTU adds FAQs)
 (phase 2) staff edits & overrides ─► evaluation on test set ─► approved corrections ─► knowledge
```

Failure contract: a failed stage is never returned as a business answer. No semantic retry for a preferred
answer, no silent provider fallback, no model recall in place of evidence. When the engine fails or is
unavailable, RSTN sends its static approved acknowledgement (LoadStone's "failure fallback") and queues the
case for staff.

## 4. Mapping to the POC

| Step | POC source (`ntu-pace-correspondence-intelligence`) | Reuse |
|---|---|---|
| [3] Thread delta | `src/ai/thread-delta.ts` | Direct. Strongest model discriminator in our evaluation (T3) |
| [4] Understand | `src/ai/correspondence-understanding.ts` | Direct. POC-proven on multi-issue emails |
| [5] Programme & owner | `src/ai/entity-resolution.ts` | Re-point at RSTN's registry |
| [6]–[7] Retrieve, check | `src/knowledge/retrieval/full-retriever.ts`, `src/knowledge/availability/checker.ts` | Re-point. POC loads a small fictional store in full; production needs indexed retrieval |
| [8] Recommend | `src/application/decision/decision-engine.ts` | Direct. Deterministic and testable |
| [9] Draft | `src/ai/grounded-composer.ts`, `live-grounded-composer.ts` | Direct |
| [10] Validation | validation in the review/execution services | Logic only, drop workflow coupling |
| [11] Verify | `src/ai/response-verification.ts` | Direct. Blocked the one unsupported claim in Round A |
| Model gateway | `src/ai/model-gateway.ts` | Direct. Per-stage model choice without touching rules |
| Override validation | POC "Change handling" path | Extract as an API |
| [2] Attachment reading | POC: PDF text is real (`pdf-parse`); **image reading is a fixture** (`IMAGE_FIXTURE`, hard-coded excerpt) | **Build** OCR/vision once samples arrive |
| Sample-email test set and gap list | POC evaluation harness (`evaluation/`) | Extend with real samples |
| UI, case lifecycle, persistence, execution | `src/app`, `src/domain`, `src/persistence`, `src/integrations` | Out of scope |

The core is built and evidenced. The work is integration, the XML contract, re-pointing at RSTN data,
indexed retrieval, the sample-email test set, hosted deployment, data protection and cost engineering.

## 5. Delivery model and data protection

### 5.1 Delivery: Synvo-hosted API (our position)

**Decision (internal, 2026-10-05): we push the hosted API.** It is the most valuable model for us: recurring
per-email revenue, the engine and prompts stay on our side (IP protection), one codebase we can update and
monitor centrally, and it is reusable for the other customers asking for the same capability. On-prem
deployment is offered only if NTU policy forbids the hosted model, and priced as a separate licence.

| Option | Engine | Knowledge for retrieval | Position |
|---|---|---|---|
| **A. Hosted API** | Synvo cloud, Singapore region | Versioned copy synced from RSTN (approved pages, FAQs, policies: mostly public content) | **Proposed** |
| **B. Hosted API, live lookup** | Synvo cloud | RSTN exposes a query API; we fetch excerpts per email | Fallback if knowledge may not be copied |
| **C. On-prem licence** | Inside NTU's network, on-prem GPU or approved model endpoint | Local | Only if required; separate licence, higher fixed cost, slower updates |

Customer-facing benefits to lead with (not our commercial reasons): nothing for RSTN to host or patch; model
and quality improvements arrive without a redeploy; per-email pricing that scales with volume; one versioned
API contract.

The approved knowledge is mostly public NTU content, so syncing a copy to our hosted index is low risk and
removes a live dependency on RSTN's server. **ASSUMPTION** until RSTN confirms (TODO A1, A2).

### 5.2 Data protection: keep the risk off our side

The hosted API means we receive enquiry emails (personal data) and pass parts of them to a cloud model. Under
Singapore's PDPA we would be NTU's data intermediary, so our own exposure has to be engineered down, not
just contracted away.

| Risk | Measure |
|---|---|
| Personal data reaching the cloud model | **Mask before any model call:** names, email addresses, phone numbers, NRIC/FIN, bank and payment references replaced with placeholders (`[NAME_1]`); restored only in the final reply returned to RSTN. OCR attachments locally first; send an image to a vision model only when OCR is insufficient, after masking where possible |
| Provider keeps or trains on our data | Enterprise endpoints only, with zero data retention and no training on inputs in the contract; Singapore region where available; provider choice fixed with NTU in writing |
| Raw personal data reaching our servers at all | Optional **on-prem privacy connector** run by RSTN: OCR and masking before anything leaves NTU, names restored in the reply on their side (`deployment-options.md` §5) |
| We become a store of NTU data | **Stateless by default:** process and return; no raw email, attachment or reply stored after the response. Decision traces store IDs, labels, evidence references, tokens and timings, not the email text. Any debug capture is opt-in, masked, and auto-deleted (e.g. 30 days) |
| Data in transit / at rest | TLS 1.2+ with mutual auth or signed requests from RSTN; encryption at rest for anything kept (test set, logs); keys in a managed KMS |
| Unauthorised access on our side | Per-client isolated deployment and keys; least-privilege staff access with MFA; every access logged; no NTU data on laptops or in dev environments |
| Sample emails used for testing | De-identified before they reach us (or on receipt in an isolated store); kept only for the project; deleted on request or at contract end |
| Prompt injection in emails | Email is data, never instructions; facts only from retrieval; verifier blocks unsupported output |
| Incident | Breach notification process aligned with PDPA timelines; documented in the data processing agreement |

Commercial/legal: a data processing agreement with NTU/RSTN stating our intermediary role, purpose limits,
retention, sub-processors (the model provider), and liability caps. Masking and statelessness are what let us
offer that agreement with confidence.

Quality impact of masking: the engine reasons on programmes and questions, not on who is asking, so masking
names and identifiers does not affect the treatment decision. The POC test set will be re-run with masking
on to confirm (TODO B19).

### 5.3 Data access, hosting and multi-customer

Knowledge and registry are **synced**, not queried per email; institutional data is looked up by **RSTN** and
passed in a second call, only when an issue needs it. No GPU is needed for the hosted API. Build PaCE as tenant
#1 of a multi-tenant engine. Detail: `hosting-and-scaling.md`.

## 6. Sample emails (replaces the historical-correspondence plan)

**Update 2026-10-05:** NTU will not share historical emails for pre-training; sample emails are available for
reference. Nothing is trained on NTU emails, and sample emails are never cited as a source of facts. The
engine answers only from NTU web pages, FAQs and policies.

Sample emails are used three ways:

| Use | How |
|---|---|
| **Test set** | De-identify; label with PaCE the expected programme, owner, treatment and the points a good reply covers. Measure accuracy before go-live and after every prompt, model or knowledge change. |
| **Gap list** | Questions in the samples that no approved source answers. NTU adds FAQs or pages before go-live, so fewer emails fall to Manual handling. |
| **Reply style** | A handful of approved replies as tone/structure examples in the drafting prompt. Wording only, never facts. |

What to ask for: a few hundred de-identified emails covering the main programmes, multi-question emails,
follow-ups and attachments, each with how PaCE actually handled it (answered, forwarded and to whom, or asked
for details). This extends the POC's evaluation harness; it is a one-off build priced outside the per-email
cost. It also gives Self-Learning (phase 2) its gate: no correction is folded in unless the test set holds.

## 7. API contract (semantics now, XSD with RSTN)

### 7.1 Request

```
Request
├── requestId, correlationId, idempotencyKey, schemaVersion
├── Message: messageId, channel (EMAIL | WEB_FORM), receivedAt, senderRef (opaque), subject,
│            body (plain text, masked if the privacy connector is used), formSignals?,
│            externalThreadId, inReplyTo, references[]
│            (no sender address, To or CC: no step needs them; see deployment-options.md G3)
├── ThreadContext[]          permitted prior messages, ordered
├── Attachments[]            attachmentId, mediaType, storageRef | inlineBase64, sizeBytes
├── InstitutionalContext[]   optional, authorised source only (source, field, value, asOf)
└── Options                  locale, requireCandidateReply, includeDiagnostics
```

Sender, thread and institutional inputs stay structurally separate so sender evidence is never promoted to
institutional fact.

### 7.2 Response

```
Result
├── correlation: correlationId, runId, engineVersion, knowledgeVersion, configVersion
├── runHealth: SUCCEEDED | DEGRADED | FAILED
├── summary: issueCount, countsByTreatment {ANSWER, HANDOFF, CLARIFY, MANUAL_REVIEW}
├── issues[]
│   ├── issueId, sourceSpan, summary, intent
│   ├── programme { status: RESOLVED | AMBIGUOUS | UNRESOLVED, id?, name?, candidates[]? }
│   ├── owner { ownerId, name, routingBasis }        e.g. "FlexiMasters in IC Design · ADMISSION → EEE"
│   ├── answerability: SUFFICIENT | INSUFFICIENT | CONFLICTING | STALE
│   ├── treatment: ANSWER | HANDOFF | CLARIFY | MANUAL_REVIEW
│   ├── rationale                                       the "Why" shown to staff
│   ├── missingInformation[], requiredInstitutionalContext[]
│   └── evidence[] { evidenceId, sourceType, url | locator, version, excerpt,
│                    authority: INSTITUTIONAL | APPROVED_KNOWLEDGE | SENDER_PROVIDED }
├── reply?                                              one per enquiry
│   ├── text, coversIssueIds[]
│   ├── claims[] { claimText, evidenceIds[] }
│   └── safety: SAFE_TO_REVIEW | BLOCKED | NOT_PRODUCED, verifierFindings[]
├── handoffNotes[]? { issueId, ownerId, noteText }     what goes to the receiving team
└── trace: stages[] { stage, status, latencyMs, model?, inputTokens?, outputTokens?, costUsd? }
```

Treatments are per issue; one email routinely yields `ANSWER / ANSWER / MANUAL_REVIEW` (slide 3). Without
evidence, answerability is `INSUFFICIENT` and nothing is drafted for that issue.

### 7.3 Override validation

`POST /override` with the **original request**, the **previous result** (signed by the engine so it cannot be
altered), `issueId`, and the requested treatment (and owner for a referral). Returns the updated issue and a
re-verified reply, or `REJECTED` with a reason and the plan unchanged. Resending keeps the engine stateless:
we never hold the email between the first call and the staff change (deployment-options.md G1).

## 8. The four requirement areas

**Multi-question understanding — ready.** Each issue is handled independently; an unanswerable issue never
blocks an answerable one.

**Referencing and traceability — ready, pending KB access.** Every claim carries evidence IDs, source URL or
locator and version (slide 7–8: "Open source" goes to the NTU programme page). Blocked only on §5.

**Multimodal — evidence handling ready; image reading still to build.** Internal note: in the POC the receipt
image text is a fixture (hard-coded excerpt); only PDF text extraction is real. What is proven is the handling
after extraction. The POC sample is a bank transfer receipt: the engine treats its content as sender evidence, and routes "confirm my payment" to Manual handling because payment status
needs an authorised source. Model choice depends on real samples:
- mostly receipts, letters, certificates (text-dense) → OCR, then a text model; cheap;
- app/portal screenshots, error dialogs, tables → vision model; a few times the text cost per attachment.

**Self-Learning — phase 2.** LoadStone's loop (reviewer feedback → controlled evaluation → knowledge refresh)
is what to build, not online RL. Log every staff edit and override against the run; review them in batches;
fold approved corrections into the knowledge base and prompts, gated by the evaluation set from §6. Priced
as its own phase-2 line item.

## 9. Cost per email

### 9.1 What we measured (Formal Round A, GPT-5.6 Luna)

Seven frozen scenarios, run one at a time. Token counts are retained originals; dollar figures are the
documented Round A results (the dated price snapshot was not kept).

| Stage | Calls (7 emails) | Input tokens | Output tokens | Median latency |
|---|---:|---:|---:|---:|
| P0-A Understand | 7 | 6,186 | 2,594 | 5.5 s |
| P0-B Programme (semantic) | 8 | 4,206 | 879 | 2.0 s |
| P0-D Draft | 7 | 9,747 | 4,141 | 4.7 s |
| P0-E Verify | 7 | 11,923 | 870 | 2.0 s |
| P0-F Thread delta | 1 | 1,006 | 756 | 8.0 s |
| **Total** | **30** | **33,068** | **9,240** | — |
| **Per email** | **~4.3** | **~4,700** | **~1,300** | **13.0 s median end to end** |

Reported model cost: **~$0.0025 per email**, ~$12.43 for a 5,000-email week. Terra was >$0.016 and Sol
~$0.038 per email; Luna was also chosen on quality.

### 9.2 Why production will cost more per email than Round A

- **Retrieved context.** Round A grounded on a tiny fictional store. Real excerpts from NTU web pages and
  FAQ/policy excerpts make P0-D and P0-E inputs larger; plan for 2–3× input tokens on those stages.
- **Attachments.** OCR is cheap; a vision call adds roughly one extra model call with image tokens per
  attachment. The share of emails with screenshots is unknown.
- **Embeddings and index hosting** for retrieval; small per email, plus a fixed monthly cost.
- **Re-runs on staff overrides** (only the affected stages).
- **Price changes** between the Round A snapshot and today.

### 9.3 Cost model for the 1-pager

```
cost per email = Σ over stages ( calls × (input tokens × input price + output tokens × output price) )
               + attachment share × reading cost
               + retrieval cost per query
               + (hosting + monitoring) ÷ emails per month
fixed (not per email) = integration build, sample-email test set, evaluation, support
```

Planning range for model cost only, in multiples of the measured Round A figure:

| Case | Assumption | Model cost / email | Per 5,000-email week |
|---|---|---:|---:|
| Measured | Round A mix, tiny store | ~$0.0025 | ~$12 |
| Expected | 2–3× grounding context, 10–20% emails with OCR attachments | ~$0.005–0.008 | ~$25–40 |
| High | as above + vision on 20% of emails + override re-runs | ~$0.01–0.02 | ~$50–100 |

These ranges are estimates, not measurements. Before quoting, re-price at today's rates and measure on
shadow traffic: run the engine beside the live inbox for 1–2 weeks with nothing sent, and report cost and
latency per email by type (simple / multi-issue / follow-up / attachment). Keep cloud API cost and on-prem
GPU amortisation (on-prem licence, option C in §5.1) as separate lines; they are not comparable units.

## 10. Risks

| Risk | Mitigation |
|---|---|
| Fluent but unsupported reply | Independent verification + rule-based validation, fail closed |
| Receipt or screenshot read as institutional truth | `SENDER_PROVIDED` authority; payment confirmation is always Manual handling |
| Stale or contradictory knowledge | Versioned sources; `CONFLICTING` / `STALE` states; gap list from §6 |
| Prompt injection in email text | Email is data, never instructions; facts only from retrieval |
| Programme ambiguity (`Data Science`, `Cyber Security` variants) | Registry returns `AMBIGUOUS` + candidates → Ask for clarification |
| XML contract churn | Freeze semantics now, version the schema |
| Unit cost drifting from the estimate | Per-stage cost in every trace from day one; shadow run before commitment |
| Residency blocks the hosted API | Lead with masking + statelessness + zero-retention provider (§5.2); on-prem licence as priced fallback |
| Personal data leak on our side | Masking before model calls, stateless processing, isolated per-client deployment, DPA (§5.2) |

## 11. Division of work

**RSTN / NTU provide:** XML contract and sample payloads; programme registry; knowledge base access; routing
directory; de-identified sample emails with how PaCE handled them; sample screenshots; volume/latency profile; residency and model
policy; fallback wording; escalation policy for blocked runs.

**Synvo builds:** the hosted API (§5.1), masking and stateless processing (§5.2), the online engine (§3), override API, attachment reading, indexed retrieval against RSTN's
store, sample-email test set and gap list (§6), XML contract, per-stage cost/latency telemetry, evaluation set and
accuracy report, shadow-run cost report, the internal architecture diagram.

Open items and owners: `TODO.md`.
