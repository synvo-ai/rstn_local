"""API v0 request and result schemas (B7). Field names here are the contract published to RSTN."""
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

SCHEMA_VERSION = "v0"

Action = Literal["REPLY_DIRECTLY", "REFER_TO_TEAM", "ASK_CLARIFICATION", "MANUAL_HANDLING"]
ACTIONS = ("REPLY_DIRECTLY", "REFER_TO_TEAM", "ASK_CLARIFICATION", "MANUAL_HANDLING")


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------- request ----------

class RawEmail(Strict):
    format: Literal["eml", "msg"] = Field(description="eml: RFC 5322 / MIME; msg: Outlook .msg, converted on arrival")
    contentBase64: str = Field(min_length=1)


class TextAttachment(Strict):
    filename: str
    mediaType: str
    contentBase64: str


class TextEmail(Strict):
    subject: str = ""
    body: str = Field(min_length=1)
    attachments: list[TextAttachment] = Field(default_factory=list, max_length=20)


class WebForm(Strict):
    fields: dict[str, str] = Field(description="Form fields as submitted, e.g. programme, enquiryType, message")


class ThreadItem(Strict):
    """An earlier message in the same thread: raw email, or subject and body as text."""
    format: Literal["eml", "msg", "text"]
    contentBase64: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    sentBy: Optional[Literal["SENDER", "PACE"]] = None

    @model_validator(mode="after")
    def _one(self):
        if self.format == "text" and not self.body:
            raise ValueError("thread item with format 'text' needs 'body'")
        if self.format != "text" and not self.contentBase64:
            raise ValueError(f"thread item with format '{self.format}' needs 'contentBase64'")
        return self


class Options(Strict):
    includeReplyDraft: bool = True
    simulate: Optional[Literal["failure", "degraded"]] = Field(None, description="Sandbox only: force a failed or limited run (scenario E5)")


class EnquiryRequest(Strict):
    schemaVersion: Literal["v0"] = "v0"
    requestId: str = Field(min_length=1, max_length=128)
    idempotencyKey: Optional[str] = Field(None, max_length=128)
    channel: Literal["EMAIL", "WEB_FORM"]
    senderRef: Optional[str] = Field(None, max_length=128, description="Opaque sender reference; never an email address")
    callbackUrl: Optional[HttpUrl] = None
    email: Optional[RawEmail] = None
    text: Optional[TextEmail] = None
    form: Optional[WebForm] = None
    thread: list[ThreadItem] = Field(default_factory=list, max_length=50)
    options: Options = Field(default_factory=Options)

    @model_validator(mode="after")
    def _exactly_one_input(self):
        given = [k for k in ("email", "text", "form") if getattr(self, k) is not None]
        if len(given) != 1:
            raise ValueError("exactly one of 'email', 'text' or 'form' is required")
        if self.channel == "WEB_FORM" and self.form is None:
            raise ValueError("channel WEB_FORM requires 'form'")
        if self.senderRef and "@" in self.senderRef:
            raise ValueError("senderRef must be an opaque reference, not an email address")
        return self


class Change(Strict):
    issueId: str
    action: Action
    ownerTeamId: Optional[str] = Field(None, description="Required when action is REFER_TO_TEAM")
    staffNote: Optional[str] = Field(None, max_length=1000)

    @model_validator(mode="after")
    def _owner(self):
        if self.action == "REFER_TO_TEAM" and not self.ownerTeamId:
            raise ValueError("ownerTeamId is required when action is REFER_TO_TEAM")
        return self


class RecheckRequest(Strict):
    request: EnquiryRequest
    previousResult: dict
    change: Change


# ---------- result ----------

class Programme(BaseModel):
    status: Literal["RESOLVED", "AMBIGUOUS", "UNRESOLVED", "NOT_NEEDED"]
    programmeId: Optional[str] = None
    name: Optional[str] = None
    candidates: list[dict] = Field(default_factory=list)


class Owner(BaseModel):
    teamId: str
    name: str
    inbox: Optional[str] = None
    routingBasis: str


class Evidence(BaseModel):
    evidenceId: str
    authority: Literal["APPROVED_KNOWLEDGE", "SENDER_PROVIDED", "INSTITUTIONAL"]
    title: str
    url: Optional[str] = None
    version: Optional[str] = None
    excerpt: str


class Issue(BaseModel):
    issueId: str
    summary: str
    topic: str
    intent: str
    programme: Programme
    owner: Optional[Owner] = None
    answerability: Literal["SUFFICIENT", "INSUFFICIENT", "NOT_ASSESSED"] = "NOT_ASSESSED"
    action: Action
    reason: str
    missingInformation: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)


class Claim(BaseModel):
    issueId: str
    text: str
    evidenceIds: list[str]


class Reply(BaseModel):
    text: Optional[str] = None
    coversIssueIds: list[str] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    safety: Literal["SAFE_TO_REVIEW", "BLOCKED", "NOT_PRODUCED"]
    findings: list[str] = Field(default_factory=list)


class HandoffNote(BaseModel):
    issueId: str
    teamId: str
    text: str


class AttachmentInfo(BaseModel):
    attachmentId: str
    filename: Optional[str]
    mediaType: str
    sizeBytes: int
    status: Literal["NOT_READ", "IGNORED", "TOO_LARGE", "UNSUPPORTED", "READ"]
    note: Optional[str] = None


class MessageInfo(BaseModel):
    messageType: Literal["ENQUIRY", "NOT_ENQUIRY"]
    notEnquiryKind: Optional[str] = None
    language: Optional[str] = None
    languageSupported: bool = True
    emailAction: Optional[dict] = Field(None, description="Set when the whole email goes one way, e.g. Manual handling for a language not supported in phase 1")
    threadMessagesUsed: int = 0


class Stage(BaseModel):
    stage: str
    status: Literal["OK", "SKIPPED", "DEGRADED", "FAILED"]
    latencyMs: int
    note: Optional[str] = None


class Trace(BaseModel):
    requestId: str
    runId: str
    engineVersion: str
    knowledgeVersion: str
    configVersion: str
    receivedAt: str
    completedAt: Optional[str] = None
    stages: list[Stage] = Field(default_factory=list)


class Result(BaseModel):
    schemaVersion: str = SCHEMA_VERSION
    runId: str
    requestId: str
    status: Literal["QUEUED", "RUNNING", "COMPLETED"]
    runHealth: Optional[Literal["SUCCEEDED", "DEGRADED", "FAILED"]] = None
    message: Optional[MessageInfo] = None
    summary: dict = Field(default_factory=dict)
    issues: list[Issue] = Field(default_factory=list)
    reply: Optional[Reply] = None
    handoffNotes: list[HandoffNote] = Field(default_factory=list)
    attachments: list[AttachmentInfo] = Field(default_factory=list)
    recheck: Optional[dict] = None
    trace: Optional[Trace] = None
    signature: Optional[str] = None
