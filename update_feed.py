"""Fetch and parse Tingsaker 1st-grade weekly plans for the TRMNL feed."""

import argparse
import io
import json
import logging
import re
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from docx import Document
from pypdf import PdfReader

VERSION = "3.3.1"
ARCHIVE_URL = "https://www.tingsakerskole.no/?show=field&fid=1369&sort=2&showfrom=0&showcount=-1"
DAYS = ["mandag", "tirsdag", "onsdag", "torsdag", "fredag"]
ALL_DAYS = DAYS + ["lørdag", "søndag"]
OSLO = ZoneInfo("Europe/Oslo")
UA = f"tingsaker-trmnl-plugin/{VERSION}"

# These are labels used in the school's weekly plans to explicitly identify
# the homework column. We intentionally do not guess ordinary school text.
HOMEWORK_LABEL_RE = re.compile(
    r"\b("
    r"Leksemappa|Leksemappen|Leselekse|Lesemappa|"
    r"Ukelekse|Ukeleksse|Ukeleksa|"
    r"Lesebok(?:\s+\d+)?|Lekse"
    r")\s*:\s*",
    re.I,
)
INFO_HEADER_RE = re.compile(r"Informasjon\s+til\s+hjemmet\s*:?", re.I)
SIGNOFF_RE = re.compile(r"\b(?:Ha\s+ei\s+fin\s+uke|Med\s+vennlig\s+hilsen)\b", re.I)
DAY_RE = re.compile(r"\b(mandag|tirsdag|onsdag|torsdag|fredag)\b", re.I)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def norm(value: str) -> str:
    value = value.replace("\u00a0", " ")
    return re.sub(r"\s+", " ", value).strip()


def fetch(url: str) -> bytes:
    response = requests.get(url, headers={"User-Agent": UA}, timeout=30)
    response.raise_for_status()
    return response.content


def archive_links(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    found = []

    for anchor in soup.find_all("a", href=True):
        text = norm(anchor.get_text(" ", strip=True))
        href = urljoin(ARCHIVE_URL, anchor["href"])

        match = re.search(r"\buke\s*(\d{1,2})\b", text, re.I)

        if not match:
            match = re.search(r"\buke[_ -]?(\d{1,2})\b", href, re.I)

        if match:
            week = int(match.group(1))
        elif re.fullmatch(r"\d{1,2}", text):
            week = int(text)
        else:
            continue

        if 1 <= week <= 53:
            found.append({
                "week": week,
                "text": text,
                "url": href,
            })

    unique = []
    seen = set()

    for item in found:
        key = (item["week"], item["url"])
        if key not in seen:
            seen.add(key)
            unique.append(item)

    return unique

def choose_week(links: list[dict], current_week: int) -> dict:
    if not links:
        raise RuntimeError("Fant ingen ukeplan-lenker i arkivet.")

    eligible = [item for item in links if item["week"] <= current_week]
    if not eligible:
        raise RuntimeError(
            f"Fant ukeplaner, men ingen for inneværende uke eller tidligere "
            f"(uke {current_week})."
        )
    return max(eligible, key=lambda item: item["week"])


def extract_pdf(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract_docx(data: bytes) -> str:
    document = Document(io.BytesIO(data))
    parts = [p.text for p in document.paragraphs if p.text.strip()]
    for table in document.tables:
        for row in table.rows:
            parts.append(" | ".join(cell.text for cell in row.cells))
    return "\n".join(parts)


def extract_text(url: str, data: bytes) -> str:
    suffix = url.lower().split("?")[0]
    if suffix.endswith(".pdf"):
        return extract_pdf(data)
    if suffix.endswith(".docx"):
        return extract_docx(data)

    # Some archive links do not expose their file type. Detect by magic bytes.
    if data.startswith(b"%PDF"):
        return extract_pdf(data)
    if data[:2] == b"PK":
        return extract_docx(data)

    # Last-resort compatibility with older links.
    try:
        return extract_pdf(data)
    except Exception as pdf_error:
        try:
            return extract_docx(data)
        except Exception as docx_error:
            raise RuntimeError("Klarte ikke å lese dokumentet som PDF eller DOCX.") from pdf_error


def _lines(text: str) -> list[str]:
    return [norm(line) for line in text.splitlines() if norm(line)]


def _day_positions(lines: list[str]) -> dict[str, int]:
    header_i = next(
        (i for i, line in enumerate(lines)
         if "DAG" in line.upper() and "LEKSE" in line.upper()),
        None,
    )
    start = header_i + 1 if header_i is not None else 0

    positions = {}
    for i in range(start, len(lines)):
        match = DAY_RE.search(lines[i])
        if match:
            day = match.group(1).lower()
            positions.setdefault(day, i)
    return positions


def _clean_homework(value: str) -> str:
    value = HOMEWORK_LABEL_RE.sub("", value)
    value = re.sub(r"^[|:;\-\s]+", "", value)
    return norm(value)


def extract_homework(text: str) -> dict[str, str]:
    """Extract explicitly labelled homework without inventing homework.

    The parser accepts several labels seen in Tingsaker plans, including
    Leksemappa, Leselekse, Lesemappa, Ukelekse and Lesebok N.
    """
    lines = _lines(text)
    positions = _day_positions(lines)
    if not positions:
        raise ValueError("Fant ingen ukedager i ukeplanen.")

    result = {day: "" for day in DAYS}
    ordered = sorted(positions.items(), key=lambda item: item[1])

    for index, (day, start) in enumerate(ordered):
        end = ordered[index + 1][1] if index + 1 < len(ordered) else len(lines)
        block = lines[start + 1:end]

        # Include the day line too: DOCX tables can place the homework label
        # on the same physical row as the weekday.
        candidates = [lines[start], *block]
        matches = []
        for line in candidates:
            for match in HOMEWORK_LABEL_RE.finditer(line):
                value = _clean_homework(line[match.start():])
                if value:
                    matches.append(value)

        if matches:
            # Deduplicate while preserving order.
            seen = set()
            result[day] = " ".join(
                value for value in matches
                if not (value in seen or seen.add(value))
            )

    if not any(result.values()):
        raise ValueError(
            "Fant ingen eksplisitt leksemarkør i ukeplanen. "
            "Stopper i stedet for å gjette."
        )
    return result


def extract_notes(text: str) -> dict[str, str]:
    """Extract only weekday-labelled notes under Informasjon til hjemmet."""
    notes = {day: "" for day in DAYS}
    match = INFO_HEADER_RE.search(text)
    if not match:
        return notes

    body = SIGNOFF_RE.split(text[match.end():], maxsplit=1)[0]
    label = re.compile(r"^\s*([A-ZÆØÅ][\wæøåÆØÅ]+)\s*:\s*(.*)$")
    current = None
    parts = {}

    for raw in body.splitlines():
        line = norm(raw)
        if not line:
            continue
        labelled = label.match(line)
        if labelled:
            current = labelled.group(1).lower()
            parts[current] = [labelled.group(2)]
        elif current:
            parts[current].append(line)

    for day in DAYS:
        if day in parts:
            notes[day] = norm(" ".join(parts[day]))
    return notes


def now_oslo() -> datetime:
    return datetime.now(OSLO)


def day_name(value: date) -> str:
    return ALL_DAYS[value.weekday()]


def next_with_homework(homework: dict[str, str], today: date) -> tuple[str, str]:
    for delta in range(1, 8):
        target = today + timedelta(days=delta)
        name = day_name(target)
        if name in homework and homework[name]:
            return name, homework[name]
    return "", ""


def build_data(
    week: int,
    homework: dict[str, str],
    source_url: str,
    notes: dict[str, str] | None = None,
) -> dict:
    notes = notes or {day: "" for day in DAYS}
    now = now_oslo()
    today_name = day_name(now.date())
    next_day, next_hw = next_with_homework(homework, now.date())

    return {
        "version": VERSION,
        "week": f"uke {week}",
        "today_day": today_name,
        "today_homework": homework.get(today_name, ""),
        "next_day": next_day,
        "next_homework": next_hw,
        "note": notes.get(today_name, ""),
        "next_note": notes.get(next_day, ""),
        "homework": homework,
        "notes": notes,
        "generated_at": now.isoformat(timespec="minutes"),
        "source": source_url,
    }


def validate_data(data: dict) -> None:
    required = {
        "version", "week", "today_day", "today_homework", "next_day",
        "next_homework", "note", "next_note", "homework", "notes",
        "generated_at", "source",
    }
    missing = required - data.keys()
    if missing:
        raise ValueError(f"Mangler felt i data.json: {sorted(missing)}")

    if not re.fullmatch(r"uke \d{1,2}", str(data["week"])):
        raise ValueError("Ugyldig ukeformat.")
    if set(data["homework"]) != set(DAYS):
        raise ValueError("homework mangler én eller flere ukedager.")
    if set(data["notes"]) != set(DAYS):
        raise ValueError("notes mangler én eller flere ukedager.")

    for field in ("today_homework", "next_homework", "note", "next_note"):
        if not isinstance(data[field], str):
            raise ValueError(f"Feltet {field} må være tekst.")


def write_json_atomic(path: Path, data: dict) -> None:
    validate_data(data)
    path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temp_name = handle.name

    Path(temp_name).replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", help="Lokal PDF/DOCX for fixture/testing")
    parser.add_argument("--out", default="data.json")
    parser.add_argument("--archive", default=ARCHIVE_URL)
    parser.add_argument("--week", type=int)
    args = parser.parse_args()

    if args.pdf:
        source = Path(args.pdf)
        raw = source.read_bytes()
        text = extract_text(str(source), raw)
        week = args.week or 42
        source_url = str(source)
    else:
        html = fetch(args.archive).decode("utf-8", errors="replace")
        links = archive_links(html)
        current_week = args.week or now_oslo().isocalendar().week
        chosen = choose_week(links, current_week)
        log.info("Valgt uke %s: %s", chosen["week"], chosen["url"])
        raw = fetch(chosen["url"])
        text = extract_text(chosen["url"], raw)
        week = chosen["week"]
        source_url = chosen["url"]

    homework = extract_homework(text)
    result = build_data(week, homework, source_url, extract_notes(text))
    write_json_atomic(Path(args.out), result)
    log.info("Oppdatert %s for uke %s", args.out, week)


if __name__ == "__main__":
    main()
