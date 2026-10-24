from detect_4b_week import detect_mislabelled_4b


def test_promotes_different_late_duplicate_when_dates_match_current_week():
    links = [
        {"week": 43, "url": "old.pdf", "position": 1},
        {"week": 43, "url": "new.pdf", "position": 2},
    ]
    texts = {
        "old.pdf": "Mandag\nLekser: Les side 10.\n",
        "new.pdf": "Mandag\nLekser: Les side 20.\n26.10.2026",
    }

    chosen, warning = detect_mislabelled_4b(links, 44, texts.__getitem__)

    assert chosen["url"] == "new.pdf"
    assert "uke 44" in warning


def test_different_duplicate_without_date_only_warns():
    links = [
        {"week": 43, "url": "old.pdf", "position": 1},
        {"week": 43, "url": "new.pdf", "position": 2},
    ]
    texts = {
        "old.pdf": "Mandag\nLekser: Les side 10.\n",
        "new.pdf": "Mandag\nLekser: Les side 20.\n",
    }

    chosen, warning = detect_mislabelled_4b(links, 44, texts.__getitem__)

    assert chosen is None
    assert "beholder uke 43" in warning


def test_identical_duplicate_is_ignored():
    links = [
        {"week": 43, "url": "old.pdf", "position": 1},
        {"week": 43, "url": "new.pdf", "position": 2},
    ]
    text = "Mandag\nLekser: Les side 10.\n26.10.2026"
    texts = {"old.pdf": text, "new.pdf": text}

    chosen, warning = detect_mislabelled_4b(links, 44, texts.__getitem__)

    assert chosen is None
    assert warning is None


def test_existing_current_week_never_gets_overridden():
    links = [
        {"week": 43, "url": "old.pdf", "position": 1},
        {"week": 43, "url": "new.pdf", "position": 2},
        {"week": 44, "url": "current.pdf", "position": 3},
    ]

    chosen, warning = detect_mislabelled_4b(links, 44, lambda item: "unused")

    assert chosen is None
    assert warning is None
