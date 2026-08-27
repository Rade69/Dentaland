#!/usr/bin/env python3
"""Dentaland — kreiranje korisničkog naloga (DENT-IMPROVE-013).

Interaktivan CLI. Lozinka se UVIJEK unosi preko `getpass` (nikad kao CLI
argument — curi kroz shell history i process listu), dva puta radi
potvrde, i nikad se ne ispisuje na ekran niti loguje. Nema signup
ekrana/UI za ovo — nema još stvarnog staff-facing klijenta koji bi ga
koristio (desktop app radi direktno preko SQLAlchemy, ne zove backend;
web/app.js zove samo javni submit endpoint).

Svaki zaposleni dobija SVOJ nalog — namjerno nema "kreiraj zajednički
admin nalog" prečice (v3.1: audit ima smisla samo uz individualne naloge).

Upotreba:
    python scripts/create_user.py --username sestra1 --role RECEPTION
    python scripts/create_user.py --username dr.ana --role DENTIST
    python scripts/create_user.py --username admin1 --role ADMIN

Baza: ista logika kao `backend/main.py::get_session_factory` — `DATABASE_URL`
env varijabla ima prednost (Postgres, DENT-IMPROVE-012), inače
`DENTALAND_DB_PATH` (SQLite fajl, default `dentaland.db`).
"""

from __future__ import annotations

import argparse
import contextlib
import getpass
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_SRC = str(ROOT / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

if sys.platform == "win32":
    # Windows konzola po defaultu koristi cp1252/cp437 — puca na š/č/ć/ž/đ
    # u porukama ispod (isti razlog kao scripts/coordination.py).
    for _stream in (sys.stdout, sys.stderr):
        with contextlib.suppress(Exception):
            _stream.reconfigure(encoding="utf-8")

from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from dentaland.models import Base, User, UserRole  # noqa: E402
from dentaland.services.auth import hash_password  # noqa: E402

VALID_ROLES = tuple(role.value for role in UserRole)
MIN_PASSWORD_LENGTH = 8


def _build_session_factory() -> sessionmaker:
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        db_url = database_url
    else:
        db_path = os.environ.get("DENTALAND_DB_PATH", "dentaland.db")
        db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    return sessionmaker(engine, expire_on_commit=False)


def _prompt_password() -> str:
    """Traži lozinku dva puta (potvrda) preko `getpass` — nikad echo na ekran."""
    while True:
        password = getpass.getpass("Lozinka (min. 8 znakova): ")
        if len(password) < MIN_PASSWORD_LENGTH:
            print(
                f"Lozinka mora imati bar {MIN_PASSWORD_LENGTH} znakova, pokušaj ponovo.",
                file=sys.stderr,
            )
            continue
        confirm = getpass.getpass("Potvrdi lozinku: ")
        if password != confirm:
            print("Lozinke se ne poklapaju, pokušaj ponovo.", file=sys.stderr)
            continue
        return password


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--username", required=True, help="korisničko ime (mora biti jedinstveno)")
    parser.add_argument(
        "--role",
        required=True,
        choices=VALID_ROLES,
        help="uloga zaposlenog: " + ", ".join(VALID_ROLES),
    )
    args = parser.parse_args()

    session_factory = _build_session_factory()

    with session_factory() as session:
        existing = session.scalar(select(User).where(User.username == args.username))
        if existing is not None:
            print(f"Greška: korisničko ime '{args.username}' već postoji.", file=sys.stderr)
            return 1

    password = _prompt_password()

    with session_factory() as session:
        user = User(
            username=args.username,
            password_hash=hash_password(password),
            role=UserRole(args.role),
        )
        session.add(user)
        session.commit()

    print(f"Kreiran korisnik '{args.username}' sa ulogom {args.role}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
