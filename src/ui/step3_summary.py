"""Étape 3 — Récapitulatif et envoi vers Odoo.

- Récap de tous les champs.
- Boutons "Modifier" (retour étape 2) et "Confirmer l'envoi".
- UPSERT sur customer.asset.workstation (création si nouveau poste,
  mise à jour sinon).
- Écran de succès avec rappel des numéros + bouton "Nouvelle installation" / "Quitter".

Architecture v0.2.0 : un seul appel API (UPSERT). Plus de modèle Traçabilité
séparé, plus de rollback transactionnel à gérer. L'historique des
modifications est conservé par le chatter natif Odoo.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from odoo_client.base import OdooClientBase, OdooError, PosteData

from .installation_draft import InstallationDraft
from .widgets import BaseStep, NavigationBar, StepHeader, ask_confirmation, show_error

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Worker d'envoi (UPSERT en un seul appel API)
# ---------------------------------------------------------------------------
class _SubmitWorker(QThread):
    finished_ok = Signal(int, str, str)   # workstation_id, serial_eq, serial_block
    failed = Signal(str)

    def __init__(
        self,
        client: OdooClientBase,
        poste_data: PosteData,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._client = client
        self._poste_data = poste_data

    def run(self) -> None:
        try:
            workstation_id = self._client.create_poste_client(self._poste_data)
        except OdooError as exc:
            self.failed.emit(f"UPSERT customer.asset.workstation en échec :\n{exc}")
            return

        self.finished_ok.emit(
            workstation_id,
            self._poste_data.workstation_serial_number,
            self._poste_data.optical_block_serial,
        )


# ---------------------------------------------------------------------------
# Écran d'étape 3
# ---------------------------------------------------------------------------
class SummaryStep(BaseStep):
    """Récapitulatif puis envoi des données à Odoo."""

    new_installation_requested = Signal()
    quit_requested = Signal()

    def __init__(
        self,
        client: OdooClientBase,
        draft: InstallationDraft,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._client = client
        self._draft = draft
        self._worker: _SubmitWorker | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        self._main_layout.addWidget(StepHeader(
            "3 — Récapitulatif",
            "Vérifier les informations puis confirmer l'envoi vers Odoo.",
        ))

        self._stack = QStackedWidget()
        self._main_layout.addWidget(self._stack, 1)

        # Vue 1 — récap
        self._summary_view = QWidget()
        self._summary_layout = QVBoxLayout(self._summary_view)
        self._summary_layout.setContentsMargins(0, 0, 0, 0)
        self._stack.addWidget(self._summary_view)

        # Vue 2 — envoi en cours
        sending_view = QWidget()
        sending_layout = QVBoxLayout(sending_view)
        sending_layout.addStretch()
        sending_layout.addWidget(QLabel("Envoi vers Odoo…"), alignment=Qt.AlignmentFlag.AlignCenter)
        bar = QProgressBar()
        bar.setRange(0, 0)
        sending_layout.addWidget(bar)
        sending_layout.addStretch()
        self._stack.addWidget(sending_view)

        # Vue 3 — succès
        self._success_view = QWidget()
        self._success_layout = QVBoxLayout(self._success_view)
        self._stack.addWidget(self._success_view)

        # Navigation par défaut
        self._nav = NavigationBar(next_text="✓ Confirmer l'envoi")
        self._nav.back_clicked.connect(self._on_back)
        self._nav.next_clicked.connect(self._on_submit)
        self._main_layout.addWidget(self._nav)

    def on_entered(self) -> None:
        # Reconstruit le récap à chaque visite (l'utilisateur a pu modifier l'étape 2)
        self._stack.setCurrentIndex(0)
        self._render_summary()
        self._nav.show()

    # ------------------------------------------------------------------ #
    # Rendu du récap
    # ------------------------------------------------------------------ #
    def _render_summary(self) -> None:
        # Vide le layout existant
        while self._summary_layout.count():
            item = self._summary_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        # — Section Client + Poste
        d = self._draft
        client_box = QGroupBox("Client et poste")
        cf = QFormLayout(client_box)
        cf.addRow("Client", QLabel(d.customer.name if d.customer else "—"))
        cf.addRow("Nom du poste (hostname)", QLabel(d.get("hostname")))
        cf.addRow("Nom du poste (libre)", QLabel(d.workstation_name or "—"))
        cf.addRow("Type d'enceinte/hotte", QLabel(d.workstation_type or "—"))
        cf.addRow("N° de série du poste", QLabel(d.workstation_serial_number or "—"))
        cf.addRow("Date d'installation", QLabel(d.get("installation_date")))
        self._summary_layout.addWidget(client_box)

        # — Numéros attribués
        nums_box = QGroupBox("Numéros attribués")
        nf = QFormLayout(nums_box)
        nf.addRow("N° de série équipement", QLabel(d.serial_number or "—"))
        nf.addRow("N° bloc optique", QLabel(d.optical_block_serial or "—"))
        self._summary_layout.addWidget(nums_box)

        # — UC + Bloc optique
        hw_box = QGroupBox("Matériel")
        hf = QFormLayout(hw_box)
        hf.addRow("Type UC", QLabel(d.modele_uc or "—"))
        hf.addRow("N° de série UC (PC)", QLabel(d.get("pc_serial_number")))
        hf.addRow("Version CPU", QLabel(d.get("cpu_version")))
        hf.addRow("Type de bloc optique", QLabel(d.type_bloc_optique or "—"))
        hf.addRow(
            "Caméra A",
            QLabel(f"Type {d.type_camera_a or '—'} | S/N {d.camera_a_serial or '—'} | "
                   f"Obj {d.objectif_a or '—'} | Câble {d.cable_a or '—'}"),
        )
        hf.addRow(
            "Caméra B",
            QLabel(f"Type {d.type_camera_b or '—'} | S/N {d.camera_b_serial or '—'} | "
                   f"Obj {d.objectif_b or '—'} | Câble {d.cable_b or '—'}"),
        )
        hf.addRow(
            "Caméra de scène",
            QLabel(f"Type {d.scene_camera_model or '—'} | S/N {d.scene_camera_serial or '—'}"),
        )
        hf.addRow("Souris", QLabel(d.souris or "—"))
        hf.addRow("Bloc d'alimentation", QLabel(d.type_bloc_alim or "—"))
        hf.addRow("Plots inox", QLabel(d.type_plot_inox or "—"))
        if d.comments:
            hf.addRow("Commentaires", QLabel(d.comments))
        self._summary_layout.addWidget(hw_box)

        # — Système
        sys_box = QGroupBox("Système")
        sf = QFormLayout(sys_box)
        sf.addRow("Version OS", QLabel(d.get("os_pretty_name")))
        sf.addRow("Version Assist", QLabel(d.get("assist_version")))
        sf.addRow("Adresses MAC", QLabel(d.get("mac_addresses")))
        sf.addRow("Type d'installation", QLabel(d.type_installation))
        self._summary_layout.addWidget(sys_box)

        self._summary_layout.addStretch()

    # ------------------------------------------------------------------ #
    # Navigation et envoi
    # ------------------------------------------------------------------ #
    def _on_back(self) -> None:
        self.request_back.emit()

    def _on_submit(self) -> None:
        if not ask_confirmation(
            self,
            "Confirmer l'envoi",
            "Les données vont être envoyées à Odoo et ne pourront plus être modifiées "
            "directement depuis cet outil.\n\nContinuer ?",
        ):
            return

        try:
            poste_data = self._draft.to_poste_data()
        except ValueError as exc:
            show_error(self, "Données incomplètes", str(exc))
            return

        self._stack.setCurrentIndex(1)
        self._nav.set_next_enabled(False)
        self._nav.set_back_enabled(False)

        self._worker = _SubmitWorker(self._client, poste_data, self)
        self._worker.finished_ok.connect(self._on_submit_done)
        self._worker.failed.connect(self._on_submit_failed)
        self._worker.start()

    def _on_submit_failed(self, message: str) -> None:
        logger.error("Envoi Odoo en échec : %s", message)
        self._stack.setCurrentIndex(0)
        self._nav.set_next_enabled(True)
        self._nav.set_back_enabled(True)
        show_error(self, "Envoi vers Odoo en échec", message)

    def _on_submit_done(
        self,
        workstation_id: int,
        serial_eq: str,
        serial_block: str,
    ) -> None:
        logger.info(
            "Envoi Odoo OK : workstation_id=%d, eq=%s, block=%s",
            workstation_id, serial_eq, serial_block,
        )
        self._render_success(serial_eq, serial_block)
        self._stack.setCurrentIndex(2)
        self._nav.hide()

    def stop_workers(self) -> None:
        """Termine proprement le QThread d'envoi (appelé au closeEvent)."""
        if self._worker is not None and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(2000)

    def _render_success(self, serial_eq: str, serial_block: str) -> None:
        # Vide le layout précédent
        while self._success_layout.count():
            item = self._success_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        title = QLabel("✅ Installation enregistrée avec succès")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #1b5e20;")
        self._success_layout.addStretch()
        self._success_layout.addWidget(title)

        # Les IDs Odoo internes (poste_id, traca_id) ne sont pas affichés au
        # technicien : ils n'ont pas de valeur métier et brouillent la lecture.
        # Ils restent disponibles dans le log pour le support.
        details = QLabel(
            f"<p style='text-align:center;'>"
            f"Numéro de série équipement attribué : <b>{serial_eq}</b><br>"
            f"Numéro de bloc optique attribué : <b>{serial_block}</b>"
            f"</p>"
        )
        details.setAlignment(Qt.AlignmentFlag.AlignCenter)
        details.setTextFormat(Qt.TextFormat.RichText)
        self._success_layout.addWidget(details)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        new_btn = QPushButton("Nouvelle installation")
        new_btn.clicked.connect(self.new_installation_requested.emit)
        btn_row.addWidget(new_btn)

        quit_btn = QPushButton("Quitter")
        quit_btn.clicked.connect(self.quit_requested.emit)
        btn_row.addWidget(quit_btn)

        btn_row.addStretch()
        self._success_layout.addLayout(btn_row)
        self._success_layout.addStretch()
