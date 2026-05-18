"""Implémentation factice de OdooClientBase pour DRY_RUN et tests pytest.

Activable au choix par :
- la variable d'environnement ``DRUGCAM_TRACA_DRY_RUN=1``
- l'instanciation directe dans les tests pytest

Aucun appel réseau, aucun import odoorpc — totalement autonome.
Logge ce qui aurait été inséré et garde l'historique en mémoire pour
inspection ultérieure (utile dans les tests).
"""

from __future__ import annotations

import itertools
import logging
from dataclasses import asdict
from typing import Any

from . import numbering
from .base import (
    Customer,
    OdooClientBase,
    PosteData,
    Product,
)


# Produits factices pour peupler les combos en mode mock (cf. v0.4.0)
DEFAULT_FAKE_CAMERAS = [
    Product(odoo_id=2001, name="CAMERA ALVIUM 1800 U-158c color CH C-Mount"),
    Product(odoo_id=2002, name="CAMERA TELI BU130 CF"),
    Product(odoo_id=2003, name="CAMERA TELI BU160 MCF"),
    Product(odoo_id=2004, name="Caméra ELP-USB500W05G-BL100"),
]
DEFAULT_FAKE_PCS = [
    Product(odoo_id=2101, name="PC Fanless eCW470 avec bouton déporté (OLD)"),
    Product(odoo_id=2102, name="PC Fanless eCW475 avec bouton déporté (NEW)"),
]
DEFAULT_FAKE_OBJECTIVES = [
    Product(odoo_id=2201, name="Objectif KOWA LM8JC"),
    Product(odoo_id=2202, name="Objectif KOWA LM12JC"),
]
DEFAULT_FAKE_MICE = [
    Product(odoo_id=2301, name="Souris Silver Storm - Seal Shield"),
    Product(odoo_id=2302, name="Souris Induction FR"),
    Product(odoo_id=2303, name="Souris Induction GPKM-408W-WH"),
]

logger = logging.getLogger(__name__)


# Liste de clients factices — couvre les deux étiquettes mentionnées au § 5.
DEFAULT_FAKE_CUSTOMERS = [
    Customer(odoo_id=101, name="CHU de Lille — Pharmacie centrale"),
    Customer(odoo_id=102, name="Hôpital Européen Georges-Pompidou"),
    Customer(odoo_id=103, name="Institut Gustave Roussy"),
    Customer(odoo_id=104, name="CHRU de Brest — UPCO"),
    Customer(odoo_id=105, name="Centre Léon Bérard (Lyon)"),
]


class MockOdooClient(OdooClientBase):
    """Implémentation en mémoire qui simule Odoo sans appel réseau."""

    def __init__(
        self,
        customers: list[Customer] | None = None,
        existing_postes: list[dict[str, Any]] | None = None,
        existing_workstation_serials: list[str] | None = None,
        existing_optical_block_serials: list[str] | None = None,
    ) -> None:
        self._customers = list(customers) if customers is not None else list(DEFAULT_FAKE_CUSTOMERS)
        self._existing_postes = list(existing_postes) if existing_postes else []
        self._existing_workstation_serials = (
            list(existing_workstation_serials)
            if existing_workstation_serials else ["AB000001", "AB000002", "AB000041"]
        )
        self._existing_optical_block_serials = (
            list(existing_optical_block_serials)
            if existing_optical_block_serials else ["010001", "010003", "010012"]
        )
        # Historique des UPSERT effectués en mode mock — accessible aux tests.
        # Chaque entrée est une PosteData.
        self.upserted_postes: list[PosteData] = []
        self._authenticated = False
        self._id_generator = itertools.count(start=1000)

    def authenticate(self) -> None:
        logger.info("[MOCK] authenticate() — aucun appel réseau, OK.")
        self._authenticated = True

    def list_active_customers(self) -> list[Customer]:
        self._require_auth()
        return list(self._customers)

    def find_poste_by_serial(self, pc_serial: str) -> dict | None:
        self._require_auth()
        if not pc_serial:
            return None
        for poste in self._existing_postes:
            if pc_serial == poste.get("pc_serial"):
                return {
                    "id": poste["id"],
                    "name": poste.get("name", "?"),
                    "customer_name": poste.get("customer_name", "?"),
                    "previous_serial": poste.get("previous_serial", "?"),
                    "previous_date": poste.get("previous_date", "?"),
                }
        return None

    def next_tracability_serial(self) -> str:
        self._require_auth()
        return numbering.next_tracability_serial(self._existing_workstation_serials)

    def next_optical_block_serial(self) -> str:
        self._require_auth()
        return numbering.next_optical_block_serial(self._existing_optical_block_serials)

    def create_poste_client(self, data: PosteData) -> int:
        """Mock UPSERT : on stocke le payload pour inspection dans les tests
        et on retourne un nouvel ID à chaque appel (le mock ne distingue pas
        encore create vs update — peu utile pour les tests unitaires)."""
        self._require_auth()
        new_id = next(self._id_generator)
        self.upserted_postes.append(data)
        # Met à jour les pools de S/N pour que les next_*_serial reflètent
        # le nouvel enregistrement (utile dans les tests d'intégration).
        if data.workstation_serial_number:
            self._existing_workstation_serials.append(data.workstation_serial_number)
        if data.optical_block_serial:
            self._existing_optical_block_serials.append(data.optical_block_serial)
        logger.info(
            "[MOCK] UPSERT customer.asset.workstation (id=%d) :\n%s",
            new_id, _pretty(asdict(data)),
        )
        return new_id

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _require_auth(self) -> None:
        if not self._authenticated:
            raise RuntimeError(
                "MockOdooClient : authenticate() doit être appelé d'abord."
            )

    # ------------------------------------------------------------------ #
    # Catalogue produits factice (v0.4.0+)
    # ------------------------------------------------------------------ #
    def list_camera_products(self) -> list[Product]:
        self._require_auth()
        return list(DEFAULT_FAKE_CAMERAS)

    def list_pc_products(self) -> list[Product]:
        self._require_auth()
        return list(DEFAULT_FAKE_PCS)

    def list_objective_products(self) -> list[Product]:
        self._require_auth()
        return list(DEFAULT_FAKE_OBJECTIVES)

    def list_mouse_products(self) -> list[Product]:
        self._require_auth()
        return list(DEFAULT_FAKE_MICE)

    def add_existing_poste(
        self,
        poste_id: int,
        name: str,
        customer_name: str,
        pc_serial: str,
        previous_serial: str = "AB000099",
        previous_date: str = "2025-01-01",
    ) -> None:
        """Aide pour les tests : injecte un poste pré-existant pour tester
        la détection de doublon. ``pc_serial`` correspond à un poste existant
        avec ce S/N PC."""
        self._existing_postes.append({
            "id": poste_id,
            "name": name,
            "customer_name": customer_name,
            "pc_serial": pc_serial,
            "previous_serial": previous_serial,
            "previous_date": previous_date,
        })


def _pretty(data: dict[str, Any]) -> str:
    """Formattage lisible pour le log d'un dict."""
    return "\n".join(f"    {k:30s} = {v!r}" for k, v in data.items())
