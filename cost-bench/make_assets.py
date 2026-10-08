"""Build made-up test inputs for the attachment cost benchmark.

All people, numbers and programmes are fictional. Outputs go to cost-bench/assets/.
"""
import random
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).parent / "assets"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
rng = random.Random(7)

PROGRAMMES = ["Graduate Certificate in Applied Data Analytics", "FlexiMasters in IC Design", "Specialist Diploma in Sustainable Finance", "Professional Certificate in Cybersecurity Operations", "Graduate Diploma in Healthcare Management"]
SENTENCES = [
    "Applicants must hold a recognised bachelor's degree and at least two years of relevant working experience.",
    "Course fees are payable in full before the start of each module, and the SkillsFuture Credit may be used to offset eligible fees.",
    "Each module is assessed through a combination of individual assignments, a group project and a closed-book examination.",
    "Learners who miss more than 25 per cent of contact hours will not be eligible for the certificate of completion.",
    "Requests to defer a module must be submitted in writing no later than ten working days before the module begins.",
    "Singapore Citizens aged 40 and above may qualify for the Mid-Career Enhanced Subsidy, subject to the funding rules in force.",
    "The programme is delivered in a blended format, with weekday evening classes on campus and self-paced online content.",
    "Refunds are processed within 30 working days, less an administrative fee, if a withdrawal is approved before the commencement date.",
    "Applicants whose degree was not taught in English must provide an IELTS score of 6.5 or an equivalent qualification.",
    "Credits earned in stackable certificates may be recognised towards the corresponding master's degree within five years.",
    "Company-sponsored learners should ask their HR department to submit the sponsorship form together with the application.",
    "The academic calendar, examination timetable and venue details are published on the learner portal two weeks before each term.",
]


def para(n):
    return " ".join(rng.choice(SENTENCES) for _ in range(n))


def text_pdf(path, pages=10):
    doc = pymupdf.open()
    for i in range(pages):
        page = doc.new_page(width=595, height=842)
        prog = PROGRAMMES[i % len(PROGRAMMES)]
        page.insert_text((56, 70), f"{prog} — Programme Handbook 2026", fontsize=13, fontname="hebo")
        body = "\n\n".join(para(5) for _ in range(5))
        page.insert_textbox(pymupdf.Rect(56, 92, 539, 790), body, fontsize=10.5, fontname="helv", lineheight=1.35)
        page.insert_text((280, 815), f"Page {i + 1} of {pages}", fontsize=8, fontname="helv")
    doc.save(path)


def scanned_pdf(src, path, dpi=150):
    """Rasterise each page as a slightly skewed greyscale JPEG: an image-only PDF like a scan."""
    src_doc = pymupdf.open(src)
    out = pymupdf.open()
    for page in src_doc:
        pix = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY)
        img = Image.frombytes("L", (pix.width, pix.height), pix.samples)
        img = img.rotate(rng.uniform(-0.8, 0.8), fillcolor=255, expand=False).filter(ImageFilter.GaussianBlur(0.4))
        jpg = OUT / "_tmp.jpg"
        img.save(jpg, quality=70)
        p = out.new_page(width=page.rect.width, height=page.rect.height)
        p.insert_image(p.rect, filename=str(jpg))
    jpg.unlink()
    out.save(path)


def receipt(path, size=(900, 1200)):
    img = Image.new("RGB", size, "white")
    d = ImageDraw.Draw(img)
    f, fb = ImageFont.truetype(FONT, 26), ImageFont.truetype(FONT_B, 34)
    y = 60
    d.text((60, y), "DBS iBanking — Transfer Successful", font=fb, fill="black"); y += 90
    rows = [("Date", "02 Oct 2026, 14:37"), ("From", "POSB Savings 123-45678-9"), ("To", "NANYANG TECHNOLOGICAL UNIVERSITY"), ("Amount", "SGD 3,924.00"), ("Reference", "PACE-FMIC-2026-08817"), ("Payer", "Tan Wei Ming"), ("NRIC", "S8812345D"), ("Mobile", "+65 9123 4567"), ("Transaction ID", "TXN20261002143711892")]
    for k, v in rows:
        d.text((60, y), k, font=f, fill="#555"); d.text((360, y), v, font=f, fill="black"); y += 70
    d.text((60, y + 40), "Please keep this receipt for your records.", font=f, fill="#555")
    img.save(path, quality=88)
    return img


def phone_photo(rec, path):
    """The receipt printed and photographed: 12 MP, on a desk, slight perspective."""
    bg = Image.new("RGB", (4032, 3024), (182, 160, 130))
    noise = Image.effect_noise((4032, 3024), 18).convert("RGB")
    bg = Image.blend(bg, noise, 0.15)
    paper = rec.resize((1800, 2400)).rotate(4, expand=True, fillcolor=(182, 160, 130))
    bg.paste(paper, (1100, 300))
    bg.filter(ImageFilter.GaussianBlur(1.2)).save(path, quality=85)


def screenshot(path):
    img = Image.new("RGB", (1920, 1080), "#f3f4f6")
    d = ImageDraw.Draw(img)
    f, fb, fs = ImageFont.truetype(FONT, 22), ImageFont.truetype(FONT_B, 30), ImageFont.truetype(FONT, 18)
    d.rectangle((0, 0, 1920, 70), fill="#1f2a44"); d.text((30, 20), "NTU PaCE Learner Portal", font=fb, fill="white")
    d.text((1500, 24), "Logged in as: Priya Ramasamy", font=fs, fill="white")
    d.rectangle((0, 70, 300, 1080), fill="#e5e7eb")
    for i, item in enumerate(["Dashboard", "My Applications", "Payments", "Course Materials", "Profile", "Help"]):
        d.text((30, 110 + i * 50), item, font=f, fill="#111")
    d.text((340, 110), "Application PACE-APP-2026-30412 — Graduate Certificate in Applied Data Analytics", font=fb, fill="#111")
    d.rectangle((340, 180, 1860, 300), fill="#fde8e8", outline="#d33")
    d.text((370, 200), "Error 4021: Payment could not be matched to this application.", font=fb, fill="#a00")
    d.text((370, 250), "Please contact PaCE with your payment reference. Status: PENDING VERIFICATION", font=f, fill="#a00")
    rows = [("Applicant", "Priya Ramasamy"), ("Email", "priya.r@example.com"), ("Intake", "January 2027"), ("Fee", "SGD 2,616.00"), ("Payment ref", "PACE-GCADA-2026-11903"), ("Submitted", "28 Sep 2026")]
    for i, (k, v) in enumerate(rows):
        d.text((370, 350 + i * 55), k, font=f, fill="#555"); d.text((700, 350 + i * 55), v, font=f, fill="#111")
    d.rectangle((370, 720, 600, 780), fill="#1f6feb"); d.text((410, 735), "Retry payment", font=f, fill="white")
    img.save(path)


EMAIL = """Subject: Payment not matched and question about the January intake

Dear PaCE team,

I applied for the Graduate Certificate in Applied Data Analytics for the January 2027 intake and paid the course fee by bank transfer on 2 October. The learner portal now shows "Error 4021: Payment could not be matched to this application". I have attached the bank transfer receipt and a screenshot of the portal.

Could you please check whether my payment has been received? I would also like to know whether I can use my SkillsFuture Credit for part of the fee, since I paid the full amount, and if so how the refund of the difference would work.

Finally, my employer may sponsor the second module. Is the sponsorship form the same for all modules, and when does it need to be submitted?

I have also attached the programme handbook I downloaded, in case it helps.

Thank you,
Priya Ramasamy
"""

REPLIES = [
    "Thank you for your enquiry. Your application has been received and is being processed. We will update you on the outcome within 10 working days.",
    "Thank you, I have uploaded my degree certificate as requested. Could you confirm whether my transcript is also needed?",
    "Please also submit your official transcript in PDF through the learner portal under My Applications.",
    "Done. Could you also tell me whether classes for the January intake are on weekday evenings or weekends?",
    "Classes are held on weekday evenings from 7pm to 10pm, with some Saturday workshops. The timetable is published two weeks before the term.",
    "Thank you. I would like to ask about the fee. Is the course fee inclusive of GST, and are there instalment options?",
    "The fee shown is inclusive of GST. Fees are payable per module; instalment plans are not available for this programme.",
    "Understood. I have now paid the first module by bank transfer. How long does it take for the payment to show on the portal?",
    "Payments usually reflect within 5 working days. If it does not appear, please send us your payment reference.",
    "It has been a week and the portal still shows the payment as pending. My reference is PACE-GCADA-2026-11903.",
]


def thread(n=10):
    """n earlier messages, each about 120–250 words with signature and header lines, as staff would see them."""
    msgs = []
    for i, r in enumerate(REPLIES[:n]):
        who = "NTU PaCE Enquiries <pace@ntu.edu.sg>" if i % 2 == 0 else "Priya Ramasamy <priya.r@example.com>"
        body = r + " " + para(3)
        sig = "\n\nBest regards,\nPaCE Enquiries Team\nNanyang Technological University\n50 Nanyang Avenue, Singapore 639798" if i % 2 == 0 else "\n\nThanks,\nPriya"
        msgs.append(f"From: {who}\nDate: {i + 12} Sep 2026\nSubject: Re: Application enquiry\n\n{body}{sig}")
    return msgs


def main():
    OUT.mkdir(exist_ok=True)
    text_pdf(OUT / "handbook_text_10p.pdf")
    scanned_pdf(OUT / "handbook_text_10p.pdf", OUT / "handbook_scan_10p.pdf")
    rec = receipt(OUT / "receipt_900x1200.jpg")
    phone_photo(rec, OUT / "receipt_photo_4032x3024.jpg")
    screenshot(OUT / "portal_1920x1080.png")
    (OUT / "email.txt").write_text(EMAIL)
    msgs = thread()
    (OUT / "thread_10_dedup.txt").write_text("\n\n-----\n\n".join(msgs))
    # Naive thread: every message quotes all earlier ones, as raw replies often do.
    quoted, chain = [], ""
    for m in msgs:
        chain = m + ("\n\n> " + chain.replace("\n", "\n> ") if chain else "")
        quoted.append(chain)
    (OUT / "thread_10_quoted.txt").write_text("\n\n=====\n\n".join(quoted))
    print("assets written to", OUT)


if __name__ == "__main__":
    main()
