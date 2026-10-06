# NTU PaCE General Enquiries — Requirement Summary (AI Scope)

Audience: Synvo internal (Guowei as AI tech lead, Li-kai, Lisa, Saim, Faye).
Status: consolidated from customer discovery, RSTN's AI-layer framing (LoadStone diagram), our pitch slides
and the POC. Open questions are tracked in `TODO.md`, not here.

Source material:
- `Arinah-Ahmad-PaCE-General-Enquiries.pdf` — customer AI-facilitated discovery with the PaCE/FlexiMasters team.
- `02. Email enquiry to Synvo from RSTN.md` + `loadstone_AI_proposed_solution.jpg` — RSTN's framing of the
  AI layer, including Prof Boh's "use our historical data" requirement.
- `RSTN.md` — target architecture, integration contract and POC evidence written for RSTN.
- `synvo_sample_slides_2026.10.02.pdf` — pitch already shown to the customer (current/future workflow on
  slides 1–2, POC screens on slides 3–10).
- `ntu-pace-correspondence-intelligence` — our POC; source of the reusable AI capability.

---

## 1. The customer problem

NTU PaCE handles general public enquiries across FlexiMasters, SCTP, short courses, IPGC and Master's
programmes. Enquiries arrive at `pace@ntu.edu.sg` and via the NTU enquiry form, which lands in the same inbox.

| Dimension | As-is (discovery, and slide 1) |
|---|---|
| Volume | ~5,000 enquiries/week; 700–1,000 emails/day; higher at admission peaks |
| Split | 60–70% forwarded to schools/programme teams; 30–40% handled by the FlexiMasters team |
| Triage | Every email read by hand; routing from keywords and personal experience |
| Reference | No programme directory; 10–12 Word templates edited by hand per reply |
| Data sources | NTU course webpages for programme/fee/intake facts; TMS for existing learners |
| Tracking | Shared-mailbox sub-folders dragged by hand; reports built from those folders |
| Target | Acknowledge or route every enquiry within 3 working days |
| Effort | Up to half a day per person on triage and routing |
| Visibility | Lost once forwarded unless the receiving team CCs PaCE; enquirers chase |

The eight pain points on slide 1: volume never stops; every email read by hand; clarification loops; hard to
find the owner (similar names across units, e.g. `Data Science` school master's vs continuing-education,
`Business Analytics` vs `Analytics and Visualisation`, `Cyber Security` degree vs short courses); manual
categorising; copy-paste replies; misrouting and rework; no visibility after forwarding.

**Single biggest improvement the customer named:** accurate classification and routing at the point of entry.

## 2. What RSTN and NTU asked of the AI layer

Two inputs shape the AI requirement beyond the discovery notes.

**a) Triage + draft + route (original ask).** AI triages each email so that it can draft a direct
response, forward to a school, or route to a human for exceptions.

**b) Use historical correspondence (Prof Boh, Director).** RSTN's reading is that the AI partner should
"extract a reasoning model of sorts" from PaCE's past emails. The competing LoadStone proposal
(`loadstone_AI_proposed_solution.jpg`) shows the shape RSTN now has in mind:

| LoadStone diagram element | What it implies for us |
|---|---|
| Programme Registry (identity, owner, contacts, current facts) → AI | Registry is the routing source of truth; AI consumes it |
| "Supported outcome?" with 3 branches | Tailored direct response → draft with evidence → FlexiMasters review & send; programme-owner response required → structured routing & handoff; insufficient/conflicting/ambiguous evidence → human exception queue |
| Static approved wording → acknowledgement, escalation and failure fallback only | A non-AI fallback reply when the AI path fails or is not allowed |
| Decision audit and service reporting | Every decision must be auditable and reportable |
| Approved historical email correspondence + approved FAQs/policies/programme info → governed response knowledge base | **Superseded (2026-10-05):** NTU will not share historical emails for training or as a knowledge source. We will get **sample emails for reference**. The knowledge base is NTU web pages, FAQs and policies only |
| Reviewer feedback and approved corrections → controlled evaluation and knowledge refresh → knowledge base | A governed feedback loop; this is what our group now calls **Self-Learning** (phase 2) |

Our POC already covers the decision branches (as four treatments, see §4), the audit trail and the
fail-closed behaviour.

**Update 2026-10-05:** NTU will not share historical emails for pre-training, but sample emails are
available for reference. We use them as a labelled test set, to list knowledge gaps for NTU, and as
reply-style examples, never as a source of facts (`draft-solution.md` §6).

## 3. Desired future state (customer)

- Enquiries classified and routed to the correct team at intake.
- Standard responses generated from a central knowledge base.
- FlexiMasters handles exceptions and complex cases only.
- Ownership transfers inside a shared system with status and resolution tracking (RSTN's system).
- Automated follow-ups and a self-service FAQ/portal (not our scope).
- Enablers the customer named: a central data foundation mapping programmes to responsible teams, and clear
  decision rules for programme/intent/urgency, multi-part handling, and automate vs review vs escalate.

Success measures: response time, triage/routing time, first-contact resolution, answer consistency, inbox
volume per staff, manual handling time, satisfaction, repeat enquiries, delay complaints, follow-up chasing.

## 4. Scope — what Synvo delivers

Per the inner-group alignment: **UI/UX and the demo are reference only. We provide an engine.** RSTN sends
the email content (most probably XML over an API); we return structured output. RSTN owns intake, case
records, status tracking and execution; NTU owns institutional truth; PaCE staff approve and act.

Slide 2 already drew this boundary for the customer. Its per-step status is our committed position:

| Slide 2 step (Synvo AI lane) | Status shown to customer | Depends on |
|---|---|---|
| Understand — questions, follow-ups | Solved, shown in POC | — |
| Identify programme — and its owner | Solved, needs NTU data source | Programme Registry |
| Check information — needed per question | Solved, needs NTU data source | Knowledge base, TMS, NTU/programme websites |
| Recommend action — per question | Solved, shown in POC | — |
| Draft & verify — independent checker | Solved, needs NTU data source | Approved knowledge for grounding |
| Review & approve (PaCE staff lane) | Partly solved | RSTN UI; we supply override validation |
| Receives handoff (schools lane) | Partly solved | RSTN execution; we supply owner, reason and evidence |
| Intake & open case; case status & dashboard | RSTN scope | — |

The four treatments, with the labels the customer saw in the POC (slides 5–6):

| Engine value | Customer-facing label | Meaning |
|---|---|---|
| `ANSWER` | Reply directly | Approved information is sufficient; a grounded draft is produced |
| `HANDOFF` | Refer to receiving team | Owner is another team; owner and routing basis returned (e.g. `FlexiMasters in Integrated Circuit Design · ADMISSION → School of EEE`) |
| `CLARIFY` | Ask for clarification | Sender must supply programme, intake or the actual question |
| `MANUAL_REVIEW` | Manual handling | Needs institutional state (e.g. payment status) or a human judgement |

What the POC screens (slides 3–10) commit us to returning:
- one entry per identified issue, with counts by treatment ("3 issues: 2 can answer now, 1 manual handling");
- per issue: programme, owner, treatment, a "Why" rationale, and evidence that opens the source
  (in the POC, the live NTU programme webpage);
- **one consolidated reply per enquiry** covering all answerable issues, plus the list of issues it covers;
- sender attachments shown as sender-provided evidence (slide 3–4: a bank transfer receipt), never as proof
  of payment;
- staff can change the handling per issue; the change is checked against controlled routing and approved
  knowledge, and an invalid change leaves the plan unchanged (slide 6).

| In Synvo scope | Out of scope (RSTN / NTU / PaCE) |
|---|---|
| Multi-question understanding and follow-up (thread delta) understanding | Mailbox/form intake, attachment storage |
| Programme/owner resolution against a governed registry | Case/thread identity, case lifecycle, dashboard |
| Per-issue sufficiency check and treatment | The registry and knowledge content themselves |
| Grounded consolidated reply with claim-to-source trace, independently verified | Sending, forwarding, case-state updates |
| Validation of staff handling changes | Staff UI, SSO, roles, approval policy |
| Screenshots/receipts read as sender evidence | Treating a receipt as institutional truth |
| Labelled test set and knowledge-gap list built from PaCE sample emails (new) | Providing and de-identifying sample emails |
| Decision trace for audit and reporting | Reporting platform, follow-up chasing, FAQ portal |

## 5. Capability readiness (as agreed in the call with Tom, Guowei, Lisa)

| Capability | Position | Depends on |
|---|---|---|
| Multi-question understanding | Ready | — |
| Referencing and traceability | Ready on our side | How to reference the knowledge base on RSTN's on-prem server |
| Multimodal (screenshots) | Ready | Sample screenshots: OCR-led or vision-led decides the model and the cost. **Internal:** POC image reading is a fixture; real OCR/vision still to build (`hosting-and-scaling.md` §4) |
| Self-Learning (was "RL") | Phase 2 | Scoping and commercial discussion (Faye) |
| Delivery shape | API call | Input contract (XML expected) |

## 5a. Internal positions added 2026-10-05

- **Delivery as a Synvo-hosted API** is our preferred model (more value to us: recurring revenue, IP stays
  with us, central updates, reusable across customers). On-prem only as a separately priced licence if NTU
  policy requires it. See `draft-solution.md` §5.1.
- **Client data safety is our risk too.** Because we may store client data and use cloud models, we must take
  measures on our side: mask personal data before any model call, process statelessly, use zero-retention
  enterprise model endpoints, isolate per client, and sign a data processing agreement. See §5.2.

## 6. Requirement statement

Give RSTN an API-callable correspondence-intelligence engine that accepts an enquiry (email content,
permitted thread context and attachments) in XML; splits it into material issues; resolves each to a
programme and owner from the governed registry; decides per issue whether approved knowledge (NTU web
content, FAQs and policies) is sufficient; recommends one of
Reply directly / Refer / Clarify / Manual handling per issue; produces one verified, source-cited reply
where allowed; validates staff handling changes; and returns everything as structured output with a full
decision trace and an explicit cost per run. It is delivered as a Synvo-hosted API that masks personal
data before any model call and keeps no copy of the email after responding. It never sends, routes or invents institutional facts.

## 7. Commercial requirement

The 1-pager for Steven needs a **cost per email processed** and a workflow/architecture diagram. Diagram:
`workflow-and-architecture.html` (customer-facing); cost: `unit-cost.html` (internal). Cost model detail: `draft-solution.md` §9.
