"""Widgets et helpers Qt réutilisables par les écrans des 5 étapes.

Conventions :
- Tous les libellés sont en français (cf. CLAUDE.md § 2).
- Les widgets exposent des signaux clairs pour communiquer avec la fenêtre principale.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

import config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Étape de base : sert de classe parente à tous les écrans du QStackedWidget
# ---------------------------------------------------------------------------
class BaseStep(QWidget):
    """Classe de base pour un écran d'étape.

    Signaux émis :
        request_next() : l'étape demande à passer à la suivante (Suivant cliqué).
        request_back() : l'étape demande à revenir en arrière.
    """

    request_next = Signal()
    request_back = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(20, 20, 20, 20)
        self._main_layout.setSpacing(15)

    def on_entered(self) -> None:
        """Hook appelé chaque fois que l'écran devient visible."""

    def on_left(self) -> None:
        """Hook appelé chaque fois que l'écran est quitté."""


# ---------------------------------------------------------------------------
# En-tête commun
# ---------------------------------------------------------------------------
class StepHeader(QWidget):
    """Bandeau titre + sous-titre affiché en haut de chaque étape."""

    def __init__(self, title: str, subtitle: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        if subtitle:
            sub_label = QLabel(subtitle)
            sub_label.setWordWrap(True)
            sub_label.setStyleSheet("color: #555;")
            layout.addWidget(sub_label)


# ---------------------------------------------------------------------------
# Barre de navigation (Précédent / Suivant)
# ---------------------------------------------------------------------------
class NavigationBar(QWidget):
    """Barre de boutons en bas d'étape (Précédent / Suivant ou personnalisé)."""

    back_clicked = Signal()
    next_clicked = Signal()

    def __init__(
        self,
        next_text: str = "Suivant ▶",
        show_back: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 0)

        self._back_button = QPushButton("◀ Précédent")
        self._back_button.clicked.connect(self.back_clicked.emit)
        if not show_back:
            self._back_button.hide()
        layout.addWidget(self._back_button)

        layout.addStretch()

        self._next_button = QPushButton(next_text)
        self._next_button.setMinimumWidth(180)
        self._next_button.setDefault(True)
        self._next_button.clicked.connect(self.next_clicked.emit)
        layout.addWidget(self._next_button)

    def set_next_enabled(self, enabled: bool) -> None:
        self._next_button.setEnabled(enabled)

    def set_next_text(self, text: str) -> None:
        self._next_button.setText(text)

    def set_back_enabled(self, enabled: bool) -> None:
        self._back_button.setEnabled(enabled)


# ---------------------------------------------------------------------------
# Chargement des fichiers JSON data_options
# ---------------------------------------------------------------------------
class DataOptionsError(Exception):
    """Erreur lors du chargement d'un fichier JSON data_options."""


def _candidate_paths(filename: str) -> list[Path]:
    """Ordre de recherche : copie utilisateur, puis valeurs embarquées."""
    return [
        config.USER_DATA_OPTIONS_DIR / filename,
        config.EMBEDDED_DATA_OPTIONS_DIR / filename,
    ]


def load_data_option(filename: str) -> dict:
    """Charge un fichier JSON data_options.

    Retourne ``{"label": str, "options": [{"display": str, "value": str}, …]}``.
    Lève :class:`DataOptionsError` si aucun fichier n'est trouvé ou s'il
    est mal formé. La GUI catch et propose la saisie libre dans ce cas
    (cf. CLAUDE.md § 9).
    """
    for path in _candidate_paths(filename):
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise DataOptionsError(
                f"Fichier {path} mal formé : {exc.msg} (ligne {exc.lineno})"
            ) from exc

        if "options" not in data or not isinstance(data["options"], list):
            raise DataOptionsError(
                f"Fichier {path} : clé 'options' absente ou invalide."
            )

        logger.debug("Chargé %s depuis %s (%d options)", filename, path, len(data["options"]))
        return data

    raise DataOptionsError(
        f"Aucun fichier '{filename}' trouvé dans "
        f"{config.USER_DATA_OPTIONS_DIR} ni {config.EMBEDDED_DATA_OPTIONS_DIR}."
    )


def populate_combo(combo: QComboBox, data_options: dict, allow_free_text: bool = True) -> None:
    """Remplit un QComboBox à partir d'un dict data_options."""
    combo.clear()
    combo.addItem("— Sélectionner —", userData="")
    for option in data_options.get("options", []):
        combo.addItem(option["display"], userData=option.get("value", option["display"]))
    combo.setEditable(allow_free_text)
    if combo.lineEdit() is not None:
        combo.lineEdit().setPlaceholderText("Sélectionner ou saisir librement")


# ---------------------------------------------------------------------------
# Helpers boîtes de dialogue
# ---------------------------------------------------------------------------
def show_error(parent: QWidget | None, title: str, message: str) -> None:
    """Affiche une boîte d'erreur Qt en français."""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Critical)
    box.setWindowTitle(title)
    box.setText(message)
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    box.exec()


def show_warning(parent: QWidget | None, title: str, message: str) -> None:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle(title)
    box.setText(message)
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    box.exec()


def ask_confirmation(parent: QWidget | None, title: str, message: str) -> bool:
    """Boîte oui/non. Retourne True si l'utilisateur a confirmé."""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle(title)
    box.setText(message)
    box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    box.setDefaultButton(QMessageBox.StandardButton.No)
    return box.exec() == QMessageBox.StandardButton.Yes


# ---------------------------------------------------------------------------
# Ligne champ : libellé + widget + indicateur d'obligation
# ---------------------------------------------------------------------------
def make_field_row(label_text: str, widget: QWidget, required: bool = False) -> QWidget:
    """Compose une ligne formulaire : étiquette à gauche, widget à droite."""
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)

    label = QLabel(label_text + (" *" if required else ""))
    if required:
        label.setStyleSheet("font-weight: bold;")
    label.setMinimumWidth(220)
    layout.addWidget(label)

    widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    layout.addWidget(widget, 1)
    return row
