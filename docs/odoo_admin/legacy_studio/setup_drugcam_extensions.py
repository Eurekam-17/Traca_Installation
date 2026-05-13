"""Crée (ou met à jour) toutes les extensions Odoo nécessaires au projet
Drugcam Traca, à partir du fichier déclaratif odoo_extensions.json.

Idempotent : peut être lancé plusieurs fois sans casser. Chaque entité
(champ, vue) est :
- créée si elle n'existe pas
- mise à jour si elle existe déjà mais que ses propriétés diffèrent
- laissée intacte si elle est déjà conforme

Usage :
    # Sur la recette (par défaut) :
    python scripts/odoo_admin/setup_drugcam_extensions.py

    # Sur la prod (avec confirmation supplémentaire) :
    python scripts/odoo_admin/setup_drugcam_extensions.py --env prod

    # Mode dry-run (montre ce qui serait fait sans rien écrire) :
    python scripts/odoo_admin/setup_drugcam_extensions.py --dry-run

    # Sur une instance complètement custom (override CLI) :
    python scripts/odoo_admin/setup_drugcam_extensions.py \\
        --host my-instance.odoo.com --db my-db --login admin@x.fr

Pré-requis :
- Le module Scalizer s6r_eurekam_customer_assets doit être installé.
- Les credentials Odoo doivent être disponibles (cf. config.py).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

# Ajout de src/ au path pour réutiliser config.py
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

import config  # noqa: E402

logger = logging.getLogger("setup_drugcam")


# ---------------------------------------------------------------------------
# Classes utilitaires
# ---------------------------------------------------------------------------
class OdooAdmin:
    """Wrapper léger autour d'odoorpc pour les opérations d'admin."""

    def __init__(self, creds: config.OdooCredentials, dry_run: bool = False) -> None:
        import odoorpc  # type: ignore[import-untyped]
        self._dry_run = dry_run
        self._odoo = odoorpc.ODOO(creds.host, protocol=creds.protocol, port=creds.port)
        self._odoo.login(creds.db, creds.login, creds.api_key)
        logger.info(
            "Connecté à Odoo : %s (db=%s, user=%s) — %s",
            creds.host, creds.db, creds.login,
            "DRY-RUN (aucune écriture)" if dry_run else "ÉCRITURES ACTIVÉES",
        )

    def search_one(self, model: str, domain: list, fields: list[str]) -> dict | None:
        records = self._odoo.env[model].search_read(domain, fields, limit=1)
        return records[0] if records else None

    def create(self, model: str, payload: dict[str, Any]) -> int:
        if self._dry_run:
            logger.info("  [DRY-RUN] CREATE %s : %s", model, _short(payload))
            return -1
        new_id = self._odoo.env[model].create(payload)
        logger.info("  CREATED %s id=%d", model, new_id)
        return new_id

    def write(self, model: str, ids: list[int], payload: dict[str, Any]) -> None:
        if self._dry_run:
            logger.info("  [DRY-RUN] WRITE %s ids=%s : %s", model, ids, _short(payload))
            return
        self._odoo.env[model].browse(ids).write(payload)
        logger.info("  UPDATED %s ids=%s", model, ids)


def _short(payload: dict[str, Any], max_len: int = 80) -> str:
    """Représentation compacte pour les logs."""
    s = json.dumps(payload, ensure_ascii=False)
    return s if len(s) <= max_len else s[: max_len - 3] + "..."


# ---------------------------------------------------------------------------
# Champs
# ---------------------------------------------------------------------------
def ensure_field(admin: OdooAdmin, spec: dict[str, Any]) -> str:
    """Crée le champ s'il n'existe pas, sinon met à jour les propriétés
    qui diffèrent. Retourne 'created' / 'updated' / 'unchanged'."""
    model_name = spec["model"]
    field_name = spec["name"]

    # Récupère l'ID du modèle (depuis ir.model)
    model_record = admin.search_one(
        "ir.model", [("model", "=", model_name)], ["id"],
    )
    if not model_record:
        raise RuntimeError(
            f"Modèle Odoo '{model_name}' introuvable. "
            "Le module Scalizer s6r_eurekam_customer_assets est-il installé ?"
        )
    model_id = model_record["id"]

    # Cherche le champ existant
    existing = admin.search_one(
        "ir.model.fields",
        [("model", "=", model_name), ("name", "=", field_name)],
        ["id", "field_description", "ttype", "selection", "tracking", "state"],
    )

    desired = {
        "model_id": model_id,
        "name": field_name,
        "field_description": spec["field_description"],
        "ttype": spec["ttype"],
        "state": spec.get("state", "manual"),
        "tracking": spec.get("tracking", 0),
    }
    if "selection" in spec:
        desired["selection"] = spec["selection"]
    if "relation" in spec:
        desired["relation"] = spec["relation"]

    if not existing:
        admin.create("ir.model.fields", desired)
        return "created"

    # Champ existant : check des propriétés
    diff: dict[str, Any] = {}
    for key in ("field_description", "ttype", "tracking"):
        if existing.get(key) != desired[key]:
            diff[key] = desired[key]
    if "selection" in spec and existing.get("selection") != desired["selection"]:
        diff["selection"] = desired["selection"]

    if not diff:
        logger.info("  ✓ %s.%s déjà conforme", model_name, field_name)
        return "unchanged"

    logger.info("  ⚙️  %s.%s : mise à jour de %s", model_name, field_name, list(diff))
    admin.write("ir.model.fields", [existing["id"]], diff)
    return "updated"


# ---------------------------------------------------------------------------
# Vues
# ---------------------------------------------------------------------------
def ensure_view(admin: OdooAdmin, spec: dict[str, Any]) -> str:
    """Crée la vue d'héritage si elle n'existe pas, sinon met à jour son arch."""
    view_name = spec["name"]

    # Cherche la vue parent par nom (plus robuste qu'un ID brut entre instances)
    inherit_view_name = spec.get("inherit_view_name")
    inherit_id = None
    if inherit_view_name:
        domain = [("name", "=", inherit_view_name), ("model", "=", spec["model"])]
        # Filtrage supplémentaire si plusieurs vues partagent le même nom
        if "inherit_view_arch_contains" in spec:
            domain.append(("arch_db", "ilike", spec["inherit_view_arch_contains"]))
        parent = admin.search_one("ir.ui.view", domain, ["id"])
        if not parent:
            raise RuntimeError(
                f"Vue parent '{inherit_view_name}' (model={spec['model']}) introuvable. "
                "Vérifier que le module qui la fournit est installé."
            )
        inherit_id = parent["id"]

    existing = admin.search_one(
        "ir.ui.view", [("name", "=", view_name), ("model", "=", spec["model"])],
        ["id", "arch_db", "priority", "inherit_id"],
    )

    desired = {
        "name": view_name,
        "model": spec["model"],
        "type": spec["type"],
        "arch": spec["arch"],
        "priority": spec.get("priority", 16),
    }
    if inherit_id is not None:
        desired["inherit_id"] = inherit_id

    if not existing:
        admin.create("ir.ui.view", desired)
        return "created"

    # Vue existante : check arch et priority
    diff: dict[str, Any] = {}
    if existing.get("arch_db") != spec["arch"]:
        diff["arch"] = spec["arch"]
    if existing.get("priority") != desired["priority"]:
        diff["priority"] = desired["priority"]

    if not diff:
        logger.info("  ✓ vue %r déjà conforme", view_name)
        return "unchanged"

    logger.info("  ⚙️  vue %r : mise à jour de %s", view_name, list(diff))
    admin.write("ir.ui.view", [existing["id"]], diff)
    return "updated"


# ---------------------------------------------------------------------------
# Entrée
# ---------------------------------------------------------------------------
def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="[%(levelname)s] %(message)s",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--env", choices=list(config.PROFILES.keys()), default=None,
        help="Profil Odoo (staging/prod). Par défaut : staging.",
    )
    parser.add_argument("--host", help="Override host Odoo")
    parser.add_argument("--db", help="Override database Odoo")
    parser.add_argument("--login", help="Override login Odoo")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Affiche ce qui serait fait sans rien écrire.",
    )
    parser.add_argument(
        "--json-file", default=str(Path(__file__).parent / "odoo_extensions.json"),
        help="Chemin du fichier déclaratif (défaut : odoo_extensions.json à côté).",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    _setup_logging(args.verbose)

    if args.env:
        config.apply_env(args.env)

    # Confirmation explicite si on touche à la prod sans dry-run
    if config.is_production() and not args.dry_run:
        print(f"\n⚠️  PRODUCTION — instance {config.ODOO_HOST} (db={config.ODOO_DB})")
        confirm = input("Tape 'OUI' pour confirmer l'écriture en prod : ")
        if confirm != "OUI":
            logger.error("Abandon par l'utilisateur.")
            return 1

    # Charge les credentials
    creds = config.load_credentials()
    if creds is None:
        logger.error(
            "Aucune clé API trouvée. Définir DRUGCAM_TRACA_API_KEY ou créer "
            "le fichier %s.", config.credentials_file(),
        )
        return 1
    # Override CLI éventuel (utile si on cible une instance non standard)
    from dataclasses import replace
    if args.host or args.db or args.login:
        creds = replace(
            creds,
            host=args.host or creds.host,
            db=args.db or creds.db,
            login=args.login or creds.login,
        )

    # Lecture du JSON déclaratif
    json_path = Path(args.json_file)
    if not json_path.is_file():
        logger.error("Fichier déclaratif introuvable : %s", json_path)
        return 1
    spec = json.loads(json_path.read_text(encoding="utf-8"))
    logger.info(
        "Spec chargée : version=%s, %d champs, %d vues",
        spec.get("_meta", {}).get("version", "?"),
        len(spec.get("fields", [])),
        len(spec.get("views", [])),
    )

    # Connexion Odoo
    try:
        admin = OdooAdmin(creds, dry_run=args.dry_run)
    except Exception as exc:  # noqa: BLE001
        logger.error("Connexion Odoo impossible : %s", exc)
        return 2

    # Application
    counts = {"created": 0, "updated": 0, "unchanged": 0}

    logger.info("\n=== CHAMPS ===")
    for field_spec in spec.get("fields", []):
        if field_spec.get("name", "").startswith("_"):
            continue
        try:
            result = ensure_field(admin, field_spec)
            counts[result] = counts.get(result, 0) + 1
        except Exception as exc:  # noqa: BLE001
            logger.error("❌ Champ %s : %s", field_spec.get("name", "?"), exc)
            return 3

    logger.info("\n=== VUES ===")
    for view_spec in spec.get("views", []):
        if view_spec.get("name", "").startswith("_"):
            continue
        try:
            result = ensure_view(admin, view_spec)
            counts[result] = counts.get(result, 0) + 1
        except Exception as exc:  # noqa: BLE001
            logger.error("❌ Vue %s : %s", view_spec.get("name", "?"), exc)
            return 4

    logger.info(
        "\n✅ Terminé : %d créées, %d mises à jour, %d déjà conformes.",
        counts.get("created", 0), counts.get("updated", 0), counts.get("unchanged", 0),
    )
    if args.dry_run:
        logger.info("(Mode DRY-RUN : aucune écriture réelle effectuée.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
