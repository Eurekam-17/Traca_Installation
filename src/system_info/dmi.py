"""Lecture des informations DMI (BIOS / SMBIOS) via dmidecode.

Donnée 1 : N° de série PC — section ``System Information`` uniquement.
Donnée 2 : Version CPU — sortie de ``dmidecode -s processor-version``.

Dmidecode exige les droits root, mais l'application est lancée en root,
donc aucune gestion de sudo n'est nécessaire ici.
"""

from __future__ import annotations

import logging
import shutil
import subprocess

logger = logging.getLogger(__name__)


class DmiError(Exception):
    """Erreur lors de l'exécution de dmidecode."""


def _run_dmidecode(args: list[str]) -> str:
    """Exécute dmidecode avec les arguments donnés et retourne stdout.

    Lève DmiError si la commande échoue ou est absente.
    """
    if shutil.which("dmidecode") is None:
        raise DmiError(
            "La commande 'dmidecode' est introuvable. "
            "Vérifier que le paquet est installé (présent par défaut sur l'ISO Drugcam)."
        )

    cmd = ["dmidecode", *args]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except subprocess.CalledProcessError as exc:
        raise DmiError(
            f"dmidecode a échoué (code {exc.returncode}) : {exc.stderr.strip()}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise DmiError("dmidecode n'a pas répondu en moins de 10 secondes.") from exc

    return result.stdout


def get_system_serial_number() -> str:
    """Donnée 1 — N° de série PC, depuis la section ``System Information``.

    ⚠️ La sortie de ``dmidecode -t system`` peut contenir plusieurs entrées
    avec un ``Serial Number`` (système, châssis, carte mère). On parse
    explicitement la section qui débute par ``System Information`` pour
    isoler le bon numéro.
    """
    output = _run_dmidecode(["-t", "system"])

    # Chaque section commence par "Handle 0xNNNN" suivi d'un titre.
    # Approche : chercher le bloc commençant par "System Information"
    # puis extraire son "Serial Number:" (premier rencontré dans le bloc).
    in_system_section = False
    for line in output.splitlines():
        stripped = line.strip()
        if stripped == "System Information":
            in_system_section = True
            continue
        if in_system_section:
            # On sort de la section au prochain titre (ligne sans indentation
            # qui ne contient pas ":") ou à un nouveau Handle.
            if line and not line.startswith(("\t", " ")) and stripped != "System Information":
                # Probable nouveau bloc — on n'a rien trouvé
                break
            if stripped.startswith("Serial Number:"):
                serial = stripped.split(":", 1)[1].strip()
                if serial:
                    return serial

    raise DmiError(
        "Impossible de localiser le 'Serial Number' dans la section "
        "'System Information' de dmidecode."
    )


def get_processor_version() -> str:
    """Donnée 2 — Version CPU.

    Sortie type : ``Intel(R) Core(TM) i5-10500 CPU @ 3.10GHz``.
    """
    output = _run_dmidecode(["-s", "processor-version"]).strip()
    if not output:
        raise DmiError("dmidecode -s processor-version a renvoyé une chaîne vide.")
    # Sur les machines multi-CPU dmidecode retourne plusieurs lignes :
    # on prend la première (toutes identiques en pratique sur nos postes).
    first_line = output.splitlines()[0].strip()
    return first_line
