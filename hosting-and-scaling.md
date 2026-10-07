# Hosting, Data Access and Scaling (internal)

Audience: Synvo internal. Companion to `deployment-options.md`. Questions answered:
1. Do we query NTU every time for knowledge and institutional data (payment status, etc.)? What latency?
2. For the hosted API (e.g. on Google Cloud), what hardware do we need?
3. What changes if we sell the same engine to more customers?

Figures marked *est.* are order-of-magnitude planning numbers, not measurements or quotes. Cloud prices must be checked in the provider's pricing calculator before they go into any proposal.

---

## 1. Do we call NTU on every email?

**Short answer: no for knowledge, rarely for institutional data, and never directly from our side.**

| Data | Changes how often | Personal data? | How the engine gets it | Calls to NTU per email |
|---|---|---|---|---|
| **Knowledge** (programme pages, FAQs, policies) | Days to weeks; withdrawals must apply fast | No | **Synced copy** in our index: full sync daily, plus a push or webhook from RSTN when content changes or is withdrawn | **0** |
| **Programme registry / routing rules** | Weeks | No (team inboxes only) | Synced with the knowledge | **0** |
| **Institutional state** (payment, application, TMS) | Live, per person | **Yes** | Not available in phase 1 (Manual handling). Later: **RSTN looks it up and passes it in**; we never call NTU systems | **0 from us**; RSTN does at most 1 lookup, only for issues that need it |

### 1.1 Knowledge: sync, not live query

| | Synced copy (proposed) | Live query to RSTN per email (fallback) |
|---|---|---|
| Retrieval latency | *est.* 10–50 ms per issue (local vector + keyword search) | *est.* 100–500 ms per query over the network × 1–3 queries per issue |
| Effect on total time | Negligible against ~13 s of model time (Round A median) | Adds up to 1–3 s per email; still small, but variable |
| Availability | Engine works if RSTN's server is down | RSTN downtime → every email degrades |
| Load on RSTN | One sync job per day | 700–1,000 emails/day × issues × queries |
| Staleness risk | Up to the sync interval, closed by the withdrawal webhook | None |
| Privacy | Copy holds public content only | Query text is derived from the email, so masked questions travel to RSTN |

Size: PaCE's approved knowledge is likely a few hundred programme pages plus FAQs and policies, i.e. *est.* tens of MB of text and well under 1 GB including the index. The POC knowledge store is 12 KB of fixtures.

Every answer cites the `knowledgeVersion` it used. When a source is withdrawn, the webhook removes it at once, so a withdrawn page is never cited, even between daily syncs.

### 1.2 Institutional data: let RSTN fetch it, only when needed

Payment and TMS status are live, personal and owned by NTU systems behind NTU authentication. Copying them to us would breach data minimisation. Calling NTU systems from our cloud would put us inside NTU's network and access controls. Instead:

```
1st call   RSTN ──email──► engine ──► result: issue 3 = MANUAL_REVIEW,
                                       requiredInstitutionalContext = [payment status, ref APCDSAI-917284]
           RSTN looks up payment status inside NTU (its own access, its own audit)
2nd call   RSTN ──email + previous result + {payment: RECEIVED, asOf: …}──► engine
                                       ──► issue 3 re-checked: ANSWER, reply updated
```

- This is the same stateless resend pattern as the staff override (`deployment-options.md` G1). We hold nothing between calls.
- It happens only for issues that need it. In discovery, payment and learner-status questions are a minority of PaCE email.
- Latency: RSTN's lookup (*est.* < 1 s inside NTU) plus a partial re-run of one issue (*est.* 3–6 s, mostly draft and verify). The email still completes well within staff review time.
- Phase 1: no lookup. These issues stay Manual handling, as already agreed (questions U8, B6).

### 1.3 Per-email latency budget (hosted API, synced knowledge)

| Step | *est.* time | Note |
|---|---|---|
| Network RSTN → us → RSTN | 50–150 ms | Singapore region both ends |
| Validate, mask | 100–500 ms | NER masking on CPU |
| OCR (only with attachments) | 1–3 s per page | Local CPU OCR |
| Model steps (understand, programme, draft, verify) | ~13 s median | Round A, sequential; dominated by the model provider |
| Retrieval + rules | < 100 ms | Local |
| **Total** | **~14–20 s per email** | Async with callback, so it never blocks RSTN's intake |

The model provider dominates. Any NTU-side lookups are outside the critical path.

## 2. Hosting hardware (hosted API on Google Cloud, Singapore `asia-southeast1`)

### 2.1 Why the footprint is small

The engine **orchestrates**. The heavy compute, i.e. the language models, runs at the model provider and is paid per token. Our servers handle request validation, masking, OCR, retrieval, rules and calls to the provider, mostly waiting on the network. **No GPU is needed** unless we self-host models (§2.4).

Throughput check: 1,000 emails/day with a 3× peak hour gives ~125 emails/hour, about 2 per minute. At ~15 s each, that is ~1 email in flight on average and *est.* < 10 at bursts. Model provider rate limits: ~6k tokens/email × 125/h ≈ 750k tokens/h ≈ 12.5k tokens/minute, well below typical enterprise limits.

### 2.2 Components, one environment

| Component | GCP service (example) | Size *est.* | Purpose |
|---|---|---|---|
| API service | Cloud Run (containers) | 2 vCPU / 4 GB, min 2 instances for availability, autoscale to ~10 | Endpoints, orchestration, rules |
| Job queue | Cloud Tasks or Pub/Sub | Managed | Async runs and callbacks; retries on provider errors |
| Masking + OCR worker | Cloud Run or a small GKE pool | 2–4 vCPU / 8 GB | NER masking (e.g. Presidio-style), OCR (e.g. Tesseract/PaddleOCR on CPU), image redaction |
| Knowledge index | Cloud SQL Postgres + pgvector | 2 vCPU / 8 GB, HA, ~20 GB disk | Knowledge, registry, versions; **no enquiry data** |
| Trace store | Same Postgres, separate schema, or BigQuery | Small | Content-free traces for billing and monitoring |
| Secrets, keys | Secret Manager + Cloud KMS | Managed | Provider keys, per-tenant encryption keys |
| Logs, monitoring | Cloud Logging / Monitoring | Managed | **Body capture disabled** (`deployment-options.md` G6) |
| Edge | Cloud Load Balancing + Cloud Armor | Managed | TLS, mTLS or signed requests, IP allow-list for RSTN |
| Environments | Same stack for test/UAT and production | Test at minimum size | Sandbox for RSTN integration (questions A9) |

Infrastructure cost for one dedicated production environment is *est.* a few hundred USD per month, with UAT on top. **Verify in the GCP pricing calculator.**

### 2.3 What this means for unit economics

Model cost for PaCE is *est.* $25–40 per week, i.e. ~$100–170 per month (`unit-cost.html`). A dedicated environment's fixed infrastructure is of the same order or larger. **At one customer, infrastructure, not the model, can dominate cost per email.** Sharing infrastructure across customers (§3) brings cost per email back towards model cost.

### 2.4 If a customer requires self-hosted models (on-prem licence, or our own GPUs)

| Model class | GPU need *est.* | Note |
|---|---|---|
| Small (~7–14B) | 1 × 24–48 GB GPU | Fine for masking/classification helpers; weak for drafting and verification |
| Medium (~30B) | 1 × 80 GB or 2 × 48 GB | Possible for some steps; needs our own evaluation on the test set |
| Large (~70B+) | 2–4 × 80 GB | Closest to hosted-model quality; costly to run 24/7 |

A 24/7 GPU node costs thousands of USD per month. That is far above PaCE's model bill, so self-hosting only makes sense when policy requires it. It would then be priced into the on-prem licence.

### 2.5 Model provider and region (to settle before go-live)

- The POC uses OpenAI models (GPT-5.6 Luna selected in Round A). Confirm which endpoints offer a **Singapore region with zero data retention** for that model. If none do, either accept processing in another region (NTU's transfer-limitation decision, disclosed in the DPA) or re-run the model evaluation on a provider that does.
- Option: Google's models through Vertex AI in `asia-southeast1` keep data inside the same cloud and region. This requires re-running Round A on the test set before switching. The model gateway already allows swapping per step.

## 3. Selling the same engine to more customers

### 3.1 What is PaCE-specific today

| PaCE-specific today | Generalise to |
|---|---|
| Programme registry | **Catalogue** of entities (programmes, products, services) with aliases and status |
| Owning schools and teams | **Owners** with routing rules by entity × intent |
| NTU web pages, FAQs, policies | **Knowledge connectors**: web crawl, file upload, CMS or API, each versioned |
| Four actions and their labels | Same four actions; **labels and allowed actions configurable per tenant** |
| PaCE reply tone | **Per-tenant reply style** examples and templates |
| Payment/TMS manual rule | **Per-tenant policy**: which issues always need staff |
| Sample-email test set | **Per-tenant test set**; onboarding is blocked until it passes |

The core (understand, identify, check, recommend, draft, verify, trace) stays one codebase and one release.

### 3.2 Multi-tenant design, built in from the start

- **Tenant identity on everything:** API keys, configs, knowledge, traces and encryption keys are scoped by `tenantId`. No query can cross tenants (row-level security or separate schemas, plus tests).
- **Two isolation tiers:**
  - *Pooled:* shared services, logical isolation, per-tenant keys. Cheapest; for most customers.
  - *Dedicated cell:* the same stack deployed per customer from one Terraform template. For regulated or large customers. NTU may well ask for this.
- **Regional cells:** one cell per region (Singapore first) so a customer's data stays in its region.
- **Per-tenant config, versioned:** catalogue, routing, labels, policies, style and model choice per step. A config change runs that tenant's test set before release.
- **Metering and quotas per tenant:** emails, tokens and cost per tenant from the trace. Rate limits so one customer's peak cannot starve another. This is also the billing source.
- **Onboarding pipeline:** connect knowledge → build catalogue → label sample emails → run test set → shadow run → go live. The more of this is tooling, the cheaper each new customer is.
- **Same privacy posture for everyone:** stateless processing, masking, optional privacy connector, ZDR provider and content-free traces. These are product features, not one-off promises.
- **Release safety:** one engine version for all tenants, rolled out per cell, gated on every tenant's test set; per-tenant pinning only as an exception.

### 3.3 Impact on the PaCE build

Building PaCE as **tenant #1 of a multi-tenant engine** costs little extra now. Tenant IDs, config instead of code, and per-tenant keys are cheap to add up front and expensive to retrofit. Deploy PaCE as a **dedicated cell**, which matches the isolation we have promised, from the same template that later runs pooled tenants.

## 4. Actions

1. Propose knowledge **sync + withdrawal webhook** to RSTN (questions B2), and the **RSTN-side lookup** pattern for future institutional data (questions B6).
2. Provider check: Singapore region + ZDR for the selected model (TODO B23); evaluate a Vertex AI option.
3. Infrastructure: Terraform template for one cell; size as §2.2; price it in the GCP calculator (Li-kai).
4. Engine extraction (TODO B6): add `tenantId` and per-tenant config from the start.
5. Correct the multimodal readiness: the POC's image reading is a **fixture** (`IMAGE_FIXTURE`, hard-coded excerpt); only PDF text extraction is real. Real OCR/vision still has to be built (TODO B11).
