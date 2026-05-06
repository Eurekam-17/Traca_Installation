"""Script CLI de test : connexion Odoo et liste des clients filtrés.

Usage :

    # Mode mock (aucun réseau, données factices)
    python -m odoo_client.cli --mock

    # Mode réel — la clé API doit être disponible (env ou credentials.json)
    python -m odoo_client.cli

    # Test du calcul des prochains numéros de série
    python -m odoo_client.cli --next-serials
"""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Outils de test pour la couche Odoo de drugcam-traca.",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Force l'usage du MockOdooClient (aucun appel réseau).",
    )
    parser.add_argument(
        "--next-serials",
        action="store_true",
        help="Affiche les prochains numéros de série Traçabilité et Bloc optique.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Affiche les logs DEBUG.",
    )
    args = parser.parse_args(argv)

    from config import setup_logging
    setup_logging(verbose=args.verbose)

    from .base import OdooConnectionError, OdooError
    from .factory import build_client

    try:
        client = build_client(force_mock=args.mock)
        client.authenticate()
    except OdooConnectionError as exc:
        print(f"❌ Connexion Odoo impossible : {exc}", file=sys.stderr)
        return 2

    print("✅ Connexion OK.\n")

    try:
        customers = client.list_active_customers()
    except OdooError as exc:
        print(f"❌ Lecture des clients en échec : {exc}", file=sys.stderr)
        return 3

    print(f"Clients filtrés ({len(customers)}) :")
    for cust in customers:
        print(f"  • [{cust.odoo_id}] {cust.name}")

    if args.next_serials:
        print("\nProchains numéros disponibles :")
        try:
            print(f"  • N° de série équipement : {client.next_tracability_serial()}")
            print(f"  • N° bloc optique        : {client.next_optical_block_serial()}")
        except OdooError as exc:
            print(f"⚠️  Calcul des numéros impossible : {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
