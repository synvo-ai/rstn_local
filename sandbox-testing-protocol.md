# NTU PaCE Enquiry Engine — Sandbox Testing Protocol

**Version:** draft 0.1, for RSTN review (final version with sandbox v2 on 28 October 2026)

**From:** Synvo (Guowei Wang, AI tech lead; Li-kai Jiang)

**For:** RSTN integration and test team

This protocol explains how RSTN can test the enquiry engine in the Synvo sandbox before any NTU data is available: what the sandbox contains, how to call it, which scenarios to run, what result to expect, and how to report issues. The API fields referred to here are defined in the accompanying **API specification (draft)**.

---

## 1. Purpose and scope

The sandbox lets RSTN:
1. **Integrate early:** call the engine from RSTN's own system and handle its results, before NTU's schema, samples or knowledge are available.
2. **Check behaviour:** confirm the engine handles the main enquiry types as agreed: splitting questions, routing, the four recommended actions, cited replies, attachments and masking.
3. **Shape the pilot:** tell us what must change before real NTU data is used.

The sandbox is **not** a measure of accuracy for NTU. All content in it is mock data that we built ourselves (section 3). Results show that the engine works end to end; accuracy on real PaCE email will be measured in the pilot, on NTU's labelled sample emails.

## 2. Timeline

| Date | What is available |
|---|---|
| Wed 14 Oct | This protocol and the API specification (drafts) |
| Wed 21 Oct | **Sandbox v1:** the engine, mock knowledge and mock emails; scenarios marked v1 below |
| Wed 28 Oct | **Sandbox v2:** adds the privacy connector and attachment reading; all scenarios; final protocol; walkthrough session |
| 28 Oct – ~4 Nov | RSTN testing window (one week, can be extended), with a mid-week check-in |
| ~Thu 5 Nov | Joint review and plan for the pilot with NTU data |

## 3. What is in the sandbox

| Item | Content |
|---|---|
| Knowledge | A mock knowledge base built from **public NTU PaCE web pages** (programme pages, FAQs, fees, intakes), versioned. Every item is marked as mock; NTU still has to approve the real sources. |
| Programme registry | Programmes, aliases and owning teams, with **made-up team names and inboxes**. |
| Reply style | Mock greeting, sign-off, acknowledgement and handoff-note templates. |
| Test emails | About 50 mock emails at v1, about 150 at v2, each with its **expected result** (issues, programme, owning team, action, points the reply should cover). All senders and personal details are made up. |
| Test attachments | Text PDFs, scanned PDFs, receipts, certificates, portal screenshots and logos, with made-up personal details (v2). |
| Tools | Sample requests in JSON and XML, a small sample client, and a callback receiver for testing without RSTN's own system. |

## 4. Access

- **Endpoint:** `https://<sandbox-host>/v0` (sent with the keys on 21 October).
- **Keys:** one API key per tester, sent separately. Keep keys private; we can revoke and reissue them at any time.
- **Network:** access may be limited to RSTN's IP addresses; please send the addresses you will test from.
- **Limits:** initially 60 requests per hour and 2 running at the same time per key. Ask us if a test needs more.
- **Availability:** working hours, Singapore time. The sandbox may be redeployed during the testing window; we announce planned downtime in advance.
- **Reset:** we can reset a tester's data and history on request.

Authentication in the sandbox is a simple API key. The production method (e.g. mutual TLS or signed requests) will be agreed separately.

## 5. How to call the engine

The API specification has the full fields. In short:

| Call | Purpose |
|---|---|
| `POST /v0/enquiries` | Submit one email or web-form enquiry. Returns a `runId` at once; the result follows by **callback** to the URL you give, or by polling. Add `?mode=sync` to wait for the result on the same call (sandbox convenience; useful for manual tests). |
| `GET /v0/runs/{runId}` | Fetch the status or result of a run. |
| `POST /v0/enquiries/{runId}/recheck` | Re-check a **staff change** to one issue's action or owning team. Send the original request, the previous result (as returned, signed) and the change. |
| `GET /v0/health` | Check that the sandbox is up. |

**Formats:** JSON, or XML using our draft schema. When RSTN's own XML schema is available, we adapt to it and the draft is retired.

**What you send:** your request ID, the channel (email or web form), received time, an **opaque sender reference** (not the email address), subject, body, earlier messages in the thread if any, and attachments (inline up to 10 MB each in the sandbox).

**What you get back:**
- **Run health:** completed, completed with limitations, or failed.
- **Issues:** each question found, with its programme, owning team, recommended action (**Reply directly / Refer to receiving team / Ask for clarification / Manual handling**) and the reason.
- **Reply draft:** one draft covering the issues that can be answered, with each statement linked to its source, and a safety status (ready for staff review, blocked, or not produced).
- **Handoff notes:** one per issue referred to another team.
- **Trace:** your request ID, our run ID, versions of engine, knowledge and configuration, and each processing step with its outcome and timing. The trace contains no email text.

The engine only recommends. Nothing is sent, forwarded or updated by the engine in the sandbox or later.

## 6. Test scenarios

Each mock email in the test pack is tagged with one of the scenario IDs below and carries its expected result. A scenario **passes** when the result matches the expected result on the points listed. Reply wording may differ from the example; it passes if it covers the expected points, cites a source for each factual statement and adds nothing unsupported.

### A. Enquiry handling

| ID | Scenario | Expected result | From |
|---|---|---|---|
| A1 | One clear question answered by the knowledge base (e.g. next intake for a named programme) | 1 issue, programme identified, **Reply directly**, reply with source, ready for review | v1 |
| A2 | Several questions in one email (e.g. intake, fees, payment) | One issue per question, each with its own action; one reply covering the answerable ones; the rest listed with reason | v1 |
| A3 | Question owned by another team (e.g. a school-specific admission decision) | **Refer to receiving team**, correct owning team, handoff note with the reason | v1 |
| A4 | Programme unclear or ambiguous (e.g. "the data course") | **Ask for clarification**, candidate programmes listed, no guessed answer | v1 |
| A5 | Question not covered by the knowledge base | **Manual handling** or **Ask for clarification** with reason; no reply statement without a source | v1 |
| A6 | Question needing payment, application or status data (e.g. "has my payment been received?") | **Manual handling**; a receipt from the sender is treated as the sender's evidence, not confirmation | v1 |
| A7 | Follow-up in a thread, earlier messages passed in the request | Earlier context used; questions already answered are not repeated | v1 |
| A8 | Web-form enquiry | Same handling as email; form fields used where present | v1 |
| A9 | Not an enquiry (auto-reply, newsletter, spam) | No issues to answer; **Manual handling** or flagged as not an enquiry, no reply draft | v1 |
| A10 | Email not in English, or mixing languages | Handled or sent to **Manual handling** with reason; no wrong-language reply | v1 |

### B. Staff changes

| ID | Scenario | Expected result | From |
|---|---|---|---|
| B1 | Staff change one issue from Reply directly to Refer to receiving team | Change accepted; that issue updated; reply draft re-checked and the issue removed from it | v1 |
| B2 | Staff change an issue to Reply directly where the knowledge base has no answer | Change rejected with reason; previous result unchanged | v1 |
| B3 | Previous result altered before resending | Request rejected (signature check) | v1 |

### C. Attachments

| ID | Scenario | Expected result | From |
|---|---|---|---|
| C1 | Text PDF or Word document | Content read and used; cited as sender-provided | v2 |
| C2 | Scanned PDF or photo of a document (e.g. a receipt) | Text read; used as the sender's evidence only | v2 |
| C3 | Screenshot where layout matters (e.g. a portal error) | Content understood; personal details in the image not passed on | v2 |
| C4 | Logo or email signature image | Ignored | v2 |
| C5 | Unsupported or very large attachment (zip, video, over the limit) | Not read; **Manual handling** for the related issue, with reason; the rest of the email still handled | v2 |

### D. Privacy

| ID | Scenario | Expected result | From |
|---|---|---|---|
| D1 | Email with name, phone, NRIC-style number and payment reference | Engine side sees placeholders only; names and details restored in the result returned to RSTN | v2 |
| D2 | Personal details inside an attachment | Masked before leaving the connector | v2 |
| D3 | Inspect the trace for any run | No email text or personal details in the trace | v1 |

### E. Integration and failure handling

| ID | Scenario | Expected result | From |
|---|---|---|---|
| E1 | Same request sent twice (same idempotency key) | One run; the second call returns the first result | v1 |
| E2 | Malformed request or missing required field | Clear error naming the field; no run started | v1 |
| E3 | Invalid or missing API key | Rejected | v1 |
| E4 | Callback URL unavailable | Result delivered on retry, or available by polling | v1 |
| E5 | Engine cannot complete (we can trigger this on request) | Run health failed or limited, no reply draft; RSTN's fallback acknowledgement path is exercised | v1 |
| E6 | Request over the rate limit | Rejected with a retry-after time | v1 |

### F. Timing

| ID | Scenario | Expected result | From |
|---|---|---|---|
| F1 | Send the test pack at a steady rate within the limits | Every run completes; RSTN records time from request to result | v1 |

The sandbox runs on test hardware, so timings are indicative only. Production timing will be measured in the pilot.

## 7. Recording results

Please record, per scenario run: scenario ID, mock email ID, your request ID, our run ID, pass or fail, and a note for any fail. A results sheet is included in the test pack. You are welcome to add your own test emails, as long as they contain **no real personal data** (section 9).

## 8. Reporting issues

Send issues to the shared channel agreed at handover (e.g. a shared sheet or ticket board), using:

| Field | Content |
|---|---|
| Title | One line |
| Scenario / email | Scenario ID and mock email ID, or "own test" |
| Request ID and run ID | From the request and result |
| Expected | What should have happened |
| Actual | What happened; attach the result if useful |
| Severity | **Blocker** (testing cannot continue), **Major** (wrong action, routing or unsupported reply statement), **Minor** (wording, format, convenience) |

We aim to acknowledge issues within one working day and to fix blockers within two. Fixes are redeployed to the sandbox and announced with a short change note.

## 9. Rules for the sandbox

- **Mock data only.** Do not send real emails, real names or any real personal data. Unlike production, the sandbox keeps requests and results for the testing window so we can investigate issues; it is deleted at the end.
- **Keys are personal** to each tester and are not to be shared.
- **No load testing** beyond the limits in section 4 without agreeing it first.

## 10. What the sandbox does not cover

- Accuracy on real PaCE email, real NTU knowledge or the real programme registry (pilot).
- RSTN's final XML schema (we adapt once it is available).
- Production hosting, authentication, security assessment and data processing agreement.
- Learning from staff feedback (later phase).
- Payment, application or status lookups.

## 11. Inputs from RSTN that would help

| Item | Needed by |
|---|---|
| Names and email addresses of testers | 19 Oct |
| IP addresses you will test from, and a callback URL if you will use callbacks | 19 Oct |
| Comments on this draft and the API specification | 21 Oct |
| Whether you will run the privacy connector in your own environment during testing, or use the copy in the sandbox | 26 Oct |
| Your XML schema or sample payloads, if available | Any time; earlier is better |
