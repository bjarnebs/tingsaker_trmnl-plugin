# Tingsaker TRMNL-plugin v3.5.1

Automatisk feed med lekser fra Tingsaker skole for 1. trinn og 4B.

## Hva er forbedret i 3.5.1?

- Samler klassefeltene under `grade_1` og `grade_4b`, uten dupliserte klassefelt på toppnivå.
- Hver klasse har egne dagsfelt, lekser og «Husk»-påminnelser.
- Feed-normaliseringen validerer JSON før den skrives.

- Fjerner det tidligere hardkodede `due: 17:00`.
- Bruker eksplisitt `Europe/Oslo` når dagens dato/ukedag beregnes.
- Velger høyeste publiserte uke som ikke ligger etter inneværende ISO-uke.
- Støtter PDF og DOCX, også når filendelsen mangler, ved hjelp av filsignatur.
- Støtter flere leksemarkører som faktisk brukes i ukeplaner, blant annet:
  `Leksemappa:`, `Leselekse:`, `Lesemappa:`, `Ukelekse:`, `Ukeleksse:` og `Lesebok 1:`.
- Parseren gjetter ikke lekser hvis den ikke finner en eksplisitt leksemarkør.
- `data.json` valideres og skrives atomisk, slik at en mislykket oppdatering ikke overskriver forrige gyldige feed.
- GitHub Actions kjører tester før produksjonsoppdateringen.
- Versjonen er samlet til `3.3.1`.

## GitHub

Legg inn innholdet i denne mappen i roten av repositoryet. Du skal blant annet se:

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

Workflowen kan startes manuelt fra **Actions → Update Tingsaker homework → Run workflow**.

Den kjører også automatisk én gang per døgn. Cron-tidspunktet er satt til 05:15 UTC; selve scriptet bruker `Europe/Oslo` slik at dato og ukedag blir riktige også ved overgang mellom sommer- og vintertid.

## Lokal test

Installer avhengigheter:

```bash
pip install -r requirements.txt
```

Kjør tester:

```bash
python -m pytest -q
```

Test mot uke 42-fixturen:

```bash
python update_feed.py --pdf tests/fixtures/uke_42-solidaritetsuka.pdf --week 42 --out data.json
```

## TRMNL-data

TRMNL henter `data.json` fra GitHub via raw-URL. Klasseinnhold ligger separat:

- `grade_1.homework` og `grade_1.reminders`: lekser og «Husk» for 1. trinn
- `grade_4b.homework` og `grade_4b.reminders`: lekser og «Husk» for 4B
- `grade_1.today_day`, `grade_1.today_homework`, `grade_1.next_day` og `grade_1.next_homework`: dagens og neste lekse for 1. trinn
- Tilsvarende dagsfelt under `grade_4b` for 4B
- `version` og `generated_at`: felles metadata

De gamle klassefeltene på toppnivå er fjernet for å unngå dupliserte data. TRMNL-layoutene i repoet bruker den nye strukturen. Oppdater eventuell egen TRMNL-input/template til å lese fra `grade_1.*` og `grade_4b.*`. Det finnes ikke noe `due`-felt.

## 4B

Versjon 3.4.0 forsøker også å hente 4B fra skolens eget arkiv. I feeden ligger dette separat under `grade_4b`:

- `grade_4b.homework`: lekser for mandag–fredag
- `grade_4b.reminders`: «Husk»-feltet for mandag–fredag
- `grade_4b.source`: kilde til ukeplanen

Lekser og «Husk» holdes atskilt. Parseren leser bare tekst som er knyttet til tydelige `Lekser`- eller `Husk`-etiketter, og skal ikke gjette dersom formatet i PDF-en ikke lar seg tolke. De fire TRMNL-layoutene viser begge klassene for dagens ukedag. Hvis 4B-arkivet ikke kan leses, beholdes 1. trinns feed og 4B-feltene blir tomme med en feilmelding i JSON.
