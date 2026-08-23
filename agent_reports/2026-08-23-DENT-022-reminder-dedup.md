# Implementer izvještaj — DENT-022 (zaštita od dupliranog slanja podsjetnika, HIGH)

Task: DENT-022 | Risk: HIGH | Implementer: Claude (direktno) | Status: IMPLEMENTED — čeka Reviewer 1/2 (Codex, Crush ili Pi)

## Cilj

Zatvoriti eksplicitno prihvaćen rizik iz DENT-020: bez oznake "podsjetnik
poslan", restart backend-a ili slučajno dvostruko pokretanje scheduler-a
može poslati isti podsjetnik dva puta. Vidi puni plan (napisan PRIJE
koda, po HIGH-risk proceduri) u `agent_reports/2026-08-23-DENT-022-plan.md`.

## Fact found — stvaran mehanizam duplikata (prije koda)

Prozor `[now+24h, now+24h+15min)` se svaki put računa iznova iz
`datetime.now(UTC)` u trenutku poziva. Uzastopni pozivi iz STABILNOG
scheduler loop-a prirodno ne preklapaju prozore (pomjeraju se za tačno
15 min svaki put). Rizik je specifičan za: (1) restart procesa unutar
~15 min od zadnjeg poziva — novi `now` se može preklopiti sa već
obrađenim prozorom; (2) dva istovremena scheduler procesa. Ovo je
provjereno čitanjem koda prije pisanja bilo kakvog fixa.

## Izmijenjeni/novi fajlovi (svi u allowed_paths)

- `src/dentaland/models.py` — `Appointment.reminder_sent_at:
  Mapped[datetime | None]` (`TZDateTime()`, nullable, bez default-a) —
  isti obrazac kao `confirmed_at`/`arrived_at` (DENT-012).
- `migrations/versions/d4e5f6a7b8c9_reminder_sent_at.py` (nov) —
  aditivna Alembic revizija, revises `c3d4e5f6a7b8`, isti
  `batch_alter_table` obrazac kao prethodna migracija.
- `src/dentaland/services/notifications.py` —
  `send_due_appointment_reminders()`: dodat `reminder_sent_at.is_(None)`
  u WHERE filter; nakon `send_appointment_reminder(...)` (best-effort,
  ne baca) postavlja se `appointment.reminder_sent_at = current` na
  ISTOM objektu unutar iste sesije; `session.commit()` na kraju bloka
  (sesija sad obuhvata i fetch i update, prošireno iz originalnog
  koda koji je zatvarao sesiju prije slanja).
- `tests/test_backend.py` — novi
  `test_scheduler_ne_salje_dvaput_isti_termin`: isti termin kroz dva
  poziva (simulacija restarta, drugi poziv 1 min kasnije sa
  preklapajućim prozorom) → `send_appointment_reminder` pozvan TAČNO
  jednom, `reminder_sent_at` postavljen u bazi.

## Šta NIJE mijenjano (potvrđeno)

- `send_appointment_reminder()`, `send_booking_confirmation()`,
  `send_appointment_confirmed()` — netaknuto.
- `REMINDER_LEAD_TIME`/`REMINDER_WINDOW` konstante, sam mehanizam
  prozora — netaknuto.
- `backend/reminder_scheduler.py`, `backend/main.py` — netaknuto.
- `desktop/`, `web/` — netaknuto.

## Verifikacija

```text
pytest tests/ -q                              → 288 passed (287 baseline + 1 novi test)
ruff check src/dentaland desktop backend tests → All checks passed!
mypy src/dentaland desktop backend             → Success: no issues found in 36 source files
```

### Migracija — ručno potvrđena na pravoj SQLite bazi (ne samo test suite)

```text
alembic upgrade head    → reminder_sent_at kolona prisutna (PRAGMA table_info potvrđen)
alembic downgrade -1    → reminder_sent_at uklonjena, confirmed_at/arrived_at i dalje prisutni (netaknuti)
alembic upgrade head    → reminder_sent_at ponovo prisutna
```

Potpuna simetrija potvrđena, ostali podaci netaknuti pri downgrade-u.

### Dedup — adversarna samo-provjera prije predaje reviewer-ima

Privremeno uklonjen `reminder_sent_at.is_(None)` filter i update red,
ponovo pokrenut `test_scheduler_ne_salje_dvaput_isti_termin` →
test PADA (`send.call_count == 2`, ne 1) — potvrđuje da test stvarno
hvata regresiju, ne prolazi trivijalno. Fix vraćen, test ponovo PASS.

## Odbačene opcije

Vidi plan fajl (poseban `reminder_log` tabela, distribuirana brava,
retry logika za neuspjele SMTP pokušaje) — sve odbačeno prije koda,
obrazloženo tamo.

## Sljedeći korak

Čeka nezavisan review od **Codex** (obavezan Reviewer 1 na HIGH, ponovo
dostupan) i **Crush ili Pi** (Reviewer 2) — ja (Claude, implementer) se
ne vraćam da sam sebe pregledam u istom kontekstu. Nakon oba reviewa,
Radovan daje human approval prije merge-a.
