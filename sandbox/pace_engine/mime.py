"""Turn the raw input (.eml, .msg, plain text or web form) into one normalised message.

Addresses (From, To, CC, Reply-To) are dropped here: no later step needs them. Only the sender's
display name is kept, for the greeting. Quoted earlier messages are cut from the body so they are
not read as new questions (scenario E8); earlier messages come in through `thread` instead.
"""
import base64
import email
import hashlib
import re
from dataclasses import dataclass, field
from email import policy
from email.utils import getaddresses, parsedate_to_datetime

from bs4 import BeautifulSoup


class InputError(ValueError):
    """Bad input the caller can fix; reported with the field name."""

    def __init__(self, field, message):
        super().__init__(message)
        self.field = field


@dataclass
class Attachment:
    attachment_id: str
    filename: str | None
    media_type: str
    data: bytes
    inline: bool = False

    @property
    def size(self):
        return len(self.data)


@dataclass
class Message:
    subject: str = ""
    body: str = ""
    quoted: str = ""
    sender_name: str | None = None
    message_id: str | None = None
    in_reply_to: str | None = None
    references: list[str] = field(default_factory=list)
    date: str | None = None
    html_only: bool = False
    attachments: list[Attachment] = field(default_factory=list)
    form_fields: dict | None = None
    sent_by: str | None = None  # SENDER or PACE, for thread messages when known

    def fingerprint(self):
        if self.message_id:
            return self.message_id
        return hashlib.sha256(re.sub(r"\s+", " ", self.body.strip().lower()).encode()).hexdigest()


def b64(data, field_name):
    try:
        return base64.b64decode(data, validate=True)
    except Exception:
        raise InputError(field_name, "not valid base64")


def html_to_text(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "head"]):
        tag.decompose()
    for bq in soup.find_all("blockquote"):  # quoted history in HTML replies
        bq.replace_with("\n[quoted text removed]\n")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for p in soup.find_all(["p", "div", "li", "tr", "h1", "h2", "h3"]):
        p.insert_after("\n")
    text = soup.get_text()
    text = re.sub(r"[ \t ]+", " ", text)
    return re.sub(r"\n\s*\n\s*\n+", "\n\n", text).strip()


_QUOTE_HEADERS = [
    re.compile(r"^\s*On\b.{0,300}\bwrote:\s*$", re.I),
    re.compile(r"^\s*-{2,}\s*Original Message\s*-{2,}", re.I),
    re.compile(r"^\s*_{8,}\s*$"),
    re.compile(r"^\s*\[quoted text removed\]\s*$"),
]
_OUTLOOK_FROM = re.compile(r"^\s*\*?From:\*?\s+\S", re.I)
_OUTLOOK_NEXT = re.compile(r"^\s*\*?(Sent|Date|To|Subject):\*?\s", re.I)


def strip_quoted(text):
    """Split a body into (new text, quoted history). Handles '>' quoting, 'On ... wrote:' and Outlook headers."""
    lines = text.splitlines()
    cut = None
    for i, line in enumerate(lines):
        joined = line + " " + (lines[i + 1] if i + 1 < len(lines) else "")
        if any(p.match(line) for p in _QUOTE_HEADERS) or (line.strip().startswith("On ") and _QUOTE_HEADERS[0].match(joined)):
            cut = i
            break
        if _OUTLOOK_FROM.match(line) and any(_OUTLOOK_NEXT.match(n) for n in lines[i + 1:i + 4]):
            cut = i
            break
    head, tail = (lines, []) if cut is None else (lines[:cut], lines[cut:])
    kept = [l for l in head if not l.lstrip().startswith(">")]
    quoted = [l for l in head if l.lstrip().startswith(">")] + tail
    return "\n".join(kept).strip(), "\n".join(quoted).strip()


def _header_ids(value):
    return re.findall(r"<[^<>\s]+>", value or "")


def parse_eml(raw: bytes, max_attachment_bytes: int, prefix="ATT") -> Message:
    try:
        msg = email.message_from_bytes(raw, policy=policy.default)
    except Exception as e:
        raise InputError("email.contentBase64", f"could not parse the raw email: {e}")
    if not msg.keys():
        raise InputError("email.contentBase64", "no email headers found; is this an .eml file?")
    out = Message(subject=str(msg.get("Subject", "") or "").strip())
    names = [n for n, _ in getaddresses([str(msg.get("From", ""))]) if n]
    out.sender_name = names[0] if names else None
    out.message_id = (_header_ids(str(msg.get("Message-ID", ""))) or [None])[0]
    out.in_reply_to = (_header_ids(str(msg.get("In-Reply-To", ""))) or [None])[0]
    out.references = _header_ids(str(msg.get("References", "")))
    try:
        out.date = parsedate_to_datetime(str(msg["Date"])).isoformat() if msg["Date"] else None
    except Exception:
        out.date = None
    body_part = msg.get_body(preferencelist=("plain", "html"))
    text = ""
    if body_part is not None:
        content = body_part.get_content()
        if body_part.get_content_type() == "text/html":
            out.html_only = True
            text = html_to_text(content)
        else:
            text = content
    out.body, out.quoted = strip_quoted(text)
    n = 0
    for part in msg.walk():
        if part.is_multipart() or part is body_part:
            continue
        ctype = part.get_content_type()
        disp = part.get_content_disposition()
        if disp is None and ctype in ("text/plain", "text/html"):
            continue  # alternative bodies
        data = part.get_payload(decode=True) or b""
        n += 1
        out.attachments.append(Attachment(
            attachment_id=f"{prefix}-{n:03d}", filename=part.get_filename(), media_type=ctype, data=data,
            inline=disp == "inline" or (disp is None and bool(part.get("Content-ID")))))
    return out


def parse_msg(raw: bytes, max_attachment_bytes: int) -> Message:
    try:
        import extract_msg
    except ImportError:
        raise InputError("email.format", ".msg input is not enabled on this server; send .eml or text")
    import io
    try:
        m = extract_msg.openMsg(io.BytesIO(raw))
    except Exception as e:
        raise InputError("email.contentBase64", f"could not read the .msg file: {e}")
    text = m.body or ""
    html_only = False
    if not text.strip() and m.htmlBody:
        html = m.htmlBody.decode("utf-8", "replace") if isinstance(m.htmlBody, bytes) else m.htmlBody
        text, html_only = html_to_text(html), True
    out = Message(subject=(m.subject or "").strip(), html_only=html_only)
    sender = m.sender or ""
    out.sender_name = (getaddresses([sender])[0][0] or None) if sender else None
    out.message_id = (_header_ids(m.messageId or "") or [None])[0]
    out.in_reply_to = (_header_ids(getattr(m, "inReplyTo", "") or "") or [None])[0]
    out.body, out.quoted = strip_quoted(text)
    for i, a in enumerate(m.attachments, 1):
        data = a.data if isinstance(a.data, bytes) else b""
        out.attachments.append(Attachment(f"ATT-{i:03d}", a.longFilename or a.shortFilename, a.mimetype or "application/octet-stream", data))
    return out


FORM_BODY_KEYS = ("message", "enquiry", "question", "details", "comments")


def parse_form(fields: dict) -> Message:
    norm = {k.strip(): (v or "").strip() for k, v in fields.items()}
    body_key = next((k for k in norm if k.lower() in FORM_BODY_KEYS), None)
    if not body_key or not norm[body_key]:
        raise InputError("form.fields", f"web form needs a message field (one of: {', '.join(FORM_BODY_KEYS)})")
    # Personal fields are dropped like email addresses; the name is kept for the greeting only.
    drop = re.compile(r"e-?mail|phone|mobile|nric|address|contact", re.I)
    signals = {k: v for k, v in norm.items() if k != body_key and v and not drop.search(k)}
    name = next((v for k, v in signals.items() if k.lower() in ("name", "full name", "fullname")), None)
    signals = {k: v for k, v in signals.items() if k.lower() not in ("name", "full name", "fullname")}
    return Message(subject=norm.get("subject", "Web form enquiry"), body=norm[body_key], sender_name=name, form_fields=signals)


def parse_request_input(req, max_attachment_bytes):
    """The current message from an EnquiryRequest."""
    if req.email is not None:
        raw = b64(req.email.contentBase64, "email.contentBase64")
        return parse_eml(raw, max_attachment_bytes) if req.email.format == "eml" else parse_msg(raw, max_attachment_bytes)
    if req.text is not None:
        body, quoted = strip_quoted(req.text.body)
        atts = [Attachment(f"ATT-{i:03d}", a.filename, a.mediaType, b64(a.contentBase64, f"text.attachments[{i - 1}].contentBase64"))
                for i, a in enumerate(req.text.attachments, 1)]
        return Message(subject=req.text.subject, body=body, quoted=quoted, attachments=atts)
    return parse_form(req.form.fields)


def parse_thread(items, max_attachment_bytes, max_messages, max_chars):
    """Earlier messages: parsed, deduplicated, oldest first, quotes cut, the latest `max_messages` kept."""
    msgs, seen = [], set()
    for i, it in enumerate(items):
        if it.format == "text":
            body, _ = strip_quoted(it.body)
            m = Message(subject=it.subject or "", body=body)
        else:
            raw = b64(it.contentBase64, f"thread[{i}].contentBase64")
            m = parse_eml(raw, max_attachment_bytes, prefix=f"T{i}") if it.format == "eml" else parse_msg(raw, max_attachment_bytes)
        m.sent_by = it.sentBy
        fp = m.fingerprint()
        if fp in seen or not m.body.strip():
            continue
        seen.add(fp)
        m.body = m.body[:max_chars]
        m.attachments = []  # earlier attachments are not re-read
        msgs.append(m)
    msgs.sort(key=lambda m: m.date or "")
    return msgs[-max_messages:]
