---
task_id: DENT-IMPROVE-004
risk: MEDIUM
implementer: pi
reviewers: [claude]
verdict: PASS_WITH_NOTES
created_at: 2026-08-20
---

# DENT-IMPROVE-004 — nezavisan review (Claude)

## Metod

Nezavisna provjera od nule (`independent-review` skill) — Pi-jev
izvještaj (`agent_reports/2026-08-20-DENT-IMPROVE-004-pi.md`) tretiran
kao tvrdnja, ne dokaz. Sve niže je nezavisno rekonstruisano, ponovo
pokrenuto i adversarno testirano u worktree-u
`Dentaland-worktrees/DENT-IMPROVE-004-blockout`
(`task/DENT-IMPROVE-004-blockout`, granat od `main` `6220901`).

## Scope

```text
git diff --stat
 desktop/views/main_window.py      |  6 +-
 src/dentaland/services/booking.py | 100 ++++
 tests/test_services.py            | 79 ++++
+ desktop/views/blockout_panel.py (novi)
+ tests/test_gui/test_blockout_panel.py (novi)
```

Sve unutar `allowed_paths`. `models.py`/`migrations/` nedirani — potvrđeno
kroz `git diff --stat`. Zaključak implementera da postojeći `TimeOff`
model pokriva sve potrebno (`doctor_id`, `od_datetime`, `do_datetime`,
`razlog`) sam sam provjerio u `src/dentaland/models.py` — tačno.

## Verdikt: PASS_WITH_NOTES

### Acceptance

| Kriterij | Status | Dokaz |
|---|---|---|
| može se kreirati blokada | PASS | `create_time_off()` + `_on_save` u panelu, testovi servisa i GUI |
| prikazuje se na kalendaru | PASS (postojeće) | `week_view.py`/`time_off_for_week` već postoje, netaknuti, pokriveni postojećim testom (napomena implementera potvrđena — nije novi kod) |
| ne može se unijeti `end <= start` | PASS | provjereno na dva mjesta: UI (`_on_save`, prije poziva servisa) i servis (`create_time_off`, `ValueError` prije otvaranja sesije) — oba testirana |
| može se obrisati | PASS | `delete_time_off()`, UI potvrda kroz `QMessageBox.question`, testovi za oba nivoa |
| blokada drugog doktora ne utiče na pogrešnog | PASS | `_check_timeoff_overlap` filtrira po `doctor_id`; test `test_create_time_off_dozvoljava_drugog_doktora` nezavisno reprodukovan |
| termini nisu tiho obrisani/pomjereni | PASS | `create_time_off` baca `OverlapError` prije ikakvog upisa ako postoji `SCHEDULED` termin u intervalu — hard block, ne silent overwrite |
| eksplicitno upozorenje pri preklapanju | PASS, uz tumačenje | implementirano kao HARD BLOCK (odbija kreiranje) sa porukom, ne kao "upozori pa dozvoli nastavak" — razumnija, sigurnija interpretacija backlog teksta; sprečava da neko slučajno sakrije aktivan termin bez svjesne dodatne akcije (npr. prvo otkazati termin) |

### Reprodukcija (nezavisna, ne prepisana)

```text
pytest tests/ -q → 240 passed, 11 warnings (identično Pi-jevoj tvrdnji)
ruff check src/dentaland desktop backend tests → All checks passed
mypy src/dentaland desktop backend → Success, 33 source files
```

### Pokušaj obaranja (Korak 4) — adversarni testovi, uklonjeni nakon review-a

Napisao sam i pokrenuo dva testa koja Pi-jev test set nije pokrio, koristeći
identičan fixture setup kao `tests/test_services.py` (ne izmišljen):

1. **Boundary touch** — blokada koja počinje TAČNO kad se postojeći termin
   završava (9:00–9:30 termin, 9:30–10:00 blokada) — provjera da
   poluotvoreni interval (`start_time < end AND end_time > start`) ne
   proizvodi lažni overlap na granici. **PASS** — kreirano bez greške.
2. **Potpuno obuhvatanje** — blokada koja obuhvata cijeli termin (8:00–11:00
   blokada oko 9:00–9:30 termina), ne samo djelimično preklapanje.
   **PASS** — ispravno odbijeno sa `OverlapError`.

Nisam uspio oboriti implementaciju na ovim graničnim slučajevima — jača
potvrda nego da nisam ni tražio. Testovi su nakon provjere obrisani (nisu
dio isporuke, samo review dokaz).

Takođe provjerio: status filter u novoj `_check_timeoff_overlap`
(`AppointmentStatus.SCHEDULED`) je identičan postojećem `_check_overlap`
za termine — nema nove nekonzistentnosti sa `PENDING`/drugim statusima.

### `blocking_findings`

Nijedan.

### Napomene (ne blokiraju)

1. GUI test set ne pokriva scenario gdje `store.create_time_off()` baca
   `OverlapError`/`ValueError` kroz UI (samo servisni sloj je testiran za
   to). Kod u `_on_save` (`except (OverlapError, ValueError) as exc:
   self._show_error(str(exc))`) izgleda ispravan vizuelnom inspekcijom, ali
   nije GUI-testiran. Minor coverage gap, ne blocking — vrijedno dodati u
   budućem sitnom follow-upu.
2. GUI test za brisanje pokriva samo "Yes" granu potvrde
   (`QMessageBox.question` mockovan da uvijek vraća Yes) — "No" grana
   (otkazano brisanje) nije eksplicitno testirana. Kod (`if answer !=
   QMessageBox.StandardButton.Yes: return`) izgleda ispravan, minor gap.

## Probni signal — `.agent/` sloj (potvrđeno protiv Pi-jevog izvještaja)

Konzistentno sa stvarnim scope-om. Prvi test na feature tasku koji
kombinuje servisni sloj I desktop GUI istovremeno (za razliku od
DENT-IMPROVE-003 koji je bio čisto infrastrukturni) — Pi je kombinovao
Booking/service i Desktop GUI routing pakete iz `.agent/TASK_ROUTING.md`
umjesto lutanja između njih, i ciljano grep-ovao postojeće
`time_off`/`blockout` reference da izbjegne dupliranje već postojećeg
kalendarskog prikaza blokada.

## Integration status

`REVIEWED → PASS_WITH_NOTES` — čeka Radovanov human approval (MEDIUM
risk), zatim merge i post-merge integration gate na `main`.

## Handoff

CILJ: operativni UI za kreiranje/prikaz/brisanje blokiranog vremena.

URAĐENO: PASS_WITH_NOTES — implementacija ispravna, u scope-u, adversarno
provjerena na graničnim slučajevima (boundary touch, potpuno obuhvatanje).
Nema blocking findings.

NE DIRATI: `models.py`/`migrations/`, postojeća overlap logika termina,
`week_view.py` prikaz blokada — nisu dirani, van scope-a.

SLJEDEĆE: Radovanov human approval → merge → post-merge integration gate
na `main`. Zatim `DENT-IMPROVE-005` (Postavke) po koordinacionoj napomeni
iz Task Contracta (nakon 004, dijeli navigacione fajlove).
