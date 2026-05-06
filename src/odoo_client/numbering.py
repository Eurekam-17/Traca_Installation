"""Logique d'incrémentation des numéros de série (§ 7 CLAUDE.md).

Module commun aux deux implémentations Odoo (réelle et mock).

Formats :
- N° série équipement : ``AB`` + 6 chiffres (``AB000001`` à ``AB999999``)
- N° bloc optique :     ``01`` + 4 chiffres (``010001`` à ``019999``)
"""

from __future__ import annotations

import re

TRACABILITE_PREFIX = "AB"
TRACABILITE_DIGITS = 6
OPTICAL_BLOCK_PREFIX = "01"
OPTICAL_BLOCK_DIGITS = 4

_TRACABILITE_RE = re.compile(rf"{TRACABILITE_PREFIX}(\d{{{TRACABILITE_DIGITS}}})")
_OPTICAL_RE = re.compile(rf"{OPTICAL_BLOCK_PREFIX}(\d{{{OPTICAL_BLOCK_DIGITS}}})")


def _next_serial(existing: list[str], pattern: re.Pattern[str], prefix: str, digits: int) -> str:
    """Calcule ``MAX + 1`` à partir d'une liste de numéros existants.

    Les valeurs ne matchant pas le pattern sont ignorées (on n'échoue pas
    sur des données pourries en base — on log un avertissement à l'appelant).
    """
    max_value = 0
    for value in existing:
        if value is None:
            continue
        match = pattern.search(str(value))
        if match:
            max_value = max(max_value, int(match.group(1)))
    return f"{prefix}{(max_value + 1):0{digits}d}"


def next_tracability_serial(existing: list[str]) -> str:
    """N° de série équipement = prochain ``ABxxxxxx`` disponible."""
    return _next_serial(existing, _TRACABILITE_RE, TRACABILITE_PREFIX, TRACABILITE_DIGITS)


def next_optical_block_serial(existing: list[str]) -> str:
    """N° bloc optique = prochain ``01xxxx`` disponible."""
    return _next_serial(existing, _OPTICAL_RE, OPTICAL_BLOCK_PREFIX, OPTICAL_BLOCK_DIGITS)
