"""Pokreće lokalni backend + statični web server zajedno, za testiranje
javne forme end-to-end BEZ interneta (bez Netlify-ja) — prije nego se
ide na bilo kakav javni deploy.

Ne pokreće desktop aplikaciju (ta se pokreće posebno, `python -m desktop.app`,
jer je to blokirajući GUI proces, ne pozadinski server).

Upotreba:
    python scripts/dev_local.py

Zaustavljanje: Ctrl+C (oba servera se čisto gase).
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"
BACKEND_PORT = 8000
WEB_PORT = 8080


def main() -> int:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    # "dentaland" paket nije pip-install-ovan (editable install) — pytest
    # to rješava preko pyproject.toml `pythonpath = ["src", "."]`, ali
    # `python -m uvicorn` kao poseban proces to ne nasljeđuje, pa se mora
    # eksplicitno postaviti PYTHONPATH ovdje.
    env = os.environ.copy()
    src_path = str(ROOT / "src")
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{src_path}{os.pathsep}{ROOT}{os.pathsep}{existing}" if existing else f"{src_path}{os.pathsep}{ROOT}"

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

    time.sleep(1)
    print()
    print("Spremno. Otvori u browseru:")
    print(f"  http://127.0.0.1:{WEB_PORT}/index.html   (javna forma za zakazivanje)")
    print(f"  http://127.0.0.1:{BACKEND_PORT}/docs       (FastAPI dokumentacija/testiranje endpointa)")
    print()
    print("Desktop aplikacija (odvojeno, u drugom terminalu): python -m desktop.app")
    print("Zaustavljanje: Ctrl+C")
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
    except KeyboardInterrupt:
        print("\nZaustavljam...")
    finally:
        for proc in (backend, web):
            if proc.poll() is None:
                proc.terminate()
        for proc in (backend, web):
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
