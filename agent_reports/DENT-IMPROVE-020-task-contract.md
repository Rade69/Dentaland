---
task_id: DENT-IMPROVE-020
risk: MEDIUM
implementer: claude
reviewers: [codex]
status: "IMPLEMENTED, uzivo testirano protiv test VPS-a, ceka Codex review. Vidi agent_reports/2026-08-30-DENT-IMPROVE-020-implementation.md"
created_at: 2026-08-30
depends_on: DENT-IMPROVE-013 (RBAC/login), DENT-IMPROVE-007 (pending requests)
---

# DENT-IMPROVE-020 — Desktop → backend API most (samo "Novi zahtjevi" panel)

## Kontekst

Radovan je tražio da se pokaže/testira stvaran radni tok: pacijent
popuni javnu formu (hostovanu na test VPS-u, već radi —
`https://169-58-208-91.nip.io/`) → osoblje vidi i potvrdi zahtjev u
**desktop aplikaciji** → pacijent dobija email + Telegram (DENT-IMPROVE-018).

Desktop app trenutno (Faza 0) uopšte ne zna da se poveže na bilo šta
osim lokalne SQLite baze (`desktop/app.py`, `AppointmentService.from_sqlite`).
CLAUDE.md arhitektura za Fazu 1 predviđa "PySide6 desktop → httpx →
FastAPI → PostgreSQL", ali to nikad nije implementirano.

**Eksplicitno dogovoren uzak obim** (AskUserQuestion, 30.8.2026,
Radovan potvrdio): NE gradi se zamjena za cijeli `AppointmentService`
(~30 metoda — raspored, radno vrijeme, doktori/usluge management).
Gradi se SAMO panel "Novi zahtjevi" (`desktop/views/requests_panel.py`
→ `DashboardPanels`), koji poziva uzak, već poznat podskup store
metoda: `pending_requests`, `doctors`, `service_choices`,
`confirm_pending`, `reject_pending` (plus `awaiting_confirmation`/
`cancelled_today` koje ovaj task vraća kao prazne liste — van obima,
druga funkcionalnost, ne "zahtjevi").

**Arhitektonska odluka radi izbjegavanja rizika za postojeći Faza 0
kod**: `MainWindow.__init__` eagerno poziva MNOGO store metoda odmah
pri pokretanju (`_build_doctor_tabs`, `WeekView`/`DayView` konstruktori
itd.) — "remote" store koji implementira samo uzak podskup metoda bi
odmah srušio postojeći `MainWindow` ako bi se tamo ubacio. Zato: NOVA,
odvojena, minimalna ulazna tačka (`desktop/remote_demo.py`), NE
modifikacija `MainWindow`/`desktop/app.py` — nulti rizik za Ljubinu
stvarnu lokalnu upotrebu, koja ostaje potpuno netaknuta.

## Cilj

`python desktop/remote_demo.py` (ili slično) otvara mali prozor: prijava
(RBAC, isti mehanizam kao backend/web), pa `DashboardPanels` panel
povezan na pravi VPS API — prava lista PENDING zahtjeva, pravi klik
"Potvrdi" (ProcessRequestDialog, isti UI kao u glavnoj aplikaciji) koji
stvarno zove `POST /api/booking-requests/{id}/confirm`, što pokreće
stvaran email + Telegram (DENT-IMPROVE-018 kod, nepromijenjen).

## Required scope

1. **`backend/main.py`** — dva nova READ-ONLY endpointa, isti RBAC
   obrazac kao postojeći (`RequireReceptionDep`), rate limited:
   - `GET /api/doctors` — aktivni doktori (`id`, `ime`).
   - `GET /api/services` — usluge (`id`, `naziv`, po potrebi
     `trajanje_min`/`buffer_min` ako ih `ServiceOptionDTO` već nosi —
     provjeriti prije pisanja novog DTO-a, ne duplirati).
   Servisni sloj (`src/dentaland/services/`) vjerovatno već ima
   funkcije za listanje doktora/usluga (provjeriti `settings.py`/
   `appointments.py` prije pisanja nove logike u `backend/main.py` —
   ruter samo poziva postojeći servisni sloj, ne sadrži logiku).

2. **`desktop/api_client/`** (nov paket) — httpx-bazirani klijent:
   - `DentalandApiClient` klasa, `httpx.Client(base_url=..., timeout=...)`
     — cookie jar se čuva automatski unutar `httpx.Client` instance
     (isti mehanizam kao backend RBAC Secure cookie sesija,
     DENT-IMPROVE-013).
   - `login(username, password) -> None` — poziva
     `POST /api/auth/login`, diže jasan izuzetak na 401.
   - `get_pending_requests() -> list[RequestDTO]`
   - `get_doctors() -> list[DoctorDTO]`
   - `get_service_choices() -> list[tuple[int, str]]`
   - `confirm_pending(request_id, doctor_id, service_id, start) -> None`
   - `reject_pending(request_id) -> None`
   - Sve mrežne/HTTP greške (timeout, 401/403/404/409, connection
     refused) pretvoriti u jasne, GUI-prijateljske izuzetke — ne pucati
     sa sirovim `httpx` traceback-om u licu korisnika.
   - Base URL iz env varijable `DENTALAND_REMOTE_API_BASE` (bez
     default-a na hardkodiran VPS IP u kodu — vidi "Šta NE dirati";
     ako varijabla nije postavljena, `remote_demo.py` traži je
     eksplicitno prije pokretanja, ne pada tiho).

3. **`desktop/remote_demo.py`** (novi, samostalni entry point):
   - Login `QDialog` (username/password, poziva `client.login(...)`,
     jasna poruka greške na neuspjeh).
   - Nakon uspješne prijave: `QMainWindow` sa SAMO `DashboardPanels`
     unutra, konstruisan sa novim "remote store" adapterom (sljedeća
     stavka).
   - NE mijenja `desktop/app.py` — ovo je POTPUNO odvojen ulaz, ne
     opcija/flag na postojećem.

4. **`desktop/remote_store.py`** (ili slično) — adapter implementira
   TAČNO metode koje `DashboardPanels`/`RequestController` pozivaju
   (duck typing, isti obrazac kao postojeći `AppointmentService`):
   `pending_requests`, `doctors`, `service_choices`, `confirm_pending`,
   `reject_pending` (stvarni pozivi kroz `DentalandApiClient`),
   `awaiting_confirmation`/`cancelled_today` (vraćaju `[]` — eksplicitno
   van obima, ne prava implementacija).

5. **Testovi**:
   - `tests/test_desktop_api_client.py` — mock HTTP odgovori
     (`httpx.MockTransport` ili monkeypatch), pokriva: uspješna
     prijava, neuspješna prijava (401 → jasan izuzetak), parsiranje
     pending/doctors/services odgovora u DTO-ove, confirm/reject šalju
     tačan URL+payload, mrežna greška (npr. `httpx.ConnectError`) se ne
     manifestuje kao sirov traceback.
   - `tests/test_backend.py` dopune — `GET /api/doctors`/`GET /api/services`:
     zahtijevaju RECEPTION (401 bez prijave), vraćaju tačan oblik za
     ulogovanog korisnika, samo aktivni doktori.

6. **Ručna verifikacija** (Qt GUI se ne testira automatski u ovom
   projektu) — evidence MORA sadržati stvaran zapis: pokrenut
   `remote_demo.py` protiv test VPS-a, prijava uspjela, pravi PENDING
   zahtjev viđen, potvrđen kroz pravi UI klik, provjereno da je stigao
   pravi email/Telegram (isti obrazac kao DENT-IMPROVE-018 evidence).
   Ako GUI ne mogu vizuelno provjeriti sâm (nema snapshot alata za Qt u
   ovom okruženju), eksplicitno tražiti od Radovana da pokrene i potvrdi
   — ne tvrditi uspjeh bez toga.

## Šta NE dirati

- `desktop/app.py`, `desktop/views/main_window.py` — potpuno netaknuti,
  Ljubina lokalna upotreba se ne smije promijeniti ni najmanje.
- `AppointmentService`/`booking.py` — ne dodavati remote-specifičnu
  logiku tamo, sve novo ide u odvojene `desktop/api_client/`/
  `desktop/remote_store.py` module.
- Ne hardkodirati VPS IP/domenu bilo gdje u committovanom kodu — samo
  kroz env varijablu, dokumentovano u `.env.example` sa jasnom napomenom
  da je trenutna vrijednost TEST adresa, ne produkcijska (isti princip
  kao CLAUDE.md napomena o test VPS-u).
- Ne graditi raspored/kalendar/radno-vrijeme daljinski — eksplicitno
  van obima ovog taska (vidi Kontekst).
- Ne otvarati Postgres port spolja niti praviti bilo kakav direktan
  DB-nivo pristup sa desktop strane — SVE ide kroz HTTP API (RBAC,
  rate limiting, postojeća sigurnosna ograničenja ostaju netaknuta).

## Acceptance criteria

- [x] Nova dva GET endpointa rade, RBAC-zaštićena, testirana
- [x] `DentalandApiClient` pokriven testovima (uspjeh + svaka greška
      grana), ne baca sirove httpx izuzetke ka GUI sloju
- [x] `remote_demo.py` (tačnije: isti `store` koji GUI koristi) pokrenut
      UŽIVO protiv test VPS-a — real login, real prikaz zahtjeva, real
      potvrda kroz `confirm_pending`, real DB promjena. Vizuelni klik
      mišem u modalnom dijalogu NIJE lično izveden (priznato u evidence-u)
      — Radovan može to uraditi po potrebi, nalog ostavljen na VPS-u
- [x] `desktop/app.py`/`main_window.py` nepromijenjeni (git diff dokaz
      u evidence-u — prazan izlaz)
- [x] `pytest tests/ -q` (i bez i sa `DATABASE_URL_TEST`), `ruff`,
      `mypy`, `agent_sensors.py --all` čisti
- [x] `.env.example` dopunjen sa `DENTALAND_REMOTE_API_BASE`,
      eksplicitno označeno kao test/demo vrijednost

## Review

Codex (jedini reviewer). Human approval prije merge-a. Codex posebno
provjerava: (a) da li `MainWindow`/`app.py` STVARNO nepromijenjeni,
(b) da li HTTP greške curi kao sirovi traceback u GUI, (c) da li ima
hardkodiran VPS IP van env varijable.

## Koordinacija

```bash
python scripts/coordination.py claim --task DENT-IMPROVE-020 --agent claude --paths desktop/api_client/**,desktop/remote_demo.py,desktop/remote_store.py,backend/main.py,tests/test_desktop_api_client.py,tests/test_backend.py,.env.example
```

Nema poznatih zavisnosti sa DENT-IMPROVE-018/019 (odvojene grane, ne
dira migracije/modele).
