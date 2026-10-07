# Synvo Response to RSTN's Questions

**For:** RSTN, ahead of the technical call on Thursday 8 October 2026, 10:00 SGT

**From:** Synvo (Guowei Wang, AI tech lead; Li-kai Jiang)

**Attached:** *Workflow and Architecture* (PDF) and *Pre-read for the technical call* (our question list)

Thank you for the questions. Our answers are below, in your numbering. Where an answer depends on something only RSTN or NTU can tell us, we have added a short question back. These are collected in section 2, together with the points from our pre-read that we would most like to settle on the call.

---

## In short

- **The engine sits behind your system as a service.** It replaces none of your components. RSTN calls it once per email and gets back a structured result.
- **It recommends; it never acts.** Sending, forwarding and case updates stay with RSTN and PaCE staff.
- **Proposed setup:** Synvo hosts the engine in Singapore. A small **privacy connector**, supplied by Synvo, runs in RSTN's network. It masks names, contact details, NRIC and payment references before anything leaves NTU, and puts them back in the result. Nothing is kept after the response.
- **It is a fixed, auditable pipeline,** not an open-ended agent. Every run returns a full trace with your request ID.
- **No learning from staff feedback in phase 1.** It is planned for phase 2 as a reviewed, reversible process, and model weights are never changed.

---

## 1. Answers

### 1. What does the engine replace?

Nothing. The engine is a **service behind your system**. Your API, worker queue and database stay as they are. Your system calls the engine once per email and receives the issues found, the recommended action for each issue, a source-cited reply draft and a decision trace.

**a. Which components stay as they are?** All of them: Outlook intake, review console, audit log, login and roles. On your side, the additions are one outgoing call per email and, in the proposed setup, the privacy connector container.

**b. Who handles email ingestion?** RSTN. Our POC did not connect to a live mailbox. Emails were loaded through a demo page, so ingestion was never part of the engine and is not part of what we deliver.

### 2. Where does the engine run, which models, which region, and who decides?

- **Where it runs:** Synvo hosts the engine in Singapore. The privacy connector runs in RSTN's network, so only masked text leaves NTU. It is processed in Singapore and is not kept after the response. Alternatives, if NTU policy requires them, are in answer 6.
- **Models:** the engine reaches its AI steps through a model layer that can be configured and replaced per step without changing the business rules. The processing services and regions used for NTU will be set to meet NTU's data policy. We will list them in writing in our security pack and in the data processing agreement. If NTU has a preferred platform, we can assess it. Any change of model is re-validated on NTU's labelled sample set before use.
- **Who decides:** NTU sets the constraints: residency, data classification and approved processors. Synvo proposes a setup that meets them and is accountable for its quality. RSTN integrates it. We would like to agree the constraints early (question E1 in our pre-read).

### 3. A trace ID with our request ID, and per-step detail for the audit log?

Yes. Every result carries:
- **your request ID** (`correlationId`), our `runId`, and the engine, knowledge and configuration versions used;
- **per step:** step name, status, start and duration, whether an AI step ran, token counts, sources used (URL and version) and the rules applied.

The trace contains **no email text**, so it can go straight into your audit record. The model detail is given as the versioned configuration used for each step. This changes whenever a model or prompt changes.

### 4. Agent design

**a. Loop or fixed graph?** A **fixed pipeline** of seven steps:
1. validate and assemble;
2. read attachments;
3. understand and split into issues;
4. identify the programme and owner;
5. check information against approved sources;
6. recommend an action;
7. draft the reply and check it independently.

There is no open-ended loop. What each step may do is fixed in advance, so runs are predictable and auditable.

**b. Limits, and what happens when a step fails.**
- The number of steps is fixed.
- AI is used in only a few steps, with a capped number of calls per email.
- Each call has a timeout and a limited number of retries.

If a step fails, the result says so:
- run health is `DEGRADED` or `FAILED`;
- the reply draft is marked `BLOCKED` or `NOT_PRODUCED`;
- the engine never returns a reply that has not passed the independent check.

RSTN then sends its approved acknowledgement and queues the case for staff. We will agree exact timeouts and retry rules in the integration contract.

**c. Model calls and tokens per email.** Only two of the seven steps always use AI: understanding the email, and drafting and checking the reply. Reading attachments and identifying the programme use AI only when needed. The other steps are rules. An average email takes about **4–5 AI calls** and a few thousand tokens. We will measure this on NTU's sample emails and in the shadow run, and report it by email type: simple, several questions, follow-up, and with attachment.

### 5. Integration contract and sandbox

Yes. We have draft fields for three calls:
- **process an email:** request and result;
- **re-check a staff change:** see below;
- **callback:** for asynchronous results.

Once we have your XML schema or sample payloads, we will send the formal specification. It will cover:
- XSD or OpenAPI;
- asynchronous calls with a callback (synchronous is possible at low volume);
- idempotency keys;
- error codes;
- a `schemaVersion` field with backward-compatibility rules.

We will provide a **sandbox** with both the engine and the connector, so you can start integration early.

On staff changes: the engine keeps nothing between calls. To re-check a staff change, RSTN resends the original request, the previous result (signed by the engine) and the change. The engine re-checks only that issue.

### 6. How is the engine delivered? What if NTU requires on-premise?

- **Proposed:** a **running service** (hosted API) plus the privacy connector, a signed container that runs in RSTN's network. The connector needs about 2–4 vCPU and 8 GB memory, no GPU, and outbound HTTPS to the engine only. We do not deliver source code or a library.
- **If the connector cannot be hosted:** RSTN calls the hosted engine directly. Data is masked on arrival and nothing is kept.
- **If NTU requires on-premise:** an on-premise licence. The engine is deployed as containers in NTU's environment or in RSTN's AWS account, with images and updates supplied by Synvo. Hardware and update cost are higher and releases slower, so it is quoted separately. We would scope it together with NTU's requirements.

### 7. How does the engine signal "I'm not sure"? Is there a confidence score?

We deliberately do **not** use a single confidence score. A model's own confidence numbers are usually not calibrated. Instead, uncertainty is explicit and has a reason:

| What can be uncertain | How the engine says so |
|---|---|
| Which programme | `RESOLVED`, `AMBIGUOUS` (with the candidates) or `UNRESOLVED` |
| Whether the sources answer the issue | `SUFFICIENT`, `INSUFFICIENT`, `CONFLICTING` or `STALE` |
| What to do | **Ask for clarification** or **Manual handling**, with the reason and the missing information |
| Whether the reply is safe | `BLOCKED` if the independent check finds a statement without a source |

We calibrate these against NTU's labelled sample emails. For example, of the issues marked **Reply directly**, how many could really be answered directly? We confirm the figures again in the shadow run.

### 8. If we manage the knowledge base, what data store do we need? How is your DB designed?

You do **not** need a vector database or a search system. What needs maintaining is the **content and its status**:
- **Approved knowledge** (programme pages, FAQs, policies): ID, URL, title, text, version or last-updated date, status (active or withdrawn) and owner.
- **Programme registry:** programmes, aliases, status, owning team and contact inbox.
- **Routing table:** the owner by programme and question type, e.g. admission goes to the school, fees to finance.

We sync a versioned copy and index it on our side. When content is withdrawn, a notification from your side removes it at once. Every answer cites the version it used.

**a. Attachments** are **not stored** by the engine. They come with the request: inline when small, by reference when large. In the proposed setup the connector reads them inside NTU. A reference can therefore be fetched on demand from Graph by the connector, and the attachment never leaves your network.

### 9. How does the engine learn from reviewer feedback?

Learning from staff feedback is **phase 2**. In phase 1 the engine's behaviour changes only through versioned releases that we test. The phase 2 design:

- **a. Signals:** approvals, edits, reroutes and explicit feedback are all recorded.
- **b. What gets updated:** **never model weights.** Only reviewable items change: programme aliases and routing rules, the knowledge-gap list for NTU, reply-style examples and retrieval tuning.
- **c. How quickly:** not instantly. A proposed change is confirmed by a person, run against the sample test set, and released with a version number. We expect this cycle to be days, not months.
- **d. Inspect and roll back:** yes. Each learned item is a separate versioned record, linked to the feedback that produced it, and can be rolled back on its own.
- **e. Stopping one wrong correction from spreading:** human confirmation, the test-set gate, and a narrow scope for each item, e.g. one programme and one question type.

### 10. Does a 2–3 month POC timeline work for you?

In principle yes, provided four inputs arrive early:
- the XML schema or sample payloads;
- sample emails and screenshots;
- access to approved knowledge;
- a decision on hosting the privacy connector.

Indicative plan, to be confirmed after the call:

| Weeks | Work |
|---|---|
| 1–2 | Integration contract; sample emails received; knowledge sync agreed |
| 3–6 | Integration; privacy connector in your sandbox; sample emails labelled with PaCE |
| 7–10 | UAT; accuracy measured on the sample set; 1–2 week shadow run on live email with nothing sent |

### 11. What were your accuracy figures measured on, and which metrics?

To be clear: our evaluation so far used the POC's **fixed test scenarios**, a small set of constructed emails and a small fictional knowledge base. It was **not real client email**. It shows that the mechanisms work: splitting issues, routing, citing sources, and blocking unsupported statements. It does **not** give an accuracy figure for live PaCE email.

We propose to measure accuracy on NTU's labelled sample emails before go-live, then again in the shadow run:

| Metric | Meaning |
|---|---|
| Routing accuracy / misroute rate | Right programme and owning team per issue |
| Action accuracy | Right choice among the four actions per issue |
| Escalation rate | Share of issues sent to Manual handling or Ask for clarification |
| Unsupported-statement rate | Reply statements without a valid source, after the check |
| Staff edit rate | How much reviewers change the draft |
| Processing time | Per email, by type |

Targets for phase 1 are best agreed together (question F1 in our pre-read).

### 12. Emails with several questions

The understanding step splits the email into **separate issues**. Each issue gets its own programme, owner and recommended action.

- **Reply:** **one combined reply** covering the issues that can be answered directly. Each statement links to its source.
- **Issues owned by other teams:** each gets a **handoff note** for the receiving team, with the reason and the evidence.
- **Independence:** an issue the engine cannot answer never blocks one it can.

The example in the attached PDF has three issues: intake, training allowance and payment. The first two are answered, and payment goes to Manual handling.

### 13. When only some questions can be answered

The result lists **every issue with its own action and reason**, for example *Reply directly / Reply directly / Manual handling*. The reply draft states which issues it covers. The others are listed with their action (refer, ask for clarification or manual handling), the reason, and any missing information. Your review console can show this per issue, so reviewers see at once which parts need a person.

Whether the reply should say that the remaining points will be followed up is a wording choice. We suggest PaCE decides it.

### 14. Retention, deletion and separation

| Data | Kept? |
|---|---|
| Email content and attachments | **No.** Discarded once the result is returned. In the proposed setup the engine only ever sees masked text. The mapping between names and placeholders stays in the connector's memory inside NTU. |
| "Memory" of a person or thread | **None.** The engine is stateless. Context it needs, such as earlier messages, comes in the request. |
| Traces | Yes, for an agreed period. IDs, labels, source references and timings only, **no email text**. |
| Embeddings | **Only of approved knowledge**, which is mostly public NTU content. Emails are never embedded. |

**a. Deletion requests:** we keep no personal data derived from emails, so there is no email-derived content on our side to delete. Traces use an opaque sender reference rather than the email address and can be deleted by reference if needed. In phase 2, learned items are de-identified and reviewed, and they fall under the same deletion process.

**b. Separation from other clients:** NTU runs in a **dedicated environment** with its own deployment, its own encryption keys and its own knowledge and configuration. Nothing is shared with other clients.

### 15. Export in a standard format

Yes.
- **Traces:** JSON (or CSV), keyed by your request ID, ready for your audit and retention systems.
- **Knowledge:** NTU's own content. We can export the synced copy as a dated snapshot, including which version each reply cited.
- **Memory:** none to export.
- **Phase 2 learned items:** will be exportable in the same way.

We can agree the export format as part of the integration contract.

### 16. A live session and hands-on access

Yes. We are happy to run another online session with the engine processing sample emails live. Please propose a time and who will join. The POC screens are for reference only, so there is no client admin UI. Hands-on access will come through the **integration sandbox** (engine and connector).

---

## 2. Our questions back

These follow from your questions. Items marked **★** are the ones we would most like to settle on the call. The full list, with our proposal for each, is in the attached pre-read. The IDs in brackets refer to it.

| # | Question | Follows from |
|---|---|---|
| R1 ★ | Can you share the **XML schema or 3–5 sample payloads** (email and web form), and how threads and follow-ups are identified? (A1, A2) | Q5 |
| R2 ★ | Should calls be **synchronous or asynchronous with a callback**? What is your timeout? (A4) | Q4, Q5 |
| R3 ★ | Does NTU accept the **proposed setup**, where only masked text leaves NTU, is processed in Singapore and is not kept? Who at NTU decides, and what do they need from us? (E1, E5) | Q2, Q14 |
| R4 ★ | Can RSTN **host the privacy connector** (one container, 2–4 vCPU, 8 GB, no GPU)? Where would it run, and who deploys updates? (E2) | Q6 |
| R5 | Does NTU or RSTN have a **preferred cloud platform or region**, or a list of approved processors, that we should design for? | Q2, Q6 |
| R6 ★ | Where does the **approved knowledge** live today, and may a versioned copy be synced to the engine? Does a **programme registry** with owning teams exist? (B1–B3) | Q8 |
| R7 | Are attachments in your system kept as **Graph references or stored copies**? This decides whether the connector fetches them or receives them inline. (A3) | Q8 |
| R8 | Which **trace fields** does your audit record need, and in what format? How long must audit records be kept? (E4) | Q3, Q15 |
| R9 ★ | How many **sample emails** and **screenshots** can be shared, and when? Can each sample include how PaCE handled it? (C1, C2, C4) | Q10, Q11 |
| R10 ★ | Which **accuracy measures and targets** should phase 1 meet? (F1) | Q11 |
| R11 ★ | For the **2–3 month POC**: does it end with live use by PaCE staff, or with a shadow run and a go/no-go decision? Are there fixed dates, such as admission peaks? (F2, F3) | Q10 |
| R12 | How should the review console show **partly answered emails** to reviewers? This helps us shape the result fields. (A5) | Q13 |
| R13 | Is **learning from feedback** needed in the POC, or can it follow in phase 2 as described in answer 9? (U11) | Q9 |
| R14 | Who should join the **live session**, and which dates suit you? | Q16 |

We look forward to the call.

Synvo
