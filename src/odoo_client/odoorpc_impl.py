"""Implémentation réelle de OdooClientBase via la librairie odoorpc.

⚠️ C'est le SEUL fichier de l'application qui importe odoorpc.
À remplacer par json2_impl.py quand l'External JSON-2 API d'Odoo sera
disponible (estimation 2027 — cf. CLAUDE.md § 2bis-C).

Architecture v0.2.0 : un seul modèle ``customer.asset.workstation`` avec
tous les champs. Le ``create_poste_client`` est en réalité un **UPSERT** :
si une workstation existe déjà avec le même **N° de série PC**
(``pc_serial_number``), elle est mise à jour ; sinon, elle est créée. Plus
de modèle Traçabilité séparé, plus de rollback transactionnel à gérer.

⚠️ La clé d'unicité est le N° de série PC, PAS le nom du poste (hostname) :
plusieurs machines d'un même client peuvent porter le même hostname
(``assist1``…), ce qui écraserait une autre fiche. Cette clé est cohérente
avec ``find_poste_by_serial`` (détection de doublon, étape 2 GUI).
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
    OdooWriteError,
    PosteData,
    Product,
)


# Domaines de filtrage product.template (cohérents avec ceux du module Odoo)
_DOMAIN_CAMERA = ["|", ("name", "=ilike", "CAMERA %"), ("name", "=ilike", "Caméra %")]
_DOMAIN_PC = [("name", "=ilike", "PC %")]
_DOMAIN_OBJECTIVE = [("name", "=ilike", "Objectif %")]
_DOMAIN_MOUSE = [("name", "=ilike", "Souris %")]

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
        """Crée la session odoorpc et s'authentifie via clé API."""
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
        """Résout les IDs des étiquettes clients à filtrer (cf. config.CUSTOMER_CATEGORIES).

        Inclut ``1- NEW``, ``EN PROD`` et ``DISTRIBUTEUR``. Résultat caché.
        """
        if self._partner_category_ids is not None:
            return self._partner_category_ids

        try:
            category_model = self._client.env[config.ODOO_MODEL_PARTNER_CATEGORY]
            ids = category_model.search([
                ("name", "in", list(config.CUSTOMER_CATEGORIES)),
            ])
        except odoorpc.error.RPCError as exc:
            raise OdooConnectionError(
                f"Lecture des étiquettes res.partner.category échouée : {exc}"
            ) from exc

        if not ids:
            logger.warning(
                "Aucune étiquette correspondant à %r — la liste sera vide.",
                config.CUSTOMER_CATEGORIES,
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
    # Détection de doublon (étape 2 GUI)
    # ------------------------------------------------------------------ #
    def find_poste_by_serial(self, pc_serial: str) -> dict | None:
        """Cherche une fiche workstation portant déjà ce N° de série PC.

        Recherche directe sur ``customer.asset.workstation.pc_serial_number``.
        Si trouvée, signal d'un poste déjà installé/enregistré au moins une fois.
        """
        if not pc_serial:
            return None
        try:
            workstation_model = self._client.env[config.ODOO_MODEL_POSTE]
            records = workstation_model.search_read(
                [("pc_serial_number", "=", pc_serial)],
                ["id", "name", "partner_id", "workstation_serial_number",
                 "installation_date"],
                limit=1,
            )
        except odoorpc.error.RPCError as exc:
            logger.warning(
                "Recherche de doublon impossible (champ pc_serial_number "
                "introuvable ?) : %s", exc,
            )
            return None

        if not records:
            return None

        record = records[0]
        partner = record.get("partner_id")
        return {
            "id": record["id"],
            "name": record.get("name", "?"),
            "customer_name": partner[1] if isinstance(partner, (list, tuple)) else "?",
            "previous_serial": record.get("workstation_serial_number") or "?",
            "previous_date": record.get("installation_date") or "?",
        }

    # ------------------------------------------------------------------ #
    # Numérotation — lecture directe sur customer.asset.workstation
    # ------------------------------------------------------------------ #
    def _max_workstation_serial(self, field_name: str) -> str:
        """Retourne la valeur MAX d'un champ texte sur customer.asset.workstation.

        Tri alphabétique descendant avec limit=1 : fonctionne correctement
        pour les formats AB000001 et 010001 car ils sont zéro-paddés à largeur
        fixe, donc l'ordre alphabétique == l'ordre numérique.

        Retourne une chaîne vide si le champ est absent (module pas installé)
        ou si aucun enregistrement ne le remplit — le calcul MAX+1 retournera
        alors le premier numéro de la série (ex. AB000001).
        """
        try:
            model = self._client.env[config.ODOO_MODEL_POSTE]
            records = model.search_read(
                [(field_name, "!=", False)],
                [field_name],
                order=f"{field_name} desc",
                limit=1,
            )
        except odoorpc.error.RPCError as exc:
            logger.warning(
                "Lecture MAX de %s.%s impossible (champ absent ?) : %s",
                config.ODOO_MODEL_POSTE, field_name, exc,
            )
            return ""
        if not records:
            return ""
        return records[0].get(field_name) or ""

    def next_tracability_serial(self) -> str:
        max_val = self._max_workstation_serial("workstation_serial_number")
        return numbering.next_tracability_serial([max_val] if max_val else [])

    def next_optical_block_serial(self) -> str:
        max_val = self._max_workstation_serial("optical_block_serial")
        return numbering.next_optical_block_serial([max_val] if max_val else [])

    # ------------------------------------------------------------------ #
    # Helpers de résolution Many2one
    # ------------------------------------------------------------------ #
    def _resolve_assist_version_id(self, version_str: str) -> int | bool:
        """Convertit ``"2.5.11"`` en ID dans customer.asset.software.version.

        Crée la version à la volée si elle n'existe pas. Retourne ``False``
        si la chaîne est vide (Odoo NULL).
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
    # UPSERT customer.asset.workstation
    # ------------------------------------------------------------------ #
    def create_poste_client(self, data: PosteData) -> int:
        """UPSERT sur customer.asset.workstation.

        Stratégie :
        1. Lookup d'une fiche existante par ``pc_serial_number`` (clé d'unicité
           matérielle, cohérente avec ``find_poste_by_serial``)
        2. Construction du payload complet (champs natifs Scalizer + champs Drugcam)
        3. Si fiche trouvée → ``write()`` sur cet ID
        4. Sinon → ``create()`` d'une nouvelle fiche

        ⚠️ La clé est le N° de série PC, PAS (client + hostname) : plusieurs
        machines d'un même client peuvent partager le même hostname
        (``assist1``…). Utiliser le hostname comme clé écraserait la fiche
        d'une autre machine → perte de donnée.

        Cas limite : si ``pc_serial_number`` est vide (``dmidecode`` indisponible,
        improbable en root sur Rocky 9), aucune fiche n'est mise à jour — on crée
        systématiquement une nouvelle fiche pour ne JAMAIS risquer d'écraser la
        mauvaise.
        """
        workstation_model = self._client.env[config.ODOO_MODEL_POSTE]
        existing: list[int] = []
        if data.pc_serial_number:
            try:
                existing = workstation_model.search(
                    [("pc_serial_number", "=", data.pc_serial_number)],
                    limit=1,
                )
            except odoorpc.error.RPCError as exc:
                raise OdooWriteError(
                    f"Lookup workstation existant échoué : {exc}"
                ) from exc
        else:
            logger.warning(
                "Aucun N° de série PC disponible : création d'une nouvelle "
                "fiche workstation sans lookup (évite tout écrasement de fiche "
                "existante)."
            )

        payload = self._build_workstation_payload(data)

        try:
            if existing:
                workstation_id = existing[0]
                workstation_model.browse(workstation_id).write(payload)
                logger.info(
                    "Workstation existante mise à jour (id=%d, pc_serial=%r, "
                    "partner=%d, name=%r)",
                    workstation_id, data.pc_serial_number, data.customer_id,
                    data.description,
                )
                return workstation_id

            new_id = workstation_model.create(payload)
        except odoorpc.error.RPCError as exc:
            raise OdooWriteError(
                f"UPSERT customer.asset.workstation refusé par Odoo : {exc}"
            ) from exc

        if not isinstance(new_id, int) or new_id <= 0:
            raise OdooWriteError(
                f"Création workstation : ID invalide retourné ({new_id!r})"
            )

        logger.info(
            "Workstation créée (id=%d, pc_serial=%r, partner=%d, name=%r)",
            new_id, data.pc_serial_number, data.customer_id, data.description,
        )
        return new_id

    def _build_workstation_payload(self, data: PosteData) -> dict[str, Any]:
        """Construit le payload complet pour customer.asset.workstation.

        - Les Selections vides sont envoyées en ``False`` (Odoo refuserait ``""``).
        - Les Many2one (camera_*_model, uc_model, camera_*_objective,
          scene_camera_model) attendent un ID entier ; ``0`` est traité comme
          ``False`` (NULL Odoo).
        """
        return {
            # Champs natifs Scalizer
            "partner_id": data.customer_id,
            "name": data.description,
            "software_fedora_version": data.os_version,
            "software_assist_version_id": self._resolve_assist_version_id(data.assist_version),
            "mac_address": data.mac_addresses,
            # Identification matérielle
            "workstation_serial_number": data.workstation_serial_number,
            "workstation_type": data.workstation_type or False,
            "installation_date": data.installation_date or False,
            # UC (Many2one product.template)
            "uc_model": data.uc_model_id or False,
            "pc_serial_number": data.pc_serial_number,
            "cpu_version": data.cpu_version,
            # Bloc optique
            "optical_block_serial": data.optical_block_serial,
            "optical_block_type": data.optical_block_type or False,
            # Caméra A (Many2one product.template pour modèle + objectif)
            "camera_a_model": data.camera_a_model_id or False,
            "camera_a_serial": data.camera_a_serial,
            "camera_a_objective": data.camera_a_objective_id or False,
            "camera_a_cable": data.camera_a_cable or False,
            # Caméra B
            "camera_b_model": data.camera_b_model_id or False,
            "camera_b_serial": data.camera_b_serial,
            "camera_b_objective": data.camera_b_objective_id or False,
            "camera_b_cable": data.camera_b_cable or False,
            # Caméra de scène (Many2one product.template, même filtre que cam A/B)
            "scene_camera_model": data.scene_camera_model_id or False,
            "scene_camera_serial": data.scene_camera_serial,
            # Accessoires (mouse_model = Many2one product.template depuis v0.5.0)
            "mouse_model": data.souris_id or False,
            "power_supply_type": data.bloc_alim or False,
            "inox_plot_type": data.plots_inox or False,
            # Commentaires libres
            "comments": data.comments,
        }

    # ------------------------------------------------------------------ #
    # Catalogue produits (depuis v0.4.0)
    # ------------------------------------------------------------------ #
    def _list_products(self, domain: list, label: str) -> list[Product]:
        """Helper : exécute search_read sur product.template avec un domaine."""
        try:
            model = self._client.env["product.template"]
            records = model.search_read(domain, ["id", "name"], order="name asc")
        except odoorpc.error.RPCError as exc:
            logger.warning("Lecture product.template (%s) impossible : %s", label, exc)
            return []
        return [Product(odoo_id=r["id"], name=r["name"]) for r in records]

    def list_camera_products(self) -> list[Product]:
        return self._list_products(_DOMAIN_CAMERA, "caméras")

    def list_pc_products(self) -> list[Product]:
        return self._list_products(_DOMAIN_PC, "PC")

    def list_objective_products(self) -> list[Product]:
        return self._list_products(_DOMAIN_OBJECTIVE, "objectifs")

    def list_mouse_products(self) -> list[Product]:
        return self._list_products(_DOMAIN_MOUSE, "souris")
