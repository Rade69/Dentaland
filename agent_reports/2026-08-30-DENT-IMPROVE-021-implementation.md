---
task_id: DENT-IMPROVE-021
risk: MEDIUM
implementer: claude
reviewers: [codex]
status: "Implementacija gotova, evidence spreman, ceka Codex review"
created_at: 2026-08-30
---

# DENT-IMPROVE-021 — Telegram podsjetnik u scheduleru — evidence

Vidi `agent_reports/DENT-IMPROVE-021-task-contract.md` za pun kontekst.

## Šta je implementirano

1. **`src/dentaland/services/telegram.py`** — nova
   `format_reminder_message(start_time)`, ista formulacija kao email
   podsjetnik ("Podsjetnik: imate zakazan termin ... u ..."), samo
   vrijeme, bez usluge/doktora.

2. **`src/dentaland/services/notifications.py`** —
   `send_due_appointment_reminders`:
   - WHERE klauzula proširena (`or_`) da uključi termine sa
     `telegram_chat_id` upisanim, ne samo email — inače bi termin bez
     email-a ali sa Telegram pretplatom bio tiho preskočen.
   - Nakon istog atomskog `UPDATE ... WHERE reminder_sent_at IS NULL`
     zauzimanja: email šalje se ako postoji `appointment.email`,
     Telegram poruka šalje se nezavisno ako postoji
     `appointment.telegram_chat_id` — oba best-effort, jedan kanal ne
     zavisi od drugog.
   - Nova zavisnost `notifications.py -> telegram.py`
     (`send_message`/`format_reminder_message`) — provjereno da
     `telegram.py` NE uvozi `notifications.py`, nema cirkularnog importa.

## Verifikacija

- `pytest tests/ -q` bez `DATABASE_URL_TEST`: **528 passed, 26 skipped**.
- Sa real Postgres: **554 passed, 0 failed**.
- `ruff check .` — samo 5 pre-postojećih grešaka u
  `scripts/coordination.py` (nepovezano), svi fajlovi ovog taska čisti.
- `mypy src backend desktop` — **Success: no issues found in 60 source
  files**.
- `agent_sensors.py --all` — **0 blocking findings**.
- Postojećih 5 DENT-022 (atomski claim) regresionih testova prolaze
  NEPROMIJENJENI — potvrđeno da izmjena nije narušila tu zaštitu.

## Novi testovi (6, `tests/test_backend.py`)

- Email + Telegram oba prisutna → oba kanala pozvana, tačan
  chat_id/tekst.
- SAMO Telegram (bez email-a) → Telegram poslan, email NIJE pokušan
  (dokazuje da prošireni WHERE stvarno radi, ne samo teoretski).
- SAMO email (bez Telegram pretplate) → identično ranijem ponašanju,
  Telegram NIJE pozvan.
- Minimizacija — Telegram tekst ne sadrži uslugu/doktora/imena.
- Bez `DENTALAND_TELEGRAM_BOT_TOKEN` — `httpx.post` se nikad ne poziva
  (best-effort tiho preskače), scheduler ne padne.

## Nije testirano uživo

Kod NIJE testiran protiv pravog Telegram bota u ovom krugu (za razliku
od DENT-IMPROVE-018) — logika je identična već dokazanom
`send_message`/`format_*` mehanizmu, samo se sad poziva iz novog
mjesta (scheduler umjesto webhook handlera). Ako se želi stvarna
potvrda (podsjetnik STVARNO stigne na Telegram 24h prije termina),
potrebno je ili sačekati pravi termin u tom prozoru na test VPS-u, ili
ručno pozvati `send_due_appointment_reminders` sa `now` postavljenim
tako da postojeći potvrđen termin (sa pretplatom) upadne u prozor.

## Sljedeći koraci

1. Codex review.
2. Human approval.
3. (Opciono) Radovanova lična potvrda da podsjetnik stvarno stigne na
   pravi Telegram, ako želi vizuelnu potvrdu prije merge-a.
