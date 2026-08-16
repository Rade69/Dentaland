#!/usr/bin/env python3
"""Dentaland — koordinacija više agenata (Claude/Codex/Crush) na paralelnim zadacima.

Sprečava da dva agenta u različitim git worktree-ovima nezavisno mijenjaju
iste fajlove. Registar živi u .coordination/registry.db u korijenu glavnog
repoa (dijeljen preko svih worktree-ova, lociran preko `git rev-parse
--git-common-dir`, koji uvijek pokazuje na isti dijeljeni .git bez obzira
iz kojeg se worktree-a poziva), tako da je vidljiv iz bilo kojeg worktree-a.

Putanje se normalizuju relativno na KORIJEN TRENUTNOG worktree-a
(`git rev-parse --show-toplevel` — različit po worktree-u, za razliku od
--git-common-dir), da bi ista logička putanja (npr. "src/dentaland/models.py")
bila uporediva preko worktree-ova. Identitet "vlasnika" je taj korijen
worktree-a, ne env varijable ni ručno praćenje ko je "ja".

Komande:
    coordination.py claim  --task DENT-014 --agent claude --paths a.py,b.py
    coordination.py release --task DENT-014
    coordination.py status
    coordination.py check  --path backend/services/tokens.py
    coordination.py hook-check   (čita PreToolUse JSON payload sa stdin)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

if sys.platform == "win32":
    # Windows konzola po defaultu koristi cp1252/cp437 — puca na š/č/ć/ž/đ.
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

AGENTS = ("claude", "codex", "crush", "pi")


def _git_rev_parse(arg: str, start: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", arg],
        cwd=start,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _git_common_dir(start: Path) -> Path:
    common_dir = Path(_git_rev_parse("--git-common-dir", start))
    if not common_dir.is_absolute():
        common_dir = start / common_dir
    return common_dir.resolve()


def registry_root() -> Path:
    """Glavni repo (dijeljen preko svih worktree-ova) — samo za lokaciju registra."""
    return _git_common_dir(Path.cwd()).parent


def worktree_root() -> Path:
    """Korijen TRENUTNOG worktree-a — različit po worktree-u, koristi se za identitet i normalizaciju."""
    return Path(_git_rev_parse("--show-toplevel", Path.cwd())).resolve()


def registry_path() -> Path:
    coord_dir = registry_root() / ".coordination"
    coord_dir.mkdir(exist_ok=True)
    return coord_dir / "registry.db"


def connect():
    import sqlite3

    conn = sqlite3.connect(registry_path(), timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            agent TEXT NOT NULL,
            branch TEXT,
            worktree_path TEXT NOT NULL,
            paths TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL,
            released_at TEXT
        )
        """
    )
    conn.commit()
    return conn


def normalize(path: str, root: Path) -> str:
    p = Path(path)
    if not p.is_absolute():
        p = Path.cwd() / p
    p = p.resolve()
    try:
        rel = p.relative_to(root)
    except ValueError as exc:
        raise ValueError(
            f"putanja {path!r} ({p}) je van trenutnog worktree-a ({root})"
        ) from exc
    return rel.as_posix().strip("/")


def paths_overlap(a: str, b: str) -> bool:
    if a == b:
        return True
    return a.startswith(b + "/") or b.startswith(a + "/")


def cmd_claim(args: argparse.Namespace) -> int:
    root = worktree_root()
    worktree = str(root)
    try:
        requested = [normalize(p, root) for p in args.paths.split(",") if p.strip()]
    except ValueError as exc:
        print(f"GREŠKA — {exc}", file=sys.stderr)
        return 1
    conn = connect()

    active = conn.execute(
        "SELECT task_id, agent, worktree_path, paths FROM claims WHERE status='active'"
    ).fetchall()

    conflicts = []
    for task_id, agent, wt, paths_json in active:
        if task_id == args.task or wt == worktree:
            continue
        for op in json.loads(paths_json):
            for rp in requested:
                if paths_overlap(rp, op):
                    conflicts.append((task_id, agent, op, rp))

    if conflicts:
        print("KONFLIKT — putanje već zauzete:", file=sys.stderr)
        for task_id, agent, op, rp in conflicts:
            print(f"  {rp!r} preklapa se sa {op!r} (task {task_id}, agent {agent})", file=sys.stderr)
        conn.close()
        return 1

    conn.execute(
        "INSERT INTO claims (task_id, agent, branch, worktree_path, paths, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, 'active', ?)",
        (
            args.task,
            args.agent,
            args.branch,
            worktree,
            json.dumps(requested),
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    conn.close()
    print(f"OK — {args.task} ({args.agent}) zauzeo: {', '.join(requested)}")
    return 0


def cmd_release(args: argparse.Namespace) -> int:
    conn = connect()
    cur = conn.execute(
        "UPDATE claims SET status='released', released_at=? WHERE task_id=? AND status='active'",
        (datetime.now(timezone.utc).isoformat(), args.task),
    )
    conn.commit()
    n = cur.rowcount
    conn.close()
    print(f"Oslobođeno {n} claim(ova) za {args.task}.")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    conn = connect()
    rows = conn.execute(
        "SELECT task_id, agent, worktree_path, paths, created_at "
        "FROM claims WHERE status='active' ORDER BY created_at"
    ).fetchall()
    conn.close()
    if not rows:
        print("Nema aktivnih claim-ova.")
        return 0
    for task_id, agent, wt, paths_json, created in rows:
        paths = ", ".join(json.loads(paths_json))
        print(f"{task_id:15} {agent:8} {created}  {wt}")
        print(f"{'':15} paths: {paths}")
    return 0


def _find_conflict(target: str, worktree: str):
    conn = connect()
    rows = conn.execute(
        "SELECT task_id, agent, worktree_path, paths FROM claims WHERE status='active'"
    ).fetchall()
    conn.close()
    for task_id, agent, wt, paths_json in rows:
        if wt == worktree:
            continue
        for op in json.loads(paths_json):
            if paths_overlap(target, op):
                return task_id, agent, wt, op
    return None


def cmd_check(args: argparse.Namespace) -> int:
    root = worktree_root()
    worktree = str(root)
    try:
        target = normalize(args.path, root)
    except ValueError as exc:
        print(f"GREŠKA — {exc}", file=sys.stderr)
        return 1
    conflict = _find_conflict(target, worktree)
    if conflict:
        task_id, agent, wt, op = conflict
        print(
            f"BLOKIRANO — {target!r} zauzet od task {task_id} (agent {agent}, worktree {wt})",
            file=sys.stderr,
        )
        return 1
    return 0


def cmd_hook_check(_args: argparse.Namespace) -> int:
    """Namijenjeno Claude Code PreToolUse hooku. Fail-open na svaku grešku."""
    try:
        payload = json.load(sys.stdin)
        tool_input = payload.get("tool_input", {})
        file_path = tool_input.get("file_path")
        if not file_path:
            return 0
        root = worktree_root()
        worktree = str(root)
        target = normalize(file_path, root)
        conflict = _find_conflict(target, worktree)
        if conflict:
            task_id, agent, wt, op = conflict
            print(
                f"Putanja {target!r} je zauzeta zadatkom {task_id} (agent {agent}, "
                f"worktree {wt}). Provjeri `python scripts/coordination.py status` "
                "prije izmjene.",
                file=sys.stderr,
            )
            return 2
        return 0
    except Exception as exc:  # fail open — alat za koordinaciju, ne security granica
        print(f"coordination hook-check greška (dozvoljeno prolazi): {exc}", file=sys.stderr)
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_claim = sub.add_parser("claim", help="Zauzmi putanje za zadatak")
    p_claim.add_argument("--task", required=True)
    p_claim.add_argument("--agent", required=True, choices=AGENTS)
    p_claim.add_argument("--branch", default=None)
    p_claim.add_argument("--paths", required=True, help="Zarezom odvojene putanje")
    p_claim.set_defaults(func=cmd_claim)

    p_release = sub.add_parser("release", help="Oslobodi claim-ove za zadatak")
    p_release.add_argument("--task", required=True)
    p_release.set_defaults(func=cmd_release)

    p_status = sub.add_parser("status", help="Prikaži aktivne claim-ove")
    p_status.set_defaults(func=cmd_status)

    p_check = sub.add_parser("check", help="Provjeri da li je putanja slobodna")
    p_check.add_argument("--path", required=True)
    p_check.set_defaults(func=cmd_check)

    p_hook = sub.add_parser("hook-check", help="Claude Code PreToolUse hook (stdin JSON)")
    p_hook.set_defaults(func=cmd_hook_check)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
