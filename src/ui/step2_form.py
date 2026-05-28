"""Étape 2 — Collecte automatique puis formulaire prérempli.

Cf. CLAUDE.md § 5 étapes 3 et 4 :
- Au début : barre de progression pendant la collecte (~5-10 s).
- Vérification de doublon dès que le S/N PC est connu.
- Champs auto-détectés en lecture seule + bouton ✏️ pour modifier.
- Champs manuels = QComboBox depuis JSON.
- N° série équipement et N° bloc optique préremplis (next_*).
- Bouton "Suivant" désactivé tant que les obligatoires ne sont pas remplis.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from odoo_client.base import OdooClientBase, OdooError
from system_info import collect_all
from system_info.collector import SystemInfo

from .installation_draft import InstallationDraft
from .widgets import (
    BaseStep,
    DataOptionsError,
    NavigationBar,
    StepHeader,
    ask_confirmation,
    load_data_option,
    populate_combo,
    show_warning,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Worker thread : collecte système + lookup doublon + next_serials
# ---------------------------------------------------------------------------
class _CollectionWorker(QThread):
    """Effectue dans un thread séparé : collecte, recherche doublon, next_serials."""

    finished_ok = Signal(SystemInfo, dict, str, str)  # info, duplicate?, next_eq, next_block
    failed = Signal(str)

    def __init__(self, client: OdooClientBase, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._client = client

    def run(self) -> None:
        try:
            info = collect_all()
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(f"Collecte système en échec : {exc}")
            return

        duplicate: dict = {}
        try:
            if info.pc_serial_number:
                found = self._client.find_poste_by_serial(info.pc_serial_number)
                if found:
                    duplicate = found
        except OdooError as exc:
            logger.warning("Lookup doublon impossible : %s — on continue.", exc)

        try:
            next_eq = self._client.next_tracability_serial()
            next_block = self._client.next_optical_block_serial()
        except OdooError as exc:
            self.failed.emit(f"Calcul des numéros de série en échec : {exc}")
            return

        self.finished_ok.emit(info, duplicate, next_eq, next_block)


# ---------------------------------------------------------------------------
# Écran d'étape 2
# ---------------------------------------------------------------------------
class FormStep(BaseStep):
    """Collecte + formulaire prérempli."""

    draft_updated = Signal(InstallationDraft)

    # ───────────────────────────────────────────────────────────────────
    # Champs Selection (valeurs locales depuis data_options/*.json).
    # L'ordre des entrées détermine l'ordre d'affichage dans le formulaire.
    # ⚠️ Les `value` des JSON DOIVENT correspondre aux valeurs techniques
    # des Selections Odoo, sinon les inserts seront rejetés.
    # ───────────────────────────────────────────────────────────────────
    DATA_OPTIONS_FILES: dict[str, str] = {
        "workstation_type.json": "workstation_type",
        "type_bloc_optique.json": "type_bloc_optique",
        "cable_a.json": "cable_a",
        "cable_b.json": "cable_b",
        "type_bloc_alimentation.json": "type_bloc_alim",
        "type_plot_inox.json": "type_plot_inox",
    }

    DATA_OPTIONS_LABELS: dict[str, str] = {
        "workstation_type": "Type d'enceinte/hotte",
        "type_bloc_optique": "Type de bloc optique",
        "cable_a": "Type câble caméra A",
        "cable_b": "Type câble caméra B",
        "type_bloc_alim": "Bloc d'alimentation",
        "type_plot_inox": "Plots inox",
    }

    # ───────────────────────────────────────────────────────────────────
    # Champs Many2one product.template (depuis v0.4.0).
    # La liste d'options est chargée dynamiquement depuis Odoo via
    # OdooClientBase.list_*_products() — pas de JSON local.
    # Mapping : attribut du draft → (libellé, méthode du client)
    # ───────────────────────────────────────────────────────────────────
    PRODUCT_FIELDS: list[tuple[str, str, str]] = [
        # (attr du draft, libellé, nom de méthode sur le client Odoo)
        ("souris_id", "Type de souris", "list_mouse_products"),
        ("modele_uc_id", "Type UC", "list_pc_products"),
        ("type_camera_a_id", "Type caméra A", "list_camera_products"),
        ("objectif_a_id", "Objectif caméra A", "list_objective_products"),
        ("type_camera_b_id", "Type caméra B", "list_camera_products"),
        ("objectif_b_id", "Objectif caméra B", "list_objective_products"),
        ("scene_camera_model_id", "Type caméra de scène", "list_camera_products"),
    ]

    # Champs libres saisis manuellement (Char/Text) — mapping draft attr → label
    FREE_TEXT_FIELDS: dict[str, str] = {
        "workstation_name": "Nom du poste (libre, défaut = hostname)",
        "workstation_serial_number": "N° de série du poste",
        "scene_camera_serial": "N° de série caméra de scène",
        "comments": "Commentaires (texte libre)",
    }

    def __init__(
        self,
        client: OdooClientBase,
        draft: InstallationDraft,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._client = client
        self._draft = draft
        self._worker: _CollectionWorker | None = None
        self._auto_field_widgets: dict[str, QLineEdit] = {}
        self._manual_combos: dict[str, QComboBox] = {}
        # Combos pour les Many2one product.template (clé = attr du draft)
        self._product_combos: dict[str, QComboBox] = {}
        self._products_loaded: bool = False  # chargés à la 1ère entrée dans l'étape
        self._free_text_inputs: dict[str, QLineEdit | QTextEdit] = {}
        self._serial_eq_input: QLineEdit | None = None
        self._serial_block_input: QLineEdit | None = None

        self._build_ui()

    # ------------------------------------------------------------------ #
    # Construction UI
    # ------------------------------------------------------------------ #
    def _build_ui(self) -> None:
        self._main_layout.addWidget(StepHeader(
            "2 — Collecte et saisie",
            "Vérifier les valeurs auto-détectées et compléter les champs manquants.",
        ))

        self._stack = QStackedWidget()
        self._main_layout.addWidget(self._stack, 1)

        # Vue 1 — collecte en cours
        self._stack.addWidget(self._build_loading_view())

        # Vue 2 — formulaire (rempli après collecte)
        self._form_widget = self._build_form_view()
        self._stack.addWidget(self._form_widget)

        # Navigation
        self._nav = NavigationBar(next_text="Voir le récapitulatif ▶")
        self._nav.back_clicked.connect(self.request_back.emit)
        self._nav.next_clicked.connect(self._on_next)
        self._nav.set_next_enabled(False)
        self._main_layout.addWidget(self._nav)

    def _build_loading_view(self) -> QWidget:
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.addStretch()
        self._loading_label = QLabel("Collecte des informations système en cours…")
        self._loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._loading_label)
        bar = QProgressBar()
        bar.setRange(0, 0)
        layout.addWidget(bar)
        layout.addStretch()
        return view

    def _build_form_view(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        # — Section Données auto-détectées
        auto_box = QGroupBox("Données auto-détectées (cliquer ✏️ pour corriger)")
        auto_form = QFormLayout(auto_box)
        auto_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        for attr, label in (
            ("pc_serial_number", "N° de série PC"),
            ("cpu_version", "Version CPU"),
            ("hostname", "Nom du poste"),
            ("os_pretty_name", "Version OS"),
            ("assist_version", "Version Assist"),
            ("mac_addresses", "Adresses MAC enp*"),
            # Les modèles caméra (camera_a_model / camera_b_model) ne sont plus
            # affichés ici depuis v0.4.0 : ils sont des Many2one product.template
            # dans Odoo. Le modèle brut détecté est affiché en tooltip sur les
            # combos "Type caméra A/B" dans la section Articles catalogue Odoo.
            ("camera_a_serial", "Caméra A — S/N"),
            ("camera_b_serial", "Caméra B — S/N"),
        ):
            row, line_edit = self._build_auto_row(attr)
            self._auto_field_widgets[attr] = line_edit
            auto_form.addRow(label + " *", row)

        layout.addWidget(auto_box)

        # — Section Saisies manuelles (Selections Odoo)
        manual_box = QGroupBox("Choix matériel (* = obligatoire)")
        manual_form = QFormLayout(manual_box)
        manual_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        for filename, attr in self.DATA_OPTIONS_FILES.items():
            combo = QComboBox()
            try:
                data = load_data_option(filename)
                # Pas de saisie libre : Odoo n'acceptera que les valeurs
                # techniques exactes des Selections (ex 'iso_jce').
                populate_combo(combo, data, allow_free_text=False)
            except DataOptionsError as exc:
                logger.warning("Fichier %s indisponible : %s — saisie libre activée.", filename, exc)
                combo.setEditable(True)
                combo.lineEdit().setPlaceholderText(
                    f"⚠️ {filename} introuvable — saisie libre (vérifier valeur Odoo)"
                )

            # Présélection de la valeur déjà présente dans le draft.
            # Utile si le draft a été partiellement rempli (retour en arrière).
            # Le technicien peut toujours changer.
            current_value = getattr(self._draft, attr, "")
            if current_value:
                idx = combo.findData(current_value)
                if idx >= 0:
                    combo.setCurrentIndex(idx)

            combo.currentIndexChanged.connect(self._on_field_changed)
            if combo.lineEdit() is not None:
                combo.lineEdit().textEdited.connect(lambda _: self._on_field_changed())
            self._manual_combos[attr] = combo
            manual_form.addRow(self.DATA_OPTIONS_LABELS[attr] + " *", combo)

        layout.addWidget(manual_box)

        # — Section Articles Odoo (Many2one product.template) ─────────────
        # Les combos sont créés vides ici ; ils sont peuplés depuis Odoo
        # dans _load_products(), appelé au premier on_entered() — une fois
        # l'authentification Odoo terminée.
        product_box = QGroupBox("Articles catalogue Odoo (* = obligatoire)")
        product_form = QFormLayout(product_box)
        product_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        for attr, label, _method in self.PRODUCT_FIELDS:
            combo = QComboBox()
            combo.addItem("— Chargement en cours… —", userData=0)
            combo.setEnabled(False)
            combo.currentIndexChanged.connect(self._on_field_changed)
            self._product_combos[attr] = combo
            product_form.addRow(label + " *", combo)

        layout.addWidget(product_box)

        # — Section Champs libres (texte saisi par le technicien)
        free_box = QGroupBox("Saisies libres (optionnelles)")
        free_form = QFormLayout(free_box)
        free_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        for attr, label in self.FREE_TEXT_FIELDS.items():
            if attr == "comments":
                widget = QTextEdit()
                widget.setMaximumHeight(80)
                widget.setPlaceholderText("Notes libres sur cette installation…")
                widget.textChanged.connect(self._on_field_changed)
            else:
                widget = QLineEdit()
                widget.textChanged.connect(self._on_field_changed)
            self._free_text_inputs[attr] = widget
            free_form.addRow(label, widget)
        layout.addWidget(free_box)

        # — Section Numéros de série attribués
        serials_box = QGroupBox("Numéros de série attribués (modifiables)")
        serials_form = QFormLayout(serials_box)
        self._serial_eq_input = QLineEdit()
        self._serial_eq_input.textChanged.connect(self._on_field_changed)
        serials_form.addRow("N° de série équipement *", self._serial_eq_input)
        self._serial_block_input = QLineEdit()
        self._serial_block_input.textChanged.connect(self._on_field_changed)
        serials_form.addRow("N° bloc optique *", self._serial_block_input)
        layout.addWidget(serials_box)

        layout.addStretch()
        scroll.setWidget(container)
        return scroll

    def _build_auto_row(self, attr: str) -> tuple[QWidget, QLineEdit]:
        """Une ligne 'champ auto' = QLineEdit en lecture seule + bouton ✏️."""
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)

        line_edit = QLineEdit()
        line_edit.setReadOnly(True)
        line_edit.setStyleSheet("background-color: #f5f5f5;")
        line_edit.textChanged.connect(self._on_field_changed)
        layout.addWidget(line_edit, 1)

        edit_btn = QPushButton("✏️")
        edit_btn.setFixedWidth(36)
        edit_btn.setToolTip("Corriger cette valeur auto-détectée")
        edit_btn.clicked.connect(lambda: self._toggle_edit(attr, line_edit))
        layout.addWidget(edit_btn)
        return row, line_edit

    # ------------------------------------------------------------------ #
    # Cycle de vie
    # ------------------------------------------------------------------ #
    def on_entered(self) -> None:
        # Charger les produits Odoo la première fois (client authentifié à ce stade)
        if not self._products_loaded:
            self._load_products()

        # Si on revient depuis l'étape 3, on ne relance pas la collecte
        if self._draft.system_info is None:
            self._stack.setCurrentIndex(0)
            self._start_collection()
        else:
            self._stack.setCurrentIndex(1)
            self._refresh_validation()

    def _load_products(self) -> None:
        """Charge les listes de produits depuis Odoo et peuple les combos Many2one.

        Appelé une seule fois depuis on_entered(), après que la connexion Odoo
        soit établie (authenticate() est terminé avant d'afficher les étapes).
        Utilise un cache par méthode pour éviter plusieurs appels API quand des
        combos partagent la même source (ex. les 3 combos caméra partagent
        list_camera_products).
        """
        product_cache: dict[str, list] = {}

        for attr, label, method_name in self.PRODUCT_FIELDS:
            combo = self._product_combos.get(attr)
            if combo is None:
                continue
            combo.clear()
            combo.addItem("— Sélectionner —", userData=0)

            try:
                if method_name not in product_cache:
                    product_cache[method_name] = getattr(self._client, method_name)()
                products = product_cache[method_name]

                if not products:
                    logger.warning(
                        "Aucun produit retourné par %s — combo %s sera vide.",
                        method_name, attr,
                    )
                    combo.setEnabled(False)
                    combo.setToolTip(
                        "Aucun article correspondant dans le catalogue Odoo. "
                        "Créer des produits avec le bon préfixe (CAMERA / PC / "
                        "Objectif / Souris) dans Odoo → Achats → Drugcam."
                    )
                else:
                    for p in products:
                        combo.addItem(p.name, userData=p.odoo_id)
                    combo.setEnabled(True)

            except Exception as exc:  # noqa: BLE001
                logger.error("Chargement produits %s en échec : %s", method_name, exc)
                combo.setEnabled(False)
                combo.setToolTip(f"Erreur de chargement depuis Odoo : {exc}")

            # Présélection si le draft contient déjà un id (retour depuis étape 3)
            current_id = getattr(self._draft, attr, 0)
            if current_id:
                idx = combo.findData(current_id)
                if idx >= 0:
                    combo.setCurrentIndex(idx)

        self._products_loaded = True

    def _start_collection(self) -> None:
        self._worker = _CollectionWorker(self._client, self)
        self._worker.finished_ok.connect(self._on_collection_done)
        self._worker.failed.connect(self._on_collection_failed)
        self._worker.start()

    def _on_collection_failed(self, message: str) -> None:
        logger.error("Collecte étape 2 en échec : %s", message)
        self._loading_label.setText(f"❌ {message}\n\nRevenir à l'étape précédente.")

    def _on_collection_done(
        self,
        info: SystemInfo,
        duplicate: dict,
        next_eq: str,
        next_block: str,
    ) -> None:
        self._draft.system_info = info

        # Surfacer les erreurs non bloquantes via un avertissement
        if info.errors:
            non_blocking = {k: v for k, v in info.errors.items() if k != "cameras_too_many"}
            if non_blocking:
                show_warning(
                    self,
                    "Collecte partielle",
                    "Certaines données n'ont pas pu être collectées :\n\n"
                    + "\n".join(f"• {k} : {v}" for k, v in non_blocking.items())
                    + "\n\nVous pouvez les corriger manuellement avec le bouton ✏️.",
                )

        # Détection de doublon — bloquant si confirmé
        if duplicate:
            confirmed = ask_confirmation(
                self,
                "Poste déjà enregistré",
                "⚠️  Cette machine est déjà enregistrée dans Odoo.\n\n"
                f"Poste existant : {duplicate.get('name', '?')}\n"
                f"Client          : {duplicate.get('customer_name', '?')}\n\n"
                "Voulez-vous tout de même continuer (création d'un nouvel enregistrement) ?",
            )
            if not confirmed:
                # Reset complet du draft : sans cela, on_entered au prochain
                # passage verrait system_info != None et n'effectuerait pas de
                # nouvelle collecte, laissant le formulaire vide.
                self._draft.system_info = None
                self._draft.overrides.clear()
                self.request_back.emit()
                return

        # Préremplir les numéros
        self._serial_eq_input.setText(next_eq)
        self._serial_block_input.setText(next_block)

        # Préremplir les champs auto
        self._populate_auto_fields(info)

        self._stack.setCurrentIndex(1)
        self._refresh_validation()

    def _populate_auto_fields(self, info: SystemInfo) -> None:
        mapping = {
            "pc_serial_number": info.pc_serial_number or "",
            "cpu_version": info.cpu_version or "",
            "hostname": info.hostname or "",
            "os_pretty_name": info.os_pretty_name or "",
            "assist_version": info.assist_version or "",
            "mac_addresses": info.mac_addresses or "",
        }
        if info.camera_pair:
            mapping["camera_a_serial"] = info.camera_pair.camera_a.serial
            mapping["camera_b_serial"] = info.camera_pair.camera_b.serial
            # Le modèle brut détecté (ex. "Allied Vision Alvium 1800 U-319c")
            # est affiché en tooltip sur les combos Many2one pour aider
            # le technicien à choisir le bon produit dans le catalogue Odoo.
            for combo_attr, detected in (
                ("type_camera_a_id", info.camera_pair.camera_a.product),
                ("type_camera_b_id", info.camera_pair.camera_b.product),
            ):
                combo = self._product_combos.get(combo_attr)
                if combo and detected:
                    existing = combo.toolTip()
                    prefix = f"Modèle détecté : {detected}"
                    if existing and "Modèle détecté" not in existing:
                        combo.setToolTip(f"{prefix}\n{existing}")
                    else:
                        combo.setToolTip(prefix)
        else:
            mapping["camera_a_serial"] = ""
            mapping["camera_b_serial"] = ""

        for attr, value in mapping.items():
            widget = self._auto_field_widgets.get(attr)
            if widget is not None:
                widget.setText(value)

    # ------------------------------------------------------------------ #
    # Édition d'un champ auto + validation
    # ------------------------------------------------------------------ #
    def _toggle_edit(self, attr: str, line_edit: QLineEdit) -> None:
        """Bascule un champ auto en édition ou repasse en lecture seule."""
        if line_edit.isReadOnly():
            line_edit.setReadOnly(False)
            line_edit.setStyleSheet("background-color: #fff8e1;")
            line_edit.setFocus()
        else:
            line_edit.setReadOnly(True)
            line_edit.setStyleSheet("background-color: #f5f5f5;")
            self._draft.overrides[attr] = line_edit.text()

    def _on_field_changed(self, *args) -> None:  # noqa: D401
        """Slot appelé à chaque modification de champ : met à jour le draft + nav."""
        self._sync_draft()
        self._refresh_validation()

    def _sync_draft(self) -> None:
        """Recopie l'état des widgets dans le draft."""
        for attr, widget in self._auto_field_widgets.items():
            value = widget.text().strip()
            if value:
                self._draft.overrides[attr] = value

        for attr, combo in self._manual_combos.items():
            text = combo.currentText().strip()
            # On ignore le placeholder "— Sélectionner —"
            if text.startswith("—") or not text:
                value = ""
            else:
                # Si une userData existe (sélection liste), on la privilégie.
                # C'est la valeur technique acceptée par Odoo pour les Selections.
                data = combo.currentData()
                value = data if data else text
            setattr(self._draft, attr, value)

        # Combos produits Odoo (Many2one product.template, depuis v0.4.0)
        # currentData() retourne l'ID Odoo (int) ou 0 si placeholder sélectionné.
        for attr, combo in self._product_combos.items():
            product_id = combo.currentData() or 0
            setattr(self._draft, attr, int(product_id))

        # Champs libres (Char/Text)
        for attr, widget in self._free_text_inputs.items():
            if isinstance(widget, QTextEdit):
                value = widget.toPlainText().strip()
            else:
                value = widget.text().strip()
            setattr(self._draft, attr, value)

        if self._serial_eq_input is not None:
            self._draft.serial_number = self._serial_eq_input.text().strip()
        if self._serial_block_input is not None:
            self._draft.optical_block_serial = self._serial_block_input.text().strip()

    def _refresh_validation(self) -> None:
        missing = self._draft.required_missing()
        self._nav.set_next_enabled(not missing)
        if missing:
            self._nav.set_next_text(f"Encore {len(missing)} champ(s) à remplir")
        else:
            self._nav.set_next_text("Voir le récapitulatif ▶")

    def _on_next(self) -> None:
        self._sync_draft()
        if self._draft.required_missing():
            return
        self.draft_updated.emit(self._draft)
        self.request_next.emit()

    def stop_workers(self) -> None:
        """Termine proprement le QThread de collecte (appelé au closeEvent)."""
        if self._worker is not None and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(2000)
