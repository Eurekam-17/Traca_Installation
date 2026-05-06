"""Récupération du nom du poste, de la version OS et de la version Assist.

Données 4, 5 et 6 du CLAUDE.md § 6.
"""

from __future__ import annotations

import logging
import re
import shutil
import socket
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


OS_RELEASE_FILE = Path("/etc/os-release")
DRUGCAM_LIBS_VERSION_RE = re.compile(r"drugcam-libs-(\d+\.\d+\.\d+)")


class OsReleaseError(Exception):
    """Erreur lors de la lecture des informations OS."""


def get_hostname() -> str:
    """Donnée 4 — Nom du poste (hostname).

    On utilise ``socket.gethostname()`` plutôt que de lire ``/etc/hostname``
    directement : c'est strictement équivalent sur Rocky 9 et beaucoup plus
    portable pour les tests Windows.
    """
    hostname = socket.gethostname().strip()
    if not hostname:
        raise OsReleaseError("Hostname vide — vérifier la configuration du poste.")
    return hostname


def get_os_pretty_name() -> str:
    """Donnée 5 — Version OS (``PRETTY_NAME`` de /etc/os-release).

    Exemple : ``Rocky Linux 9.3 (Blue Onyx)``.
    """
    if not OS_RELEASE_FILE.is_file():
        raise OsReleaseError(
            f"{OS_RELEASE_FILE} introuvable. "
            "Le poste tourne-t-il bien sous une distribution standard ?"
        )

    try:
        content = OS_RELEASE_FILE.read_text(encoding="utf-8")
    except OSError as exc:
        raise OsReleaseError(f"Impossible de lire {OS_RELEASE_FILE} : {exc}") from exc

    for line in content.splitlines():
        if line.startswith("PRETTY_NAME="):
            value = line.split("=", 1)[1].strip()
            # Retirer guillemets simples ou doubles éventuels
            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                value = value[1:-1]
            if value:
                return value

    raise OsReleaseError(f"Champ PRETTY_NAME absent de {OS_RELEASE_FILE}.")


def get_assist_version() -> str:
    r"""Donnée 6 — Version Assist, extraite de ``rpm -qa | grep drugcam-libs``.

    Sortie type de rpm : ``drugcam-libs-2.5.11.662-2.el9.x86_64``.
    On extrait via la regex ``drugcam-libs-(\d+\.\d+\.\d+)`` les 3 premiers
    blocs de version, soit ``2.5.11``.

    Lève :class:`OsReleaseError` si le paquet n'est pas installé (cas qui
    sera transmis à la GUI pour avertir le technicien — cf. § 11).
    """
    if shutil.which("rpm") is None:
        raise OsReleaseError(
            "La commande 'rpm' est introuvable. "
            "Le poste n'est probablement pas une distribution RHEL/Rocky."
        )

    try:
        result = subprocess.run(
            ["rpm", "-qa", "drugcam-libs"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except subprocess.CalledProcessError as exc:
        raise OsReleaseError(
            f"'rpm -qa drugcam-libs' a échoué (code {exc.returncode}) : "
            f"{exc.stderr.strip()}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise OsReleaseError("'rpm -qa drugcam-libs' n'a pas répondu en moins de 10s.") from exc

    output = result.stdout.strip()
    if not output:
        raise OsReleaseError(
            "Le paquet 'drugcam-libs' n'est pas installé sur ce poste."
        )

    match = DRUGCAM_LIBS_VERSION_RE.search(output)
    if not match:
        raise OsReleaseError(
            f"Impossible d'extraire la version depuis la sortie rpm : {output!r}"
        )

    return match.group(1)
