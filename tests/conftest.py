"""Fixtures pytest communes : ajout de src/ au sys.path et logging silencieux."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Permet d'importer "config", "system_info", "odoo_client" depuis tests/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Aucun bruit dans la sortie de test
logging.getLogger().setLevel(logging.WARNING)
