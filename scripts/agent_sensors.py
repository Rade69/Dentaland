#!/usr/bin/env python3
"""Dentaland — arhitektonski senzori (AST guardovi) za DENT-IMPROVE-010.

Hvata klasu problema iz finalnog REF audita: View koji direktno mutira store
mimoilazeći Controller, Controller koji dira SQLAlchemy/session, i Service
koji zavisi od PySide6.

Komande:
    agent_sensors.py --changed           # samo git-izmijenjeni fajlovi
    agent_sensors.py --all               # cijeli relevantan scope
    agent_sensors.py --changed --json    # mašinski output (list[dict])

Senzor NE zamjenjuje testove ni review — samo daje deterministički rani signal.
"""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from contextlib import suppress
from dataclasses import asdict, dataclass
from pathlib import Path

if sys.platform == "win32":
    # Windows konzola po defaultu koristi cp1252/cp437 — puca na š/č/ć/ž/đ.
    for _stream in (sys.stdout, sys.stderr):
        with suppress(Exception):
            _stream.reconfigure(encoding="utf-8")

# ---- Guard definicije ----

# Direktne mutacijske metode store-a (iz F1-F4 nalaza finalnog REF audita).
VIEW_MUTATIONS = {
    "create",
    "update",
    "move",
    "cancel",
    "delete",
    "mark_confirmed",
    "mark_arrived",
    "unmark_arrived",
    "mark_completed",
    "mark_no_show",
    "set_doctor_active",
    "add_service",
    "update_service",
    "set_working_hours",
    "create_time_off",
    "delete_time_off",
}

ARCH_VIEW_RULE = "View -> Controller -> Service"
ARCH_CONTROLLER_RULE = "Controller ne smije persistence"
ARCH_SERVICE_RULE = "Service mora biti UI-neutralan"


@dataclass
class Finding:
    code: str
    severity: str
    file: str
    line: int
    signal: str
    rule: str
    guide: str

    def to_dict(self) -> dict:
        return asdict(self)


# ---- ARCH-VIEW-001 ----


def analyze_arch_view(path: str, source: str) -> list[Finding]:
    """Traži direktne ``self.store.<mutacija>(...)`` pozive u View-u."""
    findings: list[Finding] = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return findings
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute):
            continue
        # func = self.store.<mutacija>  →  func.value = self.store
        if not isinstance(func.value, ast.Attribute):
            continue
        if not isinstance(func.value.value, ast.Name):
            continue
        if func.value.value.id != "self" or func.value.attr != "store":
            continue
        if func.attr not in VIEW_MUTATIONS:
            continue
        findings.append(
            Finding(
                code="ARCH-VIEW-001",
                severity="BLOCK",
                file=path,
                line=node.lineno,
                signal=f"direct mutating store call: self.store.{func.attr}(...)",
                rule=ARCH_VIEW_RULE,
                guide="ARCH-VIEW-001",
            )
        )
    return findings


# ---- ARCH-CONTROLLER-001 ----


def _imports_sqlalchemy(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(
            a.name == "sqlalchemy" or a.name.startswith("sqlalchemy.") for a in node.names
        ):
            return True
        if isinstance(node, ast.ImportFrom) and (
            node.module == "sqlalchemy" or (node.module or "").startswith("sqlalchemy.")
        ):
            return True
    return False


def analyze_arch_controller(path: str, source: str) -> list[Finding]:
    """Traži SQLAlchemy import/select/Session/.execute/.commit u Controller-u."""
    findings: list[Finding] = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return findings

    # SQLAlchemy import (module-level ili unutar funkcije)
    if _imports_sqlalchemy(tree):
        findings.append(
            Finding(
                code="ARCH-CONTROLLER-001",
                severity="BLOCK",
                file=path,
                line=1,
                signal="SQLAlchemy import u Controller-u",
                rule=ARCH_CONTROLLER_RULE,
                guide="ARCH-CONTROLLER-001",
            )
        )

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                if func.id == "select":
                    findings.append(
                        Finding(
                            code="ARCH-CONTROLLER-001",
                            severity="BLOCK",
                            file=path,
                            line=node.lineno,
                            signal="SQLAlchemy select(...) u Controller-u",
                            rule=ARCH_CONTROLLER_RULE,
                            guide="ARCH-CONTROLLER-001",
                        )
                    )
                elif func.id == "Session":
                    findings.append(
                        Finding(
                            code="ARCH-CONTROLLER-001",
                            severity="BLOCK",
                            file=path,
                            line=node.lineno,
                            signal="SQLAlchemy Session(...) u Controller-u",
                            rule=ARCH_CONTROLLER_RULE,
                            guide="ARCH-CONTROLLER-001",
                        )
                    )
            elif isinstance(func, ast.Attribute) and func.attr in ("execute", "commit"):
                findings.append(
                    Finding(
                        code="ARCH-CONTROLLER-001",
                        severity="BLOCK",
                        file=path,
                        line=node.lineno,
                        signal=f"direktna DB operacija: .{func.attr}(...) u Controller-u",
                        rule=ARCH_CONTROLLER_RULE,
                        guide="ARCH-CONTROLLER-001",
                    )
                )
    return findings


# ---- ARCH-SERVICE-001 ----


def analyze_arch_service(path: str, source: str) -> list[Finding]:
    """Traži PySide6 import (bilo koji oblik) u Service sloju."""
    findings: list[Finding] = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return findings
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(
            a.name == "PySide6" or a.name.startswith("PySide6.") for a in node.names
        ):
            findings.append(
                Finding(
                    code="ARCH-SERVICE-001",
                    severity="BLOCK",
                    file=path,
                    line=node.lineno,
                    signal="PySide6 import u Service sloju",
                    rule=ARCH_SERVICE_RULE,
                    guide="ARCH-SERVICE-001",
                )
            )
        if isinstance(node, ast.ImportFrom) and (
            node.module == "PySide6" or (node.module or "").startswith("PySide6.")
        ):
            findings.append(
                Finding(
                    code="ARCH-SERVICE-001",
                    severity="BLOCK",
                    file=path,
                    line=node.lineno,
                    signal="PySide6 import u Service sloju",
                    rule=ARCH_SERVICE_RULE,
                    guide="ARCH-SERVICE-001",
                )
            )
    return findings


# ---- Dispečer ----


def analyze_file(path: str, source: str) -> list[Finding]:
    """Analiziraj jedan fajl i vrati nalaze za guard(ove) koji mu odgovaraju."""
    findings: list[Finding] = []
    normalized = path.replace("\\", "/")
    if normalized.startswith("desktop/views/"):
        findings += analyze_arch_view(path, source)
    elif normalized.startswith("desktop/controllers/"):
        findings += analyze_arch_controller(path, source)
    elif normalized.startswith("src/dentaland/services/"):
        findings += analyze_arch_service(path, source)
    return findings


# ---- CLI ----


def _repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(result.stdout.strip())


def _changed_files(root: Path) -> list[str]:
    tracked = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    return sorted(set(tracked) | set(untracked))


def _all_files(root: Path) -> list[str]:
    scopes = ("desktop/views", "desktop/controllers", "src/dentaland/services")
    files: list[str] = []
    for scope in scopes:
        base = root / scope
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            files.append(path.relative_to(root).as_posix())
    return files


def _run(paths: list[str], root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for rel in paths:
        full = root / rel
        if not full.is_file() or not rel.endswith(".py"):
            continue
        try:
            source = full.read_text(encoding="utf-8")
        except Exception:
            continue
        findings += analyze_file(rel, source)
    return findings


def _print_human(findings: list[Finding]) -> None:
    for finding in findings:
        print(f"[{finding.severity}] {finding.code}")
        print(f"{finding.file}:{finding.line}")
        print()
        print(finding.signal)
        print()
        print(f"Rule: {finding.rule}")
        print()
    total = len(findings)
    noun = "finding" if total == 1 else "findings"
    print(f"Result: {total} blocking {noun}")


def _print_json(findings: list[Finding]) -> None:
    print(json.dumps([f.to_dict() for f in findings], ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dentaland arhitektonski senzori")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--changed", action="store_true", help="samo git-izmijenjeni fajlovi")
    group.add_argument("--all", action="store_true", help="cijeli relevantan scope")
    parser.add_argument("--json", action="store_true", help="mašinski output (list[dict])")
    args = parser.parse_args(argv)

    root = _repo_root()
    paths = _changed_files(root) if args.changed else _all_files(root)

    findings = _run(paths, root)
    if args.json:
        _print_json(findings)
    else:
        _print_human(findings)
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
