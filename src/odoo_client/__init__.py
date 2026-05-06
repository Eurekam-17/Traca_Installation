"""Couche d'accès Odoo — strictement isolée du reste de l'application.

Toute communication Odoo passe par OdooClientBase pour anticiper la migration
vers la future External JSON-2 API d'Odoo (cf. CLAUDE.md § 2bis-C, deadline
fin 2027 sur Odoo Online).

Aucun autre module de l'application ne doit importer odoorpc directement.
"""

from .base import OdooClientBase, OdooConnectionError, OdooDuplicateError, PosteData, TracabiliteData

__all__ = [
    "OdooClientBase",
    "OdooConnectionError",
    "OdooDuplicateError",
    "PosteData",
    "TracabiliteData",
]
