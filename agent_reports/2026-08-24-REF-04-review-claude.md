---
task_id: REF-04
risk: MEDIUM
reviewer: claude
implementer: pi
reviewer_role: Reviewer 2 (arhitektura)
previous_review: 2026-08-24-REF-04-review-codex.md (PASS_WITH_NOTES)
verdict: PASS_WITH_NOTES
commits: [06dfd4f]
created_at: 2026-08-24
---

# REF-04 — Claude review (arhitektura, Reviewer 2)

```yaml
verdict: PASS_WITH_NOTES
scope: PASS
acceptance: PASS
architecture: PASS_WITH_NOTES
blocking_findings: []
```

```text
CILJ: Arhitektonska procjena Controller/View granice i dugoročnog troška
      lazy-import kompromisa (Codexov eksplicitan zahtjev).
URAĐENO: PASS_WITH_NOTES — kompromis je opravdan i dobro dokumentovan za
      SADA, ali je širi nego što Codexov review opisuje (proteže se i na
      MainWindow privatno stanje, ne samo dijaloge) i treba biti
      eksplicitno zabilježen kao poznat tehnički dug, ne tiho prihvaćen.
NE DIRATI: dialog klase, day/week view, servisni sloj — nedirano.
SLJEDEĆE: Radovanov human approval, pa merge — prije REF-05.
```

## 1. Nezavisna verifikacija (ponovljena)

```text
pytest tests/ -q                              → 341 passed, 11 warnings
ruff check src/dentaland desktop backend tests → All checks passed!
mypy src/dentaland desktop backend             → Success: no issues found in 42 source files
```

## 2. Netačna tvrdnja u implementer izvještaju — non-blocking, ali za zapis

`agent_reports/2026-08-24-REF-04-appointment-controller.md:14` kaže "Izvor:
`agent_reports/REF-04-task-contract.md` (napisan PRIJE koda)" — ovo je
NETAČNO. Sam Task Contract fajl (`REF-04-task-contract.md:14`) ispravno
kaže "napisan naknadno (poslije implementacije) — procesna greška". Dva
fajla u istom paketu tvrde suprotno o istoj proceduralnoj činjenici. Slažem
se sa Codexovom procjenom da ovo nije blocking (scope/acceptance su
netaknuti netačnom tvrdnjom), ali vrijedi ispraviti radi audit traga —
implementer treba ažurirati liniju 14 u sljedećem dodiru tog fajla.

## 3. Arhitektonska procjena lazy-import kompromisa (Codexov zahtjev)

Pročitao sam `appointment_controller.py` u cjelini. Docstring na vrhu
fajla (linije 11-16) transparentno objašnjava kompromis — dobra praksa,
nije sakriveno u kodu bez objašnjenja.

**Kompromis je opravdan za sada:**
- Rješava stvaran, dokazan problem (Codex je pronašao konkretan test —
  `test_delete_akcija_trajno_uklanja_termin_kroz_pravi_servis` — koji
  monkeypatch-uje NAKON konstrukcije `MainWindow`-a; rani DI bi taj test
  slomio).
- Alternative (dialog registry/provider) bi dodale novu infrastrukturu
  izvan cilja OVOG taska — ispravno zadržan disciplinovan scope, ne
  širen bez potrebe (CLAUDE.md: agent ne širi obim sam).
- Zabrana mijenjanja postojećih GUI testova je eksplicitan zahtjev ovog
  taska — kompromis poštuje tu granicu, ne zaobilazi je.

**Ono što Codexov review ne pominje, a vrijedi dodati — kompromis je ŠIRI
od samo dijaloga:**

`_doctors()`, `_has_doctors()`, `_current_doctor_id()` (linije 47-54)
čitaju `MainWindow` PRIVATNO stanje (`_doctors`, `_has_doctors`,
`_current_doctor_id` — sve sa vodećim underscore-om) preko
`getattr(self._parent_widget, "_doctors", [])`. Ovo je ISTA kategorija
kompromisa kao lazy dialog import (Controller zna/čita View internals),
samo drugi mehanizam (`getattr` na privatne atribute umjesto lazy import).
Razlog je vjerovatno isti — izbjeći promjenu `MainWindow`-a ili dodavanje
eksplicitnog state-passing mehanizma bez potrebe za ovaj task.

**Preporuka (non-blocking, za budući REF task, ne za ovaj):** zabilježiti
oba oblika (lazy dialog import + privatno-stanje `getattr`) kao POZNAT,
NAMJERAN tehnički dug u `.agent/PROJECT_MAP.md` ili sličnom mjestu —
razlog da se eksplicitno zapiše (ne samo u docstringu jednog fajla) je da
budući REF task (vjerovatno REF-05, koji uvodi `ScheduleController` i
dalje smanjuje `MainWindow` odgovornosti, ili REF-08 završni cleanup) ima
priliku da svjesno odluči da li čistiji state-passing/dialog-provider
pristup sad ima smisla — kad `MainWindow` bude tanji, možda "gledanje
nazad" prirodno nestane bez posebnog task-a.

Ovo NE mijenja verdikt na REJECT — mehanizam je funkcionalan, testiran i
dokumentovan. `PASS_WITH_NOTES` jer arhitektonski kompromis postoji i
zaslužuje eksplicitno praćenje, ne tih.

## 4. Ostatak arhitekture — potvrđeno

- Controller ne uvozi SQLAlchemy (potvrđeno čitanjem cijelog fajla, ne
  samo grep-om).
- Svaka workflow metoda prati identičan redoslijed kao stari
  `MainWindow` kod (dialog konstrukcija → `exec()` → `get_data()` →
  validacija → store poziv → `OverlapError`/`ValueError` handling →
  refresh) — potvrđeno vlastitim čitanjem uporedo sa Codexovom analizom.
- `_refresh_callback()` je injektovan, Controller ne implementira refresh
  logiku — ispravno ne preduhitrava REF-05.

## Zaključak

PASS_WITH_NOTES. Extraction je ispravan, testiran (5 novih + 32
nepromijenjena GUI testa), i scope je čist. Lazy-import/getattr kompromis
je opravdan i transparentno dokumentovan za sada, ali je širi nego što je
prvobitno opisano — preporučujem eksplicitno zabilježiti oba oblika kao
poznat tehnički dug za buduće REF taskove da razmotre, ne kao nešto što
se tiho zaboravi. Nema blokirajućih nalaza. Čeka Radovanov human approval
prije merge-a.
