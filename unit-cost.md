# What One Email Costs (internal)

**Internal: do not share.** This is the cost basis for the commercial 1-pager. Workflow and architecture are on the
customer-facing page `workflow-and-architecture.html`. This file covers only the cost model behind it.
More detail is in `draft-solution.md` §9 and `hosting-and-scaling.md` §2. Open items are in `TODO.md`.

Proposed setup (2026-10-07): a hosted engine plus a privacy connector in RSTN's network (`draft-solution.md` §5.1).

## 1. Measured: POC Formal Round A (28 Sep 2026)

Seven fixed test emails, GPT-5.6 Luna, run one at a time. The token counts are retained originals. The dollar
figure is the documented Round A result. The price list used that day was not kept, so **re-price before
quoting** (TODO B4).

| Measure | Value |
|---|---|
| Model cost per email | ~$0.0025 |
| Model calls per email | ~4.3 |
| Tokens per email | ~6,000 (4.7k in, 1.3k out) |
| End-to-end latency | 13 s median, sequential |

Only step 3 (Understand) and step 7 (Draft & verify) always call a model. Step 2 calls one only for attachments,
and step 4 only when the programme is unclear. Steps 1, 5 and 6 are rules. This is why the unit cost is low and
predictable.

### Where the tokens go (7 emails, Luna)

| Stage | Calls | Input | Output | Share |
|---|---:|---:|---:|---:|
| Understand | 7 | 6,186 | 2,594 | 21% |
| Follow-up delta | 1 | 1,006 | 756 | 4% |
| Identify programme | 8 | 4,206 | 879 | 12% |
| Draft reply | 7 | 9,747 | 4,141 | 33% |
| Verify reply | 7 | 11,923 | 870 | 30% |
| **Total** | **30** | **33,068** | **9,240** | **100%** |

Share is of total tokens. Drafting and verifying make up two thirds of the bill, and both grow with the size of
the retrieved evidence.

## 2. Planning range, model cost only

| Case | Assumption | Per email | Per 5,000-email week |
|---|---|---:|---:|
| Measured | POC mix, tiny fictional knowledge store | ~$0.0025 | ~$12 |
| Expected | 2–3× evidence in draft and verify; 10–20% of emails with OCR attachments | $0.005–0.008 | $25–40 |
| High | As above, plus vision on 20% of emails and re-runs after staff overrides | $0.01–0.02 | $50–100 |

The Expected and High cases are scaled up from the measured run. They are estimates, not measurements.

## 3. Unit cost formula for the 1-pager

```
cost per email = Σ stages ( calls × (input tokens × input price + output tokens × output price) )
               + attachment share × reading cost (vision only; OCR runs in the connector)
               + retrieval cost per query (embeddings, search)
               + (hosting + monitoring per month) ÷ emails per month

fixed, priced separately = integration build · privacy connector · sample-email test set
                           · evaluation · support · phase 2
```

## 4. What moves the number

- **Delivery model.** In the proposed setup, model cost scales per email and is our cost. The privacy connector
  runs on RSTN's infrastructure (one small CPU container), so it adds nothing per email on our side. Its build and
  support count as a fixed cost. An on-prem licence would turn model cost into GPU amortisation, quoted separately.
- **Fixed infrastructure at one customer.** One dedicated hosting environment costs *est.* a few hundred USD per
  month. That is the same order as PaCE's model bill (~$100–170 per month), so multi-tenancy matters for margin
  (`hosting-and-scaling.md` §2.3).
- **Data protection overhead.** Masking and OCR run in the connector. Zero-retention enterprise endpoints may be
  priced differently from standard APIs. Check this when re-pricing (TODO B4).
- **Size of retrieved evidence.** Real NTU pages, FAQs and policies are larger than the POC store. Capping evidence
  per issue keeps drafting and verifying in check.
- **Screenshots.** OCR adds little. Vision adds roughly one extra model call per attachment. Sample screenshots
  decide which we need.
- **Model choice per stage.** The model gateway lets simple stages use a cheaper model without touching business
  rules. In Round A, Luna was the cheapest model and also scored highest in blind review (18.5 of 21).

## 5. Before quoting a price

1. Re-price the token counts at today's provider rates, including any zero-retention endpoint premium.
2. Run the engine beside the live inbox for 1–2 weeks with nothing sent. Report cost and latency per email by type:
   simple, multi-question, follow-up, and with attachment.
3. Quote cloud model cost and on-prem GPU amortisation as separate lines. They are not comparable units.

Sources: slide 2 of `synvo_sample_slides_2026.10.02.pdf`; POC Round A call metrics
(`evaluation/reports/PHASE_6_ROUND_A_2026-09-28T09-36-11-001Z`); `PHASE_6_MODEL_SELECTION_DECISION_RECORD.md`.
