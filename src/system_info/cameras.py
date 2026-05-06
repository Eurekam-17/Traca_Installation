"""Détection des caméras Allied Vision et Toshiba-Teli (USB).

Donnée 3 — Caméras (modèle + S/N).

La méthode privilégiée est la lecture directe de /sys/bus/usb/devices/*/
(plus fiable que dmesg qui peut être tronqué). La règle de tri impérative
est : la caméra avec le plus petit S/N est la caméra **A**, la plus grande
est la caméra **B** (cf. CLAUDE.md § 6).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


SUPPORTED_MANUFACTURERS = ("Allied Vision", "Toshiba-Teli")
USB_DEVICES_PATH = Path("/sys/bus/usb/devices")


class CameraError(Exception):
    """Erreur lors de la détection des caméras."""


class NotEnoughCamerasError(CameraError):
    """Moins de 2 caméras Drugcam ont été détectées (cas bloquant)."""


class TooManyCamerasError(CameraError):
    """Plus de 2 caméras détectées : un choix manuel est requis."""


@dataclass(frozen=True)
class Camera:
    """Représentation d'une caméra Drugcam détectée."""

    manufacturer: str
    product: str
    serial: str
    sysfs_path: str  # pour debug


@dataclass(frozen=True)
class CameraPair:
    """Couple (caméra A, caméra B) trié par numéro de série croissant."""

    camera_a: Camera
    camera_b: Camera


def _read_sysfs_attr(device_dir: Path, attr: str) -> str | None:
    """Lit un attribut texte d'un device USB sysfs. Retourne None si absent."""
    target = device_dir / attr
    if not target.is_file():
        return None
    try:
        return target.read_text(encoding="utf-8", errors="replace").strip()
    except OSError as exc:
        logger.debug("Lecture de %s échouée : %s", target, exc)
        return None


def _serial_sort_key(serial: str) -> tuple[int, str]:
    """Clé de tri robuste pour des serials potentiellement numériques.

    On essaie de convertir en entier ; sinon on tombe en tri lexicographique.
    Le tuple (rang, valeur) garantit que tous les serials numériques sont
    comparés ensemble avant les non-numériques.
    """
    try:
        return (0, f"{int(serial):020d}")
    except ValueError:
        return (1, serial)


def detect_cameras() -> list[Camera]:
    """Énumère toutes les caméras supportées branchées en USB.

    Retourne une liste éventuellement vide ou contenant 1, 2 ou 3+ caméras.
    Le filtrage par manufacturer permet d'ignorer le clavier, la souris, etc.
    """
    if not USB_DEVICES_PATH.is_dir():
        raise CameraError(
            f"{USB_DEVICES_PATH} introuvable. "
            "Cette détection requiert un système Linux avec sysfs (Rocky 9 OK)."
        )

    cameras: list[Camera] = []
    for device_dir in USB_DEVICES_PATH.iterdir():
        # On ignore les sous-interfaces USB (ex. 1-1:1.0) — on ne s'intéresse
        # qu'aux devices racine qui portent l'attribut manufacturer.
        manufacturer = _read_sysfs_attr(device_dir, "manufacturer")
        if not manufacturer or manufacturer not in SUPPORTED_MANUFACTURERS:
            continue

        product = _read_sysfs_attr(device_dir, "product") or "Inconnu"
        serial = _read_sysfs_attr(device_dir, "serial")
        if not serial:
            logger.warning(
                "Caméra %s détectée (%s) sans numéro de série — ignorée.",
                manufacturer, device_dir.name,
            )
            continue

        cameras.append(Camera(
            manufacturer=manufacturer,
            product=product,
            serial=serial,
            sysfs_path=str(device_dir),
        ))

    logger.info("Caméras Drugcam détectées : %d", len(cameras))
    return cameras


def get_camera_pair() -> CameraPair:
    """Retourne le couple (caméra A, caméra B) trié par S/N croissant.

    - Lève :class:`NotEnoughCamerasError` si moins de 2 caméras.
    - Lève :class:`TooManyCamerasError` si plus de 2 — la GUI proposera
      alors un choix manuel au technicien.
    """
    cameras = detect_cameras()

    if len(cameras) < 2:
        raise NotEnoughCamerasError(
            f"{len(cameras)} caméra(s) détectée(s), 2 requises. "
            "Vérifier que le bloc optique est bien branché et alimenté."
        )
    if len(cameras) > 2:
        raise TooManyCamerasError(
            f"{len(cameras)} caméras détectées, 2 attendues. "
            "Un choix manuel sera proposé."
        )

    sorted_cameras = sorted(cameras, key=lambda c: _serial_sort_key(c.serial))
    return CameraPair(camera_a=sorted_cameras[0], camera_b=sorted_cameras[1])
