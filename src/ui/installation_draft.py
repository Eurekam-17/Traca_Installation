"""Brouillon d'installation transporté entre les étapes 1 → 2 → 3.

Contient :
- le client sélectionné à l'étape 1
- les données système collectées à l'étape 2 (SystemInfo)
- les saisies manuelles du formulaire (étape 2)
- les numéros de série attribués

Méthodes utilitaires pour produire les payloads PosteData / TracabiliteData
à envoyer à l'étape 3.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from odoo_client.base import Customer, PosteData
from system_info import SystemInfo


@dataclass
class InstallationDraft:
    """Toutes les données d'une installation en cours de saisie."""

    # Étape 1 — choix client
    customer: Customer | None = None

    # Étape 2 — collecte automatique + saisies manuelles
    system_info: SystemInfo | None = None

    # Saisies manuelles, deux types depuis v0.4.0 :
    # - Selections classiques (valeur technique snake_case) → str
    # - Many2one product.template (Type Caméra/UC/Objectif) → int (id Odoo, 0 = vide)
    workstation_type: str = ""             # Selection         → workstation_type
    type_bloc_optique: str = ""            # Selection         → optical_block_type
    type_bloc_alim: str = ""               # Selection         → power_supply_type
    type_plot_inox: str = ""               # Selection         → inox_plot_type
    cable_a: str = ""                      # Selection         → camera_a_cable
    cable_b: str = ""                      # Selection         → camera_b_cable
    # Many2one vers product.template (depuis v0.4.0)
    souris_id: int = 0                     # Many2one          → mouse_model
    modele_uc_id: int = 0                  # Many2one          → uc_model
    objectif_a_id: int = 0                 # Many2one          → camera_a_objective
    objectif_b_id: int = 0                 # Many2one          → camera_b_objective
    type_camera_a_id: int = 0              # Many2one          → camera_a_model
    type_camera_b_id: int = 0              # Many2one          → camera_b_model
    scene_camera_model_id: int = 0         # Many2one          → scene_camera_model

    # Saisies libres (Char/Text)
    workstation_name: str = ""             # libre         → x_workstation_name
    workstation_serial_number: str = ""    # libre         → x_workstation_serial_number
    scene_camera_serial: str = ""          # libre         → x_scene_camera_serial
    comments: str = ""                     # text long     → x_comments

    # Numéros de série attribués automatiquement (mais éditables, cf. § 7)
    serial_number: str = ""              # AB + 6 chiffres
    optical_block_serial: str = ""       # 01 + 4 chiffres

    # Surcharges éventuelles des champs auto (l'utilisateur a cliqué ✏️)
    overrides: dict[str, str] = field(default_factory=dict)

    # ------------------------------------------------------------------ #
    # Helpers d'accès — appliquent les overrides au-dessus de SystemInfo
    # ------------------------------------------------------------------ #
    def get(self, attr: str, default: str = "") -> str:
        """Retourne la valeur effective : override ou champ collecté."""
        if attr in self.overrides and self.overrides[attr]:
            return self.overrides[attr]
        if self.system_info is not None:
            value = getattr(self.system_info, attr, None)
            if value is not None:
                return str(value)
        return default

    @property
    def camera_a_model(self) -> str:
        if "camera_a_model" in self.overrides:
            return self.overrides["camera_a_model"]
        if self.system_info and self.system_info.camera_pair:
            return self.system_info.camera_pair.camera_a.product
        return ""

    @property
    def camera_b_model(self) -> str:
        if "camera_b_model" in self.overrides:
            return self.overrides["camera_b_model"]
        if self.system_info and self.system_info.camera_pair:
            return self.system_info.camera_pair.camera_b.product
        return ""

    @property
    def camera_a_serial(self) -> str:
        if "camera_a_serial" in self.overrides:
            return self.overrides["camera_a_serial"]
        if self.system_info and self.system_info.camera_pair:
            return self.system_info.camera_pair.camera_a.serial
        return ""

    @property
    def camera_b_serial(self) -> str:
        if "camera_b_serial" in self.overrides:
            return self.overrides["camera_b_serial"]
        if self.system_info and self.system_info.camera_pair:
            return self.system_info.camera_pair.camera_b.serial
        return ""

    # ------------------------------------------------------------------ #
    # Validation et conversion vers les payloads Odoo
    # ------------------------------------------------------------------ #
    def required_missing(self) -> list[str]:
        """Liste des champs obligatoires manquants, pour activer/désactiver
        le bouton 'Valider et envoyer' de l'étape 2.

        Retourne une liste vide si tout est OK.

        Note : les champs purement informatifs (commentaires, S/N caméra de
        scène "ne servira pas", noms libres) ne sont pas obligatoires.
        """
        missing: list[str] = []
        checks = {
            "Client": self.customer is not None,
            "N° de série PC": bool(self.get("pc_serial_number")),
            "Version CPU": bool(self.get("cpu_version")),
            "Caméra A — S/N": bool(self.camera_a_serial),
            "Caméra B — S/N": bool(self.camera_b_serial),
            "Nom du poste (hostname)": bool(self.get("hostname")),
            "Version OS": bool(self.get("os_pretty_name")),
            "Version Assist": bool(self.get("assist_version")),
            "Adresses MAC": bool(self.get("mac_addresses")),
            "Type d'enceinte/hotte": bool(self.workstation_type),
            "Type UC": bool(self.modele_uc_id),
            "Type de bloc optique": bool(self.type_bloc_optique),
            "Type caméra A": bool(self.type_camera_a_id),
            "Type caméra B": bool(self.type_camera_b_id),
            "Objectif caméra A": bool(self.objectif_a_id),
            "Objectif caméra B": bool(self.objectif_b_id),
            "Type câble caméra A": bool(self.cable_a),
            "Type câble caméra B": bool(self.cable_b),
            "Type de souris": bool(self.souris_id),
            "Type bloc d'alimentation": bool(self.type_bloc_alim),
            "Type de plots inox": bool(self.type_plot_inox),
            "N° de série équipement": bool(self.serial_number),
            "N° bloc optique": bool(self.optical_block_serial),
        }
        for label, ok in checks.items():
            if not ok:
                missing.append(label)
        return missing

    def to_poste_data(self) -> PosteData:
        """Construit le payload complet pour customer.asset.workstation.

        En v0.2.0, c'est l'unique conversion : tous les champs métier
        (matériel, accessoires, snapshot système, commentaires) sont stockés
        sur la fiche workstation directement. Pas de modèle Traçabilité séparé.
        """
        if self.customer is None:
            raise ValueError("Aucun client sélectionné.")
        installation_date = self.get(
            "installation_date",
            self.system_info.installation_date if self.system_info else "",
        )
        return PosteData(
            # Champs natifs Scalizer
            customer_id=self.customer.odoo_id,
            description=self.get("hostname"),
            os_version=self.get("os_pretty_name"),
            assist_version=self.get("assist_version"),
            mac_addresses=self.get("mac_addresses"),
            # Identification matérielle
            workstation_serial_number=self.serial_number,
            workstation_type=self.workstation_type,
            installation_date=installation_date,
            # UC (Many2one product.template depuis v0.4.0)
            uc_model_id=self.modele_uc_id,
            pc_serial_number=self.get("pc_serial_number"),
            cpu_version=self.get("cpu_version"),
            # Bloc optique
            optical_block_serial=self.optical_block_serial,
            optical_block_type=self.type_bloc_optique,
            # Caméra A : modèle/objectif = Many2one product, S/N = collecte sysfs
            camera_a_model_id=self.type_camera_a_id,
            camera_a_serial=self.camera_a_serial,
            camera_a_objective_id=self.objectif_a_id,
            camera_a_cable=self.cable_a,
            # Caméra B
            camera_b_model_id=self.type_camera_b_id,
            camera_b_serial=self.camera_b_serial,
            camera_b_objective_id=self.objectif_b_id,
            camera_b_cable=self.cable_b,
            # Caméra de scène (Many2one product, même filtre que cam A/B)
            scene_camera_model_id=self.scene_camera_model_id,
            scene_camera_serial=self.scene_camera_serial,
            # Accessoires
            souris_id=self.souris_id,
            bloc_alim=self.type_bloc_alim,
            plots_inox=self.type_plot_inox,
            # Texte libre
            comments=self.comments,
        )
