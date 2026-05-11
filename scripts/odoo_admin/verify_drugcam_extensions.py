"""Vérifie l'état d'une instance Odoo par rapport au JSON déclaratif.

Lecture seule : aucune écriture, juste un rapport. Code retour :
- 0 si tout est conforme
- 1 si au moins une entité manque
- 2 si au moins une entité existe mais avec une propriété divergente
- >= 3 si erreur technique

Usage :
    # Vérifier la recette (par défaut)
    python scripts/odoo_admin/verify_drugcam_extensions.py

    # Vérifier la prod
    python scripts/odoo_admin/verify_drugcam_extensions.py --env prod

Sortie type :
    [OK]      x_workstation_type
    [DIFF]    x_uc_model : tracking 0 != 100
    [MISSING] x_camera_a_cable
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

import config  # noqa: E402

logger = logging.getLogger("verify_drugcam")


# ---------------------------------------------------------------------------
class OdooReader:
    def __init__(self, creds: config.OdooCredentials) -> None:
        import odoorpc  # type: ignore[import-untyped]
        self._odoo = odoorpc.ODOO(creds.host, protocol=creds.protocol, port=creds.port)
        self._odoo.login(creds.db, creds.login, creds.api_key)

    def search_one(self, model: str, domain: list, fields: list[str]) -> dict | None:
        recs = self._odoo.env[model].search_read(domain, fields, limit=1)
        return recs[0] if recs else None


# ---------------------------------------------------------------------------
def check_field(reader: OdooReader, spec: dict[str, Any]) -> tuple[str, str]:
    """Retourne (status, detail). Status ∈ {'OK', 'DIFF', 'MISSING'}."""
    field_name = spec["name"]
    existing = reader.search_one(
        "ir.model.fields",
        [("model", "=", spec["model"]), ("name", "=", field_name)],
        ["id", "field_description", "ttype", "selection", "tracking", "state"],
    )
    if not existing:
        return "MISSING", f"{spec['model']}.{field_name}"

    diffs = []
    if existing.get("field_description") != spec["field_description"]:
        diffs.append(f"label: {existing.get('field_description')!r} != {spec['field_description']!r}")
    if existing.get("ttype") != spec["ttype"]:
        diffs.append(f"ttype: {existing.get('ttype')!r} != {spec['ttype']!r}")
    if existing.get("tracking") != spec.get("tracking", 0):
        diffs.append(f"tracking: {existing.get('tracking')} != {spec.get('tracking', 0)}")
    if "selection" in spec and existing.get("selection") != spec["selection"]:
        diffs.append("selection: divergente")

    if diffs:
        return "DIFF", f"{spec['model']}.{field_name} → " + " ; ".join(diffs)
    return "OK", f"{spec['model']}.{field_name}"


def check_view(reader: OdooReader, spec: dict[str, Any]) -> tuple[str, str]:
    view_name = spec["name"]
    existing = reader.search_one(
        "ir.ui.view",
        [("name", "=", view_name), ("model", "=", spec["model"])],
        ["id", "arch_db", "priority"],
    )
    if not existing:
        return "MISSING", view_name

    diffs = []
    if existing.get("arch_db") != spec["arch"]:
        diffs.append("arch divergente")
    if existing.get("priority") != spec.get("priority", 16):
        diffs.append(f"priority: {existing.get('priority')} != {spec.get('priority', 16)}")

    if diffs:
        return "DIFF", f"{view_name} → " + " ; ".join(diffs)
    return "OK", view_name


# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--env", choices=list(config.PROFILES.keys()), default=None,
        help="Profil Odoo (staging/prod). Par défaut : staging.",
    )
    parser.add_argument(
        "--json-file", default=str(Path(__file__).parent / "odoo_extensions.json"),
        help="Chemin du fichier déclaratif.",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="[%(levelname)s] %(message)s",
    )

    if args.env:
        config.apply_env(args.env)

    creds = config.load_credentials()
    if creds is None:
        logger.error("Aucune clé API trouvée pour le profil %s.", config.ACTIVE_PROFILE)
        return 1

    spec = json.loads(Path(args.json_file).read_text(encoding="utf-8"))

    try:
        reader = OdooReader(creds)
    except Exception as exc:  # noqa: BLE001
        logger.error("Connexion Odoo impossible : %s", exc)
        return 3

    print(
        f"\n=== Audit de l'instance {creds.host} (db={creds.db}) ===\n"
        f"Spec : {args.json_file} (version {spec.get('_meta', {}).get('version', '?')})\n"
    )

    counts = {"OK": 0, "DIFF": 0, "MISSING": 0}

    print("─── Champs ────────────────────────────────────────────────────")
    for field_spec in spec.get("fields", []):
        if field_spec.get("name", "").startswith("_"):
            continue
        status, detail = check_field(reader, field_spec)
        counts[status] = counts.get(status, 0) + 1
        symbol = {"OK": "✅", "DIFF": "⚠️ ", "MISSING": "❌"}[status]
        print(f"  {symbol} [{status:7s}] {detail}")

    print("\n─── Vues ──────────────────────────────────────────────────────")
    for view_spec in spec.get("views", []):
        if view_spec.get("name", "").startswith("_"):
            continue
        status, detail = check_view(reader, view_spec)
        counts[status] = counts.get(status, 0) + 1
        symbol = {"OK": "✅", "DIFF": "⚠️ ", "MISSING": "❌"}[status]
        print(f"  {symbol} [{status:7s}] {detail}")

    print(
        f"\n=== Bilan : {counts['OK']} OK, {counts['DIFF']} divergentes, "
        f"{counts['MISSING']} manquantes ===\n"
    )

    if counts["MISSING"] > 0:
        print(
            "→ Lancer `python scripts/odoo_admin/setup_drugcam_extensions.py "
            "--dry-run` pour voir ce qui serait créé.\n"
        )
        return 1
    if counts["DIFF"] > 0:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
