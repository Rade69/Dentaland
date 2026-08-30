---
task_id: DENT-IMPROVE-018
risk: HIGH
implementer: claude
reviewers: [codex]
status: "Implementacija gotova, evidence spreman, ceka Codex review + human approval"
created_at: 2026-08-30
---

# DENT-IMPROVE-018 — Telegram bot podsjetnici (jezgro) — evidence

Vidi `agent_reports/DENT-IMPROVE-018-task-contract.md` za pun scope/kontekst.

## Šta je implementirano

1. **Migracija** `migrations/versions/a7b8c9d0e1f2_telegram_optin.py` — 4
   nove nullable kolone na `appointments`: `telegram_link_token_hash`
   (`String(64)`), `telegram_link_token_expires_at` (`DateTime`),
   `telegram_chat_id` (`String(64)`), `telegram_subscribed_at`
   (`DateTime`). Odgovarajuća polja dodana u `Appointment` u
   `src/dentaland/models.py`.
2. **`src/dentaland/services/telegram.py`** (nov modul) —
   `generate_link_token`/`hash_token` (isti obrazac kao
   `Session.token_hash`, DENT-IMPROVE-013), `build_deep_link`,
   `verify_webhook_secret` (fail-closed — bez konfigurisanog secreta
   UVIJEK vraća `False`), `send_message` (best-effort, tiho preskače
   bez tokena), `consume_telegram_link_token` (jednokratna semantika —
   briše hash/expiry nakon upotrebe, filtrira po
   `telegram_chat_id IS NULL` da spriječi ponovnu upotrebu),
   `format_subscribed_message` (minimizacija — samo vrijeme termina).
3. **`POST /api/telegram/webhook`** (`backend/main.py`) — fail-closed
   secret provjera (403 bez ispravnog `X-Telegram-Bot-Api-Secret-Token`),
   `60/minute` rate limit, tiho ignoriše nevažeći/istekao/već iskorišten
   token (nema razlike u odgovoru — izbjegava token enumeration), uvijek
   vraća `200` na prepoznat/neprepoznat update tip.
4. **`confirm_request`** (`src/dentaland/services/requests.py`) — token
   se generiše SAMO ako je `DENTALAND_TELEGRAM_BOT_USERNAME`
   konfigurisan (inače neupotrebljiv, nema deep link odredišta), TTL 72h.
   Deep link se prosljeđuje u `send_appointment_confirmed` (novi opcioni
   `telegram_deep_link` parametar, `notifications.py`) — bez njega email
   je identičan ranijem ponašanju.
5. **`.env.example`** — dodane `DENTALAND_TELEGRAM_BOT_TOKEN`,
   `DENTALAND_TELEGRAM_BOT_USERNAME`, `DENTALAND_TELEGRAM_WEBHOOK_SECRET`,
   sve opcione, isti obrazac kao SMTP sekcija.
6. **`tests/test_telegram.py`** (nov, 27 testova) + 2 nova testa u
   `tests/test_requests.py` (bot-username-off/on grananje u
   `confirm_request`).

## Odluka koja nije bila eksplicitno u contractu

`consume_telegram_link_token` vraća `None` i kad token nije nađen i kad
je nađen ali `start_time` na terminu ispadne `None` (teorijski nemoguć
slučaj u praksi — token se generiše u istoj transakciji gdje se
`start_time` postavlja, tik prije commit-a). Webhook stoga šalje
potvrdnu poruku isključivo kad je vraćena vrijednost različita od
`None`, umjesto da odvojeno prati "da li je red nađen". Namjerno
pojednostavljeno — razlikovanje ta dva slučaja nema praktičnu vrijednost
i vodilo bi u mrtav/konfuzan kod (prva verzija ove funkcije je imala
tačno takav bug — pozivala nepostojeću pomoćnu funkciju i bezuslovno
slala poruku bez obzira na ishod; uočeno i ispravljeno prije bilo kakvog
testiranja, vidi commit `b2c1971`).

## Verifikacija

- `pytest tests/ -q` bez `DATABASE_URL`/`DATABASE_URL_TEST` (SQLite): **453
  passed, 20 skipped** (skipped = Postgres-only testovi, očekivano).
- `pytest tests/ -q` sa `DATABASE_URL`+`DATABASE_URL_TEST` postavljenim
  istovremeno (real lokalni Postgres, port 5433, ista lekcija kao
  DENT-IMPROVE-012/017 — `create_all()` sam nije dovoljan dokaz):
  **473 passed, 0 failed**.
- `ruff check .` — 5 pre-postojećih grešaka u `scripts/coordination.py`
  (nepovezano sa ovim taskom, `datetime.UTC` alias prijedlozi), SVI
  fajlovi ovog taska čisti.
- `mypy src backend` — **Success: no issues found in 21 source files**.
- `python scripts/agent_sensors.py --all` — **0 blocking findings**.

## Šta NIJE testirano (eksplicitno, po acceptance kriterijumu)

**Kod NIJE testiran protiv pravog Telegram Bot API-ja.** Radovan još
nije javio bot token (kreira ga preko @BotFather). Sve gore navedeno je
mock/unit/integration testiranje na nivou aplikacije i baze — `httpx.post`
je u testovima mock-ovan, `send_message` nikad nije stvarno pozvao
`api.telegram.org`. Kad token stigne, ostaje da se: (1) postavi env
varijable na dev/test okruženju, (2) registruje webhook preko
`setWebhook` Telegram API poziva sa `secret_token` parametrom, (3)
provjeri end-to-end na test VPS-u (isti kao za HTTPS/backend deployment,
29.8.2026) ili lokalno preko tunela.

## Sljedeći koraci

1. Codex review (jedini reviewer, pravilo od 29.8.2026).
2. Human approval (Radovan).
3. Merge u `main` (isti obrazac kao DENT-IMPROVE-016/017: `--no-ff`,
   post-merge integration gate, push, provjera CI, update
   `CURRENT_STATE.md`/backlog).
4. Kad Radovan javi token: end-to-end test, ažuriranje evidence-a sa
   stvarnim rezultatom.
