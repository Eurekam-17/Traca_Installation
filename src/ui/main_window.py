"""Fenêtre principale et navigation par étapes (QStackedWidget).

Test de connexion Odoo dès le lancement (cf. CLAUDE.md § 5 étape 1) :
si KO, on bascule sur un écran d'erreur avec un bouton "Réessayer".
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

import config

from odoo_client.base import Customer, OdooClientBase, OdooConnectionError

from .installation_draft import InstallationDraft
from .step1_customer import CustomerStep
from .step2_form import FormStep
from .step3_summary import SummaryStep

logger = logging.getLogger(__name__)


# Indices du QStackedWidget de la fenêtre principale
PAGE_LOADING = 0
PAGE_ERROR = 1
PAGE_STEPS = 2  # contient lui-même un QStackedWidget des 3 étapes


class _OdooLoginWorker(QThread):
    """Tente authenticate() dans un thread séparé pour ne pas bloquer la GUI."""

    finished_ok = Signal()
    failed = Signal(str)

    def __init__(self, client: OdooClientBase, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._client = client

    def run(self) -> None:
        try:
            self._client.authenticate()
        except OdooConnectionError as exc:
            self.failed.emit(str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(f"Erreur inattendue : {exc}")
            return
        self.finished_ok.emit()


class MainWindow(QMainWindow):
    """Fenêtre principale de l'outil de traçabilité Drugcam."""

    def __init__(self, client: OdooClientBase, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._update_window_title()
        self.resize(900, 720)

        self._client = client
        self._draft = InstallationDraft()
        self._login_worker: _OdooLoginWorker | None = None

        # Conteneur racine : bandeau env en haut + QStackedWidget en dessous
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(self._build_env_banner())

        self._stack = QStackedWidget()
        root_layout.addWidget(self._stack, 1)
        self.setCentralWidget(root)

        # — Page chargement
        self._stack.addWidget(self._build_loading_page())
        # — Page erreur connexion
        self._stack.addWidget(self._build_error_page())
        # — Page étapes
        self._steps_stack = self._build_steps_stack()
        self._stack.addWidget(self._steps_stack)

        # Lance le test de connexion dès l'ouverture
        self._try_connect()

    def _update_window_title(self) -> None:
        """Inclut le profil dans le titre de la fenêtre (visible dans la barre des tâches)."""
        env_label = "PROD" if config.is_production() else "STAGING"
        self.setWindowTitle(
            f"Traçabilité installations Drugcam — Eurekam [{env_label}]"
        )

    def _build_env_banner(self) -> QWidget:
        """Bandeau permanent en haut : indique l'environnement Odoo actif.

        - Orange pour staging et tout autre profil non-prod
        - Rouge pour prod (avertissement explicite)
        - Mode mock = mention 'MOCK / DRY-RUN' dans le bandeau
        """
        banner = QLabel()
        banner.setObjectName("env_banner")
        banner.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if config.DRY_RUN:
            text = "🧪 MOCK / DRY-RUN — aucune écriture Odoo réelle"
            bg, fg = "#1565c0", "#ffffff"  # bleu vif
        elif config.is_production():
            text = (
                f"🔴 PRODUCTION — {config.ODOO_HOST} (db: {config.ODOO_DB}) "
                "— toute écriture impactera la base réelle Eurekam"
            )
            bg, fg = "#b71c1c", "#ffffff"  # rouge vif
        else:
            text = (
                f"🟠 {config.active_profile_label()} — {config.ODOO_HOST} "
                f"(db: {config.ODOO_DB}) — environnement de test"
            )
            bg, fg = "#e65100", "#ffffff"  # orange vif

        banner.setText(text)
        banner.setStyleSheet(
            f"background-color: {bg}; color: {fg}; "
            "padding: 6px 12px; font-weight: bold; font-size: 12px;"
        )
        return banner

    # ------------------------------------------------------------------ #
    # Pages d'accueil (chargement / erreur)
    # ------------------------------------------------------------------ #
    def _build_loading_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addStretch()

        title = QLabel("Drugcam — Outil de traçabilité")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        sub = QLabel("Connexion à Odoo…")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet("color: #666; margin-bottom: 20px;")
        layout.addWidget(sub)

        bar = QProgressBar()
        bar.setRange(0, 0)
        bar.setMaximumWidth(400)
        layout.addWidget(bar, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addStretch()
        return page

    def _build_error_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addStretch()

        title = QLabel("❌ Connexion à Odoo impossible")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #b71c1c;")
        layout.addWidget(title)

        self._error_message = QLabel()
        self._error_message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._error_message.setWordWrap(True)
        self._error_message.setMaximumWidth(700)
        self._error_message.setStyleSheet("color: #555;")
        layout.addWidget(self._error_message, alignment=Qt.AlignmentFlag.AlignCenter)

        retry = QPushButton("Réessayer")
        retry.setMinimumWidth(180)
        retry.clicked.connect(self._try_connect)
        layout.addWidget(retry, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addStretch()
        return page

    def _build_steps_stack(self) -> QStackedWidget:
        steps = QStackedWidget()

        self._step1 = CustomerStep(self._client)
        self._step1.customer_selected.connect(self._on_customer_selected)
        self._step1.request_next.connect(lambda: self._goto_step(1))
        steps.addWidget(self._step1)

        self._step2 = FormStep(self._client, self._draft)
        self._step2.draft_updated.connect(lambda d: setattr(self, "_draft", d))
        self._step2.request_next.connect(lambda: self._goto_step(2))
        self._step2.request_back.connect(lambda: self._goto_step(0))
        steps.addWidget(self._step2)

        self._step3 = SummaryStep(self._client, self._draft)
        self._step3.request_back.connect(lambda: self._goto_step(1))
        self._step3.new_installation_requested.connect(self._reset_workflow)
        self._step3.quit_requested.connect(self.close)
        steps.addWidget(self._step3)

        return steps

    # ------------------------------------------------------------------ #
    # Connexion Odoo
    # ------------------------------------------------------------------ #
    def _try_connect(self) -> None:
        self._stack.setCurrentIndex(PAGE_LOADING)
        self._login_worker = _OdooLoginWorker(self._client, self)
        self._login_worker.finished_ok.connect(self._on_login_ok)
        self._login_worker.failed.connect(self._on_login_failed)
        self._login_worker.start()

    def _on_login_ok(self) -> None:
        self._stack.setCurrentIndex(PAGE_STEPS)
        self._goto_step(0)

    def _on_login_failed(self, message: str) -> None:
        logger.error("Connexion Odoo en échec : %s", message)
        self._error_message.setText(
            f"{message}\n\n"
            "Vérifier la connectivité réseau (le PC doit être sur le réseau client) "
            "ainsi que la clé API du compte de service."
        )
        self._stack.setCurrentIndex(PAGE_ERROR)

    # ------------------------------------------------------------------ #
    # Fermeture propre — termine les éventuels QThread en cours
    # ------------------------------------------------------------------ #
    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 — Qt API
        """Évite le warning 'QThread destroyed while still running' à la
        fermeture si un worker est encore actif (auth, collecte, envoi).
        """
        for step in (self._step1, self._step2, self._step3):
            stop = getattr(step, "stop_workers", None)
            if stop is not None:
                stop()
        if self._login_worker is not None and self._login_worker.isRunning():
            self._login_worker.quit()
            self._login_worker.wait(2000)
        super().closeEvent(event)

    # ------------------------------------------------------------------ #
    # Navigation entre étapes
    # ------------------------------------------------------------------ #
    def _goto_step(self, index: int) -> None:
        # Sortie de l'étape courante
        current = self._steps_stack.currentWidget()
        if hasattr(current, "on_left"):
            current.on_left()
        # Entrée dans la nouvelle
        self._steps_stack.setCurrentIndex(index)
        new = self._steps_stack.currentWidget()
        if hasattr(new, "on_entered"):
            new.on_entered()

    # ------------------------------------------------------------------ #
    # Cycle d'installation
    # ------------------------------------------------------------------ #
    def _on_customer_selected(self, customer: Customer) -> None:
        self._draft.customer = customer

    def _reset_workflow(self) -> None:
        """Repart de zéro pour une nouvelle installation."""
        self._draft = InstallationDraft()
        # On reconstruit les étapes 2 et 3 pour repartir d'un état propre
        # (méthode pragmatique : remplacer dans le QStackedWidget).
        old_step2 = self._step2
        old_step3 = self._step3

        self._step2 = FormStep(self._client, self._draft)
        self._step2.request_next.connect(lambda: self._goto_step(2))
        self._step2.request_back.connect(lambda: self._goto_step(0))

        self._step3 = SummaryStep(self._client, self._draft)
        self._step3.request_back.connect(lambda: self._goto_step(1))
        self._step3.new_installation_requested.connect(self._reset_workflow)
        self._step3.quit_requested.connect(self.close)

        self._steps_stack.removeWidget(old_step2)
        self._steps_stack.removeWidget(old_step3)
        old_step2.deleteLater()
        old_step3.deleteLater()
        self._steps_stack.insertWidget(1, self._step2)
        self._steps_stack.insertWidget(2, self._step3)

        self._goto_step(0)
