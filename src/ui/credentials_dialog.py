"""Boîte de dialogue de saisie des credentials Odoo au premier lancement.

Si aucune source de credentials n'est trouvée pour le profil actif, on demande
la clé API au technicien et on la sauvegarde dans
``~/.drugcam-traca/credentials.<profile>.json`` avec permissions 600.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

import config


class CredentialsDialog(QDialog):
    """Demande au technicien la clé API et les paramètres de connexion Odoo.

    Le sélecteur d'environnement permet de basculer entre staging et prod
    avant la saisie : les champs Host/DB/Login se mettent à jour
    automatiquement.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Configuration Odoo — première utilisation")
        self.setMinimumWidth(560)

        layout = QVBoxLayout(self)

        intro = QLabel(
            "Aucune clé API n'a été trouvée pour ce profil. Choisissez "
            "l'environnement Odoo et saisissez la clé API du compte de "
            "service (généralement <b>traca-bot@eurekam.fr</b>).<br><br>"
            "Les informations seront sauvegardées dans "
            "<code>~/.drugcam-traca/credentials.&lt;profil&gt;.json</code> "
            "(permissions 600). Un fichier distinct est utilisé pour chaque "
            "environnement."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        form = QFormLayout()

        # Sélecteur de profil (staging / prod / …)
        self._env = QComboBox()
        for key, profile in config.PROFILES.items():
            self._env.addItem(str(profile["label"]), userData=key)
        # Sélectionne le profil actuellement actif
        idx = self._env.findData(config.ACTIVE_PROFILE)
        if idx >= 0:
            self._env.setCurrentIndex(idx)
        self._env.currentIndexChanged.connect(self._on_env_changed)
        form.addRow("Environnement", self._env)

        # Avertissement quand on est sur prod
        self._warning = QLabel("")
        self._warning.setWordWrap(True)
        form.addRow("", self._warning)

        self._host = QLineEdit(config.ODOO_HOST)
        form.addRow("Host", self._host)
        self._db = QLineEdit(config.ODOO_DB)
        form.addRow("Base de données", self._db)
        self._login = QLineEdit(config.ODOO_LOGIN)
        form.addRow("Login (compte de service)", self._login)
        self._api_key = QLineEdit()
        self._api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key.setPlaceholderText("Clé API générée depuis le profil Odoo")
        form.addRow("Clé API", self._api_key)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Enregistrer")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Met à jour l'avertissement initial selon le profil actif
        self._on_env_changed()

    def _on_env_changed(self, *_args: object) -> None:
        """Quand on change de profil, met à jour les champs et l'avertissement."""
        env_key = self._env.currentData()
        if env_key not in config.PROFILES:
            return
        p = config.PROFILES[env_key]
        self._host.setText(str(p["host"]))
        self._db.setText(str(p["db"]))
        self._login.setText(str(p["login"]))

        if env_key == "prod":
            self._warning.setText(
                "<span style='color:#b71c1c; font-weight:bold;'>"
                "⚠️ ENVIRONNEMENT DE PRODUCTION — toute écriture impactera "
                "la base réelle Eurekam."
                "</span>"
            )
        else:
            self._warning.setText(
                "<span style='color:#e65100;'>"
                f"🟠 Environnement de test : {p['label']}"
                "</span>"
            )

    def selected_env(self) -> str:
        """Retourne la clé du profil sélectionné (ex 'staging', 'prod')."""
        return str(self._env.currentData())

    def _on_accept(self) -> None:
        if not self._api_key.text().strip():
            self._api_key.setStyleSheet("border: 1px solid red;")
            return
        self.accept()

    def to_credentials(self) -> config.OdooCredentials:
        return config.OdooCredentials(
            host=self._host.text().strip(),
            db=self._db.text().strip(),
            login=self._login.text().strip(),
            api_key=self._api_key.text().strip(),
            protocol=config.ODOO_PROTOCOL,
            port=config.ODOO_PORT,
        )
