# Review — DENT-020 (email reminder scheduler)

Reviewer: claude | Implementer: codex | Datum: 2026-08-20

```yaml
verdict: PASS
scope: PASS
acceptance: PASS
architecture: PASS
blocking_findings: []
```

## Šta je provjereno nezavisno

- **Scope**: `git diff main --stat` potvrđuje samo `backend/main.py`,
  `src/dentaland/services/notifications.py`, `tests/test_backend.py`, novi
  `backend/reminder_scheduler.py`. Nijedan `forbidden_path` diran
  (`models.py`, `migrations/`, `booking.py`, `requests.py`, `pyproject.toml`
  — potvrđeno da APScheduler nije dodat kao zavisnost, tačno kako je
  obrazloženo).
- **Prozor logika**: pročitao `send_due_appointment_reminders()` direktno —
  poluotvoreni interval `[now+24h, now+24h+15min)`, filter na `SCHEDULED` +
  ne-prazan email. Testovi (`due_at_start`, `due_inside`, `too_early`,
  `too_late`, `cancelled`) pokrivaju tačno granice, ne samo "sretan put".
- **Detached-session pitanje** (sumnjao sam prije čitanja testa):
  `send_due_appointment_reminders()` čita `appointment.email`/`.start_time`
  IZVAN `with session_factory() as session:` bloka, nakon što se sesija
  zatvori. Teoretski rizik `DetachedInstanceError`. Test 1 stvarno prolazi
  kroz pravu DB sesiju (ne mockovanu) i uspijeva — potvrđeno da
  `Session.close()` ne expire-uje već učitane skalarne kolone, samo
  `commit()` to radi po defaultu. Nije bug.
- **Verifikacija, ponovo pokrenuto nezavisno**:
  ```
  pytest tests/test_backend.py -v → 13 passed (uklj. sva 3 nova testa)
  pytest tests/ -q → 222 passed
  mypy backend src/dentaland → Success, 0 grešaka
  ruff check backend src/dentaland tests → All checks passed
  ```
  Slaže se sa Codex-ovim navodom.
- **Lifecycle wiring**: `lifespan()` pokreće scheduler task na startup,
  `cancel()` + `await` uz `suppress(CancelledError)` na shutdown — standardna,
  ispravna asyncio praksa. `dependency_overrides` mehanizam za
  `get_session_factory` ispravno propagiran i u scheduler task, ne samo u
  HTTP rute — testabilno bez pokretanja stvarnog infinite loop-a.
- **Rizik duplog slanja**: dokumentovan i u kodu (docstring) i u izvještaju,
  tačno onako kako je Task Contract tražio.

## Pokušaj obaranja (nije uspio, ali vrijedan pomena)

Poll interval (15 min) == širina prozora — matematički se tesselira BEZ
preklapanja/rupa POD PRETPOSTAVKOM da `asyncio.sleep()` ne driftuje. U
praksi, svaki prolaz troši i vrijeme na sam DB upit/slanje, pa se stvarni
razmak između uzastopnih `now` vrijednosti postepeno produžava za taj
iznos — teoretski, termin koji "upadne" tačno u tu mikroskopsku rupu
(milisekunde do par sekundi po prolazu) bi mogao biti propušten. Ovo NIJE
blocking — drift bi morao akumulirati stotine/hiljade prolaza da probije
prozor, i mehanizam je već eksplicitno "best-effort", ne "exactly-once"
garancija. Spominjem kao LOW/informational, ne kao nalaz koji traži
popravku.

## Informational napomena (za FlowOS, ne za ovaj task)

Probni signal navodi da je Codex pročitao globalni skill `architecture-guard`
kao dio orijentacije — taj skill je FlowOS-specifičan sadržaj (View→
Controller→Services granice, `tests/architecture/test_boundaries.py`) koji
u Dentaland kontekstu nema primjenu. Bezopasno (finalni kod ispravno prati
POSTOJEĆE Dentaland konvencije, ne FlowOS obrazac), ali je signal da
globalni skill trigger opis možda treba užu specifičnost da ne triguje van
FlowOS-a — to je out-of-scope napomena za budući FlowOS rad, ne za ovaj
review.

## Integration status

`VERIFIED, ne merge-ovano` — čeka Radovanov human approval.
