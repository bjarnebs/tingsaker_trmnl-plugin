import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
FIXTURE = Path(__file__).parent / "fixtures" / "uke_42-solidaritetsuka.pdf"


def run_fixture(tmp_path):
    out = tmp_path / "data.json"
    subprocess.run(
        [sys.executable, str(ROOT / "update_feed.py"),
         "--pdf", str(FIXTURE), "--week", "42", "--out", str(out)],
        check=True,
    )
    return json.loads(out.read_text(encoding="utf-8"))


def test_week42(tmp_path):
    data = run_fixture(tmp_path)
    hw = data["grade_1"]["homework"]

    assert "Les første side av leseleksa" in hw["mandag"]
    assert "Les tegneserien tre ganger" in hw["tirsdag"]
    assert "Gjør skriveoppgavene" in hw["onsdag"]
    assert "tre ting på b" in hw["torsdag"]
    assert hw["fredag"] == ""

    assert "Ta derfor med både mat og frukt" in data["grade_1"]["reminders"]["onsdag"]
    assert data["grade_1"]["reminders"]["mandag"] == ""
    assert "Sponsorskjema" not in data["grade_1"]["reminders"]["onsdag"]
    assert "due" not in data
    assert not ({"week", "homework", "notes", "today_homework", "today_day", "source"} & data.keys())
    assert data["grade_1"]["label"] == "1. klasse"
    assert not ({"week", "homework", "notes", "today_homework", "today_day", "source"} & data.keys())
    assert data["grade_1"]["label"] == "1. klasse"


def test_variant_labels_are_supported():
    from update_feed import extract_homework

    text = """
    DAG På skolen Lekse
    Mandag Samling Lesebok 1: Les side 3.
    Tirsdag Lekse Ukelekse: Øv på bokstavene.
    Onsdag Stasjoner Ukeleksse: Les hjemme.
    Torsdag Leksemappa: Les teksten.
    Fredag Gym
    """
    hw = extract_homework(text)
    assert hw["mandag"] == "Les side 3."
    assert hw["tirsdag"] == "Øv på bokstavene."
    assert hw["onsdag"] == "Les hjemme."
    assert hw["torsdag"] == "Les teksten."
    assert hw["fredag"] == ""


def test_no_label_means_fail():
    from update_feed import extract_homework

    text = """
    DAG På skolen Lekse
    Mandag Samling Norsk
    Tirsdag Lek Stasjoner
    Onsdag Gym
    Torsdag Kunst
    Fredag Fellessamling
    """
    try:
        extract_homework(text)
    except ValueError as exc:
        assert "eksplisitt leksemarkør" in str(exc)
    else:
        raise AssertionError("Parseren skal ikke gjette lekser")


def test_week_selection_never_jumps_into_future():
    from update_feed import choose_week

    links = [
        {"week": 41, "url": "41.pdf"},
        {"week": 43, "url": "43.pdf"},
        {"week": 44, "url": "44.pdf"},
    ]
    assert choose_week(links, 43)["week"] == 43
    assert choose_week(links, 42)["week"] == 41


def test_atomic_output_validation(tmp_path):
    from update_feed import write_json_atomic

    path = tmp_path / "data.json"
    data = {
        "version": "3.5.1", "generated_at": "2026-10-20T21:00+02:00",
        "grade_1": {
            "label": "1. klasse", "week": "uke 42", "today_day": "mandag",
            "today_homework": "", "next_day": "", "next_homework": "",
            "homework": {d: "" for d in ["mandag", "tirsdag", "onsdag", "torsdag", "fredag"]},
            "reminders": {d: "" for d in ["mandag", "tirsdag", "onsdag", "torsdag", "fredag"]}, "source": "test",
        },
    }
    write_json_atomic(path, data)
    assert json.loads(path.read_text())["version"] == "3.5.1"


def test_sunday_preview_uses_monday_homework_and_reminders(monkeypatch):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    import update_feed
    from update_feed import build_data

    # Make this test genuinely run as a Sunday preview, regardless of CI day.
    sunday = datetime(2026, 10, 25, 12, 0, tzinfo=ZoneInfo("Europe/Oslo"))
    monkeypatch.setattr(update_feed, "now_oslo", lambda: sunday)

    homework = {day: "" for day in ["mandag", "tirsdag", "onsdag", "torsdag", "fredag"]}
    reminders = {day: "" for day in homework}
    homework["mandag"] = "Ta med gymtøy"
    reminders["mandag"] = "Husk innesko"

    data = build_data(44, homework, "test", reminders, preview_next_week=True)
    grade = data["grade_1"]
    assert grade["week"] == "uke 44"
    assert grade["today_day"] == "søndag"
    assert grade["today_homework"] == "Leksefri"
    assert grade["next_day"] == "mandag"
    assert grade["next_homework"] == "Ta med gymtøy"
    assert grade["reminders"]["mandag"] == "Husk innesko"


def test_normal_week_does_not_preview_monday():
    from update_feed import build_data

    homework = {day: "" for day in ["mandag", "tirsdag", "onsdag", "torsdag", "fredag"]}
    data = build_data(43, homework, "test")
    from update_feed import day_name, now_oslo
    assert data["grade_1"]["today_day"] == day_name(now_oslo().date())



def test_weekend_labels_are_real_days_and_homework_free():
    from datetime import date
    from update_feed import next_with_homework

    homework = {day: "" for day in ["mandag", "tirsdag", "onsdag", "torsdag", "fredag"]}
    assert next_with_homework(homework, date(2026, 10, 24)) == ("søndag", "Leksefri")
    assert next_with_homework(homework, date(2026, 10, 25)) == ("mandag", "")
    assert next_with_homework(homework, date(2026, 10, 23)) == ("lørdag", "Leksefri")
