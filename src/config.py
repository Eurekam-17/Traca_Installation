"""Configuration globale et gestion des credentials Odoo.

Toutes les constantes de connexion sont définies ici. Les valeurs sensibles
(clé API) ne sont JAMAIS codées en dur : elles sont chargées depuis une
variable d'environnement ou un fichier ~/.drugcam-traca/credentials.json
avec des permissions restrictives.

Cf. CLAUDE.md § 10 pour la spécification complète.
"""

from __future__ import annotations

import json
import logging
import os
import stat
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Profils d'environnement Odoo
# ---------------------------------------------------------------------------
# ⚠️ Choix de design : par défaut on tape sur la STAGING. Cela évite
# qu'une erreur de config d'un nouveau poste fasse écrire en prod par
# accident. Pour passer en prod il faut le déclarer explicitement via :
#   - argument CLI : --env prod
#   - variable d'env : DRUGCAM_TRACA_ENV=prod
#
# Pour ajouter un profil (ex : pré-prod), ajouter une entrée à PROFILES.
PROFILES: dict[str, dict[str, str | int]] = {
    "staging": {
        "label": "Sandbox (eurekam-sandbox-32137656)",
        "host": "eurekam-sandbox.odoo.com",
        "db": "eurekam-sandbox-32137656",
        "login": "traca-bot@eurekam.fr",
        "protocol": "jsonrpc+ssl",
        "port": 443,
    },
    "prod": {
        "label": "Production (eurekam.odoo.com)",
        "host": "eurekam.odoo.com",
        "db": "eurekam",
        "login": "traca-bot@eurekam.fr",
        "protocol": "jsonrpc+ssl",
        "port": 443,
    },
}

# Profil actif. Lu une seule fois au chargement du module (à override par
# main.py via apply_env() si l'utilisateur passe --env).
ACTIVE_PROFILE: str = os.environ.get("DRUGCAM_TRACA_ENV", "staging").lower()
if ACTIVE_PROFILE not in PROFILES:
    # Fallback safe : staging si profil inconnu fourni
    ACTIVE_PROFILE = "staging"


def _profile() -> dict[str, str | int]:
    """Retourne le profil actif (raccourci interne)."""
    return PROFILES[ACTIVE_PROFILE]


# Constantes exportées (résolues à partir du profil actif). Elles peuvent
# être surchargées individuellement par variable d'env (rétro-compat).
ODOO_HOST: str = os.environ.get("DRUGCAM_TRACA_ODOO_HOST", str(_profile()["host"]))
ODOO_DB: str = os.environ.get("DRUGCAM_TRACA_ODOO_DB", str(_profile()["db"]))
ODOO_LOGIN: str = os.environ.get("DRUGCAM_TRACA_ODOO_LOGIN", str(_profile()["login"]))
ODOO_PROTOCOL: str = os.environ.get("DRUGCAM_TRACA_ODOO_PROTOCOL", str(_profile()["protocol"]))
ODOO_PORT: int = int(os.environ.get("DRUGCAM_TRACA_ODOO_PORT", str(_profile()["port"])))


def apply_env(env_name: str) -> None:
    """Bascule le profil actif vers ``env_name`` et met à jour les constantes.

    À appeler depuis main.py si l'utilisateur passe ``--env prod``.
    Lève ValueError si le profil n'existe pas.
    """
    global ACTIVE_PROFILE, ODOO_HOST, ODOO_DB, ODOO_LOGIN, ODOO_PROTOCOL, ODOO_PORT
    global CREDENTIALS_FILE
    if env_name not in PROFILES:
        raise ValueError(
            f"Profil inconnu : {env_name!r}. Profils disponibles : {list(PROFILES)}"
        )
    ACTIVE_PROFILE = env_name
    p = PROFILES[env_name]
    ODOO_HOST = str(p["host"])
    ODOO_DB = str(p["db"])
    ODOO_LOGIN = str(p["login"])
    ODOO_PROTOCOL = str(p["protocol"])
    ODOO_PORT = int(p["port"])
    CREDENTIALS_FILE = credentials_file()


def is_production() -> bool:
    """Vrai si le profil actif est la production. Utilisé pour le bandeau rouge."""
    return ACTIVE_PROFILE == "prod"


def active_profile_label() -> str:
    """Libellé court du profil actif, à afficher dans la GUI."""
    return str(_profile()["label"])


# ---------------------------------------------------------------------------
# Étiquettes (res.partner.category) à filtrer dans la liste des clients
# ---------------------------------------------------------------------------
# Validés avec Loïc — noms réels chez Eurekam.
CUSTOMER_CATEGORY_PROJET = "1- NEW"
CUSTOMER_CATEGORY_PROD = "EN PROD"


# ---------------------------------------------------------------------------
# Modèles Odoo cibles
# ---------------------------------------------------------------------------
# customer.asset.workstation : modèle du module Scalizer s6r_eurekam_customer_assets
# qui stocke les fiches postes Drugcam (~390 enregistrements en recette).
# Depuis la v0.2.0, tous les champs métier (type d'enceinte, UC, caméras,
# accessoires, commentaires) sont stockés directement sur ce modèle via les
# champs x_* créés en mode 'manual' (résistants aux mises à jour Scalizer).
# Pas de modèle Traçabilité séparé — l'historique d'installations est
# remplacé par l'audit log natif Odoo (chatter).
ODOO_MODEL_POSTE = os.environ.get(
    "DRUGCAM_TRACA_MODEL_POSTE", "customer.asset.workstation"
)
ODOO_MODEL_PARTNER = "res.partner"
ODOO_MODEL_PARTNER_CATEGORY = "res.partner.category"
ODOO_MODEL_ASSIST_VERSION = "customer.asset.software.version"


# ---------------------------------------------------------------------------
# Mode DRY-RUN : aucune écriture Odoo réelle, tout passe par mock_impl
# ---------------------------------------------------------------------------
DRY_RUN: bool = os.environ.get("DRUGCAM_TRACA_DRY_RUN", "0") == "1"


# ---------------------------------------------------------------------------
# Chemins applicatifs
# ---------------------------------------------------------------------------
APP_DATA_DIR: Path = Path.home() / ".drugcam-traca"
LOG_DIR: Path = APP_DATA_DIR / "logs"
USER_DATA_OPTIONS_DIR: Path = APP_DATA_DIR / "data_options"

# Ancien fichier (avant la séparation par profil) — utilisé en migration.
LEGACY_CREDENTIALS_FILE: Path = APP_DATA_DIR / "credentials.json"


def credentials_file() -> Path:
    """Chemin du fichier de credentials du profil actif.

    Un fichier par profil : credentials.staging.json, credentials.prod.json…
    Cela évite d'écraser une clé valide en switchant entre environnements.
    """
    return APP_DATA_DIR / f"credentials.{ACTIVE_PROFILE}.json"


# Alias rétro-compat (chemin du profil actif au moment du dernier apply_env)
CREDENTIALS_FILE: Path = LEGACY_CREDENTIALS_FILE  # remplacé dans apply_env()

# Le dossier data_options embarqué dans le code (valeurs par défaut).
# On résout le chemin par rapport à config.py lui-même : ça fonctionne aussi bien
# en dev (config.py dans src/) qu'après installation en wheel (config.py dans
# site-packages/), car data_options/ est dans les deux cas un dossier voisin.
EMBEDDED_DATA_OPTIONS_DIR: Path = Path(__file__).resolve().parent / "data_options"


def ensure_app_directories() -> None:
    """Crée les dossiers applicatifs s'ils n'existent pas.

    À appeler au démarrage avant toute opération de log ou de credentials.
    """
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Credentials Odoo — chargement sécurisé
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class OdooCredentials:
    """Identifiants pour la connexion Odoo."""

    host: str
    db: str
    login: str
    api_key: str
    protocol: str = "jsonrpc+ssl"
    port: int = 443


class CredentialsError(Exception):
    """Erreur lors du chargement ou de la sauvegarde des credentials."""


def load_credentials() -> OdooCredentials | None:
    """Charge les credentials Odoo selon l'ordre de priorité.

    1. Variable d'environnement ``DRUGCAM_TRACA_API_KEY``
    2. Fichier ``~/.drugcam-traca/credentials.<profile>.json`` (profil actif)
    3. Fallback migration : ancien ``~/.drugcam-traca/credentials.json``

    Retourne ``None`` si aucune source n'est disponible.
    """
    api_key = os.environ.get("DRUGCAM_TRACA_API_KEY")
    if api_key:
        logger.info("Clé API chargée depuis la variable d'environnement.")
        return OdooCredentials(
            host=ODOO_HOST,
            db=ODOO_DB,
            login=ODOO_LOGIN,
            api_key=api_key,
            protocol=ODOO_PROTOCOL,
            port=ODOO_PORT,
        )

    # Cherche d'abord le credentials du profil actif, puis le legacy en fallback
    candidate_files = [credentials_file(), LEGACY_CREDENTIALS_FILE]
    for path in candidate_files:
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise CredentialsError(f"Fichier {path} illisible : {exc}") from exc

        try:
            creds = OdooCredentials(
                host=data.get("host", ODOO_HOST),
                db=data.get("db", ODOO_DB),
                login=data.get("login", ODOO_LOGIN),
                api_key=data["api_key"],
                protocol=data.get("protocol", ODOO_PROTOCOL),
                port=int(data.get("port", ODOO_PORT)),
            )
        except KeyError as exc:
            raise CredentialsError(f"Champ manquant dans {path} : {exc}") from exc

        # Anti-mismatch : si le fichier référence un host qui ne correspond
        # PAS au profil actif, on ignore (sécurité contre clé prod sur staging
        # par exemple). On log pour le debug.
        if creds.host != ODOO_HOST:
            logger.warning(
                "Credentials %s référencent host=%s alors que profil %s = %s — ignoré.",
                path, creds.host, ACTIVE_PROFILE, ODOO_HOST,
            )
            continue

        logger.info("Credentials chargés depuis %s", path)
        return creds

    return None


def save_credentials(creds: OdooCredentials) -> None:
    """Sauvegarde les credentials dans le fichier du profil actif (perms 600).

    Le fichier est ``~/.drugcam-traca/credentials.<profile>.json`` — un
    fichier distinct par environnement, pour éviter qu'une saisie en prod
    écrase la clé de staging.
    """
    ensure_app_directories()
    target = credentials_file()
    payload = {
        "host": creds.host,
        "db": creds.db,
        "login": creds.login,
        "api_key": creds.api_key,
        "protocol": creds.protocol,
        "port": creds.port,
    }
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # Permissions 600 (lecture/écriture propriétaire uniquement)
    try:
        target.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError as exc:  # pragma: no cover — Windows / FS exotiques
        logger.warning("Impossible de restreindre les permissions de %s : %s",
                       target, exc)


# ---------------------------------------------------------------------------
# Configuration du logging — fichier rotatif quotidien
# ---------------------------------------------------------------------------
def setup_logging(verbose: bool = False) -> None:
    """Configure le logger racine : fichier dans ~/.drugcam-traca/logs/ + console.

    Args:
        verbose: si vrai, niveau DEBUG sur la console (toujours INFO+ en fichier).
    """
    from datetime import date
    from logging.handlers import RotatingFileHandler

    ensure_app_directories()

    log_file = LOG_DIR / f"traca-{date.today().isoformat().replace('-', '')}.log"

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s — %(message)s")
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    # Évite les doublons si setup_logging est appelé plusieurs fois
    root.handlers.clear()
    root.addHandler(file_handler)
    root.addHandler(console_handler)
