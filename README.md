# Tingsaker – lekser for TRMNL

Automatisk oppdatert leksefeed fra Tingsaker skole for **1. trinn og 4B**, laget for visning på TRMNL.

## Innhold

- [Funksjoner](#funksjoner)
- [Slik fungerer oppdateringen](#slik-fungerer-oppdateringen)
- [Dataformat](#dataformat)
- [Tester](#tester)
- [TRMNL-oppsett](#trmnl-oppsett)
- [Feilsøking](#feilsøking)
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

Denne delen beskriver hvilke verdier pluginen forventer. Navn på menyer og tilgjengelige datakilder kan variere med TRMNL-oppsettet ditt, så bruk dette som en sjekkliste mot den aktuelle plugin-editoren.

### 1. Koble til JSON-feed

Bruk den rå JSON-filen i GitHub som datakilde (raw file), ikke HTML-visningen av GitHub-filen:

```text
https://raw.githubusercontent.com/bjarnebs/tingsaker_trmnl-plugin/main/data.json
```

Hvis TRMNL-oppsettet ber om en URL til ekstern data, lim inn adressen der. Kontroller først at adressen åpner gyldig JSON i nettleseren. Feedens innhold oppdateres automatisk av GitHub Actions; det er normalt ikke nødvendig å redigere `data.json` manuelt.

### 2. Kontroller feltene

Dataene er nøstet under `grade_1` og `grade_4b`. Eksempler på felt som layoutene bruker:

| Formål | JSON-felt |
| --- | --- |
| Ukedag for 1. trinn | `grade_1.today_day` |
| Dagens lekser for 1. trinn | `grade_1.today_homework` |
| Påminnelse for 1. trinn | `grade_1.reminders` med dagens ukedag som nøkkel |
| Ukedag for 4B | `grade_4b.today_day` |
| Lekser for 4B | `grade_4b.homework` med dagens ukedag som nøkkel |
| Påminnelse for 4B | `grade_4b.reminders` med dagens ukedag som nøkkel |
| Sist generert | `generated_at` |

De medfølgende Liquid-layoutene forventer disse objektene og feltene. Ikke flat ut JSON-strukturen eller flytt klassefeltene til toppnivå uten samtidig å oppdatere layoutene.

### 3. Velg layout

Repositoryet inneholder fire Liquid-layouts:

- `full.liquid` – full visning av begge klassene.
- `half_vertical.liquid` – layout for vertikal halvskjerm.
- `half_horizontal.liquid` – layout for horisontal halvskjerm.
- `quadrant.liquid` – kompakt visning i én kvadrant.

Velg layouten som passer skjermoppsettet ditt, og bruk den tilsvarende Liquid-filen i plugin-editoren. For første oppsett er `full.liquid` et nyttig utgangspunkt fordi den viser begge klassene og tidspunktet for oppdateringen.

### 4. Test før du tar den i bruk

1. Åpne JSON-URL-en og kontroller at den returnerer JSON, ikke en GitHub-nettside eller en feilmelding.
2. Kontroller at `grade_1`, `grade_4b` og `generated_at` finnes i dataene.
3. Forhåndsvis layouten i TRMNL og se at begge klassene vises.
4. Kontroller en dag med lekser og en dag uten lekser, slik at reserve-tekstene også blir testet.

## Feilsøking

- **TRMNL viser ikke data:** Kontroller at du bruker `raw.githubusercontent.com`-adressen, og at JSON-filen åpnes uten innlogging.
- **Feltene vises som tomme:** Kontroller at datakilden er koblet til riktig JSON, og at feltnavnene har prefikset `grade_1` eller `grade_4b`.
- **Feil ukedag eller gamle lekser:** Se på `generated_at` i JSON-filen, og kontroller siste kjøring under GitHub Actions.
- **4B mangler data:** Se etter feilmelding i JSON-dataene og sjekk resultatet av arkivkontrollen for 4B under Actions.
- **Layouten gir Liquid-feil:** Kontroller at du bruker layoutfilen fra dette repositoryet sammen med den tilhørende datastrukturen.

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
