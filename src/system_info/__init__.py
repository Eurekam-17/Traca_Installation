"""Collecte automatique des informations système du poste Drugcam.

Tous les modules de ce package sont conçus pour Rocky Linux 9 + KDE Plasma.
L'application est lancée en root, donc aucun appel sudo n'est géré ici.
"""

from .collector import SystemInfo, collect_all

__all__ = ["SystemInfo", "collect_all"]
