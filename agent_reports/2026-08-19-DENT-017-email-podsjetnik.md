# Implementer izveštaj — DENT-017 (email podsjetnik)

Task: DENT-017 | Risk: LOW | Implementer: pi | Status: IMPLEMENTED (čeka review)

## Validacija `.agent/` navigacionog sloja (prije prve izmjene koda)

- **Fajlova pročitano prije prve izmjene**: `.agent/PROJECT_MAP.md`,
  `.agent/TASK_ROUTING.md`, `agent_reports/DENT-017-task-contract.md`,
  `src/dentaland/services/notifications.py`, `tests/test_notifications.py`.
- **Koristio `.agent/`?** DA — `PROJECT_MAP.md` me je direktno uputio na
  "Notifications" sekciju (`src/dentaland/services/notifications.py` +
  `tests/test_notifications.py`), bez potrebe za `ls`/`find` po repou.
- **Pitao za pojašnjenje strukture?** NE — struktura je bila jasna iz
  `.agent/` fajlova i Task Contracta.

### NALAZ (važan za validaciju sloja)

`.agent/` fajlovi NE postoje u `main` (niti su commit-ovani — `git ls-files
.agent/` je prazan). Nalaze se isključivo kao untracked fajlovi u worktree-u
`DENT-AGENT-CONTEXT-001`. Da bih ih pročitao, morao sam ručno znati (iz
`git worktree list`) da taj worktree postoji i otvoriti fajlove odatle —
sloj nije "navigabilan iz main-a" dok se ne merge-uje. Ovo NIJE blokiralo
rad (task je samostalan), ali je signal da `.agent/` sloj trenutno ne služi
svrsi "manje lutanja" dok god živi samo u drugom worktree-u.

## Plan implementacije

Dodati `send_appointment_reminder(to_email, start_time)` + `_compose_reminder_message`
u `src/dentaland/services/notifications.py`, identičan obrazac kao
`send_appointment_confirmed` (`_dispatch`, best-effort, minimizacija). Poruka:
SAMO ime ordinacije i tačno vrijeme termina (DD.MM.GGGG. u HH:MM, lokalno
Europe/Sarajevo). Rečenica "Za izmjenu termina koristite link…" se IZOSTAVLJA —
cancel/reschedule token mehanizam je eksplicitno van obima, a nesiguran token
se ne izmišlja (Task Contract).

## Verifikacija

```
pytest tests/test_notifications.py -v  → 14 passed (4 nova za reminder)
pytest tests/ -q                        → 206 passed
ruff check src/dentaland tests          → All checks passed!
mypy src/dentaland                      → Success: no issues found in 8 source files
```

## Scope potvrda

`git status` pokazuje izmjene samo u `allowed_paths` (`notifications.py`,
`test_notifications.py`, `agent_reports/**`). Nijedan `forbidden_path` nije
diran (booking.py, models.py, desktop/, backend/, web/, migrations/, CLAUDE.md,
AGENTS.md).
