"""Pokreće SVE što treba za lokalno testiranje, jednom komandom, bez
razmišljanja odakle šta pokrenuti — backend, javnu formu i desktop
aplikaciju, sa ispravnim PYTHONPATH za sve troje.

Cilj: pravi end-to-end test (pošalji zahtjev kroz formu → vidi ga u
desktop aplikaciji) prije bilo kakvog javnog (Netlify/VPS) deploya.

Upotreba:
    python scripts/dev_local.py              # backend + web forma + desktop app
    python scripts/dev_local.py --no-desktop  # samo backend + web forma

Radi iz BILO KOG foldera (main checkout ili bilo koji git worktree) —
putanje se računaju u odnosu na lokaciju ovog fajla, ne trenutni
working directory. Ako testiraš zadatak koji je još u worktree-u (npr.
DENT-009), pokreni ovu ISTU skriptu iz tog worktree-a — koristiće kod i
`dentaland.db` iz tog worktree-a, ne iz main-a.

Zaustavljanje: Ctrl+C (svi pokrenuti procesi se čisto gase).
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"
BACKEND_PORT = 8000
WEB_PORT = 8080


def _build_env() -> dict[str, str]:
    # "dentaland" paket nije pip-install-ovan (editable install) — pytest
    # to rješava preko pyproject.toml `pythonpath = ["src", "."]`, ali
    # svaki poseban proces (uvicorn, desktop app) to ne nasljeđuje, pa se
    # mora eksplicitno postaviti PYTHONPATH ovdje, na jednom mjestu, za sve.
    env = os.environ.copy()
    src_path = str(ROOT / "src")
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        f"{src_path}{os.pathsep}{ROOT}{os.pathsep}{existing}"
        if existing
        else f"{src_path}{os.pathsep}{ROOT}"
    )
    return env


def main() -> int:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-desktop",
        action="store_true",
        help="ne pokreći desktop aplikaciju, samo backend + web forma",
    )
    args = parser.parse_args()

    env = _build_env()
    print(f"Radni folder: {ROOT}")
    print()

    print(f"Pokrećem backend na http://127.0.0.1:{BACKEND_PORT} ...")
    backend = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--port", str(BACKEND_PORT)],
        cwd=ROOT,
        env=env,
    )

    print(f"Pokrećem web formu na http://127.0.0.1:{WEB_PORT} ...")
    web = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(WEB_PORT)],
        cwd=WEB_DIR,
    )

    desktop: subprocess.Popen | None = None
    if not args.no_desktop:
        print("Pokrećem desktop aplikaciju ...")
        desktop = subprocess.Popen(
            [sys.executable, "-m", "desktop.app"],
            cwd=ROOT,
            env=env,
        )

    time.sleep(1)
    print()
    print("Spremno. Otvori u browseru:")
    print(f"  http://127.0.0.1:{WEB_PORT}/index.html   (javna forma za zakazivanje)")
    print(f"  http://127.0.0.1:{BACKEND_PORT}/docs       (FastAPI dokumentacija/testiranje endpointa)")
    if desktop is not None:
        print("Desktop aplikacija se otvara u posebnom prozoru.")
    print()
    print("Test: pošalji zahtjev kroz formu, provjeri da se pojavi u desktop")
    print('aplikaciji (panel "Novi zahtjevi", kad taj dio dashboarda bude gotov).')
    print()
    print("Zaustavljanje: Ctrl+C (gasi backend i web server; ako je desktop app")
    print("i dalje otvoren, zatvoriti ga ručno kao svaki drugi prozor).")
    print()

    try:
        while True:
            time.sleep(1)
            if backend.poll() is not None:
                print("Backend se neočekivano zaustavio.")
                break
            if web.poll() is not None:
                print("Web server se neočekivano zaustavio.")
                break
            # Desktop app se namjerno NE prati ovdje — normalno je da
            # korisnik zatvori taj prozor prije nego završi sa testiranjem
            # backend-a/forme, to ne treba da zaustavi ostatak.
    except KeyboardInterrupt:
        print("\nZaustavljam...")
    finally:
        procs = [backend, web] + ([desktop] if desktop is not None else [])
        for proc in procs:
            if proc.poll() is None:
                proc.terminate()
        for proc in procs:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
