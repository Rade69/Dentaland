---
task_id: DENT-IMPROVE-018
risk: HIGH
implementer: claude
reviewers: [codex]
status: "NOT STARTED — ceka Telegram bot token od Radovana prije testiranja (kod se moze pisati bez njega, sam Bot API poziv testira se tek kad token stigne)"
created_at: 2026-08-30
depends_on: DENT-IMPROVE-013, DENT-IMPROVE-014, DENT-IMPROVE-014C
---

# DENT-IMPROVE-018 — Telegram bot podsjetnici (jezgro)

## Kontekst

Viber je 30.8.2026 stavljen na pauzu — otkrivena moguća ~€100/mjesec
fiksna naknada po botu (vidi CLAUDE.md "Šta se namjerno ne gradi
unaprijed") je neproporcionalna za obim jedne ordinacije. Radovan je
odlučio da se umjesto toga implementira **Telegram bot** — potpuno
besplatan (Telegram Bot API nema nikakvu naplatu), uz prihvaćen
kompromis manje rasprostranjenosti kod pacijenata u BiH u odnosu na
Viber ("ko ga bude, biće obaviješten").

Arhitektonska odluka (potvrđena 30.8.2026, prenesena iz ranije Viber
diskusije, isti princip): polja idu direktno na `appointments` tabelu,
BEZ novog "pacijent" entiteta — sistem trenutno nema trajan pacijent
zapis (samo `ime`/`telefon` tekst po terminu), i to se ne mijenja ovim
taskom.

**Bitno—cancel/reschedule token mehanizam NE postoji još** (potvrđeno
`grep` pretragom `notifications.py:80` — eksplicitno dokumentovano kao
"dok ne postoji siguran cancel/reschedule token mehanizam"). Ovaj task
NE gradi taj opšti mehanizam — gradi SVOJ, uže-namjenski token SAMO za
Telegram opt-in link, po istom sigurnosnom obrascu kao postojeći
`Session.token_hash` (DENT-IMPROVE-013, `models.py:234-251`):
`secrets.token_urlsafe(32)` sirov token nikad u bazi, SHA-256 hash
(`String(64)`), `expires_at`, `hmac.compare_digest()` poređenje,
jednokratna semantika.

## Cilj

Pacijent čiji je zahtjev POTVRĐEN (`confirm_request`) dobija email sa
Telegram deep-link-om. Klik na link + `/start` u Telegram-u vezuje
njegov `chat_id` za taj konkretan termin. Otkazivanje/rok-isteka
poštuje isti minimizacioni princip kao email podsjetnici (CLAUDE.md:
"nikad naziv usluge, samo vrijeme termina").

## Required scope

1. **Migracija** (`models.py` + nova `migrations/versions/*.py`) — na
   `appointments` tabeli, sve nullable:
   - `telegram_link_token_hash: String(64)`
   - `telegram_link_token_expires_at: TZDateTime()`
   - `telegram_chat_id: String` (String, ne Integer — Telegram chat ID
     može biti velik/negativan za grupe, string izbjegava svaku sumnju
     oko opsega)
   - `telegram_subscribed_at: TZDateTime()`

2. **`src/dentaland/services/telegram.py`** (nov modul, po uzoru na
   `notifications.py`-ov best-effort princip — greška u slanju NIKAD ne
   ruši pozivaoca):
   - `generate_link_token() -> tuple[str, str]` — vraća (sirov token,
     SHA-256 heks hash), isti obrazac kao token generisanje za
     `Session` (DENT-IMPROVE-013 `auth.py`, ako tamo postoji helper —
     PROVJERITI prije pisanja novog, ne duplirati).
   - `build_deep_link(bot_username: str, raw_token: str) -> str` —
     `https://t.me/<bot_username>?start=<raw_token>`.
   - `send_message(chat_id: str, text: str) -> None` — poziva Telegram
     Bot API `sendMessage` (HTTPS POST, `httpx` — već zavisnost
     projekta). Best-effort: hvata/loguje grešku, ne diže izuzetak.
     Bez `DENTALAND_TELEGRAM_BOT_TOKEN` env varijable — tiho
     preskače (isti obrazac kao SMTP).
   - `verify_webhook_secret(header_value: str | None) -> bool` —
     `hmac.compare_digest()` protiv `DENTALAND_TELEGRAM_WEBHOOK_SECRET`
     env varijable. Ako env varijabla nije postavljena, VRATI `False`
     uvijek (fail-closed, ne fail-open) i logovati upozorenje.

3. **Webhook endpoint** (`backend/main.py`) — `POST /api/telegram/webhook`:
   - Provjeri `X-Telegram-Bot-Api-Secret-Token` header preko
     `verify_webhook_secret` — ako ne prođe, `403`, ne parsirati body.
   - Parsiraj Telegram update JSON. Ako je poruka `/start <token>`:
     - Hash primljeni token, potraži `Appointment` sa tim
       `telegram_link_token_hash` I `telegram_link_token_expires_at >
       now()` I `telegram_chat_id IS NULL` (spriječava ponovnu upotrebu
       — jednokratna semantika).
     - Ako nađe: upiši `telegram_chat_id`, `telegram_subscribed_at`,
       OBRIŠI `telegram_link_token_hash`/`telegram_link_token_expires_at`
       (token je jednokratan, poništava se nakon upotrebe — isti princip
       kao CLAUDE.md cancel-token zahtjev). Pošalji potvrdnu poruku
       (SAMO vrijeme termina, ne usluga/doktor).
     - Ako ne nađe (token nepostojeći/istekao/već iskorišten): tiho
       ignoriši (ne otkrivati zašto — izbjeći token enumeration/probing
       informacije), NE slati grešku nazad Telegram-u koja bi otkrila
       razliku.
   - Bilo koji drugi update tip: no-op, vrati `200` (Telegram Bot API
     zahtijeva brz `200` odgovor, inače ponavlja slanje update-a).
   - Rate limiting na ovom endpointu (CLAUDE.md: "rate limiting na
     svakom javnom endpointu") — primarno je zaštićen secret token
     verifikacijom (isti princip kao CLAUDE.md napomena za Viber
     webhook), ali dodati razuman limit kao dodatan sloj.

4. **Wiring u `confirm_request`** (`src/dentaland/services/requests.py`
   ili gdje god `confirm_request` živi — PROVJERITI tačnu lokaciju prije
   pisanja):
   - Pri potvrdi termina: generiši link token, upiši hash+expiry (npr.
     24h ili 72h rok — implementer bira, dokumentuje zašto) na taj
     `Appointment` red, pa proslijedi `build_deep_link(...)` rezultat u
     `send_appointment_confirmed` poziv, tako da email sadrži link.
   - `send_appointment_confirmed` (`notifications.py`) dobija opcioni
     parametar za deep link tekst — dodati SAMO ako je proslijeđen (ne
     lomiti postojeće pozivaoce/testove koji ga ne šalju).

5. **Env varijable** (dodati u `.env.example` sa objašnjenjem, PRATITI
   postojeći SMTP obrazac — sve opcione, bez njih se funkcija tiho
   isključuje):
   - `DENTALAND_TELEGRAM_BOT_TOKEN`
   - `DENTALAND_TELEGRAM_BOT_USERNAME`
   - `DENTALAND_TELEGRAM_WEBHOOK_SECRET`

6. **Testovi** (`tests/test_telegram.py` ili slično):
   - Generisanje tokena: sirov token se NIKAD ne pojavljuje u onome što
     se čuva (samo hash).
   - Webhook secret verifikacija: tačan header prolazi, netačan/nema
     header pada, `403` bez configured secreta.
   - `/start` sa validnim tokenom: `telegram_chat_id` upisan, token
     obrisan (jednokratnost), red više ne prihvata isti token ponovo.
   - `/start` sa isteklim/nepostojećim tokenom: tiho ignorisano, `200`,
     ništa upisano.
   - `send_message`/webhook bez konfigurisanih env varijabli: nema pada,
     tiho preskače (matching SMTP best-effort testovi u
     `tests/test_notifications.py` ako postoje — pogledati obrazac).
   - Poruka sadrži SAMO vrijeme termina, NIKAD naziv usluge/doktora
     (spot-check string sadržaja, isti obrazac kao postojeći email
     minimizacioni testovi).

## Šta NE dirati

- `src/dentaland/services/availability.py` — overlap logika, nepovezano.
- Ne graditi opšti cancel/reschedule token mehanizam — samo uže-namjenski
  Telegram opt-in token opisan iznad.
- Ne dirati `web/privacy.html` bez Radovanovog odobrenja — ako Telegram
  kao novi "primalac" podataka (CLAUDE.md v3.1 "primaoci" princip)
  zahtijeva pomen u privacy notice-u, PRIJAVITI kao `OUT_OF_SCOPE_FINDING`,
  ne mijenjati dokument samostalno.
- Ne dirati postojeći Viber-povezan kod ako ga ima (nema — Viber rad je
  stao prije koda, samo je arhitektonska odluka dokumentovana u
  CLAUDE.md).

## Acceptance criteria

- [ ] Migracija čisto primijenjena (`alembic upgrade head` na lokalnoj
      test bazi, ne samo `create_all()` — ista lekcija kao
      `DENT-IMPROVE-017`)
- [ ] `telegram.py` modul: generisanje tokena, deep link, slanje poruke,
      webhook secret verifikacija — sve sa testovima
- [ ] Webhook endpoint radi, rate limited, fail-closed na secret
      verifikaciji
- [ ] `confirm_request` generiše token i prosljeđuje deep link u email
- [ ] Poruke nikad ne sadrže naziv usluge/doktora
- [ ] Bez env varijabli — cijela funkcija se tiho isključuje, nema pada
- [ ] `pytest tests/ -q`, `ruff`, `mypy`, `agent_sensors.py --all` čisti
- [ ] Evidence izvještaj eksplicitno navodi da li je STVARNO testirano
      protiv pravog Telegram bota (token dostupan) ili samo protiv
      mock/test tokena — ne miješati tvrdnje

## Review

Codex (jedini reviewer, pravilo od 29.8.2026). Human approval prije
merge-a. Codex posebno provjerava: (a) token jednokratnost i
fail-closed webhook verifikacija, (b) da li poruke stvarno poštuju
minimizacioni princip, (c) da li `confirm_request` wiring lomi
postojeće testove.

## Koordinacija

```bash
python scripts/coordination.py claim --task DENT-IMPROVE-018 --agent claude --paths src/dentaland/services/telegram.py,backend/main.py,models.py,migrations/versions/**,src/dentaland/services/notifications.py,src/dentaland/services/requests.py,.env.example,tests/test_telegram.py
```

Nema poznatih zavisnosti sa drugim aktivnim taskovima.
