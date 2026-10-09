"""Mock knowledge base (M1) and retrieval.

Format, one or more YAML files in data/knowledge/: `items:` each with id, programmeId (null for general
items), topic, title, text, url, version. M1 (crawl of public NTU PaCE pages) writes the same format.
Retrieval is BM25 over title + text, limited to the resolved programme plus general items.
"""
import hashlib
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import yaml

_STOP = set("a an and are as at be by can do does for from how i in is it my of on or the to what when where which who will with you your".split())


def tokens(text):
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOP]


@dataclass
class Item:
    id: str
    programme_id: str | None
    topic: str
    title: str
    text: str
    url: str | None
    version: str | None


class KnowledgeBase:
    def __init__(self, folder: Path):
        files = sorted(Path(folder).glob("*.yaml"))
        self.items: list[Item] = []
        h = hashlib.sha256()
        for f in files:
            raw = f.read_bytes()
            h.update(raw)
            for it in (yaml.safe_load(raw) or {}).get("items", []):
                self.items.append(Item(it["id"], it.get("programmeId"), it.get("topic", "GENERAL"), it["title"], it["text"].strip(), it.get("url"), str(it.get("version", ""))))
        self.version = "kb-" + h.hexdigest()[:10]
        self._docs = [tokens(i.title + " " + i.text) for i in self.items]
        self._df = Counter(w for d in self._docs for w in set(d))
        self._avg = sum(map(len, self._docs)) / max(1, len(self._docs))

    def _bm25(self, q, i, k1=1.4, b=0.75):
        doc = self._docs[i]
        tf = Counter(doc)
        n = len(self.items)
        s = 0.0
        for w in q:
            if w not in tf:
                continue
            idf = math.log(1 + (n - self._df[w] + 0.5) / (self._df[w] + 0.5))
            s += idf * tf[w] * (k1 + 1) / (tf[w] + k1 * (1 - b + b * len(doc) / self._avg))
        return s

    def search(self, query, programme_id=None, topic=None, k=4):
        """Top items for the query. With a programme, other programmes' items are excluded."""
        q = tokens(query)
        scored = []
        for i, it in enumerate(self.items):
            if it.programme_id and it.programme_id != programme_id:
                continue
            s = self._bm25(q, i)
            if topic and it.topic == topic:
                s *= 1.5
            if programme_id and it.programme_id == programme_id:
                s *= 1.3
            if s > 0:
                scored.append((s, it))
        scored.sort(key=lambda x: -x[0])
        return [it for _, it in scored[:k]]
