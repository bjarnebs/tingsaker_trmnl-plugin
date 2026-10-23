"""Add grade-aware and weekend-aware fields to the generated feed."""

import json
import sys
from pathlib import Path

import update_feed

DAYS = update_feed.DAYS
NEXT_WEEKDAY = {
    "mandag": "tirsdag",
    "tirsdag": "onsdag",
    "onsdag": "torsdag",
}


def revision(item: dict) -> int:
    import re
    match = re.search(r"/(\d+)-uke[_ -]?\d+\.(?:pdf|docx)(?:$|\?)", item["url"], re.I)
    return int(match.group(1)) if match else 0


def latest_for_week(links: list[dict], week: int) -> dict | None:
    candidates = [item for item in links if item["week"] == week]
    return max(candidates, key=revision) if candidates else None


def next_plan(archive_url: str, week: int) -> tuple[dict | None, dict | None]:
    html = update_feed.fetch(archive_url).decode("utf-8", errors="replace")
    links = update_feed.archive_links(html, archive_url)
    item = latest_for_week(links, week + 1)
    if not item:
        return None, None
    try:
        raw = update_feed.fetch(item["url"])
        text = update_feed.extract_text(item["url"], raw, layout=True)
        return item, {"text": text}
    except Exception:
        return item, None


def next_for(homework: dict[str, str], today: str, next_week_homework: dict[str, str] | None) -> tuple[str, str]:
    if today in NEXT_WEEKDAY:
        day = NEXT_WEEKDAY[today]
        return day, homework.get(day, "")
    if today == "torsdag":
        if next_week_homework is not None:
            return "mandag", next_week_homework.get("mandag", "")
        return "helg", ""
    return "helg", ""


def main(path: str = "data.json") -> None:
    target = Path(path)
    data = json.loads(target.read_text(encoding="utf-8"))
    grade_1 = data["grade_1"]
    current_week = int(grade_1["week"].split()[-1])
    today = grade_1["today_day"]

    next_week_1 = None
    next_week_4b = None
    if today == "torsdag":
        _, payload = next_plan(update_feed.ARCHIVE_URL, current_week)
        if payload:
            next_week_1 = update_feed.extract_homework(payload["text"])
        _, payload = next_plan(update_feed.ARCHIVE_4B_URL, current_week)
        if payload:
            next_week_4b = update_feed.extract_4b_sections(payload["text"])["homework"]

    next_day, next_homework = next_for(grade_1["homework"], today, next_week_1)
    grade_1["next_day"] = next_day
    grade_1["next_homework"] = next_homework

    grade_4b = data.get("grade_4b")
    if grade_4b:
        hw4 = grade_4b.get("homework", {})
        next4_day, next4_hw = next_for(hw4, today, next_week_4b)
        grade_4b.update({
            "label": "4. klasse",
            "week": grade_4b.get("week") or grade_1["week"],
            "today_day": today,
            "today_homework": hw4.get(today, ""),
            "next_day": next4_day,
            "next_homework": next4_hw,
        })

    data["version"] = update_feed.VERSION
    serialized = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    # Validate the exact serialized payload before replacing the feed.
    json.loads(serialized)
    target.write_text(serialized, encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data.json")
