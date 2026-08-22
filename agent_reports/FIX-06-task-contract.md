---
task_id: FIX-06
risk: LOW
implementer: pi
reviewers: [claude]
status: "Implementacija (Pi, commit b392954) + review (Claude): PASS. Vidi agent_reports/2026-08-21-FIX-06-pi.md i .../2026-08-21-FIX-06-review-claude.md. LOW risk — čeka Radovanovu odluku o human approval-u prije merge-a. Posljednji task korektivnog paketa FIX-01..06."
created_at: 2026-08-21
---

# FIX-06 — Vizuelno uskladiti Settings i Blockout

## Task Contract

**Cilj:** Glavni appointment workflow (editor, detalji, cancel, delete,
move) koristi zajedničku `BaseDialog` vizuelnu osnovu — bijela
površina, teal primarno dugme, "Odustani"/naslovom-imenovano primarno
dugme umjesto generičkog OK/Cancel. `SettingsPanel`-ovi dijalozi
(`ServiceDialog`, `IntervalDialog`) i `BlockoutPanel`-ova potvrda
brisanja i dalje koriste generički `QDialog`+`QDialogButtonBox`
(OK/Cancel) i `QMessageBox.question` — vizuelno djeluju kao drugi
proizvod. Posljednji task u korektivnom paketu (FIX-01 do FIX-06),
posljednji je namjerno LOW/polish.

**Risk:** LOW (čisto vizuelna izmjena postojećih dijaloga; poziv-ugovor
prema panelima se ne mijenja — vidi ispod).

**Izvor:** `docs/dentaland-desktop-korektivni-plan.md`, sekcija 7
(PRIORITET 7). Pun kontekst korektivnog plana (FIX-01 do FIX-06) tamo —
ovaj task pokriva SAMO FIX-06, ne šire.

## Dio A — `desktop/views/settings_panel.py`: `ServiceDialog`/`IntervalDialog` na `BaseDialog`

Obje klase trenutno nasljeđuju `QDialog` direktno, grade formu preko
`QFormLayout(self)`, i dodaju `QDialogButtonBox(Ok|Cancel)` na dnu.
Konvertovati OBIE na `BaseDialog` (`desktop/views/dialogs/base_dialog.py`,
već korišten za cijeli glavni appointment workflow):

```python
class ServiceDialog(BaseDialog):
    def __init__(self, parent=None, *, naziv="", trajanje=30, buffer=0):
        super().__init__("Usluga", parent, icon="settings")
        form = QFormLayout()
        # ... isti widgeti kao sada (naziv_edit/trajanje_spin/buffer_spin) ...
        self.body_layout().addLayout(form)
        self.add_secondary_button("Odustani")
        self.add_primary_button("Sačuvaj")
```

Isti obrazac za `IntervalDialog` (naslov "Interval radnog vremena",
icon npr. `"settings"` — nema posebne "sat" ikonice u
`sidebar.svg_icon`, provjeriti dostupne nazive prije biranja drugog:
`calendar`/`settings`/`printer`/`tooth`/`phone`/`note`/`alert`).
Ugniježđeni `QFormLayout()` unutar `body_layout()` je već ustaljen
obrazac u redizajnu (vidi `AppointmentEditorDialog` koji radi isto sa
`QGridLayout`) — ne treba graditi formu direktno u `body_layout()`.

**Vanjski ugovor prema `SettingsPanel` se NE mijenja** —
`dialog.exec() != QDialog.DialogCode.Accepted` i `dialog.values()`
ostaju identični (`BaseDialog` je i dalje `QDialog` podklasa,
`add_primary_button`/`add_secondary_button` već kablovani na
`accept()`/`reject()`). `SettingsPanel`-ov pozivni kod (`_on_add_service`,
`_on_edit_service`, `_on_add_interval`) se NE dira.

Postojeći `QMessageBox.warning(self, "Postavke", str(exc))` pozivi u
`SettingsPanel` (nakon `dialog.exec()`, kad servisni sloj baci
`ValueError`) **ostaju kako jesu** — to je greška NAKON što se dijalog
već zatvorio, dijalog objekat više nije prikazan pa `show_error()`
unutar njega nije primjenjivo. Ovo NIJE u obimu FIX-06 (ispravan
mehanizam, samo vizuelno nepovezan sa temom — prihvatljivo, ne
prepravljati bez razloga).

## Dio B — `desktop/views/blockout_panel.py`: destruktivna potvrda brisanja

`_on_delete(self, block_id: int)` trenutno koristi generički
`QMessageBox.question(...)` (Yes/No). Napraviti mali Dentaland
destructive-confirm dijalog po uzoru na već postojeći
`desktop/views/dialogs/delete_appointment.py`
(`DeleteAppointmentDialog(BaseDialog)`, icon="alert", crveno primarno
dugme, "Odustani"/"Obriši ..." dugmad) — **NE kopirati Enter-safety
izuzetak** (`setAutoDefault(False)`/`setDefault(False)`) —
`delete_appointment.py`-ev docstring eksplicitno kaže da je to "jedina
destruktivna, nepovratna akcija u cijelom redizajnu koja to zahtijeva"
(hard delete termina); brisanje blokade je niži rizik (lako se ponovo
kreira), standardno `BaseDialog` Enter-na-primarno ponašanje je u redu.

Predložen naziv: `BlockoutDeleteConfirmDialog` u
`desktop/views/dialogs/` (novi fajl, matches konvenciju — svi ostali
destructive/confirm dijalozi glavnog workflow-a žive tamo) ILI lokalna
klasa u `blockout_panel.py` ako je implementer proceni jednostavnijom —
implementer bira, obje su prihvatljive za LOW risk.

Sadržaj dijaloga: prikazati doktora + vrijeme + razlog blokade (isti
podaci koji su već u `_refresh_list()` retku, linije 129–140) —
**potreban je pristup punom `block` objektu, ne samo `block_id`**.
`_refresh_list()` lambda trenutno hvata `block_id=block.id`
(linija 146) — promijeniti na hvatanje cijelog `block` objekta (ili
dohvatiti ga ponovo u `_on_delete` preko `store.list_time_off()` +
filter po ID-u, implementer bira jednostavniji put).

```python
def _on_delete(self, block: Any) -> None:
    dialog = BlockoutDeleteConfirmDialog(block, self)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return
    self._clear_error()
    try:
        self.store.delete_time_off(block.id)
    except ValueError as exc:
        self._show_error(str(exc))
        return
    self.refresh()
    self.changed.emit()
```

`QMessageBox` import u `blockout_panel.py` se uklanja ako više nije
korišten nigdje drugo u fajlu (provjeriti prije brisanja importa).

## Allowed paths

```text
desktop/views/settings_panel.py
desktop/views/blockout_panel.py
desktop/views/dialogs/base_dialog.py
desktop/views/dialogs/**
tests/test_gui/test_settings_panel.py
tests/test_gui/test_blockout_panel.py
```

`base_dialog.py` je u allowed_paths SAMO ako se pokaže da nešto stvarno
nedostaje (npr. novi helper) — očekivano da NIJE potrebno, postojeći
API (`body_layout`, `add_primary_button`, `add_secondary_button`,
`show_error`) već pokriva oba dijela ovog taska. Ako se ipak promijeni,
obrazložiti u `agent_report`.

## Forbidden paths

```text
src/dentaland/models.py
migrations/
src/dentaland/services/booking.py
desktop/views/main_window.py
desktop/views/week_view.py
desktop/views/day_view.py
desktop/views/dialogs/appointment_editor.py
desktop/views/dialogs/move_appointment.py
desktop/views/dialogs/cancel_appointment.py
desktop/views/dialogs/process_request.py
desktop/views/dialogs/delete_appointment.py
```

## Obavezni regression testovi

1. `ServiceDialog`/`IntervalDialog`: `dialog.exec()` +
   `QDialog.DialogCode.Accepted`/`Rejected` i dalje rade identično
   (postojeći `test_settings_panel.py` testovi ne smiju regresirati —
   ako testovi provjeravaju konkretne `QDialogButtonBox` dugmadi/OK-Cancel
   tekst, ažurirati na nova dugmad "Odustani"/"Sačuvaj").
2. `dialog.values()` vraća ispravne vrijednosti nakon Accept — regresija
   ne smije uticati na formu/podatke, samo na dugmad/chrome.
3. Novi test: `ServiceDialog`/`IntervalDialog` sadrže dugmad sa tekstom
   "Odustani" i "Sačuvaj" (ne "OK"/"Cancel").
4. Novi test: `BlockoutDeleteConfirmDialog` (ili lokalna klasa) prikazuje
   podatke blokade (doktor/vrijeme), Accept poziva `delete_time_off`,
   Reject/X ne briše ništa (isti obrazac kao postojeći
   `test_delete_odustani_ne_brise_termin` za appointments).
5. Regresija — postojeći `test_blockout_panel.py`/`test_settings_panel.py`
   testovi za CRUD tok (kreiranje/uređivanje usluge, dodavanje intervala,
   kreiranje/brisanje blokade) i dalje prolaze.

## Acceptance criteria

- [ ] `ServiceDialog`/`IntervalDialog` koriste `BaseDialog`
      (bijela površina, teal primarno dugme, "Odustani"/"Sačuvaj").
- [ ] Poziv-ugovor prema `SettingsPanel` nepromijenjen
      (`exec()`/`DialogCode`/`values()`).
- [ ] Brisanje blokade koristi Dentaland-stil destructive confirm
      dijalog umjesto generičkog `QMessageBox.question`.
- [ ] Nijedan postojeći CRUD tok (usluge, radno vrijeme, blokade) nije
      regresiran.
- [ ] Nema izmjena van `allowed_paths`, posebno nema izmjena u
      `main_window.py`/`week_view.py`/`day_view.py`/glavnim appointment
      dijalozima.

## Verification

```bash
pytest tests/ -q
ruff check src/dentaland desktop backend tests
mypy src/dentaland desktop backend
```

Baseline za poređenje (izmjereno 21.8.2026 na `main` nakon `FIX-05`):
pytest 276 passed (čist FIX-05 baseline; napomena — trenutni `main`
može pokazivati više zbog paralelnog `FIX-07` rada, izmjeriti tačan
broj na svom worktree-u prije početka, ne pretpostavljati napamet).

## Review

Claude, nezavisan od implementera. LOW risk — po tabeli u
`docs/dentaland-agentski-razvoj.md` human approval nije obavezan, ali
Radovan i dalje odlučuje da li ga traži (kao i za sve dosadašnje LOW/
MEDIUM taskove ove sesije).

## Koordinacija — obavezno prije početka

Provjeri `python scripts/coordination.py status` prije `claim` na
`allowed_paths`. Radi u zasebnom git worktree
(`Dentaland-worktrees/FIX-06-<slug>`, grana `task/FIX-06-<slug>`).
