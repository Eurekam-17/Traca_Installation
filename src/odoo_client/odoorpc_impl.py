"""Implémentation réelle de OdooClientBase via la librairie odoorpc.

⚠️ C'est le SEUL fichier de l'application qui importe odoorpc.
À remplacer par json2_impl.py quand l'External JSON-2 API d'Odoo sera
disponible (estimation 2027 — cf. CLAUDE.md § 2bis-C).
"""

from __future__ import annotations

import logging
from typing import Any

import odoorpc  # type: ignore[import-untyped]

import config

from . import numbering
from .base import (
    Customer,
    OdooClientBase,
    OdooConnectionError,
    OdooDuplicateError,
    OdooWriteError,
    PosteData,
    TracabiliteData,
)

logger = logging.getLogger(__name__)


class OdoorpcClient(OdooClientBase):
    """Client Odoo basé sur odoorpc (JSON-RPC + SSL)."""

    def __init__(self, credentials: config.OdooCredentials) -> None:
        self._creds = credentials
        self._odoo: odoorpc.ODOO | None = None
        self._partner_category_ids: list[int] | None = None

    # ------------------------------------------------------------------ #
    # Authentification
    # ------------------------------------------------------------------ #
    def authenticate(self) -> None:
        """Crée la session odoorpc et s'authentifie via clé API.

        Cf. CLAUDE.md § 2bis-B : on utilise une clé API (et non un mot de
        passe) pour le compte de service traca-bot.
        """
        try:
            self._odoo = odoorpc.ODOO(
                self._creds.host,
                protocol=self._creds.protocol,
                port=self._creds.port,
            )
            self._odoo.login(
                self._creds.db,
                self._creds.login,
                self._creds.api_key,
            )
            logger.info(
                "Connexion Odoo OK (host=%s, db=%s, user=%s)",
                self._creds.host, self._creds.db, self._creds.login,
            )
        except odoorpc.error.RPCError as exc:
            raise OdooConnectionError(
                f"Authentification Odoo refusée : {exc}"
            ) from exc
        except Exception as exc:  # urllib, socket, ssl, etc.
            raise OdooConnectionError(
                f"Connexion Odoo impossible ({self._creds.host}:{self._creds.port}) : {exc}"
            ) from exc

    @property
    def _client(self) -> odoorpc.ODOO:
        """Renvoie la session odoorpc, en exigeant une authentification préalable."""
        if self._odoo is None:
            raise OdooConnectionError(
                "authenticate() doit être appelé avant toute opération."
            )
        return self._odoo

    # ------------------------------------------------------------------ #
    # Clients
    # ------------------------------------------------------------------ #
    def _get_filter_category_ids(self) -> list[int]:
        """Résout les IDs des étiquettes ``Projet en cours`` et ``Clients en Prod``.

        Mis en cache côté instance.
        """
        if self._partner_category_ids is not None:
            return self._partner_category_ids

        try:
            category_model = self._client.env[config.ODOO_MODEL_PARTNER_CATEGORY]
            ids = category_model.search([
                ("name", "in", [
                    config.CUSTOMER_CATEGORY_PROJET,
                    config.CUSTOMER_CATEGORY_PROD,
                ]),
            ])
        except odoorpc.error.RPCError as exc:
            raise OdooConnectionError(
                f"Lecture des étiquettes res.partner.category échouée : {exc}"
            ) from exc

        if not ids:
            logger.warning(
                "Aucune étiquette correspondant à %r ou %r — la liste sera vide.",
                config.CUSTOMER_CATEGORY_PROJET, config.CUSTOMER_CATEGORY_PROD,
            )

        self._partner_category_ids = list(ids)
        return self._partner_category_ids

    def list_active_customers(self) -> list[Customer]:
        """Tous les res.partner portant au moins l'une des deux étiquettes."""
        category_ids = self._get_filter_category_ids()
        if not category_ids:
            return []

        try:
            partner_model = self._client.env[config.ODOO_MODEL_PARTNER]
            records = partner_model.search_read(
                [("category_id", "in", category_ids)],
                ["id", "name"],
                order="name asc",
            )
        except odoorpc.error.RPCError as exc:
            raise OdooConnectionError(
                f"Lecture de res.partner échouée : {exc}"
            ) from exc

        return [Customer(odoo_id=r["id"], name=r["name"]) for r in records]

    # ------------------------------------------------------------------ #
    # Détection de doublon (étape 3 GUI)
    # ------------------------------------------------------------------ #
    def find_poste_by_serial(self, pc_serial: str) -> dict | None:
        """Cherche un installation_log existant pour ce S/N PC.

        Si trouvé, retourne les infos du poste (workstation) lié au log le
        plus récent. C'est le signal d'un poste déjà installé/enregistré
        au moins une fois.
        """
        if not pc_serial:
            return None
        try:
            log_model = self._client.env[config.ODOO_MODEL_TRACABILITE]
            records = log_model.search_read(
                [("x_pc_serial_number", "=", pc_serial)],
                ["x_workstation_id", "x_partner_id", "x_serial_number", "x_installation_date"],
                limit=1,
                order="x_installation_date desc",
            )
        except odoorpc.error.RPCError as exc:
            logger.warning(
                "Recherche de doublon impossible (modèle=%s) : %s",
                config.ODOO_MODEL_TRACABILITE, exc,
            )
            return None

        if not records:
            return None

        record = records[0]
        workstation = record.get("x_workstation_id")
        partner = record.get("x_partner_id")
        return {
            "id": workstation[0] if isinstance(workstation, (list, tuple)) else 0,
            "name": workstation[1] if isinstance(workstation, (list, tuple)) else "?",
            "customer_name": partner[1] if isinstance(partner, (list, tuple)) else "?",
            "previous_serial": record.get("x_serial_number", "?"),
            "previous_date": record.get("x_installation_date", "?"),
        }

    # ------------------------------------------------------------------ #
    # Numérotation
    # ------------------------------------------------------------------ #
    def _existing_serials(self, field_name: str) -> list[str]:
        """Liste toutes les valeurs d'un champ texte du modèle Traçabilité."""
        try:
            model = self._client.env[config.ODOO_MODEL_TRACABILITE]
            records = model.search_read([], [field_name])
        except odoorpc.error.RPCError as exc:
            logger.warning(
                "Lecture %s.%s impossible (modèle peut-être inexistant) : %s",
                config.ODOO_MODEL_TRACABILITE, field_name, exc,
            )
            return []
        return [r.get(field_name) or "" for r in records]

    def next_tracability_serial(self) -> str:
        existing = self._existing_serials("x_serial_number")
        return numbering.next_tracability_serial(existing)

    def next_optical_block_serial(self) -> str:
        existing = self._existing_serials("x_optical_block_serial")
        return numbering.next_optical_block_serial(existing)

    # ------------------------------------------------------------------ #
    # Helpers de résolution Many2one
    # ------------------------------------------------------------------ #
    def _resolve_assist_version_id(self, version_str: str) -> int | bool:
        """Convertit une chaîne ``"2.5.11"`` en ID dans customer.asset.software.version.

        Si la version n'existe pas encore en base, elle est créée à la volée.
        Retourne ``False`` si la chaîne est vide (ce qui correspond à NULL Odoo).
        """
        if not version_str:
            return False
        try:
            model = self._client.env[config.ODOO_MODEL_ASSIST_VERSION]
            ids = model.search([("name", "=", version_str)], limit=1)
            if ids:
                return ids[0]
            new_id = model.create({"name": version_str})
            logger.info(
                "Version Assist '%s' créée dans Odoo (id=%d)", version_str, new_id,
            )
            return new_id
        except odoorpc.error.RPCError as exc:
            raise OdooWriteError(
                f"Résolution version Assist '{version_str}' impossible : {exc}"
            ) from exc

    # ------------------------------------------------------------------ #
    # Créations / lookup
    # ------------------------------------------------------------------ #
    def create_poste_client(self, data: PosteData) -> int:
        """Lookup-or-create d'une fiche customer.asset.workstation.

        Si un poste existe déjà pour ce client avec le même hostname, on
        retourne son ID (pas de doublon). Sinon on en crée un nouveau.
        Mapping cf. § 8 + adaptations Odoo Eurekam.
        """
        try:
            workstation_model = self._client.env[config.ODOO_MODEL_POSTE]
            existing = workstation_model.search(
                [
                    ("partner_id", "=", data.customer_id),
                    ("name", "=", data.description),
                ],
                limit=1,
            )
        except odoorpc.error.RPCError as exc:
            raise OdooWriteError(
                f"Lookup workstation existant échoué : {exc}"
            ) from exc

        if existing:
            workstation_id = existing[0]
            logger.info(
                "Workstation existante réutilisée (id=%d, partner=%d, name=%r)",
                workstation_id, data.customer_id, data.description,
            )
            return workstation_id

        # Création — mapping vers les vrais champs Odoo de customer.asset.workstation
        payload = {
            "partner_id": data.customer_id,
            "name": data.description,                                   # hostname
            "software_fedora_version": data.os_version,                 # PRETTY_NAME OS
            "software_assist_version_id": self._resolve_assist_version_id(data.assist_version),
            "mac_address": data.mac_addresses,                          # enp* concaténées
        }
        return self._create_record(config.ODOO_MODEL_POSTE, payload)

    def create_tracability_record(self, data: TracabiliteData) -> int:
        """Crée la fiche x_customer_asset_installation_log.

        Mapping vers les noms techniques réels du modèle Eurekam.
        Le champ x_partner_id est ``related='x_workstation_id.partner_id'``,
        donc Odoo le calcule automatiquement — pas besoin de l'envoyer.

        Pour les champs Selection (workstation_type, uc_model, mouse_model,
        etc.) Odoo n'accepte que les valeurs techniques définies à la
        création du modèle (ex: 'iso_jce'). Si le draft contient un libellé
        à la place, Odoo retournera une erreur ValueError.
        """
        payload = {
            # Identification
            "x_name": f"{data.serial_number} — {data.installation_date}",
            "x_serial_number": data.serial_number,
            "x_workstation_id": data.workstation_id,
            "x_optical_block_serial": data.optical_block_serial,
            "x_workstation_name": data.workstation_name,
            "x_workstation_type": data.workstation_type or False,
            "x_workstation_serial_number": data.workstation_serial_number,
            "x_installation_date": data.installation_date,
            # UC
            "x_uc_model": data.uc_model or False,
            "x_pc_serial_number": data.pc_serial_number,
            "x_cpu_version": data.cpu_version,
            # Bloc optique
            "x_optical_block_type": data.type_bloc_optique or False,
            # Caméras A et B
            "x_camera_a_model": data.camera_a_model or False,
            "x_camera_a_serial": data.camera_a_serial,
            "x_camera_a_objective": data.camera_a_objective or False,
            "x_camera_a_cable": data.camera_a_cable or False,
            "x_camera_b_model": data.camera_b_model or False,
            "x_camera_b_serial": data.camera_b_serial,
            "x_camera_b_objective": data.camera_b_objective or False,
            "x_camera_b_cable": data.camera_b_cable or False,
            # Caméra de scène
            "x_scene_camera_model": data.scene_camera_model or False,
            "x_scene_camera_serial": data.scene_camera_serial,
            # Accessoires
            "x_mouse_model": data.souris or False,
            "x_power_supply_type": data.bloc_alim or False,
            "x_inox_plot_type": data.plots_inox or False,
            # Snapshots système
            "x_assist_version": data.assist_version,
            "x_mac_addresses": data.mac_addresses,
            "x_os_version": data.os_version,
            # Commentaires libres
            "x_comments": data.comments,
        }
        return self._create_record(config.ODOO_MODEL_TRACABILITE, payload)

    def _create_record(self, model_name: str, payload: dict[str, Any]) -> int:
        """Création générique avec conversion d'erreur."""
        try:
            model = self._client.env[model_name]
            new_id = model.create(payload)
        except odoorpc.error.RPCError as exc:
            raise OdooWriteError(
                f"Création {model_name} refusée par Odoo : {exc}"
            ) from exc

        if not isinstance(new_id, int) or new_id <= 0:
            raise OdooWriteError(
                f"Création {model_name} : ID invalide retourné ({new_id!r})"
            )

        logger.info("Enregistrement créé : %s (id=%d)", model_name, new_id)
        return new_id

    # ------------------------------------------------------------------ #
    # Suppression (rollback)
    # ------------------------------------------------------------------ #
    def delete_poste_client(self, poste_id: int) -> bool:
        """Tentative de rollback : supprime la fiche Postes clients donnée.

        Le compte de service traca-bot doit avoir le droit `unlink` sur le
        modèle. Si ce n'est pas le cas, on log et retourne False (l'utilisateur
        sera prévenu côté GUI).
        """
        try:
            self._client.env[config.ODOO_MODEL_POSTE].unlink([poste_id])
            logger.info("Rollback OK : Postes clients id=%d supprimé.", poste_id)
            return True
        except odoorpc.error.RPCError as exc:
            logger.error(
                "Rollback échoué : impossible de supprimer Postes clients id=%d : %s",
                poste_id, exc,
            )
            return False
