# Deployment Options — SDK vs Hosted API (internal)

Audience: Synvo internal. Not for the customer.
Question: should we deliver the engine as a binary SDK that runs at the customer, or as a cloud API hosted by
us? Two concerns raised:
1. SDK: we may lose control of customer behaviour and traffic tracking. Is that bad for the business story,
   and can log collection fix it?
2. Cloud API: storing customer data on our side could be a problem. How much do we need to collect or
   store, and does it breach their privacy protection?

---

## 1. Bottom line

**Decision 2026-10-07: promote option C (hosted engine + on-prem privacy connector) to RSTN first.** Option A
(hosted only) is the fallback if RSTN cannot run the connector; option B (SDK) is a priced on-prem licence only.


- **Lead with the hosted API.** As designed, it does not need to store any enquirer personal data. It is
  compatible with Synvo acting as NTU's data intermediary under the PDPA, provided we close the gaps in §4.3.
  Three of those are real defects in the current design.
- **Add an optional on-prem "privacy connector"** (§5). This small component runs in RSTN's network and masks
  personal data before anything leaves NTU, then restores it in the reply. The engine, prompts and models stay
  in our cloud. It answers the privacy concern without giving up control.
- **A full binary SDK only as a priced on-prem licence.** Log collection can give us usage reporting for
  billing and audit. It cannot give us enforcement, quality visibility or protection of our prompts (§3).
  It weakens the recurring-revenue story but is not a dead end if priced as an enterprise licence.

## 2. Options

| | **A. Hosted API** | **B. Binary SDK, fully on-prem** | **C. Hosted API + on-prem privacy connector** |
|---|---|---|---|
| Where the engine runs | Synvo cloud (SG region) | Customer servers | Synvo cloud |
| Where model calls go | Our provider account, ZDR endpoints | Customer's own key, or local model | Our provider account |
| What leaves NTU | Email text and attachments; we mask on arrival | Nothing, or excerpts to the customer's model provider | Masked text only; real names and identifiers never leave |
| Our IP (prompts, rules, evaluation) | Stays with us | Shipped inside the binary; extractable | Stays with us; connector holds only generic masking |
| Usage metering | Exact: every call passes through us | Self-reported by the SDK | Exact |
| Quality monitoring, hotfixes | Live, central | Blind; customer controls upgrades | Live, central |
| Self-Learning (phase 2) | Feedback flows to us | Feedback stays at customer | Feedback flows to us (masked) |
| Customer ops burden | None | Install, host, patch, GPU if local models | Run one small service |
| Privacy story | Good, needs trust in our masking | Strongest | Strong: we never see real identifiers |
| Revenue model | Per email, recurring | Licence + maintenance | Per email, recurring |

## 3. SDK: control, tracking and the business story

### 3.1 What we lose with a binary SDK

- **Usage visibility.** If the SDK uses the customer's own model key or a local model, every call bypasses us.
  We see nothing unless the SDK reports it.
- **Our IP.** The engine's value lies in prompts, decision rules, schemas and the evaluation set. The POC is
  TypeScript. Bundling it into a binary only slows extraction, because prompts are plain text in memory.
- **Quality and safety.** We cannot see blocked runs, accuracy drift or failures, so problems reach us late
  and through complaints.
- **Release control.** The customer chooses when to upgrade. Version drift multiplies our support cost, and a
  safety fix cannot be pushed.
- **Phase 2.** Self-Learning needs staff edits and outcomes. With an SDK those stay at the customer.

### 3.2 Can log collection solve it?

Partly: it solves **reporting**, not **control**.

| Mechanism | What it gives | Limits |
|---|---|---|
| SDK sends content-free usage records daily (run count, timestamps, stages, tokens, run health, versions) to our endpoint | Billing basis; basic health trend | NTU on-prem networks often block outbound traffic. The customer can disable it |
| Signed, hash-chained usage file exported monthly when outbound is blocked | Tamper-evident record for billing and audit | Tamper-evident, not tamper-proof; relies on the customer sending it |
| Signed licence with expiry and volume tier; renewal needs the latest usage report | Leverage: no report, no renewal | A hard stop would break PaCE's inbox. Real enforcement is a grace period, then fallback-only mode. That is commercially sensitive with a university |
| Contractual audit rights | Legal backstop | Slow, adversarial; rarely used with a strategic customer |
| SDK calls models **through our hosted gateway** (variant B2) | Exact metering; prompts can stay server-side | Masked email text then passes through us, so it is effectively option C with more moving parts |

Logs must stay **content-free**: counts, IDs, timings and versions only. Logs that carried email text would
recreate the privacy problem the SDK was meant to avoid.

### 3.3 Business story

- **Hosted API:** usage-based recurring revenue, a live quality dashboard, a central improvement loop and reuse
  for other customers. This is a SaaS story and the stronger one.
- **SDK:** licence and maintenance revenue, closer to a services or software-licence story. It is still
  sellable to education and government buyers who require on-prem, but price it as a fixed enterprise licence
  with volume tiers. Do not price per email when the per-email count is self-reported.
- **Verdict:** the SDK is not "bad", but it should not be the default. Offer it only when policy forbids
  hosting, at a price that covers support and version drift.

## 4. Hosted API: what data we touch and whether it is a privacy problem

### 4.1 Data inventory, per email

| Data | Why the engine needs it | Personal data? | Sent to the model? | Stored by us (target design) |
|---|---|---|---|---|
| Body, subject | Understand the issues | Yes: names, phone numbers, sometimes NRIC or payment references | **Masked** text only | No |
| Earlier thread messages | Follow-up changes | Yes | Masked | No |
| Attachments | Read receipts and screenshots | Yes: names, account numbers | Masked OCR text; image only when OCR fails, after local redaction | No |
| Web-form fields (programme picked, etc.) | Programme hints | Usually no | Yes | No |
| **Sender address, To/CC** | **Not needed** for any engine step | Yes | No | No. **Drop from the request** (§4.3) |
| Message and thread IDs | Correlation, idempotency | Pseudonymous | No | In trace |
| NTU institutional data (future: payment status, etc.) | Answer issues needing it | Yes | Only the specific field needed | No |
| **Result** (issue summaries, rationale, reply, handoff notes) | Returned to RSTN | Yes, after names are restored | n/a | **No** |
| **Trace** (stage, status, tokens, latency, versions, hash of masked input, labels) | Billing, monitoring, audit | No | n/a | Yes, for an agreed period (e.g. 12 months) |
| HTTP access logs (caller, request ID, status, size) | Operations, security | No (RSTN's server, not enquirers) | n/a | Yes, 30–90 days |
| Sample emails / test set | Accuracy testing | De-identified before we receive it | Masked, during test runs | Yes, for the project only; deleted at end |
| Knowledge copy (programme pages, FAQs, policies) | Evidence for answers | No (public institutional content) | Excerpts | Yes, versioned |

**Result:** in steady state we store **no enquirer personal data**. Personal data is processed **transiently,
in memory**, during a run of about 15 seconds. Masked text passes through the model provider on a
zero-retention endpoint.

### 4.2 Against the PDPA (Synvo as data intermediary)

A data intermediary's main obligations are **protection** (reasonable security arrangements), **retention
limitation** (do not keep data longer than needed) and **breach notification** to the organisation (NTU).
The organisation, NTU, keeps the consent, purpose and **transfer limitation** obligations. If any processing
happens outside Singapore, for example at a model provider's region, NTU needs contractual safeguards.

| Obligation | Status in our design |
|---|---|
| Protection | Masking, TLS + authenticated requests, encryption at rest, per-client isolation, least-privilege access, audit logs |
| Retention limitation | Stateless processing; trace without content; no result storage; test set deleted at project end |
| Breach notification | Process to notify NTU without undue delay, written into the DPA |
| Transfer (NTU's duty; we enable it) | Keep processing and model endpoint in Singapore where available; list sub-processors and regions in the DPA |

Conclusion: the hosted API does **not** inherently breach privacy protection. The risk lies in the
implementation details below.

**To confirm with NTU (not assumed here):** whether NTU applies any additional internal cloud or data
classification policy on top of the PDPA, and whether enquiry emails fall into a restricted category. This is
question E1/E2 in `questions-for-rstn.md`.

### 4.3 Gaps in the current design (fix before we promise "nothing stored")

| # | Gap | Fix |
|---|---|---|
| G1 | **Override needs stored state.** `POST /override` takes only `runId`, so we would have to keep the email and result between the first call and the staff change (hours or days) | **Stateless override:** RSTN resends the original request plus the previous result, signed by us, together with the issue and the requested action. Fallback, only if resending is impossible: an encrypted cache with a short time limit (e.g. 72 h), disclosed in the DPA |
| G2 | **The POC persists everything.** Its database stores `Message.body`, addresses, `AiCapabilityRun.structuredOutput` and `ReliabilityRun.result` (the full result). Carrying this into the engine would make us a store of personal data | When extracting the engine (TODO B6), drop all content tables. Keep only trace fields: stage, status, tokens, latency, versions, hash of the masked input |
| G3 | **The request asks for more than we need.** Sender address, recipients and CC are not used by any step | Remove them from the request. RSTN passes an opaque `senderRef`. The reply uses a `[NAME]` placeholder that RSTN fills in |
| G4 | **Masking happens after data reaches us.** Raw text arrives at our servers before we mask it | Option C connector (§5), or RSTN masks in its own pipeline with our masking library |
| G5 | **Vision calls can leak identifiers.** A receipt image contains a name and account number | OCR first. Redact detected regions in the image locally before any vision call. Vision only when OCR is insufficient |
| G6 | **Application and error logs can capture payloads**, e.g. exception traces or APM request bodies | Never log request or response bodies; scrub at the logger; turn off crash dumps and payload capture in APM; add a test that fails if a body appears in logs |
| G7 | **Provider-side retention.** Many model providers keep prompts for a period for abuse monitoring unless zero data retention is approved for the account | Get written ZDR approval for our account before go-live; list the provider as a sub-processor |
| G8 | **Masking is not perfect.** Named-entity detection misses some names and identifiers | Layered defence: connector-side masking + ZDR + no storage. Measure the masking miss rate on the sample set and report it |

## 5. Option C: on-prem privacy connector + hosted engine

```
NTU / RSTN network                                   Synvo cloud (SG)
┌─────────────────────────────────┐                  ┌──────────────────────────┐
│ RSTN system                     │                  │ Engine (7 steps)         │
│   │ raw email + attachments     │                  │ prompts, rules, models   │
│   ▼                             │  masked text,    │ knowledge index (public) │
│ Privacy connector (Synvo, thin) │  placeholders ──►│ trace (no content)       │
│   · OCR attachments locally     │                  │                          │
│   · mask names, emails, phones, │ ◄── result with  │                          │
│     NRIC, account refs          │     placeholders │                          │
│   · keep the mapping in memory  │                  └──────────────────────────┘
│   · restore names in the reply  │
│   ▼                             │
│ RSTN staff screen               │
└─────────────────────────────────┘
```

- The connector contains no prompts or decision logic, only generic masking, OCR and restoring. Giving it
  to the customer costs us no IP.
- The identifier mapping never leaves NTU. Our cloud sees `[NAME_1]`, `[PHONE_1]`, `[NRIC_1]`.
- Metering, monitoring, hotfixes and phase 2 all stay with us, as in option A.
- Cost: one small service for RSTN to run. If RSTN refuses, we fall back to A and mask on arrival (G4 stays
  a disclosed residual risk).

## 6. What to do

1. Keep the hosted API as the proposal. Add the privacy connector as the answer to "what about personal data",
   and ask RSTN on Thursday whether they can run it (`questions-for-rstn.md`, E4).
2. Fix G1–G3 in the API contract now (`draft-solution.md` §7), before we show RSTN the fields.
3. G2, G5, G6: build requirements for the engine extraction (TODO B6, B19, B20).
4. G7: ask the model provider for ZDR approval in writing (TODO B23).
5. SDK: do not offer proactively. If NTU requires on-prem, quote a fixed licence with volume tiers, signed
   usage reports and audit rights. Prefer variant B2 (model calls through our gateway) if outbound traffic is
   allowed.
