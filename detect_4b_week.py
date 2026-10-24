"""Detect likely mislabelled 4B weekly plans and repair data.json."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from update_feed import (
    ARCHIVE_4B_URL,
    DAYS,
    extract_4b_sections,
    extract_text,
    fetch,
    next_with_homework,
    norm,
    now_oslo,
)

DATE_RE = re.compile(r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b")
WEEK_RE = re.compile(r"\buke\s*(\d{1,2})\b", re.I)


def archive_candidates(html: str, base_url: str = ARCHIVE_4B_URL) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    found = []
    for position, anchor in enumerate(soup.find_all("a", href=True)):
        text = norm(anchor.get_text(" ", strip=True))
        href = urljoin(base_url, anchor["href"])
        match = WEEK_RE.search(text) or WEEK_RE.search(href)
        if not match and re.fullmatch(r"\d{1,2}", text):
            match = re.match(r"(\d{1,2})", text)
        if not match:
            continue
        week = int(match.group(1))
        if 1 <= week <= 53:
            found.append({"week": week, "text": text, "url": href, "position": position})
    unique = []
    seen = set()
    for item in found:
        key = (item["week"], item["url"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def content_signature(text: str) -> str:
    sections = extract_4b_sections(text)
    parts = []
    for section in ("homework", "reminders"):
        for day in DAYS:
            parts.append(f"{section}:{day}:{norm(sections[section][day]).lower()}")
    return "\n".join(parts)


def document_dates(text: str) -> set:
    dates = set()
    for day, month, year in DATE_RE.findall(text):
        try:
            dates.add(datetime(int(year), int(month), int(day)).date())
        except ValueError:
            pass
    return dates


def detect_mislabelled_4b(links: list[dict], current_week: int, load_text) -> tuple[dict | None, str | None]:
    """Return a likely next-week candidate and a human-readable warning.

    The school archive occasionally contains two documents with the same week
    label. If the archive's newest same-week document is materially different,
    and its embedded dates belong to the current ISO week, treat the label as a
    likely typo. This is deliberately conservative: without date evidence we
    only warn and keep the labelled week.
    """
    current = [item for item in links if item["week"] == current_week]
    if current:
        return None, None

    previous = current_week - 1
    candidates = [item for item in links if item["week"] == previous]
    if len(candidates) < 2:
        return None, None

    older, newer = candidates[-2], candidates[-1]
    old_text = load_text(older["url"])
    new_text = load_text(newer["url"])
    if content_signature(old_text) == content_signature(new_text):
        return None, None

    dates = document_dates(new_text)
    date_weeks = {d.isocalendar().week for d in dates if d.year >= 2020}
    if current_week not in date_weeks:
        return None, (
            f"4B: fant to ulike dokumenter merket uke {previous}, men siste "
            f"kandidat har ingen tydelig dato i uke {current_week}; beholder uke {previous}."
        )

    warning = (
        f"4B: siste arkivdokument er merket uke {previous}, men innholdet er "
        f"ulikt forrige versjon og datoene peker på uke {current_week}; "
        f"bruker det som sannsynlig feilmerket uke {current_week}."
    )
    return newer, warning


def repair_data(data_path: Path, current_week: int, archive_url: str = ARCHIVE_4B_URL) -> bool:
    data = json.loads(data_path.read_text(encoding="utf-8"))
    html = fetch(archive_url).decode("utf-8", errors="replace")
    links = archive_candidates(html, archive_url)

    def load_text(url):
        raw = fetch(url)
        return extract_text(url, raw, layout=True)

    chosen, warning = detect_mislabelled_4b(links, current_week, load_text)
    if warning:
        print(f"::warning title=4B ukeplan::{warning}")
    if not chosen:
        return False

    text = load_text(chosen["url"])
    sections = extract_4b_sections(text)
    grade = data["grade_4b"]
    grade["week"] = f"uke {current_week}"
    grade["homework"] = sections["homework"]
    grade["reminders"] = sections["reminders"]
    grade["source"] = chosen["url"]
    grade["today_homework"] = sections["homework"].get(grade["today_day"], "")
    next_day, next_homework = next_with_homework(sections["homework"], now_oslo().date())
    grade["next_day"] = next_day
    grade["next_homework"] = next_homework
    data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data.json")
    parser.add_argument("--week", type=int, required=True)
    args = parser.parse_args()
    repair_data(Path(args.data), args.week)


if __name__ == "__main__":
    main()
