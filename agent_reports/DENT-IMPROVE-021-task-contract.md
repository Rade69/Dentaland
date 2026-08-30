---
task_id: DENT-IMPROVE-021
risk: MEDIUM
implementer: claude
reviewers: [codex]
status: "IMPLEMENTED, evidence spreman, ceka Codex review. Vidi agent_reports/2026-08-30-DENT-IMPROVE-021-implementation.md"
created_at: 2026-08-30
depends_on: DENT-IMPROVE-017 (email reminder scheduler), DENT-IMPROVE-018 (Telegram opt-in)
---

# DENT-IMPROVE-021 — Telegram podsjetnik na dan termina (ne samo email)

## Kontekst

Radovan je uživo testirao Telegram opt-in (DENT-IMPROVE-018) i primijetio
da poruka koju dobija odmah nakon klika na link ("Pretplaćeni ste...")
NIJE stvarni podsjetnik — to je jednokratna potvrda pretplate. Provjereno
u kodu: `send_due_appointment_reminders` (scheduler koji šalje podsjetnike
~24h prije termina) poziva ISKLJUČIVO `send_appointment_reminder`
(email) — nikad ne dodiruje Telegram. DENT-IMPROVE-018 je namjerno bio
samo "jezgro" (opt-in mehanizam), stvarno slanje Telegram podsjetnika je
eksplicitno ostavljeno za kasnije (vidi taj Task Contract, "Required
scope" — samo `send_message`/`consume_telegram_link_token`, ne scheduler
integracija).

## Cilj

`send_due_appointment_reminders` šalje Telegram poruku (uz postojeći
email, ne umjesto njega) SVAKOM terminu koji ima upisan
`telegram_chat_id` (pacijent se ranije pretplatio), u ISTOM 24h prozoru
kao email. Isti minimizacioni princip — samo vrijeme termina.

## Required scope

1. **`src/dentaland/services/telegram.py`** — nova
   `format_reminder_message(start_time: datetime) -> str`, ista formulacija
   kao email podsjetnik (`_compose_reminder_message` u `notifications.py`,
   "imate zakazan termin ... u ...") — SAMO vrijeme, ne usluga/doktor.

2. **`src/dentaland/services/notifications.py`** —
   `send_due_appointment_reminders`:
   - WHERE klauzula proširena da uključi termine sa `telegram_chat_id`
     upisanim, NE SAMO `email` (trenutno bi termin BEZ emaila ali SA
     Telegram pretplatom bio tiho preskočen — praktično rijetko jer
     javna forma uvijek traži email, ali polje je nullable u modelu,
     zaštititi defanzivno).
   - Nakon ISTOG atomskog `UPDATE ... WHERE reminder_sent_at IS NULL`
     zauzimanja (jedno zauzimanje pokriva OBA kanala, ne duplirati
     claim logiku) — pozvati `send_appointment_reminder` AKO ima email
     (nepromijenjeno), I NEZAVISNO pozvati novi Telegram poziv AKO ima
     `telegram_chat_id` — oba best-effort, jedno ne zavisi od uspjeha
     drugog (ako email padne, Telegram se i dalje pokuša, i obrnuto).
   - Nova zavisnost `notifications.py -> telegram.py` (za `send_message`/
     `format_reminder_message`) — provjeriti da ne pravi cirkularan
     import (`telegram.py` trenutno NE uvozi `notifications.py`).

3. **Testovi** (`tests/test_notifications.py` ili gdje već žive
   `send_due_appointment_reminders` testovi):
   - Termin sa `telegram_chat_id` I email-om u prozoru → OBA kanala
     pozvana.
   - Termin SAMO sa `telegram_chat_id` (bez email-a) → Telegram poslan,
     email NIJE pokušan (prazan/None email se i dalje ne šalje).
   - Termin SAMO sa email-om (bez Telegram pretplate) → identično
     ranijem ponašanju, bez Telegram poziva.
   - Bez `DENTALAND_TELEGRAM_BOT_TOKEN` konfigurisanog → tiho preskače,
     ne ruši scheduler (isti best-effort princip).
   - Atomski claim i dalje sprečava dvostruko slanje (postojeći
     DENT-022 test ne smije se pokvariti — pokrenuti ga eksplicitno).
   - Minimizacija: Telegram tekst podsjetnika ne sadrži uslugu/doktora.

## Šta NE dirati

- `send_appointment_confirmed`/Telegram opt-in tok (DENT-IMPROVE-018) —
  nepromijenjen, ovaj task samo DODAJE poziv u scheduler.
- `backend/reminder_scheduler.py` — samo poziva
  `send_due_appointment_reminders`, ne treba izmjenu ako se sva logika
  doda unutar te funkcije.
- Atomski claim mehanizam (`UPDATE ... WHERE reminder_sent_at IS NULL`)
  — koristiti kakav jeste, ne praviti poseban claim za Telegram kanal
  (jedno zauzimanje = jedan pokušaj podsjetnika, bez obzira na broj
  kanala).

## Acceptance criteria

- [x] Telegram podsjetnik se šalje SAMO terminima sa upisanim
      `telegram_chat_id`, u istom 24h prozoru kao email
- [x] Email i Telegram su nezavisni best-effort pozivi (pad jednog ne
      blokira drugi)
- [x] Poruka sadrži SAMO vrijeme termina
- [x] Postojeći DENT-022 atomski-claim testovi i dalje prolaze
      nepromijenjeni
- [x] `pytest tests/ -q` (i bez i sa `DATABASE_URL_TEST`), `ruff`,
      `mypy`, `agent_sensors.py --all` čisti

## Review

Codex (jedini reviewer). Human approval prije merge-a.

## Koordinacija

```bash
python scripts/coordination.py claim --task DENT-IMPROVE-021 --agent claude --paths src/dentaland/services/notifications.py,src/dentaland/services/telegram.py,tests/test_notifications.py
```

Nema poznatih zavisnosti sa paralelnim taskovima.
