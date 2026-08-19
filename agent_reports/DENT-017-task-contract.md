---
task_id: DENT-017
title: Email podsjetnik na termin — servisna funkcija (bez scheduler/GUI)
risk: LOW
implementer: pi
reviewer: claude
status: ASSIGNED
created_at: 2026-08-19
---

# Task Contract — DENT-017: Email podsjetnik (servisni sloj)

Namjena ovog taska je dvojaka: (1) implementirati malu, jasno ograničenu
funkcionalnost koju `docs/dentaland-razvojni-plan-v3.1.md` ("Podsjetnici"
sekcija) već specificira sadržajno, i (2) probni task za validaciju
`.agent/` navigacionog sloja (`DENT-AGENT-CONTEXT-001`) — servisni tip
zadatka, drugačiji od GUI-ja (`DENT-016`), radi raznolikosti signala.
Prije prve izmjene koda, u `agent_report` kratko zapisati (vidi
`.agent/TASK_ROUTING.md` — "Validacija" tabela): koje je fajlove pročitao
prije prve izmjene, da li je koristio `.agent/PROJECT_MAP.md`/
`TASK_ROUTING.md`, da li je morao pitati za pojašnjenje strukture.

```yaml
id: DENT-017
title: send_appointment_reminder — email podsjetnik dan/nekoliko dana prije termina
risk: LOW
objective: >
  Dodati funkciju send_appointment_reminder(to_email, start_time) u
  src/dentaland/services/notifications.py, analognu postojećim
  send_booking_confirmation/send_appointment_confirmed (isti best-effort
  princip preko _dispatch, nikad ne baca izuzetak, SMTP config iz env-a).
  Poruka: "Dentaland: imate zakazan termin DD.MM.GGGG. u HH:MM. Za izmjenu
  termina koristite link…" (tačan tekst iz plana v3.1, "Podsjetnici"
  sekcija) — SAMO ime ordinacije i vrijeme termina, NIKAD naziv usluge ili
  doktora (isto pravilo kao _compose_confirmed_message).
allowed_paths: [src/dentaland/services/notifications.py, tests/test_notifications.py, agent_reports/DENT-017-task-contract.md, agent_reports/2026-08-19-DENT-017-email-podsjetnik.md]
forbidden_paths: [src/dentaland/services/booking.py, src/dentaland/models.py, desktop/, backend/, web/, migrations/, CLAUDE.md, AGENTS.md]
objective_detalji: >
  IZRIČITO VAN OBIMA ovog taska (ne dirati, ne pokušavati "usput"
  riješiti):
  - scheduler/cron koji poziva ovu funkciju u pravo vrijeme (X dana prije
    termina) — to je poseban budući task, ovaj task pravi SAMO funkciju
    koja se može pozvati ručno/testom sa poznatim appointment podacima;
  - "cancel/reschedule token" link u poruci (plan pominje "koristite
    link…", ali generisanje/validacija tog tokena je zaseban mehanizam
    koji ovaj task ne implementira — u poruci ostaviti placeholder tekst
    ili izostaviti rečenicu o linku ako nema sigurnog mjesta za njega bez
    tog mehanizma; ne izmišljati privremeni/nesiguran token format);
  - GUI stranica "Podsjetnici" (sidebar ruta, trenutno `StubPage` u
    `desktop/views/main_window.py`) — ostaje netaknuta, ovaj task ne dira
    `desktop/`.

  Funkcija prati identičan obrazac kao `send_appointment_confirmed`:
  `_dispatch(to_email, compose_callable)`, novi `_compose_reminder_message`
  helper analogan `_compose_confirmed_message`, best-effort (uhvati
  Exception, `logger.warning`, nikad ne propagira).
acceptance:
  - send_appointment_reminder(to_email, start_time) postoji i slijedi isti best-effort obrazac (ne baca ni kad SMTP nije konfigurisan ili konekcija padne).
  - Poruka sadrži SAMO ime ordinacije i tačno vrijeme termina (datum + sat:minut, lokalno Europe/Sarajevo vrijeme kao i postojeće funkcije) — provjerljivo testom da tekst ne sadrži uslugu/doktora.
  - Bez email adrese ili bez SMTP konfiguracije — funkcija se tiho vraća, SMTP se ne poziva (isti obrazac kao postojeći testovi za druge dvije funkcije).
  - Nema izmjene u desktop/, backend/, web/, scheduler/cron logici.
  - Nula regresije u postojećim notifications testovima.
verification: [pytest tests/test_notifications.py -v, pytest tests/ -q, ruff check src/dentaland tests, mypy src/dentaland]
review:
  reviewers: 1
  required: [scope, security — provjeriti da poruka stvarno ne otkriva uslugu/doktora]
```

## Napomena o procesu

Ovaj task ne zavisi ni od jednog drugog aktivnog taska (samostalan unutar
`notifications.py`) — nema koordinacije/claim konflikta sa `DENT-016`
(Crush, GUI/print, potpuno druge putanje) ni sa bilo kojim drugim aktivnim
worktree-om. Prije početka: `python scripts/coordination.py claim --task
DENT-017 --agent pi --paths src/dentaland/services/notifications.py,tests/test_notifications.py`.
