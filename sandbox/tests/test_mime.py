from pathlib import Path

from pace_engine import language
from pace_engine.mime import parse_eml, parse_form, strip_quoted

EML = Path(__file__).resolve().parent.parent / "testpack" / "eml"


def test_html_only_with_quoted_history_and_logo():  # E8
    m = parse_eml((EML / "E8-01.eml").read_bytes(), 10 << 20)
    assert m.html_only
    assert "applications for the Graduate Diploma" in m.body
    assert "send me the brochure" not in m.body
    assert m.attachments[0].inline


def test_plain_quoted_reply_cut():  # E8
    new, quoted = strip_quoted("Thanks. One more question?\n\nOn Mon, 5 Oct 2026 at 10:12, X <x@y.z> wrote:\n> old question?\n")
    assert new == "Thanks. One more question?"
    assert "old question" in quoted


def test_outlook_header_cut():
    body = "New question here.\n\nFrom: PaCE <a@b.c>\nSent: Monday, 5 October 2026 10:00\nTo: me\nSubject: Re: x\n\nOld text"
    assert strip_quoted(body)[0] == "New question here."


def test_addresses_dropped():
    m = parse_eml((EML / "A2-01.eml").read_bytes(), 10 << 20)
    assert m.sender_name == "Priya Ramasamy"
    assert "@" not in (m.sender_name or "")


def test_form_drops_contact_fields():
    m = parse_form({"Name": "A B", "Email": "a@b.c", "Mobile": "+65 1", "Programme": "X", "Message": "When?"})
    assert m.body == "When?" and m.sender_name == "A B"
    assert m.form_fields == {"Programme": "X"}


def test_language():  # A10
    assert language.check("Hello, when does the next intake for the data analytics course start? Thank you.")[0]
    assert not language.check("您好，我想了解应用数据分析研究生证书课程的下一期开课时间，以及报名截止日期。")[0]
    assert not language.check("Saya ingin bertanya tentang yuran untuk Sijil Profesional dalam Operasi Keselamatan Siber. Adakah saya boleh menggunakan kredit SkillsFuture untuk membayar yuran tersebut?")[0]
