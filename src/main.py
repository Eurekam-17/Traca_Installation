"""Point d'entrée de l'AppImage drugcam-traca.

Étapes au lancement (cf. CLAUDE.md § 5 étape 1) :
1. Initialise les dossiers ~/.drugcam-traca/.
2. Configure le logging fichier + console.
3. Charge / demande les credentials Odoo (sauf en mode --mock / DRY_RUN).
4. Crée le client Odoo (réel ou mock).
5. Lance la fenêtre principale qui se charge du test de connexion.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

import config

logger = logging.getLogger(__name__)


def _check_root_on_linux() -> None:
    """Avertit (sans bloquer) si l'application n'est pas lancée en root sur Linux.

    L'application a besoin de root pour ``dmidecode`` et la lecture sysfs.
    Sur Windows / macOS (développement uniquement) on skip silencieusement.
    """
    if sys.platform != "linux":
        return
    if hasattr(os, "geteuid") and os.geteuid() != 0:
        logger.warning(
            "Application non lancée en root : dmidecode et la lecture des caméras "
            "vont probablement échouer. Lancer avec sudo."
        )


def _ensure_credentials() -> config.OdooCredentials | None:
    """Charge ou demande les credentials Odoo.

    En mode DRY_RUN ou --mock, retourne ``None`` (pas besoin).
    Sinon, lance un dialogue Qt si rien n'est trouvé.
    Retourne ``None`` si l'utilisateur annule.
    """
    if config.DRY_RUN:
        return None

    try:
        creds = config.load_credentials()
    except config.CredentialsError as exc:
        logger.error("Credentials illisibles : %s", exc)
        creds = None

    if creds is not None:
        return creds

    # Aucune source disponible — on demande à l'utilisateur via Qt
    from PySide6.QtWidgets import QDialog
    from ui.credentials_dialog import CredentialsDialog
    dialog = CredentialsDialog()
    if dialog.exec() != QDialog.DialogCode.Accepted:
        logger.info("Saisie des credentials annulée par l'utilisateur.")
        return None

    # Si l'utilisateur a basculé d'environnement dans le dialog,
    # on applique le profil sélectionné AVANT de sauvegarder le fichier
    # (sinon il irait dans le mauvais credentials.<profile>.json).
    chosen_env = dialog.selected_env()
    if chosen_env != config.ACTIVE_PROFILE:
        logger.info(
            "Bascule depuis le dialog : profil %s → %s",
            config.ACTIVE_PROFILE, chosen_env,
        )
        config.apply_env(chosen_env)

    creds = dialog.to_credentials()
    try:
        config.save_credentials(creds)
        logger.info("Credentials sauvegardés dans %s", config.credentials_file())
    except OSError as exc:
        logger.error("Sauvegarde des credentials échouée : %s", exc)
    return creds


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Outil de traçabilité des installations Drugcam.",
    )
    parser.add_argument(
        "--env",
        choices=list(config.PROFILES.keys()),
        default=None,
        help=(
            "Environnement Odoo cible. Par défaut : 'staging' (sauf si la "
            "variable DRUGCAM_TRACA_ENV est définie). Le bandeau coloré en "
            "haut de la fenêtre rappelle visuellement l'environnement actif."
        ),
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Force l'utilisation du client Odoo factice (DRY_RUN). "
             "Aucune écriture réelle, idéal pour démo ou développement.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Affiche les logs DEBUG sur la console.",
    )
    args = parser.parse_args(argv)

    # Bascule éventuelle vers le profil demandé en CLI
    if args.env:
        config.apply_env(args.env)

    config.ensure_app_directories()
    config.setup_logging(verbose=args.verbose)
    # Affiche la version installée — utile pour diagnostiquer un AppImage
    # buildée à partir d'un code source désynchronisé (cas vécu).
    try:
        from importlib.metadata import version
        app_version = version("drugcam-traca")
    except Exception:  # noqa: BLE001
        app_version = "?"
    logger.info("=== Démarrage drugcam-traca v%s ===", app_version)
    logger.info(
        "Profil Odoo actif : %s (%s, db=%s)",
        config.ACTIVE_PROFILE, config.ODOO_HOST, config.ODOO_DB,
    )
    if config.is_production():
        logger.warning("⚠️  ENVIRONNEMENT DE PRODUCTION — toute écriture impacte la prod réelle.")
    _check_root_on_linux()

    if args.mock:
        os.environ["DRUGCAM_TRACA_DRY_RUN"] = "1"
        # Recharge le flag global après modification de l'environnement
        config.DRY_RUN = True
        logger.info("Mode --mock : aucune écriture Odoo ne sera effectuée.")

    # Initialise QApplication AVANT toute boîte de dialogue.
    # On passe une argv minimale : Qt parse sinon -v/-platform/etc. et peut
    # rejeter nos arguments métier comme --mock.
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([sys.argv[0]])
    app.setApplicationName("drugcam-traca")
    app.setOrganizationName("Eurekam")

    if not config.DRY_RUN:
        creds = _ensure_credentials()
        if creds is None:
            logger.error("Aucun credential Odoo : l'application se ferme.")
            return 1

    # Construit le client (réel ou mock selon DRY_RUN)
    from odoo_client.factory import build_client
    try:
        client = build_client()
    except Exception as exc:  # noqa: BLE001
        from ui.widgets import show_error
        show_error(None, "Erreur d'initialisation", str(exc))
        return 2

    # Lance la fenêtre principale
    from ui.main_window import MainWindow
    window = MainWindow(client)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
