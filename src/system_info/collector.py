"""Orchestration de la collecte parallèle des 8 données système.

Cf. CLAUDE.md § 6 pour la liste exhaustive et § 5 étape 3 pour l'exigence
de parallélisme (la GUI affiche une barre de progression pendant ~5-10 s).

La collecte est résiliente : chaque sous-collecte qui échoue est consignée
dans ``errors`` plutôt que de faire échouer l'ensemble. La GUI peut ainsi
afficher les champs récupérés et signaler ceux qui posent problème.
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import date

from . import cameras as _cameras
from . import dmi as _dmi
from . import network as _network
from . import os_release as _os

logger = logging.getLogger(__name__)

# Verrou partagé pour protéger les écritures concurrentes dans SystemInfo
# (en particulier info.errors qui est un dict — l'opérateur [] = n'est pas
# atomique en présence de rebalances internes du dict).
_INFO_LOCK = threading.Lock()


@dataclass
class SystemInfo:
    """Conteneur du résultat de la collecte système.

    Chaque champ peut être ``None`` si la sous-collecte a échoué — l'appelant
    inspecte alors ``errors`` pour comprendre quoi.
    """

    # Donnée 1 — N° de série PC
    pc_serial_number: str | None = None
    # Donnée 2 — Version CPU
    cpu_version: str | None = None
    # Donnée 3 — Caméras (couple A/B trié par S/N croissant)
    camera_pair: _cameras.CameraPair | None = None
    cameras_raw: list[_cameras.Camera] = field(default_factory=list)
    # Donnée 4 — Nom du poste
    hostname: str | None = None
    # Donnée 5 — Version OS
    os_pretty_name: str | None = None
    # Donnée 6 — Version Assist (drugcam-libs)
    assist_version: str | None = None
    # Donnée 7 — MAC enp* concaténées par '|'
    mac_addresses: str | None = None
    # Donnée 8 — Date d'installation (ISO)
    installation_date: str = field(default_factory=lambda: date.today().isoformat())

    # Erreurs rencontrées : { champ -> message }
    errors: dict[str, str] = field(default_factory=dict)

    @property
    def is_complete(self) -> bool:
        """Vrai si toutes les données obligatoires ont été collectées sans erreur.

        La date d'installation est toujours définie donc pas vérifiée.
        """
        return (
            not self.errors
            and self.pc_serial_number is not None
            and self.cpu_version is not None
            and self.camera_pair is not None
            and self.hostname is not None
            and self.os_pretty_name is not None
            and self.assist_version is not None
            and self.mac_addresses is not None
        )


def _safe_call(name: str, func, info: SystemInfo, attr: str) -> None:
    """Appelle ``func()`` et stocke le résultat dans ``info.<attr>``.

    Toute exception est consignée dans ``info.errors[name]`` et journalisée.
    Les écritures sont protégées par :data:`_INFO_LOCK` pour éviter toute
    corruption en cas d'accès concurrent.
    """
    try:
        result = func()
        with _INFO_LOCK:
            setattr(info, attr, result)
        logger.debug("Collecte '%s' OK : %r", name, result)
    except Exception as exc:  # noqa: BLE001 — capture volontairement large
        msg = str(exc)
        with _INFO_LOCK:
            info.errors[name] = msg
        logger.error("Collecte '%s' en échec : %s", name, msg)


def _collect_cameras(info: SystemInfo) -> None:
    """Collecte spécifique caméras : on garde la liste brute même si erreur,
    pour permettre un choix manuel côté GUI quand >2 caméras sont trouvées.
    """
    try:
        raw = _cameras.detect_cameras()
        with _INFO_LOCK:
            info.cameras_raw = raw
    except _cameras.CameraError as exc:
        with _INFO_LOCK:
            info.errors["cameras"] = str(exc)
        logger.error("Collecte 'cameras' (énumération) en échec : %s", exc)
        return

    try:
        pair = _cameras.get_camera_pair()
        with _INFO_LOCK:
            info.camera_pair = pair
    except _cameras.NotEnoughCamerasError as exc:
        with _INFO_LOCK:
            info.errors["cameras"] = str(exc)
        logger.error("Collecte 'cameras' : %s", exc)
    except _cameras.TooManyCamerasError as exc:
        # Cas non bloquant : la GUI affichera un avertissement et laissera
        # le technicien saisir manuellement les caméras A et B.
        with _INFO_LOCK:
            info.errors["cameras_too_many"] = str(exc)
        logger.warning("Collecte 'cameras' : %s", exc)
    except _cameras.CameraError as exc:
        with _INFO_LOCK:
            info.errors["cameras"] = str(exc)
        logger.error("Collecte 'cameras' : %s", exc)


def collect_all() -> SystemInfo:
    """Lance les 8 collectes en parallèle et retourne un :class:`SystemInfo`.

    Le ThreadPoolExecutor est largement suffisant : ce sont des appels I/O
    (subprocess + lecture sysfs), pas du calcul intensif.
    """
    info = SystemInfo()

    tasks = [
        ("pc_serial", _dmi.get_system_serial_number, "pc_serial_number"),
        ("cpu_version", _dmi.get_processor_version, "cpu_version"),
        ("hostname", _os.get_hostname, "hostname"),
        ("os_pretty_name", _os.get_os_pretty_name, "os_pretty_name"),
        ("assist_version", _os.get_assist_version, "assist_version"),
        ("mac_addresses", _network.get_mac_addresses_concatenated, "mac_addresses"),
    ]

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(_safe_call, name, func, info, attr): name
            for name, func, attr in tasks
        }
        # _collect_cameras est dans son propre thread car il fait deux appels
        cameras_future = executor.submit(_collect_cameras, info)

        for future in as_completed([*futures, cameras_future]):
            try:
                future.result()
            except Exception as exc:  # noqa: BLE001
                logger.exception("Future inattendu en échec : %s", exc)

    # MAC vide = pas d'erreur Python mais signal métier (cf. § 11)
    if info.mac_addresses == "":
        info.errors["mac_addresses"] = (
            "Aucune interface réseau filaire (enp*) n'a été détectée."
        )
        info.mac_addresses = None

    if info.is_complete:
        logger.info("Collecte système complète et sans erreur.")
    else:
        logger.warning(
            "Collecte système terminée avec %d erreur(s) : %s",
            len(info.errors), list(info.errors.keys()),
        )

    return info
