"""Récupération des adresses MAC des interfaces filaires (enp*).

Donnée 7 — Adresses MAC ``enp*``.

On utilise ``ip -o link show`` (plus stable à parser que ``ip addr``).
Format final : adresses MAC séparées par ``|`` dans l'ordre de découverte.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess

logger = logging.getLogger(__name__)


# Format strict d'une adresse MAC IEEE 802 (12 hexa séparés par ':')
MAC_RE = re.compile(r"\b([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5})\b")
# On filtre uniquement les interfaces nommées enpXsY (Predictable Network Interface Names)
ENP_LINE_RE = re.compile(r"^\d+:\s+(enp\w+):")


class NetworkError(Exception):
    """Erreur lors de la récupération des adresses MAC."""


def get_enp_mac_addresses() -> list[str]:
    """Liste les adresses MAC de toutes les interfaces ``enp*``.

    Retourne une liste éventuellement vide (la GUI demandera confirmation
    si aucune interface n'est trouvée, cf. CLAUDE.md § 11).
    """
    if shutil.which("ip") is None:
        raise NetworkError(
            "La commande 'ip' est introuvable. "
            "Le paquet 'iproute' est-il installé ? (Standard sur Rocky 9.)"
        )

    try:
        result = subprocess.run(
            ["ip", "-o", "link", "show"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
    except subprocess.CalledProcessError as exc:
        raise NetworkError(
            f"'ip -o link show' a échoué (code {exc.returncode}) : {exc.stderr.strip()}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise NetworkError("'ip -o link show' n'a pas répondu en moins de 5s.") from exc

    macs: list[str] = []
    for line in result.stdout.splitlines():
        if not ENP_LINE_RE.match(line):
            continue
        mac_match = MAC_RE.search(line)
        if not mac_match:
            logger.warning("Interface enp* trouvée sans MAC parseable : %s", line.strip())
            continue
        macs.append(mac_match.group(1).lower())

    logger.info("Interfaces enp* détectées : %d", len(macs))
    return macs


def get_mac_addresses_concatenated() -> str:
    """Donnée 7 — toutes les MAC enp* concaténées, séparateur ``|``.

    Format final attendu côté Odoo : ``aa:bb:cc:dd:ee:ff|11:22:33:44:55:66``.
    Retourne une chaîne vide si aucune interface enp* n'est détectée.
    """
    return "|".join(get_enp_mac_addresses())
