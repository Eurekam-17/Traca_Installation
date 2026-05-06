"""Sélection automatique de l'implémentation Odoo selon l'environnement.

- Si ``DRUGCAM_TRACA_DRY_RUN=1`` : retourne un :class:`MockOdooClient`.
- Sinon : charge les credentials et retourne un :class:`OdoorpcClient`.

Permet à la GUI et aux scripts CLI d'avoir un point d'entrée unique
indépendant de l'implémentation.
"""

from __future__ import annotations

import logging

import config

from .base import OdooClientBase, OdooConnectionError

logger = logging.getLogger(__name__)


def build_client(force_mock: bool = False) -> OdooClientBase:
    """Construit le client Odoo adapté au contexte.

    Args:
        force_mock: si vrai, retourne toujours un mock (utile pour CLI/tests).

    Returns:
        Une instance prête à l'emploi (mais ``authenticate()`` reste à appeler).

    Raises:
        OdooConnectionError: si DRY_RUN est faux et qu'aucun credential n'est trouvé.
    """
    if force_mock or config.DRY_RUN:
        from .mock_impl import MockOdooClient
        logger.info("Client Odoo : mode MOCK (DRY_RUN actif).")
        return MockOdooClient()

    creds = config.load_credentials()
    if creds is None:
        raise OdooConnectionError(
            "Aucun credential Odoo trouvé. Définir la variable d'environnement "
            "DRUGCAM_TRACA_API_KEY ou créer ~/.drugcam-traca/credentials.json."
        )

    # Import paresseux : permet d'utiliser le mode mock sans avoir odoorpc installé.
    from .odoorpc_impl import OdoorpcClient
    logger.info("Client Odoo : mode RÉEL (odoorpc).")
    return OdoorpcClient(creds)
