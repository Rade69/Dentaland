---
task_id: DENT-IMPROVE-018
risk: HIGH
implementer: claude
reviewers: [codex]
status: "Fix runda 1 (Codex F1-F3) zavrsena, ceka ponovni Codex review"
created_at: 2026-08-30
---

## Fix runda 1 (Codex review, `2026-08-30-DENT-IMPROVE-018-review-codex.md`, verdict REJECT)

**F1 (HIGH, blocking) — popravljeno.** `telegram_webhook` je primao
`payload: dict` kao FastAPI/Pydantic parametar — tijelo se parsira
PRIJE ulaska u funkciju, dakle prije secret provjere. Codex je živom
probom pokazao: pogrešan secret + neispravan JSON → `422` umjesto
obaveznog `403` (curi informaciju da je body parsiranje pokušano prije
autentifikacije). Fix: endpoint sad prima samo `Request`, ručno čita
`await request.json()` (uz `try/except ValueError` i provjeru
`isinstance(payload, dict)`) TEK NAKON `verify_webhook_secret`. Endpoint
mora biti `async def` da bi `await request.json()` radio.

**F2 (HIGH, blocking) — popravljeno.** `send_message` je logovao
`exc` (cijeli izuzetak) na grešku — `httpx.HTTPStatusError`/mrežne
greške u svom string obliku sadrže PUN URL, uključujući bot token
(`/bot<token>/sendMessage`). Fix: `httpx.HTTPStatusError` grana
loguje SAMO `exc.response.status_code`, generička grana loguje SAMO
`type(exc).__name__` — nikad `str(exc)`/`repr(exc)` za bilo koju httpx
grešku.

**F3 (HIGH, blocking) — popravljeno, najozbiljniji nalaz.**
`consume_telegram_link_token` je radio SELECT → Python izmjene →
COMMIT — dva istovremena webhook poziva sa istim tokenom su oba mogla
proći SELECT provjeru (`telegram_chat_id IS NULL`) prije nego ijedan
commit-uje, i oba "potrošiti" isti token (lost update). Fix: JEDAN
atomski `UPDATE ... WHERE <isti uslovi> RETURNING start_time` — Postgres
garantuje da samo jedna konkurentna transakcija uspješno pogodi red,
druga (blokirana na row lock-u dok prva ne commit-uje) ponovo evaluira
`WHERE` protiv committed stanja i pogodi nula redova.

**Adversarna verifikacija F3 (metodologija kao DENT-IMPROVE-013 F1)** —
LIČNO reprodukovan bug prije fixa: privremeno vraćen stari
select-pa-update kod (`git stash`), pokrenut nov deterministički test
(`tests/test_telegram_postgres.py::test_atomski_update_blokira_i_ponovo_evaluira_where_pod_konkurencijom`)
koji NE zavisi od sreće u thread scheduling-u (drži transakciju A
namjerno otvorenu, thread B mora BLOKIRATI na Postgres row lock-u, pa
se odblokira tek nakon A-inog commit-a) — **PADA** sa starim kodom
(B je dobio ne-`None` rezultat, dokazan "lost update"), **PROLAZI**
nakon `git stash pop` (fix vraćen). Napomena: naivan test sa dva
threada + `Barrier` (probano prvo) NIJE pouzdano reprodukovao race na
lokalnom, brzom Postgres-u — otud determinističko rješenje sa
namjerno otvorenom transakcijom, ne oslanjanje na scheduling sreću.

**Novi testovi**: `tests/test_telegram.py` +4 (F1: neispravan JSON sa
pogrešnim/tačnim secretom; F2: token se ne pojavljuje u logu za
`HTTPStatusError` i generičku grešku). Nov
`tests/test_telegram_postgres.py` (Postgres-only, `skipif` bez
`DATABASE_URL_TEST`) sa dva testa: deterministički (opisan iznad) i
crno-kutijski dvo-thread regresioni test kroz stvarnu javnu funkciju.

Verifikacija nakon fixa: `pytest tests/ -q` bez `DATABASE_URL_TEST`:
**457 passed, 22 skipped**. Sa real Postgres: **479 passed, 0 failed**.
`ruff`/`mypy src backend desktop` čisti, `agent_sensors.py --all` →
0 blocking findings.

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

## End-to-end test protiv PRAVOG Telegram bota (30.8.2026, addendum)

Radovan je poslao pravi bot token (kreiran preko @BotFather, bot
`@Dentaland_zubar_bot`, potvrđen preko `getMe`). Umjesto samo mock
testova, urađen je **stvaran end-to-end test** na test VPS-u:

1. Task grana privremeno checkout-ovana na VPS-u (`/opt/dentaland`,
   preko `git fetch`/`checkout -b`), `httpx` instaliran u venv,
   `alembic upgrade head` primijenjen na `dentaland_vpstest` bazu (nova
   `a7b8c9d0e1f2` migracija čisto primijenjena, sekvenca `appointments.id`
   ručno ispravljena — batch `recreate="always"` iz migracije je
   resetovao SERIAL sekvencu, poznata Postgres kvirka, ne bug u kodu).
2. Tri Telegram env varijable dodane u `dentaland-backend.service`
   (root-only fajl na disku, nikad u repou), servis restartovan.
3. Webhook registrovan preko `setWebhook` (`secret_token` parametar) na
   `https://169-58-208-91.nip.io/api/telegram/webhook` — `getWebhookInfo`
   potvrdio čist status.
4. Napravljen sintetički potvrđen termin (`ime="TEST VPS Telegram"`,
   `appointments.id=2`, jasno markiran test podatak, ostaje u bazi kao
   dokaz — isti princip kao ranija `id=1` VPS deployment proba, vidi
   `docs/dentaland-politika-produkcijski-podaci.md`), pravi deep link
   izgrađen i poslat Radovanu.
5. Radovan kliknuo link, pritisnuo Telegram "Start" dugme (prvi klik
   nije poslao ništa — otvaranje razgovora BEZ pritiska na Start ne
   generiše `/start` poruku, korisna potvrda da UX zahtijeva taj korak;
   dokumentovano za budući korisnički vodič ako zatreba).
6. **Rezultat, potvrđeno sa dvije nezavisne strane (server baza +
   korisnikov screenshot Telegram razgovora):**
   - Webhook primio poziv, `X-Telegram-Bot-Api-Secret-Token` prošao.
   - `telegram_chat_id`/`telegram_subscribed_at` upisani u bazu
     (`1556581316`, `2026-08-30 11:24:07+00`).
   - `telegram_link_token_hash`/`_expires_at` obrisani (jednokratnost).
   - Radovan STVARNO primio poruku u Telegram-u: "Pretplaćeni ste na
     Dentaland podsjetnike. Vaš termin je zakazan za 31.08.2026. u
     13:15." — SAMO datum/vrijeme, bez naziva usluge/doktora
     (minimizacija potvrđena na pravoj poruci, ne samo testom stringa).
   - **Replay test**: isti (već iskorišten) sirov token poslat ponovo
     direktno na webhook (curl, drugi `chat_id=999999`) → HTTP `200`
     (Telegram ne dobija grešku), ali `telegram_chat_id` u bazi OSTAO
     `1556581316` — jednokratnost potvrđena na pravom serveru, ne samo
     u unit testu.
7. Nakon testa: VPS vraćen na `main` (`git checkout main`), Telegram env
   varijable uklonjene iz service fajla, servis restartovan (active),
   `deleteWebhook` pozvan (main nema webhook kod, nema potrebe da
   Telegram i dalje pokušava da isporučuje update-ove). Homepage
   sanity-check nakon revert-a: `GET /` → `200`.

**Zaključak:** cijeli lanac (deep link → Telegram → webhook → fail-closed
secret provjera → jednokratna potrošnja tokena → upis chat_id-a → slanje
minimizovane potvrdne poruke) je stvarno dokazan na pravom internetu sa
pravim Telegram bot nalogom, ne samo mock-ovan. Ovo je jača evidencija
od inicijalnog plana ("kad token stigne, ostaje da se testira") — test je
urađen isti dan kad je token stigao, prije merge-a, na dedikovanom test
VPS-u, bez dodirivanja `main` koda.

## Sljedeći koraci

1. Codex review (jedini reviewer, pravilo od 29.8.2026).
2. Human approval (Radovan).
3. Merge u `main` (isti obrazac kao DENT-IMPROVE-016/017: `--no-ff`,
   post-merge integration gate, push, provjera CI, update
   `CURRENT_STATE.md`/backlog).
4. Kad Radovan javi token: end-to-end test, ažuriranje evidence-a sa
   stvarnim rezultatom.
