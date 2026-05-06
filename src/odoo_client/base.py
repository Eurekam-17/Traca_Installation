"""Interface abstraite OdooClientBase et types associés.

Cette interface est l'unique point d'entrée Odoo pour le reste de l'application
(cf. CLAUDE.md § 2bis-C). Aucun import de odoorpc dans ce fichier : la couche
de transport est entièrement encapsulée dans :mod:`odoo_client.odoorpc_impl`
ou :mod:`odoo_client.mock_impl`.

Quand l'External JSON-2 API d'Odoo remplacera /xmlrpc et /jsonrpc en 2027,
seule une nouvelle implémentation de :class:`OdooClientBase` sera à écrire ;
le reste de l'application restera inchangé.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Exceptions du module
# ---------------------------------------------------------------------------
class OdooError(Exception):
    """Base de toutes les erreurs Odoo levées par cette couche."""


class OdooConnectionError(OdooError):
    """Connexion ou authentification Odoo impossible."""


class OdooDuplicateError(OdooError):
    """Le poste à enregistrer existe déjà côté Odoo (même S/N PC).

    Attributs :
        existing_poste_name: nom du poste existant
        existing_customer_name: nom du client associé
        existing_poste_id: ID Odoo du poste existant (pour mise à jour ultérieure)
    """

    def __init__(
        self,
        message: str,
        existing_poste_name: str,
        existing_customer_name: str,
        existing_poste_id: int,
    ) -> None:
        super().__init__(message)
        self.existing_poste_name = existing_poste_name
        self.existing_customer_name = existing_customer_name
        self.existing_poste_id = existing_poste_id


class OdooWriteError(OdooError):
    """Échec d'une opération d'écriture Odoo (create/write)."""


# ---------------------------------------------------------------------------
# Dataclasses de transfert (mapping Odoo cf. CLAUDE.md § 8)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Customer:
    """Client (res.partner) renvoyé par list_active_customers."""

    odoo_id: int
    name: str


@dataclass(frozen=True)
class PosteData:
    """Données à insérer dans la table ``Postes clients`` (§ 8)."""

    customer_id: int  # res.partner ID
    description: str  # Donnée 4 — hostname
    os_version: str  # Donnée 5 — PRETTY_NAME
    assist_version: str  # Donnée 6 — drugcam-libs version
    mac_addresses: str  # Donnée 7 — concaténation '|'


@dataclass(frozen=True)
class TracabiliteData:
    """Données à insérer dans la table ``Traçabilité`` Odoo.

    Mapping vers ``x_customer_asset_installation_log`` (modèle créé pour
    ce projet, lié à customer.asset.workstation via x_workstation_id).

    ⚠️ Pour tous les champs Selection (workstation_type, uc_model, etc.),
    la valeur attendue est la **valeur technique** (snake_case) définie
    dans les fichiers data_options/*.json (clé ``value``) — PAS le libellé.
    Sinon Odoo refusera la création.
    """

    # Identification ------------------------------------------------------
    serial_number: str  # AB + 6 chiffres                  → x_serial_number
    workstation_id: int  # ID workstation existante        → x_workstation_id
    optical_block_serial: str  # 01 + 4 chiffres           → x_optical_block_serial
    workstation_name: str  # Nom du poste (libre)          → x_workstation_name
    workstation_type: str  # Selection (iso_jce, etc.)     → x_workstation_type
    workstation_serial_number: str  # libre                → x_workstation_serial_number
    installation_date: str  # ISO YYYY-MM-DD               → x_installation_date

    # UC -----------------------------------------------------------------
    uc_model: str  # Selection (lian_li, ecw470, ...)      → x_uc_model
    pc_serial_number: str  # libre (dmidecode)             → x_pc_serial_number
    cpu_version: str  #                                    → x_cpu_version

    # Bloc optique --------------------------------------------------------
    type_bloc_optique: str  # Selection (sortie_droite, …) → x_optical_block_type

    # Caméra A -----------------------------------------------------------
    camera_a_model: str  # Selection                       → x_camera_a_model
    camera_a_serial: str  # libre                          → x_camera_a_serial
    camera_a_objective: str  # Selection (f8, f12)         → x_camera_a_objective
    camera_a_cable: str  # Selection                       → x_camera_a_cable

    # Caméra B -----------------------------------------------------------
    camera_b_model: str  #                                 → x_camera_b_model
    camera_b_serial: str  #                                → x_camera_b_serial
    camera_b_objective: str  #                             → x_camera_b_objective
    camera_b_cable: str  #                                 → x_camera_b_cable

    # Caméra de scène ----------------------------------------------------
    scene_camera_model: str  # Selection (microsoft, elp)  → x_scene_camera_model
    scene_camera_serial: str  # libre                      → x_scene_camera_serial

    # Accessoires --------------------------------------------------------
    souris: str  # Selection (sealshield, silicone, …)     → x_mouse_model
    bloc_alim: str  # Selection                            → x_power_supply_type
    plots_inox: str  # Selection (lohmann, _3m)            → x_inox_plot_type

    # Snapshots système (figés au moment de l'installation) --------------
    assist_version: str  #                                 → x_assist_version
    mac_addresses: str  #                                  → x_mac_addresses
    os_version: str = ""  #                                → x_os_version

    # Texte libre --------------------------------------------------------
    comments: str = ""  #                                  → x_comments


# ---------------------------------------------------------------------------
# Interface abstraite
# ---------------------------------------------------------------------------
class OdooClientBase(ABC):
    """Contrat que toute implémentation Odoo doit respecter.

    Les méthodes lèvent des exceptions du module (jamais d'exception odoorpc
    brute remontée à l'appelant — c'est le rôle de l'implémentation de
    convertir ses erreurs natives en :class:`OdooError`).
    """

    @abstractmethod
    def authenticate(self) -> None:
        """Établit la connexion et s'authentifie. Lève OdooConnectionError sinon."""

    @abstractmethod
    def list_active_customers(self) -> list[Customer]:
        """Liste les clients étiquetés ``Projet en cours`` ou ``Clients en Prod``.

        Triés par nom croissant pour affichage direct dans la GUI.
        """

    @abstractmethod
    def find_poste_by_serial(self, pc_serial: str) -> dict | None:
        """Cherche un poste existant par numéro de série PC.

        Retourne ``{'id': int, 'name': str, 'customer_name': str}`` si trouvé,
        ``None`` sinon. Utilisé pour la détection de doublon (étape 3 GUI).
        """

    @abstractmethod
    def next_tracability_serial(self) -> str:
        """Retourne le prochain N° de série équipement disponible (format ``AB000001``)."""

    @abstractmethod
    def next_optical_block_serial(self) -> str:
        """Retourne le prochain N° de bloc optique disponible (format ``010001``)."""

    @abstractmethod
    def create_poste_client(self, data: PosteData) -> int:
        """Crée un enregistrement ``Postes clients`` et retourne son ID Odoo."""

    @abstractmethod
    def create_tracability_record(self, data: TracabiliteData) -> int:
        """Crée un enregistrement ``Traçabilité`` et retourne son ID Odoo."""

    @abstractmethod
    def delete_poste_client(self, poste_id: int) -> bool:
        """Supprime un enregistrement ``Postes clients`` par son ID.

        Utilisé pour le rollback transactionnel quand la création de la fiche
        Traçabilité échoue après une création Postes clients réussie.

        Retourne True si la suppression a réussi, False sinon (l'appelant
        doit alors avertir l'utilisateur de nettoyer manuellement côté Odoo).
        """
