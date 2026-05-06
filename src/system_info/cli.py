"""Script CLI de test : exécute la collecte et affiche tout dans le terminal.

Usage (sur un poste Drugcam, en root) :

    sudo python -m system_info.cli

Permet à un technicien de valider que toutes les données système sont
correctement détectées AVANT de lancer la GUI complète.
"""

from __future__ import annotations

import argparse
import sys
from textwrap import indent

from .collector import collect_all


def _format_section(title: str, body: str) -> str:
    line = "─" * 60
    return f"\n{line}\n{title}\n{line}\n{body}\n"


def main(argv: list[str] | None = None) -> int:
    """Point d'entrée du script CLI ``drugcam-traca-collect``."""
    parser = argparse.ArgumentParser(
        description="Collecte les données système d'un poste Drugcam et les affiche.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Affiche les logs DEBUG sur la sortie standard.",
    )
    args = parser.parse_args(argv)

    # Import paresseux pour éviter de créer ~/.drugcam-traca/ si on ne fait que --help
    from config import setup_logging
    setup_logging(verbose=args.verbose)

    print("Collecte en cours…\n")
    info = collect_all()

    print(_format_section(
        "Donnée 1 — N° de série PC",
        info.pc_serial_number or "❌ NON COLLECTÉE",
    ), end="")

    print(_format_section(
        "Donnée 2 — Version CPU",
        info.cpu_version or "❌ NON COLLECTÉE",
    ), end="")

    if info.camera_pair:
        a, b = info.camera_pair.camera_a, info.camera_pair.camera_b
        body = (
            f"  Caméra A : {a.manufacturer} {a.product}  (S/N : {a.serial})\n"
            f"  Caméra B : {b.manufacturer} {b.product}  (S/N : {b.serial})"
        )
    elif info.cameras_raw:
        body = f"⚠️  {len(info.cameras_raw)} caméra(s) détectée(s) — choix manuel requis :\n"
        for i, cam in enumerate(info.cameras_raw):
            body += f"  [{i}] {cam.manufacturer} {cam.product}  (S/N : {cam.serial})\n"
    else:
        body = "❌ NON COLLECTÉES"
    print(_format_section("Donnée 3 — Caméras (couple A/B)", body), end="")

    print(_format_section(
        "Donnée 4 — Nom du poste (hostname)",
        info.hostname or "❌ NON COLLECTÉ",
    ), end="")

    print(_format_section(
        "Donnée 5 — Version OS (PRETTY_NAME)",
        info.os_pretty_name or "❌ NON COLLECTÉE",
    ), end="")

    print(_format_section(
        "Donnée 6 — Version Assist (drugcam-libs)",
        info.assist_version or "❌ NON COLLECTÉE",
    ), end="")

    print(_format_section(
        "Donnée 7 — Adresses MAC enp*",
        info.mac_addresses or "❌ NON COLLECTÉES",
    ), end="")

    print(_format_section(
        "Donnée 8 — Date d'installation",
        info.installation_date,
    ), end="")

    if info.errors:
        print("\n" + "═" * 60)
        print("ERREURS RENCONTRÉES")
        print("═" * 60)
        for key, msg in info.errors.items():
            print(f"  • {key} : {msg}")
        print()
        return 1

    print("\n✅ Collecte complète sans erreur.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
