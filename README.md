# Tingsaker – lekser for TRMNL

Automatisk oppdatert leksefeed fra Tingsaker skole for **1. trinn og 4B**, laget for visning på TRMNL.

## Innhold

- [Funksjoner](#funksjoner)
- [Slik fungerer oppdateringen](#slik-fungerer-oppdateringen)
- [Dataformat](#dataformat)
- [Tester](#tester)
- [TRMNL-oppsett](#trmnl-oppsett)
- [Prosjektfiler](#prosjektfiler)

## Funksjoner

- Henter og tolker ukeplaner for 1. trinn og 4B fra skolens arkiv.
- Støtter PDF og DOCX, også når filendelsen mangler, ved å undersøke filsignaturen.
- Kjenner igjen leksemarkører som `Leksemappa:`, `Leselekse:`, `Lesemappa:`, `Ukelekse:` og `Lesebok 1:`.
- Holder lekser og «Husk»-meldinger adskilt.
- Bruker `Europe/Oslo` ved beregning av dato og ukedag, inkludert overgangen mellom sommer- og vintertid.
- Velger den nyeste publiserte ukeplanen som ikke ligger etter gjeldende ISO-uke.
- Gjetter ikke lekser når tydelige leksemarkører mangler.
- Validerer `data.json` og skriver filen atomisk, slik at en mislykket oppdatering ikke erstatter forrige gyldige feed.

## Slik fungerer oppdateringen

GitHub Actions kjører tester og oppdaterer feeden automatisk én gang i døgnet. Workflowen kan også startes manuelt fra **Actions → Update Tingsaker homework → Run workflow**.

Planlagt kjøring er satt til **05:15 UTC**. Scriptet bruker likevel `Europe/Oslo` for lokal dato og ukedag.

Arkivkontrollene tester dokumentene som er lenket fra ukeplanarkivene for begge klassene. Hvis en arkivfil ikke kan behandles, feiler den aktuelle kontrollen, slik at problemer blir synlige i GitHub Actions.

## Dataformat

TRMNL-data publiseres i `data.json`. Klassefeltene ligger under hvert sitt objekt:

| Felt | Innhold |
| --- | --- |
| `grade_1.homework` | Lekser for 1. trinn |
| `grade_1.reminders` | «Husk»-meldinger for 1. trinn |
| `grade_1.today_day` / `grade_1.today_homework` | Dagens ukedag og lekser for 1. trinn |
| `grade_1.next_day` / `grade_1.next_homework` | Neste ukedag og lekser for 1. trinn |
| `grade_4b.homework` | Lekser for 4B |
| `grade_4b.reminders` | «Husk»-meldinger for 4B |
| `grade_4b.source` | Kilde til ukeplanen for 4B |
| Dagsfelter under `grade_4b` | Dagens og neste dags lekser for 4B |
| `version` / `generated_at` | Felles versjon og tidspunkt for generering |

Det finnes ikke noe `due`-felt. De tidligere dupliserte klassefeltene på toppnivå er fjernet. Bruk `grade_1.*` og `grade_4b.*` i egne TRMNL-inputs og templates.

Hvis arkivet for 4B ikke kan leses, beholdes feeden for 1. trinn. 4B-feltene blir tomme, og JSON-dataene inneholder en feilmelding.

## Tester

Installer avhengighetene:

```bash
pip install -r requirements.txt
```

Kjør testene:

```bash
python -m pytest -q
```

Test parseren med uke 42-fixturen:

```bash
python update_feed.py --pdf tests/fixtures/uke_42-solidaritetsuka.pdf --week 42 --out data.json
```

Se **Actions** i GitHub for resultatene fra automatiske tester og arkivkontroller.

## TRMNL-oppsett

Konfigurer TRMNL til å hente `data.json` fra GitHub via raw-URL. Layoutene i repositoryet er laget for den nye datastrukturen med `grade_1` og `grade_4b`.

## Prosjektfiler

```text
.github/workflows/update.yml
tests/
update_feed.py
data.json
requirements.txt
settings.yml
full.liquid
quadrant.liquid
half_vertical.liquid
half_horizontal.liquid
README.md
```
