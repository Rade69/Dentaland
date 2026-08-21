---
task_id: DENT-021
reviewer: claude
risk: LOW
verdict: PASS
date: 2026-08-21
---

# Review — DENT-021 revizija (veći avatari + brojčana znaka, LOW)

```yaml
verdict: PASS
scope: PASS
acceptance: PASS
architecture: PASS
blocking_findings: []
```

## Scope — PASS

`git diff --stat` u worktree-u: `week_view.py` (+14), `day_view.py`
(+12), `main_window.py` (+103/-9), tri test fajla, + novi
`desktop/assets/doctors/*.png`. Tačno unutar `allowed_paths` iz revizije
u `agent_reports/DENT-021-task-contract.md`. Codex-ov stari
necommitovan diff u glavnom checkout-u nije diran (provjereno —
`git status` u worktree-u je nezavisan od glavnog checkout-a).

## Implementacija — PASS, tačno prati specifikaciju

`visible_doctor_counts()` u `week_view.py`/`day_view.py` je bit-za-bit
identična predloženoj implementaciji iz kontrakta (isti `_fetch_appointments()`
+ `_cell_span()` guard, BEZ primjene `_filter_doctor_id`). `main_window.py`:
`DOCTOR_AVATAR_SIZE = 48`, `_update_doctor_panel_counts()` pozvan na kraju
`_update_status_legend()` (jedno mjesto, pokriva sve postojeće trigere —
tačno kako je traženo). Badge je `QLabel` sa `border-radius: 12px` +
`background-color` stilom — provjereno da se stvarno renderuje (ne
QFrame `WA_StyledBackground` gotcha iz ranijih faza ovog projekta, jer
je ovo QLabel, ne QFrame).

## Adversarna provjera (nezavisna reprodukcija, live GUI, ne samo testovi)

Napisao sam sopstveni offscreen skript (pravi `AppointmentService`, ne
mock) koji:

1. Kreira 2 termina za Ljubu, 1 za Zorku, 0 za Anu u trenutnoj sedmici.
2. Konstruiše pravi `MainWindow` → `avatar.pixmap().size()` i
   `avatar.size()` za sva tri doktora = **48×48** (potvrđeno povećanje
   sa prijašnjih 38×38).
3. `badge texts (bez filtera) = ['2', '1', '0']` — tačno.
4. **Ključna provjera dizajn-zahtjeva**: pozvao
   `win.week_view.set_filter(doctor_ids["Zorka"])` (simulira klik na
   Zorkin tab) pa ponovo `win._update_doctor_panel_counts()` →
   `badge texts NAKON filtera = ['2', '1', '0']` — **NEPROMIJENJENO**.
   Ovo direktno dokazuje da `visible_doctor_counts()` ignoriše aktivni
   doctor-filter tab, tačno kako je Radovan tražio (panel prikazuje sve
   doktore uvijek, filter utiče samo na kalendarski grid).
5. Sačuvao `win.grab()` screenshot — vizuelno potvrđeno da se obojeni
   kružić STVARNO iscrtava (zelen/crven/plav ispunjen krug), ne prazan/
   proziran widget. Tekst brojeva se ne vidi jasno na screenshotu zbog
   nedostatka fonta u offscreen renderu (isti poznati ograničenje kao
   ranije u ovoj sesiji), ali `label.text()` provjera iznad je
   pouzdaniji, direktan dokaz sadržaja od pixel-inspekcije.

## Verifikacija (ponovljena nezavisno)

```text
pytest tests/ -q                              → 264 passed, 11 warnings
ruff check src/dentaland desktop backend tests → All checks passed!
mypy src/dentaland desktop backend             → Success: no issues found in 35 source files
```

Poklapa se sa Pi-jevim izvještajem (264 = 258 FIX-01 baseline + 6 novih
testova).

## Edge case razmotren (ne blokira)

Znaka je fiksna 24×24px sa 12px fontom — udobno staje jednocifrene i
dvocifrene brojeve; za realan obim jedne ordinacije (par termina do
možda 20-ak sedmično po doktoru) ovo je više nego dovoljno, trocifreni
broj (100+) bi vizuelno prelio ali je nerealan scenario za ovaj
kontekst. Ne blokira.

## Zaključak

Oba Radovanova zahtjeva iz revizije su ispunjena i nezavisno dokazana:
avatari vidljivo veći (48px, mjereno direktno, ne samo tvrđeno), broj u
znaci tačan i neosjetljiv na doctor-filter (adversarno potvrđeno preko
`set_filter`). Scope čist, testovi tačni, pun gate zelen. **PASS.**

## Handoff

```text
CILJ: Panel doktora — veći avatari (48px) i brojčana znaka (broj
      termina po doktoru u trenutnom periodu) umjesto praznog kružića
      boje, nezavisno od aktivnog doctor-filter taba.
URAĐENO: PASS — oba zahtjeva ispunjena i adversarno dokazana (avatar
      veličina mjerena direktno; filter-nezavisnost dokazana pozivom
      set_filter() pa provjerom da se badge count NE mijenja).
NE DIRATI: src/dentaland/, migracije, Codex-ov stari necommitovan diff
      u glavnom checkout-u (čisti se tek nakon merge-a).
SLJEDEĆE: commit (6 izmijenjenih fajlova + 3 nova PNG-a + oba
      agent_report-a) i merge u main, čim Radovan odobri (LOW risk —
      human approval opcion, ali Radovan je do sad tražio odobrenje za
      svaki merge ove sesije). Zatim: Claude čisti Codex-ov stari
      necommitovan main_window.py/test_main_window.py diff u glavnom
      checkout-u (bezbjedno tek nakon što je ova verzija mergovana).
```
