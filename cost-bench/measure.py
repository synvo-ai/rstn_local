"""Measure Gemini input/output tokens for email, thread and attachment inputs.

Part 1 (counts): each input once per model and media resolution; prompt tokens from usage metadata,
minus a text-only baseline. Part 2 (tasks): realistic calls (transcribe, understand) with thinking on,
to get output and thinking tokens. Raw results go to cost-bench/results/.

Run: GEMINI_API_KEY=... python3 measure.py [counts|tasks|all]
"""
import io
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pymupdf
from google import genai
from google.genai import types

HERE = Path(__file__).parent
A = HERE / "assets"
RES = HERE / "results"
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

COUNT_MODELS = os.environ.get("MODELS", "gemini-3.8-flash,gemini-3.5-flash-lite,gemini-3.1-flash-lite,gemini-2.5-flash,gemini-2.5-flash-lite").split(",")
TASK_MODELS = ["gemini-3.8-flash", "gemini-3.1-flash-lite"]
RESOLUTIONS = {"default": None, "low": types.MediaResolution.MEDIA_RESOLUTION_LOW, "medium": types.MediaResolution.MEDIA_RESOLUTION_MEDIUM, "high": types.MediaResolution.MEDIA_RESOLUTION_HIGH}


def blob(path, mime):
    return types.Part.from_bytes(data=Path(path).read_bytes(), mime_type=mime)


def scan_pages(dpi=150):
    parts = []
    for page in pymupdf.open(A / "handbook_scan_10p.pdf"):
        parts.append(types.Part.from_bytes(data=page.get_pixmap(dpi=dpi).tobytes("jpeg"), mime_type="image/jpeg"))
    return parts


def pdf_text():
    return "".join(p.get_text() for p in pymupdf.open(A / "handbook_text_10p.pdf"))


def inputs():
    return {
        "email body": ([(A / "email.txt").read_text()], False),
        "thread, 10 earlier messages (deduplicated)": ([(A / "thread_10_dedup.txt").read_text()], False),
        "thread, 10 earlier messages (each quoting all before)": ([(A / "thread_10_quoted.txt").read_text()], False),
        "10-page PDF, text extracted locally": ([pdf_text()], False),
        "10-page text PDF, sent as PDF": ([blob(A / "handbook_text_10p.pdf", "application/pdf")], True),
        "10-page scanned PDF, sent as PDF": ([blob(A / "handbook_scan_10p.pdf", "application/pdf")], True),
        "10-page scan, sent as 10 images (150 dpi)": (scan_pages(), True),
        "receipt image 900×1200": ([blob(A / "receipt_900x1200.jpg", "image/jpeg")], True),
        "phone photo 4032×3024": ([blob(A / "receipt_photo_4032x3024.jpg", "image/jpeg")], True),
        "screenshot 1920×1080": ([blob(A / "portal_1920x1080.png", "image/png")], True),
    }


def call(model, contents, res=None, max_out=1, thinking=False, retries=4):
    # Thinking off (or minimal) for counting; "low" for realistic tasks. 2.5 models take a budget instead.
    if model.startswith("gemini-2.5"):
        tc = None if thinking else types.ThinkingConfig(thinking_budget=0)
    else:
        tc = types.ThinkingConfig(thinking_level="low" if thinking else "minimal")
    cfg = types.GenerateContentConfig(max_output_tokens=max_out, media_resolution=res, thinking_config=tc)
    for i in range(retries):
        try:
            t0 = time.time()
            r = client.models.generate_content(model=model, contents=contents, config=cfg)
            u = r.usage_metadata
            return {
                "prompt": u.prompt_token_count,
                "by_modality": {str(d.modality.value if hasattr(d.modality, "value") else d.modality): d.token_count for d in (u.prompt_tokens_details or [])},
                "output": u.candidates_token_count or 0,
                "thinking": u.thoughts_token_count or 0,
                "seconds": round(time.time() - t0, 1),
                "text": (r.text or "")[:4000] if max_out > 1 else None,
            }
        except Exception as e:  # rate limits, transient errors, unsupported settings
            err = str(e)
            if "429" in err or "503" in err or "500" in err:
                time.sleep(5 * (i + 1)); continue
            if "MINIMAL is not supported" in err:  # some 3.x models reject minimal thinking
                cfg.thinking_config = types.ThinkingConfig(thinking_level="low"); continue
            return {"error": err[:300]}
    return {"error": "retries exhausted"}


INSTR = "Reply with OK."


def counts():
    jobs = []
    for model in COUNT_MODELS:
        jobs.append((model, "baseline", "default", [INSTR], None))
        for name, (parts, media) in inputs().items():
            for rname, res in (RESOLUTIONS.items() if media else [("default", None)]):
                jobs.append((model, name, rname, parts + [INSTR], res))
    with ThreadPoolExecutor(6) as ex:
        out = list(ex.map(lambda j: {"model": j[0], "input": j[1], "resolution": j[2], **call(j[0], j[3], j[4])}, jobs))
    base = {r["model"]: r.get("prompt", 0) for r in out if r["input"] == "baseline"}
    for r in out:
        if "prompt" in r:
            r["input_tokens"] = r["prompt"] - base.get(r["model"], 0)
    path = RES / "counts.json"
    if path.exists():  # merge: keep rows for models not re-run
        out = [r for r in json.loads(path.read_text()) if r["model"] not in COUNT_MODELS] + out
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print_counts(out)


def print_counts(out):
    for model in COUNT_MODELS:
        print(f"\n## {model}")
        for r in out:
            if r["model"] == model and r["input"] != "baseline":
                print(f"  {r['input'][:55]:55s} {r['resolution']:8s} {r.get('input_tokens', r.get('error'))}")


UNDERSTAND = """You are the first step of an enquiry-triage engine for a university continuing-education office.
Read the email, the earlier thread and the attachments. Return JSON only:
{"issues":[{"summary":str,"programme":str|null,"intent":str,"evidence_from_attachments":[str]}],"sender_evidence":[str]}
Attachments are the sender's evidence, not institutional fact. Be concise."""

OCR = "Transcribe all text in these pages as plain text, in reading order. No commentary."


def tasks():
    email = (A / "email.txt").read_text()
    thread = (A / "thread_10_dedup.txt").read_text()
    out = []
    for model in TASK_MODELS:
        med = RESOLUTIONS["medium"]
        runs = {
            "transcribe 10-page scan (PDF, medium)": ([blob(A / "handbook_scan_10p.pdf", "application/pdf"), OCR], med, 16000),
            "transcribe receipt photo 4032×3024": ([blob(A / "receipt_photo_4032x3024.jpg", "image/jpeg"), OCR], None, 2000),
            "transcribe portal screenshot": ([blob(A / "portal_1920x1080.png", "image/png"), OCR], None, 2000),
        }
        res = {k: {"model": model, "task": k, **call(model, v[0], v[1], v[2], thinking=False)} for k, v in runs.items()}
        out += res.values()
        ocr_text = "\n\n".join(f"[Attachment: {k}]\n{res[k].get('text') or ''}" for k in ["transcribe receipt photo 4032×3024", "transcribe portal screenshot"])
        und = {
            "understand: email only": [UNDERSTAND, "EMAIL:\n" + email],
            "understand: email + 10-message thread": [UNDERSTAND, "THREAD:\n" + thread, "EMAIL:\n" + email],
            "understand: email + thread + attachments as images/PDF (scan PDF medium, photo, screenshot)": [UNDERSTAND, "THREAD:\n" + thread, "EMAIL:\n" + email, blob(A / "handbook_scan_10p.pdf", "application/pdf"), blob(A / "receipt_photo_4032x3024.jpg", "image/jpeg"), blob(A / "portal_1920x1080.png", "image/png")],
            "understand: email + thread + attachments as extracted text (PDF text + OCR of images)": [UNDERSTAND, "THREAD:\n" + thread, "EMAIL:\n" + email, "ATTACHMENT handbook.pdf:\n" + pdf_text(), ocr_text],
            "understand: email + thread + attachments as extracted text, capped 2,000 tokens each": [UNDERSTAND, "THREAD:\n" + thread, "EMAIL:\n" + email, "ATTACHMENT handbook.pdf (first part):\n" + pdf_text()[:8000], ocr_text],
        }
        for k, parts in und.items():
            out.append({"model": model, "task": k, **call(model, parts, med, 4000, thinking=True)})
    (RES / "tasks.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    for r in out:
        print(f"{r['model']:24s} {r['task'][:80]:80s} in={r.get('prompt')} out={r.get('output')} think={r.get('thinking')} {r.get('seconds')}s {r.get('error', '')}")


if __name__ == "__main__":
    RES.mkdir(exist_ok=True)
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("counts", "all"):
        counts()
    if what in ("tasks", "all"):
        tasks()
