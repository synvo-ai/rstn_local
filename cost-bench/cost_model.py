"""Per-email cost model: Round A base calls + measured thread and attachment tokens.

Token figures come from results/counts.json and results/tasks.json (Gemini, 8 Oct 2026) and from the
published patch formula for gpt-5.6-luna. Prices are standard tier, USD per 1M tokens, checked 8 Oct 2026.
Writes results/cost_table.json and prints a table.
"""
import json
import math
from pathlib import Path

RES = Path(__file__).parent / "results"
USD_SGD = 1.29

PRICES = {  # input, output (output includes thinking)
    "gpt-5.6-luna": (0.20, 1.20),
    "gemini-3.1-flash-lite": (0.25, 1.50),
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-3.8-flash (2026)": (0.75, 3.75),
    "gemini-3.8-flash (from 1 Jan 2027)": (1.50, 7.50),
}

# Round A, per email: 4.3 calls, 4,724 input and 1,320 output tokens (33,068 / 9,240 over 7 emails).
BASE_IN, BASE_OUT = 4724, 1320

# Measured (Gemini 3.x, media_resolution medium) and per-model image tokens.
THREAD_PER_MSG = 151          # 1,512 tokens for 10 deduplicated earlier messages
THREAD_QUOTED_10 = 10186      # same 10 messages, each quoting all earlier ones
TEXT_PER_PAGE = 620           # 6,197 tokens for 10 pages of extracted text
TRANSCRIBE_OUT_PER_PAGE = 590 # 5,867 output tokens to transcribe 10 scanned pages
CAP_PER_ATTACHMENT = 2000     # extracted text kept per attachment
DV_IN, DV_OUT = 3096, 716     # Round A draft + verify per email; scaled for real evidence and re-checks
DIGEST = 300                  # attachment facts passed on to draft and verify
UNDERSTAND_EXTRA_OUT = 260    # understand output grows from ~310 to ~575 with attachments


def luna_image_tokens(w, h, budget=2500, max_side=2048, mult=1.2):
    """gpt-5.6 patch formula at detail=high (images resized to fit before sending)."""
    s = min(1, max_side / max(w, h)); w, h = int(w * s), int(h * s)
    if math.ceil(w / 32) * math.ceil(h / 32) > budget:
        f = math.sqrt(32 * 32 * budget / (w * h)); w, h = int(w * f), int(h * f)
    return math.ceil(math.ceil(w / 32) * math.ceil(h / 32) * mult)


IMG = {  # tokens: (scanned page, phone photo, screenshot)
    "gemini": (532, 540, 527),                                  # medium; measured
    "gpt-5.6-luna": (luna_image_tokens(1240, 1754), luna_image_tokens(4032, 3024), luna_image_tokens(1920, 1080)),
}


def img(model):
    return IMG["gpt-5.6-luna"] if "luna" in model else IMG["gemini"]


def cost(model, extra_in, extra_out):
    pi, po = PRICES[model]
    return ((BASE_IN + extra_in) * pi + (BASE_OUT + extra_out) * po) / 1e6


def scenarios(model):
    page, photo, shot = img(model)
    t10 = 10 * THREAD_PER_MSG
    scan10 = 10 * page
    imgs = photo + shot
    rows = [
        ("Plain email (Round A)", 0, 0),
        ("+ 10 earlier messages, deduplicated (into understand + draft)", 2 * t10, 0),
        ("+ 10 earlier messages, each quoting all before (naive)", 2 * THREAD_QUOTED_10, 0),
        ("Thread + receipt photo, read once by the model", 2 * t10 + photo + 2 * DIGEST, UNDERSTAND_EXTRA_OUT),
        ("Thread + 10-page scan + photo + screenshot, all sent as images to every call (naive)", 2 * t10 + 4 * (scan10 + imgs), UNDERSTAND_EXTRA_OUT),
        ("Thread + 10-page scan + photo + screenshot, images read once, digest passed on", 2 * t10 + scan10 + imgs + 2 * DIGEST, UNDERSTAND_EXTRA_OUT),
        ("Thread + 10-page scan + photo + screenshot, model transcribes everything first", 2 * t10 + scan10 + imgs + min(10 * TEXT_PER_PAGE, CAP_PER_ATTACHMENT) + 400 + 2 * DIGEST, 10 * TRANSCRIBE_OUT_PER_PAGE + 380 + UNDERSTAND_EXTRA_OUT),
        ("Thread + 10-page scan + photo + screenshot, OCR in the connector, text capped (proposed)", 2 * t10 + CAP_PER_ATTACHMENT + 400 + 2 * DIGEST, UNDERSTAND_EXTRA_OUT),
        ("Proposed path + 3× knowledge evidence in draft/verify + one staff re-check", 2 * t10 + CAP_PER_ATTACHMENT + 400 + 2 * DIGEST + 2 * DV_IN + (3 * DV_IN + 2 * DIGEST + t10), UNDERSTAND_EXTRA_OUT + DV_OUT),
        ("Worst case: naive quoted thread + 3 × 10-page scans as images to every call", 2 * THREAD_QUOTED_10 + 4 * 3 * scan10, UNDERSTAND_EXTRA_OUT),
        ("Worst case above + 3× evidence + one staff re-check", 2 * THREAD_QUOTED_10 + 4 * 3 * scan10 + 2 * DV_IN + (3 * DV_IN + 2 * 3 * scan10 + THREAD_QUOTED_10), UNDERSTAND_EXTRA_OUT + DV_OUT),
    ]
    return [(name, ei, eo, cost(model, ei, eo)) for name, ei, eo in rows]


def main():
    table = {m: [{"case": n, "extra_in": ei, "extra_out": eo, "usd": round(c, 5), "sgd": round(c * USD_SGD, 5)} for n, ei, eo, c in scenarios(m)] for m in PRICES}
    (RES / "cost_table.json").write_text(json.dumps({"usd_sgd": USD_SGD, "image_tokens": IMG, "table": table}, indent=1))
    names = [r["case"] for r in next(iter(table.values()))]
    print("image tokens (page, photo, screenshot):", IMG)
    print(f"{'case':92s}" + "".join(f"{m[:22]:>24s}" for m in PRICES))
    for i, n in enumerate(names):
        print(f"{n[:92]:92s}" + "".join(f"{'S$%.4f' % table[m][i]['sgd']:>24s}" for m in PRICES))


if __name__ == "__main__":
    main()
