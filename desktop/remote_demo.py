"""Daljinski demo (DENT-IMPROVE-020) — SAMO panel "Novi zahtjevi",
povezan na pravi backend preko HTTP API-ja.

Potpuno odvojen ulaz od glavne aplikacije (``desktop/app.py``) — NE
mijenja/dijeli kod sa ``MainWindow``, koji ostaje isključivo lokalan
(SQLite) za stvarnu upotrebu u ordinaciji. Ovaj prozor postoji SAMO da
se pokaže/testira: javna forma → ovaj panel → potvrda → email/Telegram.

Pokretanje::

    set DENTALAND_REMOTE_API_BASE=https://169-58-208-91.nip.io
    python desktop/remote_demo.py

``DENTALAND_REMOTE_API_BASE`` MORA biti postavljena eksplicitno — nema
hardkodiran default u kodu (trenutna VPS adresa je TEST-only, vidi
CLAUDE.md "Otvorena pitanja" — hosting odluka nije donesena).
"""

from __future__ import annotations

import os
import sys

from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from desktop.api_client import AuthenticationFailedError, ConnectionFailedError, DentalandApiClient
from desktop.remote_store import RemoteRequestsStore
from desktop.views.dialogs.base_dialog import BaseDialog
from desktop.views.requests_panel import DashboardPanels

ENV_API_BASE = "DENTALAND_REMOTE_API_BASE"


class LoginDialog(BaseDialog):
    """Prijava (RBAC, isti mehanizam kao backend/web) prije otvaranja panela."""

    def __init__(self, client: DentalandApiClient) -> None:
        super().__init__("Prijava — Dentaland daljinski demo", icon="user")
        self._client = client

        self.body_layout().addWidget(QLabel("Korisničko ime"))
        self.username_input = QLineEdit()
        self.body_layout().addWidget(self.username_input)

        self.body_layout().addWidget(QLabel("Lozinka"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.body_layout().addWidget(self.password_input)

        self.add_secondary_button("Otkaži")
        login_button = self.add_footer_button("Prijavi se", "dialogPrimaryButton")
        login_button.clicked.connect(self._attempt_login)

    def _attempt_login(self) -> None:
        self.clear_error()
        username = self.username_input.text().strip()
        password = self.password_input.text()
        if not username or not password:
            self.show_error("Unesi korisničko ime i lozinku.")
            return
        try:
            self._client.login(username, password)
        except AuthenticationFailedError as exc:
            self.show_error(str(exc))
            return
        except ConnectionFailedError as exc:
            self.show_error(str(exc))
            return
        self.accept()


class RemoteDemoWindow(QMainWindow):
    """Minimalan prozor — samo panel zahtjeva, ništa drugo (vidi Task Contract)."""

    def __init__(self, store: RemoteRequestsStore) -> None:
        super().__init__()
        self.setWindowTitle("Dentaland — daljinski demo (samo Novi zahtjevi)")
        container = QWidget()
        layout = QVBoxLayout(container)
        info = QLabel(
            "Daljinski demo — prikazuje SAMO zahtjeve sa javne forme. "
            "Raspored/podešavanja nisu dio ovog prozora."
        )
        info.setWordWrap(True)
        layout.addWidget(info)
        panels = DashboardPanels(store, self)
        layout.addWidget(panels)
        self.setCentralWidget(container)
        self.resize(360, 640)


def main() -> int:
    from PySide6.QtWidgets import QApplication

    base_url = os.environ.get(ENV_API_BASE)
    if not base_url:
        print(
            f"Greška: {ENV_API_BASE} nije postavljena. Primjer:\n"
            f"  set {ENV_API_BASE}=https://169-58-208-91.nip.io\n"
            f"  python desktop/remote_demo.py",
            file=sys.stderr,
        )
        return 1

    app = QApplication(sys.argv)
    client = DentalandApiClient(base_url)

    login_dialog = LoginDialog(client)
    if login_dialog.exec() != LoginDialog.DialogCode.Accepted:
        client.close()
        return 0

    store = RemoteRequestsStore(client)
    window = RemoteDemoWindow(store)
    window.show()

    try:
        return app.exec()
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
