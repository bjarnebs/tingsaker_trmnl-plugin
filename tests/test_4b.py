from update_feed import extract_4b_sections


def test_4b_keeps_lekser_and_husk_separate():
    text = """
    Mandag
    Lekser: Les side 12.
    Husk: Ta med gymtøy.
    Tirsdag
    Lekser: Gjør oppgave 1
    Husk: Husk bibliotekboka
    Onsdag
    Lekser: Les tre ganger
    Torsdag
    Husk: Turdag, kle deg etter været
    Fredag
    """
    result = extract_4b_sections(text)
    assert result["homework"]["mandag"] == "Les side 12."
    assert result["reminders"]["mandag"] == "Ta med gymtøy."
    assert result["homework"]["tirsdag"] == "Gjør oppgave 1"
    assert result["reminders"]["tirsdag"] == "Husk bibliotekboka"
    assert result["homework"]["onsdag"] == "Les tre ganger"
    assert result["homework"]["fredag"] == ""
    assert result["reminders"]["fredag"] == ""


def test_4b_multiline_cells_and_empty_fields():
    text = """
    Mandag
    Lekser: Les teksten
    to ganger hjemme.
    Husk:
    Tirsdag
    Lekser:
    Husk: Ta med boka
    og pennal.
    """
    result = extract_4b_sections(text)
    assert result["homework"]["mandag"] == "Les teksten to ganger hjemme."
    assert result["reminders"]["mandag"] == ""
    assert result["homework"]["tirsdag"] == ""
    assert result["reminders"]["tirsdag"] == "Ta med boka og pennal."


def test_4a_specific_notes_are_not_added_to_4b():
    text = """
    Mandag
    Lekser: Les side 4.
    Dette gjelder 4A: ta med ekstra ark.
    Husk: Ta med matpakke.
    """
    result = extract_4b_sections(text)
    assert "4A" not in result["homework"]["mandag"]
    assert "ekstra ark" not in result["homework"]["mandag"]
    assert result["reminders"]["mandag"] == "Ta med matpakke."


def test_4b_refuses_unlabelled_content():
    try:
        extract_4b_sections("Mandag Samling og tur. Tirsdag Kunst og håndverk.")
    except ValueError as exc:
        assert "Lekser/Husk" in str(exc)
    else:
        raise AssertionError("Parseren skal ikke gjette lekser eller husk")
