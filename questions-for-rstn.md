# NTU PaCE Enquiry Engine — Pre-read for the RSTN × Synvo Technical Call

**Call:** Thursday 8 October 2026, 10:00 SGT
**From:** Synvo (Guowei Wang, AI tech lead; Li-kai Jiang)
**Reference:** *Workflow and Architecture* page (shared separately), which shows the diagram, the seven
processing steps and the proposed API.

Part 1 lists how we currently understand the project; please confirm or correct each point. Part 2 lists
our questions. Each one comes with our current proposal, so "agree" is a complete answer. Items marked
**[call]** are the ones we would most like to settle on Thursday. The rest can follow by email.

---

## Part 1 — Our understanding (please confirm or correct)

| # | Our understanding | ✔ / ✘ / comment |
|---|---|---|
| U1 | RSTN owns the system: mailbox and form intake, case records, case status, dashboard, staff screen, and sending or forwarding emails. | |
| U2 | Synvo provides the AI engine only, called by RSTN through an API, with one call per incoming email. Our POC screens are reference only. | |
| U3 | For each email, the engine returns: the separate issues in the email; the programme and owning team for each issue; a recommended action per issue (**Reply directly / Refer to receiving team / Ask for clarification / Manual handling**); one reply draft covering the answerable issues, with each statement linked to its source; and a decision trace. | |
| U4 | The engine **recommends only**. It never sends, forwards or updates a case. PaCE staff review, edit or override, and RSTN executes. | |
| U5 | Input will most likely be **XML over HTTPS**. Thread context (earlier messages) and attachments are passed in the same request. | |
| U6 | The engine answers only from **NTU-approved sources**: programme pages, FAQs and policies held in RSTN's knowledge base. Where those sources do not answer an issue, it recommends Clarify or Manual handling and does not guess. | |
| U7 | NTU will **not** provide historical emails for training. **Sample emails** will be provided for reference; we use them as a labelled test set, to list knowledge gaps, and as reply-style examples, never as a source of facts. | |
| U8 | Payment, application and TMS status are **not** available to the engine in phase 1. Issues that need them (e.g. "has my payment been received?") are always Manual handling. A receipt or screenshot from the sender is treated as the sender's evidence, not as confirmation. | |
| U9 | If the engine fails or cannot produce a safe result, RSTN sends its own approved acknowledgement and queues the case for staff. | |
| U10 | Proposed delivery: a **Synvo-hosted API** in a Singapore region, with personal data masked before analysis, and no copy of the email kept after the response. On-premise deployment only if NTU policy requires it. | |
| U11 | Learning from staff feedback ("Self-Learning") is **phase 2**, scoped separately. | |
| U12 | The programme registry (programmes, aliases, owning teams) is the source of truth for routing. The engine reads it but does not maintain it. | |

---

## Part 2 — Questions

### A. Integration and API

| # | Question | Our proposal / assumption |
|---|---|---|
| A1 **[call]** | Can you share the **XML schema or 3–5 sample payloads** for an incoming email (email and web-form)? | We adapt to your schema; we will bring our draft request/response fields to the call. |
| A2 **[call]** | How are **threads and follow-ups** identified (thread ID, In-Reply-To, your case ID)? Will you pass earlier messages, or should the engine fetch them? | You pass the permitted earlier messages in the same request. |
| A3 | How are **attachments** passed: inline (base64) or by reference URL? Size and type limits? | Inline up to an agreed size; reference URL above it. |
| A4 **[call]** | **Synchronous or asynchronous?** Should the engine reply on the same call, or call back / be polled? | Asynchronous with a callback, so peaks do not block intake; synchronous is possible for low volume. |
| A5 | Should the **result be XML or JSON**? Which fields will your staff screen show? | Same format as the request. Full result returned; you choose what to display. |
| A6 | When staff **change the recommended action** for an issue, should RSTN call the engine to re-check the change (as in our POC), or handle it on your side? | A second call in which RSTN resends the email and the previous result with the change. The engine re-checks only that issue and keeps nothing between calls. |
| A7 | How should a **failed or blocked run** be signalled, and who owns the fallback acknowledgement wording? | Explicit status in the result; RSTN owns the wording. |
| A8 | **Authentication** between RSTN and the engine? | Mutual TLS or signed requests, with per-environment keys. |
| A9 | **Environments**: will there be a test/UAT environment with sample data, and when? | We provide a sandbox API endpoint for your integration testing. |
| A10 | Could you share **RSTN's architecture diagram**, so we can align our side with it? | — |

### B. Knowledge and data sources

| # | Question | Our proposal / assumption |
|---|---|---|
| B1 **[call]** | Where does the **approved knowledge** live on your server, in what form (documents, web pages, database), and how are **versions and withdrawals** tracked? | — |
| B2 **[call]** | May a **versioned copy** of that approved knowledge be synced to the engine's index? Most of it is public NTU content. If not, can you expose a **query interface**? | Periodic sync of a versioned copy, plus an immediate update when content is withdrawn. |
| B3 **[call]** | Does a **programme registry** exist today (programmes, aliases, status, owning team, contact inbox)? If not, who will build and maintain it? | We read it; NTU/RSTN maintain it. We can help with an initial draft from NTU web pages. |
| B4 | How is the **owner** decided when it depends on the type of question (e.g. admission → school, fees → finance)? Is there a routing table by programme and intent? | Registry plus routing rules by intent. |
| B5 | Which sources are **approved** for answering: programme pages, FAQs, policies, fee tables, intake calendars? Are NTU public programme pages approved (our POC cited them)? | Programme pages, FAQs and policies; nothing else unless approved. |
| B6 | Is there any plan for an authorised interface to **payment, application or TMS status**? | Not in phase 1 (see U8). Later: the engine returns which data an issue needs, RSTN looks it up inside NTU and resends, so the engine never calls NTU systems directly. |

### C. Sample emails and attachments

| # | Question | Our proposal / assumption |
|---|---|---|
| C1 **[call]** | How many **sample emails** can be shared, and when? | A few hundred, de-identified, covering the main programmes, multi-question emails, follow-ups and emails with attachments. |
| C2 | Can each sample include **how PaCE handled it**: answered directly, forwarded to which team, or asked for details? | This is what lets us measure routing and action accuracy. |
| C3 | Who **de-identifies** the samples, and who in PaCE can **confirm our labels**? | PaCE or RSTN de-identifies before sharing; one PaCE contact reviews labels. |
| C4 **[call]** | Can you share **10–30 example screenshots/attachments** (redacted), and roughly what share of emails carry one? | This decides whether text extraction (OCR) is enough or image understanding is needed. |

### D. Volume and performance

| # | Question | Our proposal / assumption |
|---|---|---|
| D1 | Expected **peak emails per hour** and per day (we have ~700–1,000 per day, ~5,000 per week from discovery)? | — |
| D2 | **Acceptable processing time** per email before a result is needed? | Within minutes, not seconds, since staff review follows; to be confirmed. |
| D3 | Should **every** email go through the engine, or only some channels or programmes at first? | Start with the pace@ntu.edu.sg mailbox and enquiry form. |

### E. Hosting and data protection

| # | Question | Our proposal / assumption |
|---|---|---|
| E1 **[call]** | Does NTU policy allow a **Synvo-hosted API in Singapore**, with masked email text processed there and nothing retained? Any residency or data-classification rules we must meet? | Hosted API (U10); on-premise only if required. |
| E2 | What does NTU require from a **data intermediary** under the PDPA: DPA template, security questionnaire, penetration test, audit rights? | We will provide a security pack: data flow, retention, access control and incident process. |
| E4 **[call]** | Could RSTN run a small **masking component** inside your network, so that names, email addresses, phone numbers and NRIC are replaced with placeholders before anything reaches the engine, and restored in the reply on your side? | We provide the component; it holds no business logic. Without it, the engine masks on arrival and stores nothing. |
| E5 | We do not need the **sender's email address, To or CC**. Can RSTN send an opaque sender reference instead? | Yes, opaque reference only. |
| E3 | **Retention**: may the engine keep decision traces (IDs, labels, source references, timings, no email text), and for how long? Any audit export format needed for reporting? | Traces kept for an agreed period; no email text stored. |

### F. Acceptance and timeline

| # | Question | Our proposal / assumption |
|---|---|---|
| F1 **[call]** | What are the **acceptance measures and targets** for phase 1 (routing accuracy, action accuracy, reply quality, handling time)? | Measured on the labelled sample set, then in a shadow run. |
| F2 | Can we run a **shadow period** (engine runs on live emails, nothing is sent, staff compare) before go-live? | 1–2 weeks. |
| F3 **[call]** | Target **timeline**: integration start, UAT, go-live? Any fixed dates (e.g. admission peaks)? | — |
| F4 | Who are the **contacts** on RSTN and PaCE for integration, knowledge content and sample labelling? | — |

---

## What we hope to leave the call with

1. Confirmation of, or corrections to, Part 1.
2. Sample payloads or the schema (A1), and the sync/async decision (A4).
3. How the engine reaches the approved knowledge (B1–B2), and whether a programme registry exists (B3).
4. A date for the sample emails and screenshots (C1, C4).
5. A position on hosting (E1) and the masking component (E4), or who at NTU decides them.
6. Phase 1 acceptance measures and timeline (F1, F3), and named contacts (F4).
