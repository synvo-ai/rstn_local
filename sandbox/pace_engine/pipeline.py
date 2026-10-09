"""The engine: one email in, issues with actions plus one reply draft out.

Stages: language check → understand (model) → resolve programme and route (registry) → decide action
(rules) → draft (model) → verify (rules, then model). A staff re-check reuses the signed previous result
and only redrafts and re-verifies.
"""
import hashlib
import re
import time
from contextlib import contextmanager
from dataclasses import dataclass, field

import yaml

from . import ENGINE_VERSION, language, prompts
from .knowledge import KnowledgeBase
from .llm import ModelError, Usage
from .mime import Message, parse_request_input, parse_thread
from .models import AttachmentInfo, EnquiryRequest
from .registry import Registry

NEEDS_PROGRAMME = {"COURSE_INFORMATION", "SCHEDULE", "FEES", "ENTRY_REQUIREMENTS"}
RECORDS = {"PAYMENT_STATUS": "payment records", "APPLICATION_STATUS": "application records", "LEARNER_RECORD": "learner records"}
READABLE_TYPES = ("application/pdf", "image/", "text/plain", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword")


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class Prepared:
    request: EnquiryRequest
    message: Message
    thread: list
    attachments: list


@dataclass
class Tracker:
    budget: int
    stages: list = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)

    @contextmanager
    def stage(self, name):
        rec = {"stage": name, "status": "OK", "latencyMs": 0}
        t0 = time.time()
        try:
            yield rec
        except Exception:
            rec["status"] = "FAILED"
            raise
        finally:
            rec["latencyMs"] = int((time.time() - t0) * 1000)
            self.stages.append(rec)

    def skip(self, name, note=None):
        self.stages.append({"stage": name, "status": "SKIPPED", "latencyMs": 0, **({"note": note} if note else {})})


def _norm(s):
    return re.sub(r"\s+", " ", s or "").strip().lower()


class Engine:
    def __init__(self, settings, gateway):
        self.s = settings
        self.gw = gateway
        self.kb = KnowledgeBase(settings.data_dir / "knowledge")
        self.reg = Registry(settings.data_dir / "registry.yaml")
        tpl_raw = (settings.data_dir / "templates.yaml").read_bytes()
        self.tpl = yaml.safe_load(tpl_raw)
        models = f"{settings.model_understand}|{settings.model_draft}|{settings.model_verify}"
        self.config_version = "cfg-" + hashlib.sha256(tpl_raw + self.reg.version.encode() + models.encode()).hexdigest()[:10]

    # ---------- input ----------

    def prepare(self, req: EnquiryRequest) -> Prepared:
        """Parse and check input before a run starts; raises InputError (reported as 400) on bad input."""
        msg = parse_request_input(req, self.s.max_attachment_bytes)
        msg.body = msg.body[: self.s.max_body_chars]
        thread = parse_thread(req.thread, self.s.max_attachment_bytes, self.s.max_thread_messages, self.s.max_chars_per_thread_message)
        atts = []
        for a in msg.attachments:
            if a.size > self.s.max_attachment_bytes:
                status, note = "TOO_LARGE", f"over the {self.s.max_attachment_bytes // (1024 * 1024)} MB limit"
            elif a.inline and a.media_type.startswith("image/") and a.size < 40_000:
                status, note = "IGNORED", "small inline image (logo or signature)"
            elif a.media_type.startswith(READABLE_TYPES):
                status, note = "NOT_READ", "attachment reading arrives in sandbox v2"
            else:
                status, note = "UNSUPPORTED", "file type not supported"
            atts.append(AttachmentInfo(attachmentId=a.attachment_id, filename=a.filename, mediaType=a.media_type, sizeBytes=a.size, status=status, note=note).model_dump())
        return Prepared(req, msg, thread, atts)

    # ---------- model calls ----------

    async def _call(self, t: Tracker, stage, model, system, payload, schema):
        est = len(str(payload)) // 3
        if t.usage.input + est > t.budget:
            raise BudgetExceeded(stage)
        out, usage = await self.gw.json(stage, model, system, payload, schema)
        t.usage.add(usage)
        return out

    # ---------- the run ----------

    async def run(self, prep: Prepared, run_id, received_at):
        req, msg = prep.request, prep.message
        t = Tracker(self.s.max_input_tokens_per_email)
        info = {"messageType": "ENQUIRY", "language": None, "languageSupported": True, "emailAction": None, "threadMessagesUsed": len(prep.thread)}

        def done(health, issues=(), reply=None, extra=None):
            return self._result(req, run_id, received_at, t, health, info, list(issues), reply, prep.attachments, extra)

        with t.stage("language_check"):
            is_en, detail = language.check(f"{msg.subject}\n{msg.body}")
        if not is_en:
            info.update(language="non-English", languageSupported=False,
                        emailAction={"action": "MANUAL_HANDLING", "reason": f"Language not supported in phase 1 ({detail})."})
            t.skip("understand", "language not supported")
            return done("SUCCEEDED", reply={"safety": "NOT_PRODUCED"})

        if req.options.simulate == "failure" and self.s.sandbox:
            t.stages.append({"stage": "understand", "status": "FAILED", "latencyMs": 0, "note": "simulated failure"})
            info["emailAction"] = {"action": "MANUAL_HANDLING", "reason": "The engine could not complete this email; use the fallback acknowledgement."}
            return done("FAILED", reply={"safety": "NOT_PRODUCED"})

        try:
            with t.stage("understand"):
                u = await self._call(t, "understand", self.s.model_understand, prompts.UNDERSTAND, self._understand_payload(prep), prompts.UNDERSTAND_SCHEMA)
        except (ModelError, BudgetExceeded) as e:
            info["emailAction"] = {"action": "MANUAL_HANDLING", "reason": "The engine could not complete this email; use the fallback acknowledgement."}
            t.stages[-1]["note"] = "over token budget" if isinstance(e, BudgetExceeded) else "model step failed"
            return done("FAILED", reply={"safety": "NOT_PRODUCED"})

        lang = (u.get("language") or "en").lower()[:2]
        info["language"] = lang
        if lang != "en":
            info.update(languageSupported=False, emailAction={"action": "MANUAL_HANDLING", "reason": "Language not supported in phase 1."})
            return done("SUCCEEDED", reply={"safety": "NOT_PRODUCED"})
        if u.get("messageType") != "ENQUIRY":
            kind = u.get("messageType")
            info.update(messageType="NOT_ENQUIRY", notEnquiryKind=kind,
                        emailAction={"action": "MANUAL_HANDLING", "reason": f"Not an enquiry ({kind.replace('_', ' ').lower()}); nothing to answer."})
            return done("SUCCEEDED", reply={"safety": "NOT_PRODUCED"})

        raw = [i for i in u.get("issues", []) if not i.get("alreadyAnswered")]
        skipped = len(u.get("issues", [])) - len(raw)
        if not raw:
            info["emailAction"] = {"action": "MANUAL_HANDLING", "reason": "No new question found in this message."}
            return done("SUCCEEDED", reply={"safety": "NOT_PRODUCED"}, extra={"alreadyAnsweredSkipped": skipped})

        with t.stage("resolve_and_route"):
            states = self._plan(raw, msg, prep.attachments)

        health, reply = "SUCCEEDED", None
        if not req.options.includeReplyDraft:
            t.skip("draft", "not requested")
            reply = {"safety": "NOT_PRODUCED"}
        elif req.options.simulate == "degraded" and self.s.sandbox:
            t.stages.append({"stage": "draft", "status": "DEGRADED", "latencyMs": 0, "note": "simulated"})
            health, reply = "DEGRADED", {"safety": "NOT_PRODUCED", "findings": ["Reply draft not produced (simulated limitation)."]}
        else:
            health, reply = await self._draft_and_verify(t, states, msg)
        return done(health, states, reply, {"alreadyAnsweredSkipped": skipped})

    def _understand_payload(self, prep):
        m = prep.message
        p = {"subject": m.subject, "body": m.body}
        if m.form_fields:
            p["formFields"] = m.form_fields
        if prep.thread:
            p["earlierMessages"] = [{"from": t.sent_by or "unknown", "date": t.date, "subject": t.subject, "body": t.body} for t in prep.thread]
        if prep.attachments:
            p["attachments"] = [{"filename": a["filename"], "mediaType": a["mediaType"]} for a in prep.attachments if a["status"] != "IGNORED"]
        return p

    # ---------- deciding ----------

    def _plan(self, raw, msg, attachments):
        form_prog = None
        if msg.form_fields:
            form_prog = next((v for k, v in msg.form_fields.items() if re.search(r"programme|program|course", k, re.I)), None)
        resolved = set()
        for r in raw:
            res = self.reg.resolve(r.get("programmeMentions") or ([form_prog] if form_prog else []))
            if res["status"] == "RESOLVED":
                resolved.add(res["programmeId"])
        inherited = next(iter(resolved)) if len(resolved) == 1 else None
        has_unread = any(a["status"] in ("NOT_READ", "UNSUPPORTED", "TOO_LARGE") for a in attachments)

        resolved_raw, groups = [], {}
        for r in raw:
            mentions = r.get("programmeMentions") or ([form_prog] if form_prog else [])
            res = self.reg.resolve(mentions)
            if res["status"] == "UNRESOLVED" and not mentions:
                res = self.reg._resolved(inherited) if inherited else {"status": "UNRESOLVED" if r["intent"] in NEEDS_PROGRAMME else "NOT_NEEDED", "candidates": []}
            # Same intent and same programme: one answer covers both, so one issue (keeps issue counts stable).
            key = (r["intent"], res.get("programmeId") or res["status"] + "|" + "|".join(sorted(m.lower() for m in mentions)))
            if r["intent"] != "OTHER" and key in groups:
                g = groups[key]
                g["summary"] = f"{g['summary']} {r['summary']}"
                g["query"] = f"{g['query']} {r['query']}"
                g["senderFacts"] = g.get("senderFacts", []) + [f for f in r.get("senderFacts", []) if f not in g.get("senderFacts", [])]
                g["mentionsAttachment"] = g.get("mentionsAttachment") or r.get("mentionsAttachment")
                continue
            r = {**r, "_res": res, "_mentions": mentions}
            groups[key] = r
            resolved_raw.append(r)

        states = []
        for n, r in enumerate(resolved_raw, 1):
            res, mentions = r["_res"], r["_mentions"]
            pid = res.get("programmeId")
            team, handling, basis = self.reg.route(r["intent"], pid)
            st = {
                "issueId": f"ISSUE-{n:03d}", "summary": r["summary"], "topic": r["topic"], "query": r["query"], "intent": r["intent"],
                "programme": res, "mentions": mentions, "owner": {"teamId": team.id, "name": team.name, "inbox": team.inbox, "routingBasis": basis},
                "handling": handling, "senderFacts": r.get("senderFacts", []), "missingInformation": [], "evidenceItems": [],
                "answerability": "NOT_ASSESSED",
            }
            if r.get("mentionsAttachment") and has_unread:
                st["missingInformation"].append("The attached file was not read (attachment reading arrives in sandbox v2).")
            self._decide(st)
            states.append(st)
        return states

    def _decide(self, st):
        intent, prog, handling = st["intent"], st["programme"], st["handling"]
        if handling == "INSTITUTIONAL":
            reason = f"Needs {RECORDS[intent]}, which the engine cannot see in phase 1; staff check the record."
            if st["missingInformation"] or any("attach" in f.lower() or "receipt" in f.lower() for f in st["senderFacts"]):
                reason += " Anything the sender attached is their own evidence, not confirmation."
            return self._set(st, "MANUAL_HANDLING", reason)
        if handling == "REFER":
            if prog["status"] == "AMBIGUOUS" and self.reg.routing[intent]["owner"] == "SCHOOL":
                return self._clarify(st, "The owning team depends on the programme, which is unclear.")
            return self._set(st, "REFER_TO_TEAM", f"Handled by {st['owner']['name']}, not the general enquiries desk.")
        if handling == "MANUAL":
            return self._set(st, "MANUAL_HANDLING", "No routing rule covers this kind of question; staff decide.")
        # ANSWER_DESK
        if intent in NEEDS_PROGRAMME and prog["status"] == "AMBIGUOUS":
            return self._clarify(st, "More than one programme matches what the sender wrote.")
        if intent in NEEDS_PROGRAMME and prog["status"] == "UNRESOLVED":
            why = "The programme named is not in the programme registry." if st["mentions"] else "The sender did not say which programme."
            return self._clarify(st, why)
        st["evidenceItems"] = self.kb.search(f"{st['query']} {st['topic']}", prog.get("programmeId"), topic=intent)
        if not st["evidenceItems"]:
            return self._set(st, "MANUAL_HANDLING", "Approved knowledge has nothing on this question.")
        return self._set(st, "REPLY_DIRECTLY", "Answered from approved knowledge.")

    def _set(self, st, action, reason):
        st["action"], st["reason"] = action, reason
        if action == "REFER_TO_TEAM":
            st["controlled"] = self.tpl["refer"].format(topic=st["topic"], team=st["owner"]["name"])
        elif action == "ASK_CLARIFICATION":
            cands = [c["name"] for c in st["programme"].get("candidates", [])]
            st["controlled"] = self.tpl["clarify"].format(candidates=" or ".join(cands)) if cands else self.tpl["clarify_unknown"]
        else:  # MANUAL_HANDLING, or the fallback if a direct reply turns out unsupported
            st["controlled"] = self.tpl["manual"].format(topic=st["topic"])
        if action in ("ASK_CLARIFICATION",):
            desk = self.reg.teams[self.reg.answer_desk]
            st["owner"] = {"teamId": desk.id, "name": desk.name, "inbox": desk.inbox, "routingBasis": "Clarification from the general enquiries desk"}
        return st

    def _clarify(self, st, reason):
        if st["programme"]["status"] == "AMBIGUOUS":
            st["missingInformation"].append("Which programme the sender means.")
        else:
            st["missingInformation"].append("The programme name.")
        return self._set(st, "ASK_CLARIFICATION", reason)

    # ---------- drafting and verification ----------

    def _greeting(self, msg):
        name = (msg.sender_name or "").strip()
        return self.tpl["greeting_named"].format(name=name) if name else self.tpl["greeting_unnamed"]

    async def _draft_and_verify(self, t, states, msg):
        payload = {
            "greeting": self._greeting(msg), "opening": self.tpl["opening"], "signOff": self.tpl["sign_off"],
            "note": "If several issues share the same controlled sentence, include it once.",
            "issues": [],
        }
        for st in states:
            item = {"issueId": st["issueId"], "question": st["summary"], "action": st["action"]}
            if st["action"] == "REPLY_DIRECTLY":
                item["evidence"] = [{"evidenceId": e.id, "title": e.title, "text": e.text} for e in st["evidenceItems"]]
                item["fallbackSentence"] = st["controlled"]
                if st["senderFacts"]:
                    item["senderSays"] = st["senderFacts"]
            else:
                item["controlledSentence"] = st["controlled"]
            payload["issues"].append(item)
        try:
            with t.stage("draft"):
                d = await self._call(t, "draft", self.s.model_draft, prompts.DRAFT, payload, prompts.DRAFT_SCHEMA)
        except (ModelError, BudgetExceeded):
            for st in states:
                if st["action"] == "REPLY_DIRECTLY":
                    st["answerability"] = "NOT_ASSESSED"
            return "DEGRADED", {"safety": "NOT_PRODUCED", "findings": ["Reply draft could not be produced."]}

        text = d.get("replyText", "")
        by_id = {i.get("issueId"): i for i in d.get("issues", [])}
        findings, claims, covers = [], [], []
        ntext = _norm(text)
        for st in states:
            if st["action"] != "REPLY_DIRECTLY":
                continue
            di = by_id.get(st["issueId"], {})
            allowed = {e.id for e in st["evidenceItems"]}
            good = [c for c in di.get("claims", []) if c.get("text") and set(c.get("evidenceIds", [])) & allowed]
            if di.get("answered") and good:
                for c in good:
                    bad = set(c["evidenceIds"]) - allowed
                    if bad:
                        findings.append(f"{st['issueId']}: a statement cites a source not given for this question.")
                    if _norm(c["text"]) not in ntext:
                        findings.append(f"{st['issueId']}: a sourced statement was changed in the draft.")
                    claims.append({"issueId": st["issueId"], "text": c["text"], "evidenceIds": [e for e in c["evidenceIds"] if e in allowed]})
                cited = {e for c in good for e in c["evidenceIds"]}
                st["evidenceItems"] = [e for e in st["evidenceItems"] if e.id in cited]
                st["answerability"] = "SUFFICIENT"
                covers.append(st["issueId"])
            else:
                st["answerability"] = "INSUFFICIENT"
                st["evidenceItems"] = []
                self._set(st, "MANUAL_HANDLING", "Approved knowledge does not answer this question.")
        for st in states:
            if st["action"] != "REPLY_DIRECTLY" and _norm(st["controlled"]) not in ntext:
                findings.append(f"{st['issueId']}: the required sentence for this action is missing from the draft.")
        if _norm(self.tpl["sign_off"]) not in ntext:
            findings.append("The sign-off is missing or changed.")

        verdict = "BLOCKED" if findings else "SAFE_TO_REVIEW"
        if findings:
            t.skip("verify", "blocked by rule checks")
        else:
            vp = {"draft": text, "issues": [
                {"issueId": st["issueId"], "action": st["action"],
                 **({"claims": [{"text": c["text"], "evidence": [{"evidenceId": e.id, "text": e.text} for e in st["evidenceItems"] if e.id in c["evidenceIds"]]} for c in claims if c["issueId"] == st["issueId"]]}
                    if st["action"] == "REPLY_DIRECTLY" else {"controlledSentence": st["controlled"]})}
                for st in states]}
            try:
                with t.stage("verify"):
                    v = await self._call(t, "verify", self.s.model_verify, prompts.VERIFY, vp, prompts.VERIFY_SCHEMA)
                verdict = v.get("verdict", "BLOCKED")
                findings = [(f"{f['issueId']}: " if f.get("issueId") else "") + f["problem"] for f in v.get("findings", []) if verdict == "BLOCKED"]
            except (ModelError, BudgetExceeded):
                return "DEGRADED", {"text": text, "coversIssueIds": covers, "claims": claims, "safety": "BLOCKED",
                                    "findings": ["Verification could not run; staff must check the draft in full."]}
        return "SUCCEEDED", {"text": text, "coversIssueIds": covers, "claims": claims, "safety": verdict, "findings": findings}

    # ---------- staff re-check ----------

    async def recheck(self, prep: Prepared, previous: dict, change, run_id, received_at):
        t = Tracker(self.s.max_input_tokens_per_email)
        prev_issues = previous.get("issues") or []
        target = next((i for i in prev_issues if i.get("issueId") == change.issueId), None)

        def rejected(reason):
            out = {k: v for k, v in previous.items() if k != "signature"}
            out["runId"] = run_id
            out["recheck"] = {"status": "REJECTED", "reason": reason, "previousRunId": previous.get("runId"), "change": change.model_dump(exclude_none=True)}
            return out

        if target is None:
            return rejected("issueId is not in the previous result.")
        states = []
        for i in prev_issues:
            st = {**i, "query": i["summary"], "mentions": [], "senderFacts": [], "evidenceItems": [], "missingInformation": list(i.get("missingInformation", [])),
                  "handling": self.reg.routing.get(i["intent"], self.reg.routing["OTHER"])["handling"]}
            if st["action"] == "REPLY_DIRECTLY":
                st["evidenceItems"] = [it for it in self.kb.items if it.id in {e["evidenceId"] for e in i.get("evidence", [])}]
            self._set(st, st["action"], st["reason"])
            if i.get("owner"):
                st["owner"] = i["owner"]
            states.append(st)
        st = next(s for s in states if s["issueId"] == change.issueId)
        note = f" Staff note: {change.staffNote}" if change.staffNote else ""

        if change.action == "REPLY_DIRECTLY":
            if st["intent"] in RECORDS:
                return rejected(f"This question needs {RECORDS[st['intent']]}, which the engine cannot see; a direct reply would have no source.")
            if st["answerability"] == "INSUFFICIENT":
                return rejected("Approved knowledge does not answer this question; a direct reply would have no source.")
            if st["intent"] in NEEDS_PROGRAMME and st["programme"]["status"] != "RESOLVED":
                return rejected("The programme is unclear, so a direct reply could give the wrong programme's facts.")
            if not st["evidenceItems"]:
                st["evidenceItems"] = self.kb.search(f"{st['summary']} {st['topic']}", st["programme"].get("programmeId"), topic=st["intent"])
            if not st["evidenceItems"]:
                return rejected("Approved knowledge has nothing on this question.")
            self._set(st, "REPLY_DIRECTLY", "Changed by staff; answered from approved knowledge." + note)
        elif change.action == "REFER_TO_TEAM":
            team = self.reg.teams.get(change.ownerTeamId)
            if team is None:
                return rejected(f"Unknown team '{change.ownerTeamId}'.")
            st["owner"] = {"teamId": team.id, "name": team.name, "inbox": team.inbox, "routingBasis": "Changed by staff"}
            st["evidenceItems"], st["answerability"] = [], "NOT_ASSESSED"
            self._set(st, "REFER_TO_TEAM", "Changed by staff." + note)
        else:
            st["evidenceItems"], st["answerability"] = [], "NOT_ASSESSED"
            self._set(st, change.action, "Changed by staff." + note)

        health, reply = await self._draft_and_verify(t, states, prep.message)
        if change.action == "REPLY_DIRECTLY" and st["answerability"] != "SUFFICIENT":
            return rejected("Approved knowledge does not answer this question; a direct reply would have no source.")
        info = previous.get("message") or {}
        extra = {"recheck": {"status": "ACCEPTED", "previousRunId": previous.get("runId"), "change": change.model_dump(exclude_none=True)}}
        return self._result(prep.request, run_id, received_at, t, health, info, states, reply, prep.attachments, extra)

    # ---------- result ----------

    def _issue_out(self, st):
        ev = [{"evidenceId": e.id, "authority": "APPROVED_KNOWLEDGE", "title": e.title, "url": e.url, "version": e.version, "excerpt": e.text[:600]} for e in st["evidenceItems"]]
        prog = {k: v for k, v in st["programme"].items() if k in ("status", "programmeId", "name", "candidates")}
        return {"issueId": st["issueId"], "summary": st["summary"], "topic": st["topic"], "intent": st["intent"], "programme": prog,
                "owner": st.get("owner"), "answerability": st["answerability"], "action": st["action"], "reason": st["reason"],
                "missingInformation": st["missingInformation"], "evidence": ev}

    def _result(self, req, run_id, received_at, t, health, info, states, reply, attachments, extra=None):
        extra = dict(extra or {})
        recheck = extra.pop("recheck", None)
        issues = [self._issue_out(s) for s in states]
        counts = {a: sum(1 for i in issues if i["action"] == a) for a in ("REPLY_DIRECTLY", "REFER_TO_TEAM", "ASK_CLARIFICATION", "MANUAL_HANDLING")}
        notes = []
        for s in states:
            if s["action"] == "REFER_TO_TEAM":
                prog = s["programme"].get("name") or "not identified"
                notes.append({"issueId": s["issueId"], "teamId": s["owner"]["teamId"],
                              "text": self.tpl["handoff_note"].format(programme=prog, summary=s["summary"], reason=s["reason"])})
        return {
            "schemaVersion": "v0", "runId": run_id, "requestId": req.requestId, "status": "COMPLETED", "runHealth": health,
            "message": info, "summary": {"issueCount": len(issues), "countsByAction": counts, **extra},
            "issues": issues, "reply": reply or {"safety": "NOT_PRODUCED"}, "handoffNotes": notes, "attachments": attachments,
            "recheck": recheck,
            "trace": {"requestId": req.requestId, "runId": run_id, "engineVersion": ENGINE_VERSION, "knowledgeVersion": self.kb.version,
                      "configVersion": self.config_version, "receivedAt": received_at,
                      "completedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "stages": t.stages},
            "_usage": {"input": t.usage.input, "output": t.usage.output, "thinking": t.usage.thinking},  # internal; stripped before returning
        }
