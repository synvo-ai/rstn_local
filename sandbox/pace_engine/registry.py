"""Mock programme registry and routing table (M2).

data/registry.yaml holds teams, programmes (with aliases and owning school) and routing rules by intent.
Programme resolution is deterministic: exact alias match first, then word overlap; several close
matches give AMBIGUOUS with candidates (scenario A4).
"""
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

# Words that say "this is a programme" but not which one.
_GENERIC = set("""the a an my your this that of in and for on programme program programmes course courses certificate cert
diploma graduate professional specialist module modules class classes ntu pace part time full""".split())


def _words(s):
    return [w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in _GENERIC]


def _norm(s):
    return " ".join(re.findall(r"[a-z0-9]+", s.lower()))


@dataclass
class Team:
    id: str
    name: str
    inbox: str | None


@dataclass
class Programme:
    id: str
    name: str
    aliases: list
    school_team: str
    status: str


class Registry:
    def __init__(self, path: Path):
        raw = Path(path).read_bytes()
        d = yaml.safe_load(raw)
        self.version = "reg-" + hashlib.sha256(raw).hexdigest()[:10]
        self.teams = {t["id"]: Team(t["id"], t["name"], t.get("inbox")) for t in d["teams"]}
        self.programmes = {p["id"]: Programme(p["id"], p["name"], p.get("aliases", []), p["schoolTeam"], p.get("status", "ACTIVE")) for p in d["programmes"]}
        self.routing = d["routing"]  # intent -> {owner: team id | "SCHOOL", handling: ANSWER_DESK | REFER | INSTITUTIONAL | MANUAL}
        self.answer_desk = d["answerDesk"]

    def resolve(self, mentions):
        """Resolve the sender's programme mentions to one programme, several candidates, or none."""
        if not mentions:
            return {"status": "UNRESOLVED", "candidates": []}
        exact, scores = set(), {}
        for m in mentions:
            nm, mw = _norm(m), set(_words(m))
            for p in self.programmes.values():
                names = [p.name] + p.aliases
                if any(_norm(n) and (_norm(n) == nm or re.search(rf"\b{re.escape(_norm(n))}\b", nm)) for n in names):
                    exact.add(p.id)
                    continue
                if not mw:
                    continue
                best = max(len(mw & set(_words(n))) / len(mw) for n in names)
                scores[p.id] = max(scores.get(p.id, 0), best)
        if len(exact) == 1:
            return self._resolved(next(iter(exact)))
        if len(exact) > 1:
            return {"status": "AMBIGUOUS", "candidates": [self._cand(i) for i in sorted(exact)]}
        close = sorted((i for i, s in scores.items() if s >= 0.5), key=lambda i: -scores[i])
        others = [i for i, s in scores.items() if s > 0 and i not in close]
        full = [i for i in close if scores[i] >= 0.99]
        if len(full) == 1 or (len(close) == 1 and not others):
            return self._resolved(full[0] if full else close[0])
        if close:
            return {"status": "AMBIGUOUS", "candidates": [self._cand(i) for i in close[:5]]}
        return {"status": "UNRESOLVED", "candidates": []}

    def _cand(self, pid):
        return {"programmeId": pid, "name": self.programmes[pid].name}

    def _resolved(self, pid):
        return {"status": "RESOLVED", "programmeId": pid, "name": self.programmes[pid].name, "candidates": []}

    def route(self, intent, programme_id):
        """Owning team and handling for one issue."""
        rule = self.routing.get(intent) or self.routing["OTHER"]
        owner = rule["owner"]
        basis = intent
        if owner == "SCHOOL":
            if programme_id:
                owner = self.programmes[programme_id].school_team
                basis = f"{self.programmes[programme_id].name} · {intent}"
            else:
                owner = rule.get("fallbackOwner", self.answer_desk)
        elif programme_id:
            basis = f"{self.programmes[programme_id].name} · {intent}"
        team = self.teams[owner]
        return team, rule["handling"], f"{basis} → {team.name}"
