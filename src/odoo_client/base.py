"""Interface abstraite OdooClientBase et types associés.

Cette interface est l'unique point d'entrée Odoo pour le reste de
l'application. Aucun import de odoorpc dans ce fichier : la couche de
transport est entièrement encapsulée dans :mod:`odoo_client.odoorpc_impl`
ou :mod:`odoo_client.mock_impl`.

Quand l'External JSON-2 API d'Odoo remplacera /xmlrpc et /jsonrpc en 2027,
seule une nouvelle implémentation de :class:`OdooClientBase` sera à écrire ;
le reste de l'application restera inchangé.

Architecture v0.2.0 : tous les champs métier (anciennement répartis entre
PosteData et TracabiliteData) sont stockés sur le **seul** modèle
``customer.asset.workstation`` (module Scalizer ``s6r_eurekam_customer_assets``)
via les champs ``x_*`` créés en mode 'manual' (cf. CHANGELOG.md). Plus de
modèle Traçabilité séparé.
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
# Dataclasses de transfert
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Customer:
    """Client (res.partner) renvoyé par list_active_customers."""

    odoo_id: int
    name: str


@dataclass(frozen=True)
class Product:
    """Article du catalogue Odoo (product.template) — utilisé pour peupler
    les combos Type Caméra / Type UC / Type Objectif depuis l'instance Odoo."""

    odoo_id: int
    name: str


@dataclass(frozen=True)
class PosteData:
    """Données pour créer ou mettre à jour une fiche ``customer.asset.workstation``.

    Mapping intégral vers les champs Odoo (mélange champs natifs Scalizer +
    champs ``x_*`` ajoutés via API au profit du projet Drugcam Traca).

    ⚠️ Pour les champs Selection (workstation_type, uc_model, mouse_model,
    etc.), la valeur attendue est la **valeur technique** (snake_case)
    définie dans les fichiers ``data_options/*.json`` (clé ``value``) —
    PAS le libellé. Sinon Odoo refusera l'écriture.

    Champs natifs Scalizer (déjà présents sur customer.asset.workstation) :
    customer_id, description (= name = hostname), os_version
    (= software_fedora_version), assist_version (= software_assist_version_id,
    Many2one), mac_addresses (= mac_address).

    Champs ``x_*`` ajoutés au modèle (état 'manual') : tous les autres.
    """

    # ----- Champs natifs Scalizer ---------------------------------------
    customer_id: int  # res.partner ID                       → partner_id
    description: str  # hostname                             → name
    os_version: str  # PRETTY_NAME OS                        → software_fedora_version
    assist_version: str  # version Assist                    → software_assist_version_id (M2O)
    mac_addresses: str  # MAC enp* concaténées par '|'       → mac_address

    # ----- Identification matérielle (champs x_* ajoutés) ---------------
    workstation_serial_number: str = ""  # AB+6 chiffres     → x_workstation_serial_number
    workstation_type: str = ""  # Selection (iso_jce, …)     → x_workstation_type
    installation_date: str = ""  # ISO YYYY-MM-DD            → x_installation_date

    # ----- UC ------------------------------------------------------------
    # uc_model_id : ID Odoo dans product.template (article PC). 0 = vide.
    uc_model_id: int = 0
    pc_serial_number: str = ""  # libre (dmidecode)
    cpu_version: str = ""

    # ----- Bloc optique --------------------------------------------------
    optical_block_serial: str = ""  # 01+4 chiffres
    optical_block_type: str = ""  # Selection

    # ----- Caméra A ------------------------------------------------------
    # camera_a_model_id : ID Odoo dans product.template (article caméra). 0 = vide.
    camera_a_model_id: int = 0
    camera_a_serial: str = ""  # libre
    # camera_a_objective_id : ID Odoo dans product.template (article objectif).
    camera_a_objective_id: int = 0
    camera_a_cable: str = ""  # Selection

    # ----- Caméra B ------------------------------------------------------
    camera_b_model_id: int = 0
    camera_b_serial: str = ""
    camera_b_objective_id: int = 0
    camera_b_cable: str = ""

    # ----- Caméra de scène ----------------------------------------------
    # Même catégorie d'article que les caméras A/B (filtre identique côté Odoo).
    scene_camera_model_id: int = 0
    scene_camera_serial: str = ""  # libre

    # ----- Accessoires ---------------------------------------------------
    # souris_id : Many2one product.template (article souris). 0 = vide.
    souris_id: int = 0  #                                    → mouse_model
    bloc_alim: str = ""  # Selection                         → x_power_supply_type
    plots_inox: str = ""  # Selection (lohmann, _3m)         → x_inox_plot_type

    # ----- Texte libre ---------------------------------------------------
    comments: str = ""  #                                    → x_comments


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
        """Liste les clients étiquetés ``1- NEW`` ou ``EN PROD``.

        Triés par nom croissant pour affichage direct dans la GUI.
        """

    @abstractmethod
    def find_poste_by_serial(self, pc_serial: str) -> dict | None:
        """Cherche un poste existant par numéro de série PC (champ x_pc_serial_number).

        Retourne ``{'id': int, 'name': str, 'customer_name': str}`` si trouvé,
        ``None`` sinon. Utilisé pour la détection de doublon (étape 2 GUI).
        """

    @abstractmethod
    def next_tracability_serial(self) -> str:
        """Retourne le prochain N° de série équipement disponible (format ``AB000001``).

        Calculé en lisant le champ ``x_workstation_serial_number`` de toutes
        les fiches workstation existantes.
        """

    @abstractmethod
    def next_optical_block_serial(self) -> str:
        """Retourne le prochain N° de bloc optique disponible (format ``010001``).

        Calculé en lisant le champ ``x_optical_block_serial`` de toutes les
        fiches workstation existantes.
        """

    @abstractmethod
    def create_poste_client(self, data: PosteData) -> int:
        """UPSERT sur ``customer.asset.workstation``.

        Si une fiche workstation existe pour le même client + même hostname,
        elle est **mise à jour** avec les nouvelles valeurs. Sinon, une
        nouvelle fiche est créée. Retourne dans tous les cas l'ID Odoo de
        la workstation.
        """

    # ------------------------------------------------------------------ #
    # Catalogue produits (depuis v0.4.0)
    # ------------------------------------------------------------------ #
    @abstractmethod
    def list_camera_products(self) -> list[Product]:
        """Liste les articles ``product.template`` qui sont des caméras.

        Filtre côté Odoo : ``name =ilike "CAMERA %" OR name =ilike "Caméra %"``.
        Utilisé par la GUI pour peupler les 3 combos (caméra A, B, scène).
        """

    @abstractmethod
    def list_pc_products(self) -> list[Product]:
        """Liste les articles ``product.template`` qui sont des UC / PC.

        Filtre : ``name =ilike "PC %"``.
        Utilisé pour peupler le combo "Type UC".
        """

    @abstractmethod
    def list_objective_products(self) -> list[Product]:
        """Liste les articles ``product.template`` qui sont des objectifs.

        Filtre : ``name =ilike "Objectif %"``.
        Utilisé pour peupler les 2 combos "Type objectif caméra A/B".
        """

    @abstractmethod
    def list_mouse_products(self) -> list[Product]:
        """Liste les articles ``product.template`` qui sont des souris.

        Filtre : ``name =ilike "Souris %"`` (exclut "Tapis de souris").
        Utilisé pour peupler le combo "Type de souris".
        """