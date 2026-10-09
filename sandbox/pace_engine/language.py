"""Phase 1 handles English only (RSTN, 8 Oct). A cheap check before any model call; the understand step's
own language field is the backstop for cases this misses (e.g. Malay or Indonesian in Latin script)."""
import re

_STOP = set("""a about above after again all am an and any are as at be because been before being below between both but by can
could did do does doing down during each few for from further had has have having he her here hers him his how i if in into is it
its just me more most my no nor not now of off on once only or other our out over own please same she should so some such than that
the their them then there these they this those through to too under until up very was we were what when where which while who why
will with would you your thank thanks regards dear hi hello""".split())


def check(text):
    """Return (is_english, detail). Unsure cases count as English and are left to the model."""
    letters = [c for c in text if c.isalpha()]
    if len(letters) < 20:
        return True, "too short to tell"
    latin = sum(1 for c in letters if c.isascii())
    if latin / len(letters) < 0.6:
        return False, "mostly non-Latin script"
    words = re.findall(r"[a-zA-Z']+", text.lower())
    if len(words) >= 15:
        share = sum(1 for w in words if w in _STOP) / len(words)
        if share < 0.12:
            return False, "few English function words"
    return True, "English"
