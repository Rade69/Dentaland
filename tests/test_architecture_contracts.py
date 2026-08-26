"""Arhitektonski senzori — replay validacija protiv poznate istorije (DENT-IMPROVE-010).

Test A/B/C pokreću ``ARCH-VIEW-001`` na ISTORIJSKIM commit-ima (preko
``git show``/``git ls-tree``) i provjeravaju da senzor reprodukuje poznatu
F1-F4 istoriju tačno — ni manje ni više. Red Team test dokumentuje poznate
granice senzora (alias/dinamički pozivi se NE hvataju).

Commit SHA-ovi su pinovani radi reproducibilnosti (provjereni kroz
``git log --first-parent``):
- ``ce2d270`` = REF-08 merge (kraj REF-00..08, F1-F4 aktivni).
- ``a87d423`` = REF-11 merge (REF-09+REF-11 primijenjeni, F2/F4 nestali).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from agent_sensors import analyze_arch_view  # noqa: E402

COMMIT_REF_08 = "ce2d270"  # REF-00..08 finalno stanje (F1-F4 aktivni)
COMMIT_REF_11 = "a87d423"  # poslije REF-09+REF-11 (F2/F4 nestali, F1/F3 ostaju)


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    return result.stdout


def _source_at(commit: str, path: str) -> str:
    return _git("show", f"{commit}:{path}")


def _view_files_at(commit: str) -> list[str]:
    out = _git("ls-tree", "-r", "--name-only", commit, "desktop/views/")
    return [p for p in out.splitlines() if p.endswith(".py")]


def _view_finding_files_at(commit: str) -> set[str]:
    files: set[str] = set()
    for path in _view_files_at(commit):
        source = _source_at(commit, path)
        findings = analyze_arch_view(path, source)
        if findings:
            files.add(path)
    return files


# --- Test A: REF-00..08 stanje — sve četiri poznate lokacije ---


def test_a_ref08_nalazi_tacno_f1_f4_lokacije() -> None:
    files = _view_finding_files_at(COMMIT_REF_08)

    assert files == {
        "desktop/views/day_view.py",  # F1: drag&drop store.move
        "desktop/views/week_view.py",  # F1
        "desktop/views/blockout_panel.py",  # F2: create_time_off/delete_time_off
        "desktop/views/settings_panel.py",  # F3: 4 settings mutacije
        "desktop/views/requests_panel.py",  # F4: cancel/mark_confirmed
    }


# --- Test B: poslije REF-09+REF-11 — F2/F4 nestali, F1/F3 ostaju ---


def test_b_poslije_ref09_ref11_f2_f4_nestali() -> None:
    files = _view_finding_files_at(COMMIT_REF_11)

    assert "desktop/views/blockout_panel.py" not in files  # F2 nestao (REF-11)
    assert "desktop/views/requests_panel.py" not in files  # F4 nestao (REF-09)
    assert "desktop/views/day_view.py" in files  # F1 ostaje (REF-10 još nije)
    assert "desktop/views/week_view.py" in files  # F1 ostaje
    assert "desktop/views/settings_panel.py" in files  # F3 ostaje (REF-12 još nije)


# --- Test C: trenutni main — F1 ostaje (REF-10 nije mergovan), ostalo čisto ---


def test_c_trenutni_main_samo_f1_ostaje() -> None:
    files = _view_finding_files_at("HEAD")

    # REF-10 je primijenjen — F1 (drag&drop store.move u day_view/week_view)
    # više ne postoji, pa senzor vraća prazan skup.
    assert files == set()


# --- Red Team: poznate granice senzora (dokumentovane, ne "pobijediti") ---


def test_red_team_alias_i_dinamicki_pozivi_se_ne_hvataju() -> None:
    # Jednostavan direktni poziv se hvata.
    direct = "class V:\n    def f(self):\n        self.store.move(1, 2, 3)\n"
    assert len(analyze_arch_view("desktop/views/v.py", direct)) == 1

    # Alias — POZNATO ograničenje: senzor NE hvata.
    alias = (
        "class V:\n    def f(self):\n"
        "        store2 = self.store\n        store2.move(1, 2, 3)\n"
    )
    assert analyze_arch_view("desktop/views/v.py", alias) == []

    # Dinamički getattr — POZNATO ograničenje: senzor NE hvata.
    dynamic = 'class V:\n    def f(self):\n        getattr(self.store, "move")(1, 2, 3)\n'
    assert analyze_arch_view("desktop/views/v.py", dynamic) == []
