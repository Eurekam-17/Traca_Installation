"""Étape 1 — Sélection du client.

Cf. CLAUDE.md § 5 étape 2 :
- Liste filtrée par étiquettes "Projet en cours" / "Clients en Prod".
- Recherche en temps réel.
- Bouton "Suivant" désactivé tant qu'aucun client sélectionné.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from odoo_client.base import Customer, OdooClientBase, OdooError

from .widgets import BaseStep, NavigationBar, StepHeader

logger = logging.getLogger(__name__)


class _CustomersFetcher(QThread):
    """Charge la liste des clients dans un thread séparé pour ne pas bloquer l'UI."""

    finished_ok = Signal(list)  # list[Customer]
    failed = Signal(str)

    def __init__(self, client: OdooClientBase, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._client = client

    def run(self) -> None:  # noqa: D401 — override Qt
        try:
            customers = self._client.list_active_customers()
        except OdooError as exc:
            self.failed.emit(str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(f"Erreur inattendue : {exc}")
            return
        self.finished_ok.emit(customers)


class CustomerStep(BaseStep):
    """Sélection du client cible de l'installation."""

    customer_selected = Signal(Customer)

    def __init__(self, client: OdooClientBase, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._client = client
        self._customers: list[Customer] = []
        self._fetcher: _CustomersFetcher | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        self._main_layout.addWidget(StepHeader(
            "1 — Sélection du client",
            "Choisir le client chez qui le poste est installé.",
        ))

        # QStackedWidget pour basculer entre 'chargement' et 'liste prête'
        self._stack = QStackedWidget()
        self._main_layout.addWidget(self._stack, 1)

        # — Vue chargement
        loading_view = QWidget()
        loading_layout = QVBoxLayout(loading_view)
        self._loading_label = QLabel("Chargement de la liste des clients depuis Odoo…")
        self._loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_layout.addStretch()
        loading_layout.addWidget(self._loading_label)
        progress = QProgressBar()
        progress.setRange(0, 0)  # mode indéterminé
        loading_layout.addWidget(progress)
        loading_layout.addStretch()
        self._stack.addWidget(loading_view)

        # — Vue liste
        list_view = QWidget()
        list_layout = QVBoxLayout(list_view)
        list_layout.setContentsMargins(0, 0, 0, 0)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Filtrer par nom de client…")
        self._search.textChanged.connect(self._apply_filter)
        list_layout.addWidget(self._search)

        self._list = QListWidget()
        self._list.itemSelectionChanged.connect(self._on_selection_changed)
        list_layout.addWidget(self._list, 1)
        self._stack.addWidget(list_view)

        # — Vue erreur
        error_view = QWidget()
        error_layout = QVBoxLayout(error_view)
        self._error_label = QLabel()
        self._error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._error_label.setWordWrap(True)
        self._error_label.setStyleSheet("color: #b71c1c; font-size: 14px;")
        error_layout.addStretch()
        error_layout.addWidget(self._error_label)
        error_layout.addStretch()
        self._stack.addWidget(error_view)

        # Navigation
        self._nav = NavigationBar(show_back=False)
        self._nav.next_clicked.connect(self._on_next)
        self._nav.set_next_enabled(False)
        self._main_layout.addWidget(self._nav)

    # ------------------------------------------------------------------ #
    # Cycle de vie
    # ------------------------------------------------------------------ #
    def on_entered(self) -> None:
        """À chaque entrée, on recharge la liste (utile en cas de retour
        depuis une étape ultérieure après ajout d'un client côté Odoo)."""
        if not self._customers:
            self._fetch_customers()

    def _fetch_customers(self) -> None:
        self._stack.setCurrentIndex(0)
        self._fetcher = _CustomersFetcher(self._client, self)
        self._fetcher.finished_ok.connect(self._on_customers_loaded)
        self._fetcher.failed.connect(self._on_customers_failed)
        self._fetcher.start()

    def _on_customers_loaded(self, customers: list[Customer]) -> None:
        self._customers = customers
        self._populate_list("")
        if not customers:
            # Pas un échec dur, mais aucun client à choisir : on bascule sur
            # la vue "erreur" plutôt que la vue liste vide qui serait muette.
            self._error_label.setText(
                "⚠️ Aucun client trouvé avec les étiquettes "
                "'Projet en cours' ou 'Clients en Prod'.\n\n"
                "Vérifier dans Odoo qu'au moins un res.partner porte l'une "
                "de ces étiquettes."
            )
            self._stack.setCurrentIndex(2)
        else:
            self._stack.setCurrentIndex(1)

    def _on_customers_failed(self, message: str) -> None:
        logger.error("Chargement clients en échec : %s", message)
        self._error_label.setText(
            f"❌ Impossible de récupérer les clients depuis Odoo.\n\n{message}\n\n"
            "Vérifier la connexion réseau puis redémarrer l'application."
        )
        self._stack.setCurrentIndex(2)

    # ------------------------------------------------------------------ #
    # Filtrage et sélection
    # ------------------------------------------------------------------ #
    def _populate_list(self, filter_text: str) -> None:
        self._list.clear()
        needle = filter_text.lower().strip()
        for cust in self._customers:
            if not needle or needle in cust.name.lower():
                item = QListWidgetItem(cust.name)
                item.setData(Qt.ItemDataRole.UserRole, cust)
                self._list.addItem(item)

    def _apply_filter(self, text: str) -> None:
        self._populate_list(text)

    def _on_selection_changed(self) -> None:
        self._nav.set_next_enabled(self._list.currentItem() is not None)

    def _on_next(self) -> None:
        item = self._list.currentItem()
        if item is None:
            return
        customer: Customer = item.data(Qt.ItemDataRole.UserRole)
        logger.info("Client sélectionné : [%d] %s", customer.odoo_id, customer.name)
        self.customer_selected.emit(customer)
        self.request_next.emit()

    def stop_workers(self) -> None:
        """Termine proprement le QThread de chargement (appelé au closeEvent)."""
        if self._fetcher is not None and self._fetcher.isRunning():
            self._fetcher.quit()
            self._fetcher.wait(2000)
