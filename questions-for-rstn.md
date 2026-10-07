# NTU PaCE Enquiry Engine — Pre-read for the RSTN × Synvo Technical Call

**Call:** Thursday 8 October 2026, 10:00 SGT

**From:** Synvo (Guowei Wang, AI tech lead; Li-kai Jiang)

This note has three parts:
1. **Proposed setup:** a short description of how we propose to deliver the engine.
2. **Our understanding:** please confirm or correct each point.
3. **Questions:** each comes with our proposal, so "agree" is a complete answer.

Items marked **★** are the ones we would most like to settle on the call. The rest can follow by email.

---

## 1. Proposed setup at a glance

```
NTU / RSTN network                                      Synvo (Singapore)
┌───────────────────────────────────────┐
│ RSTN system: intake, case, staff UI   │
│        │ email + attachments          │
│        ▼                              │  masked request   ┌──────────────────────┐
│ Privacy connector (supplied by Synvo) │ ────────────────► │ Enquiry engine       │
│  · reads attachments (OCR)            │                   │ issues, programme,   │
│  · replaces names, contacts, NRIC,    │  masked result    │ action, cited reply, │
│    payment refs with placeholders     │ ◄──────────────── │ checks, trace        │
│  · puts them back in the result       │                   └──────────────────────┘
│        │                              │
│        ▼                              │
│ PaCE staff review, edit, act          │
└───────────────────────────────────────┘
```

- **Personal data stays inside NTU.** The engine sees placeholders such as `[NAME_1]`, never who the enquirer is.
- **Nothing is kept.** The engine keeps no copy of the email, attachments or reply after it responds.
- **Little to run on RSTN's side.** RSTN runs one small container, the connector. It holds no business logic and needs no GPU. The engine is hosted and updated by Synvo.
- **Alternatives** if needed:
  - *hosted engine only*, where RSTN calls the engine directly and data is masked on arrival;
  - *on-premise licence*, where the whole engine runs in NTU's network, quoted separately.

---

## 2. Our understanding (please confirm or correct)

| # | Our understanding | ✔ / ✘ / comment |
|---|---|---|
| U1 | RSTN owns the system: mailbox and form intake, case records, case status, dashboard, the staff screen, and sending or forwarding emails. | |
| U2 | Synvo provides the AI engine and the privacy connector, called by RSTN through an API with one call per incoming email. Our POC screens are for reference only. | |
| U3 | For each email, the engine returns:<br>• the separate issues in the email;<br>• the programme and owning team for each issue;<br>• one recommended action per issue (**Reply directly / Refer to receiving team / Ask for clarification / Manual handling**);<br>• one reply draft covering the answerable issues, with each statement linked to its source;<br>• a decision trace. | |
| U4 | The engine **recommends only**. It never sends, forwards or updates a case. PaCE staff review, edit or override, and RSTN executes. | |
| U5 | Input will most likely be **XML over HTTPS**. Earlier messages in the thread and attachments are passed in the same request. | |
| U6 | The engine answers only from **NTU-approved sources**: programme pages, FAQs and policies. Where these do not answer an issue, it recommends Ask for clarification or Manual handling. It does not guess. | |
| U7 | NTU will **not** provide historical emails for training. **Sample emails** will be provided for reference. We use them as a labelled test set, to list knowledge gaps, and as examples of reply style, never as a source of facts. | |
| U8 | Payment, application and TMS status are **not** available to the engine in phase 1. Issues that need them (e.g. "has my payment been received?") are always Manual handling. A receipt or screenshot from the sender counts as the sender's evidence, not as confirmation. | |
| U9 | If the engine fails or cannot produce a safe result, RSTN sends its own approved acknowledgement and queues the case for staff. | |
| U10 | Proposed delivery is as in section 1: a Synvo-hosted engine in Singapore, with a privacy connector in RSTN's network so personal data does not leave NTU, and nothing kept after the response. | |
| U11 | Learning from staff feedback ("Self-Learning") is **phase 2**, scoped separately. | |
| U12 | The programme registry (programmes, aliases, owning teams) is the source of truth for routing. The engine reads it but does not maintain it. | |

---

## 3. Questions

### A. Integration and API

| # | Question | Our proposal / assumption |
|---|---|---|
| A1 ★ | Can you share the **XML schema or 3–5 sample payloads** for an incoming email, for both email and web form? | We adapt to your schema. We will bring our draft request and result fields to the call. |
| A2 ★ | How are **threads and follow-ups** identified: thread ID, In-Reply-To, or your case ID? Will you pass earlier messages, or should the engine fetch them? | You pass the relevant earlier messages in the same request. |
| A3 | How are **attachments** passed: inline (base64) or by reference? What size and type limits apply? | Inline up to an agreed size, by reference above it. The connector reads them before anything leaves NTU. |
| A4 ★ | Should the call be **synchronous or asynchronous**? Should the engine reply on the same call, or call back or be polled? | Asynchronous with a callback, so peaks never block intake. Synchronous is possible at low volume. |
| A5 | Should the **result be XML or JSON**? Which fields will your staff screen show? | Same format as the request. We return the full result; you choose what to display. |
| A6 | When staff **change the recommended action** for an issue, should RSTN call the engine to re-check the change, as in our POC, or handle it on your side? | RSTN resends the email and the previous result with the change. The engine re-checks only that issue and keeps nothing between calls. |
| A7 | How should a **failed or blocked run** be signalled, and who owns the fallback acknowledgement wording? | Explicit status in the result. RSTN owns the wording. |
| A8 | How should RSTN and the engine **authenticate** each other? | Mutual TLS or signed requests, with separate keys per environment. |
| A9 | Will there be a **test/UAT environment** with sample data, and when? | We provide a sandbox engine and connector for your integration testing. |
| A10 | Could you share **RSTN's architecture diagram**, so we can align our side with it? | — |

### B. Knowledge and data sources

| # | Question | Our proposal / assumption |
|---|---|---|
| B1 ★ | Where does the **approved knowledge** live, and in what form (documents, web pages, database)? How are **versions and withdrawals** tracked? | — |
| B2 ★ | May a **versioned copy** of the approved knowledge be synced to the engine? Most of it is public NTU content. If not, can you expose a **query interface**? | A daily sync of a versioned copy, plus an immediate update when content is withdrawn. Answers always cite the version used. |
| B3 ★ | Does a **programme registry** exist today, with programmes, aliases, status, owning team and contact inbox? If not, who will build and maintain it? | The engine reads it; NTU or RSTN maintain it. We can help prepare a first draft from NTU web pages. |
| B4 | How is the **owner** decided when it depends on the type of question (e.g. admission goes to the school, fees to finance)? Is there a routing table by programme and question type? | Registry plus routing rules by question type. |
| B5 | Which sources are **approved** for answering: programme pages, FAQs, policies, fee tables, intake calendars? Are NTU's public programme pages approved? Our POC cited them. | Programme pages, FAQs and policies. Nothing else unless approved. |
| B6 | Is there any plan for an authorised interface to **payment, application or TMS status**? | Not in phase 1 (see U8). Later, the engine can state which data an issue needs; RSTN looks it up inside NTU and resends, so the engine never connects to NTU systems. |

### C. Sample emails and attachments

| # | Question | Our proposal / assumption |
|---|---|---|
| C1 ★ | How many **sample emails** can be shared, and when? | A few hundred, de-identified. They should cover the main programmes, emails with several questions, follow-ups, and emails with attachments. |
| C2 | Can each sample include **how PaCE handled it**: answered directly, forwarded to which team, or asked for details? | This is what lets us measure routing and action accuracy before go-live. |
| C3 | Who **de-identifies** the samples, and who in PaCE can **confirm our labels**? | PaCE or RSTN de-identifies before sharing. One PaCE contact reviews our labels. |
| C4 ★ | Can you share **10–30 example screenshots or attachments** (redacted)? Roughly what share of emails carry one? | This tells us whether text extraction is enough or deeper image analysis is needed. |

### D. Volume and performance

| # | Question | Our proposal / assumption |
|---|---|---|
| D1 | What are the expected **peak emails per hour and per day**? From discovery we have ~700–1,000 per day and ~5,000 per week. | — |
| D2 | How long may processing take per email before staff need the result? | Typically well under a minute per email. Staff review follows anyway. |
| D3 | Should **every** email go through the engine from day one, or only some channels or programmes at first? | Start with the pace@ntu.edu.sg mailbox and the enquiry form. |

### E. Hosting and data protection

| # | Question | Our proposal / assumption |
|---|---|---|
| E1 ★ | Does NTU policy allow the **proposed setup** in section 1, where only masked text leaves NTU, is processed in Singapore and is not retained? Are there residency or data-classification rules we must meet? | Proposed setup. Hosted engine only, or an on-premise licence, if policy requires. |
| E2 ★ | Can RSTN **host the privacy connector** in your network? Where would it run (VM, container platform), and who deploys updates? | One small container, CPU only, outbound HTTPS to the engine only. Synvo supplies signed updates; RSTN deploys them. |
| E3 | We do not need the **sender's email address, To or CC**. Can RSTN send an opaque sender reference instead? | Opaque reference only. |
| E4 | **Retention:** may the engine keep decision traces (IDs, labels, source references, timings, no email text), and for how long? Is an audit export format needed for reporting? | Traces kept for an agreed period. No email text stored. |
| E5 | What does NTU require from a **data intermediary** under the PDPA: DPA template, security questionnaire, penetration test, audit rights? | We provide a security pack covering data flow, retention, access control and incident process. |

### F. Acceptance and timeline

| # | Question | Our proposal / assumption |
|---|---|---|
| F1 ★ | What are the **acceptance measures and targets** for phase 1: routing accuracy, action accuracy, reply quality, handling time? | Measured first on the labelled sample set, then in a shadow run. |
| F2 | Can we run a **shadow period** before go-live, where the engine runs on live emails, nothing is sent, and staff compare? | 1–2 weeks. |
| F3 ★ | What is the target **timeline** for integration start, UAT and go-live? Are there fixed dates, e.g. admission peaks? | — |
| F4 | Who are the **contacts** at RSTN and PaCE for integration, knowledge content and sample labelling? | — |

---

## What we hope to leave the call with

1. Confirmation of, or corrections to, sections 1 and 2.
2. The schema or sample payloads (A1), and the decision on synchronous or asynchronous calls (A4).
3. How the engine receives the approved knowledge (B1, B2), and whether a programme registry exists (B3).
4. Dates for the sample emails and screenshots (C1, C4).
5. A position on the proposed setup and on hosting the privacy connector (E1, E2), or who at NTU decides.
6. Phase 1 acceptance measures, the timeline, and named contacts (F1, F3, F4).
