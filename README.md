# Drugcam — Outil de traçabilité installations

Assistant graphique pour les techniciens Eurekam. Automatise la saisie de la
configuration matérielle d'un poste Drugcam Assist au moment de l'installation
chez un client, et envoie les données dans Odoo.

> Spécifications complètes dans [`CLAUDE.md`](CLAUDE.md).
> Historique des versions dans [`CHANGELOG.md`](CHANGELOG.md).
> Import en masse via Excel/CSV : voir [`docs/odoo_import/`](docs/odoo_import/).
> Module Odoo associé (depuis v0.3.0) : [`odoo_module/eurekam_drugcam_traca/`](odoo_module/eurekam_drugcam_traca/).
> Doc Odoo (incl. legacy Studio archivé) : [`docs/odoo_admin/`](docs/odoo_admin/).
> Cible : **Rocky Linux 9 + KDE Plasma**, livraison **AppImage**.

---

## Sommaire

1. [Démarrage rapide pour le technicien](#1--démarrage-rapide-pour-le-technicien)
2. [Choix de l'environnement Odoo (staging / prod)](#2--choix-de-lenvironnement-odoo-staging--prod)
3. [Architecture](#3--architecture)
4. [Développement](#4--développement)
5. [Mode mock (sans Odoo réel)](#5--mode-mock-sans-odoo-réel)
6. [Construire l'AppImage](#6--construire-lappimage)
7. [Maintenance des fichiers data_options](#7--maintenance-des-fichiers-data_options)
8. [Limitations connues du prototype](#8--limitations-connues-du-prototype)

---

## 1 — Démarrage rapide pour le technicien

1. Récupérer `drugcam-traca-X.Y.Z-x86_64.AppImage` (cf. § 6).
2. Le copier sur le poste Drugcam (par exemple sur le bureau).
3. Le rendre exécutable : `chmod +x drugcam-traca-*.AppImage`.
4. Le lancer **en root** : `sudo -E ./drugcam-traca-*.AppImage`.
   ⚠️ Par défaut, l'application se connecte à la **staging** (sécurité).
   Pour la prod : `sudo -E ./drugcam-traca-*.AppImage --env prod`.
5. Au premier lancement, choisir l'environnement et saisir la clé API Odoo
   (compte de service `traca-bot@eurekam.fr`). Les identifiants sont
   mémorisés dans `~/.drugcam-traca/credentials.<profil>.json` (perms `600`,
   un fichier par environnement).

L'application guide ensuite le technicien sur 3 écrans :
1. Sélection du client (filtré par étiquettes Odoo).
2. Collecte automatique + formulaire prérempli.
3. Récapitulatif et confirmation d'envoi.

🟠 **Bandeau orange** en haut de la fenêtre = staging (test).
🔴 **Bandeau rouge** = prod (toute écriture impacte la base réelle).
🧪 **Bandeau bleu** = mode `--mock` (aucune écriture).

Les logs sont dans `~/.drugcam-traca/logs/traca-AAAAMMJJ.log`.

---

## 2 — Choix de l'environnement Odoo (staging / prod)

L'application connaît deux profils prédéfinis dans
[`src/config.py`](src/config.py) (constante `PROFILES`) :

| Profil | Host | DB |
|---|---|---|
| **staging** (défaut) | `eurekam-sandbox.odoo.com` | `eurekam-sandbox-32137656` |
| **prod** | `eurekam.odoo.com` | `eurekam` |

> Note : entre v0.1.4 et v0.2.3, l'instance staging était une recette
> Odoo.sh nommée différemment (`eurekam-recette` ou
> `eurekam-staging-28517368`). Elle a été remplacée par la sandbox
> `eurekam-sandbox` à partir de la v0.2.4. Si tu trouves une référence
> à l'ancien nom dans un fichier ou un script, c'est un oubli — me le
> signaler.

**3 façons de choisir l'environnement** (par ordre de priorité) :

1. Argument CLI : `--env prod` ou `--env staging`
2. Variable d'environnement : `DRUGCAM_TRACA_ENV=prod` (utile dans un .desktop, un wrapper, etc.)
3. Sélecteur dans la boîte de dialogue de saisie de credentials au premier lancement

**Sécurités intégrées** :
- Le profil par défaut est **staging** : oubli de configuration → pas d'écriture en prod.
- Un fichier credentials distinct par profil : impossible de "mélanger" une clé staging avec une URL prod par accident. Si vous saisissez une clé prod alors que vous êtes en staging, le fichier `credentials.staging.json` n'est PAS écrasé.
- Le bandeau coloré reste affiché en permanence : impossible de croire qu'on est sur staging alors qu'on est en prod.

Pour ajouter un nouveau profil (ex : pré-prod), éditer le dictionnaire
`PROFILES` dans `src/config.py` et reconstruire l'AppImage.

---

## 3 — Architecture

```
src/
├── main.py                 # Point d'entrée : init logs, credentials, lance la GUI
├── config.py               # Chemins, credentials, setup_logging, DRY_RUN
│
├── system_info/            # Collecte système (Rocky 9 only)
│   ├── dmi.py              # dmidecode — n° série PC + version CPU
│   ├── cameras.py          # /sys/bus/usb/devices/* — caméras Drugcam
│   ├── network.py          # ip -o link show — MAC enp*
│   ├── os_release.py       # hostname, /etc/os-release, rpm drugcam-libs
│   ├── collector.py        # Orchestre les 8 collectes en parallèle
│   └── cli.py              # Script de test : python -m system_info.cli
│
├── odoo_client/            # Couche Odoo strictement isolée (cf. CLAUDE.md § 2bis-C)
│   ├── base.py             # Interface abstraite OdooClientBase + dataclasses
│   ├── numbering.py        # Logique d'incrémentation des numéros AB et 01
│   ├── odoorpc_impl.py     # Implémentation réelle via odoorpc
│   ├── mock_impl.py        # Implémentation factice (DRY_RUN, tests)
│   ├── factory.py          # build_client() : choisit auto entre mock et réel
│   └── cli.py              # Script de test : python -m odoo_client.cli --mock
│
├── ui/                     # Interface graphique PySide6
│   ├── main_window.py          # Fenêtre + QStackedWidget des 3 étapes
│   ├── widgets.py              # NavigationBar, dialogues, helpers JSON
│   ├── credentials_dialog.py   # Saisie clé API au 1er lancement
│   ├── installation_draft.py   # Objet de transfert entre étapes
│   ├── step1_customer.py       # Étape 1 : sélection client
│   ├── step2_form.py           # Étape 2 : collecte + formulaire prérempli
│   └── step3_summary.py        # Étape 3 : récap + envoi Odoo
│
└── data_options/           # JSON éditables (cf. § 6)

tests/                      # pytest, aucun appel réseau
scripts/get_camera.sh       # Référence bash de la détection caméras
build_appimage.sh           # Construction de l'AppImage
```

### Points clés (cf. CLAUDE.md)

- **§ 2bis-C** : la couche `odoo_client/` est **la seule** à importer `odoorpc`.
  Quand l'External JSON-2 API d'Odoo remplacera `/jsonrpc` (deadline fin 2027),
  seul un nouveau `json2_impl.py` sera à écrire.
- **§ 6, donnée 3** : règle impérative — la caméra avec le **plus petit S/N**
  est la **caméra A**, la plus grande est la **B**.
- **§ 7** : les numéros de série sont préremplis avec `MAX(existant) + 1`,
  mais restent éditables dans la GUI.
- **§ 9** : les fichiers `data_options/*.json` peuvent être édités sans
  recompilation (cf. § 6 de ce README).

---

## 4 — Développement

Pré-requis : Python 3.11+, pip.

```bash
# Création d'un venv
python -m venv .venv
source .venv/bin/activate            # (sur Windows : .venv\Scripts\activate)

# Dépendances
pip install -r requirements.txt
pip install -e ".[dev]"              # ajoute pytest + black + ruff

# Lancer les tests (aucun appel réseau)
pytest

# Formatter / linter
black src tests
ruff check src tests

# Lancer la GUI en mode démo (mock, aucun appel Odoo)
PYTHONPATH=src python src/main.py --mock
```

### Tester la collecte système (sur un poste Drugcam uniquement)

```bash
sudo PYTHONPATH=src python -m system_info.cli
```

### Tester la connexion Odoo

```bash
# Mode mock : aucun réseau, données factices
PYTHONPATH=src python -m odoo_client.cli --mock --next-serials

# Mode réel : nécessite la clé API (env DRUGCAM_TRACA_API_KEY ou credentials.json)
PYTHONPATH=src python -m odoo_client.cli --next-serials
```

---

## 5 — Mode mock (sans Odoo réel)

Pour développer ou démontrer sans clé API ni accès Odoo :

```bash
DRUGCAM_TRACA_DRY_RUN=1 PYTHONPATH=src python src/main.py
# ou de manière équivalente :
PYTHONPATH=src python src/main.py --mock
```

En mode mock :
- 5 clients factices sont chargés (CHU Lille, Pompidou, etc.).
- Aucun appel réseau n'est effectué.
- Les insertions sont **simulées** et journalisées dans le log.

---

## 6 — Construire l'AppImage

À faire sur une machine Linux x86_64 (Rocky 9 recommandé pour rester proche
de la cible client).

```bash
# Pré-requis (sur Rocky 9) :
sudo dnf install -y python3 python3-pip python3-venv fuse-libs

# Construction
chmod +x build_appimage.sh
./build_appimage.sh

# Test sur une Rocky 9 vierge :
chmod +x dist/drugcam-traca-*.AppImage
sudo ./dist/drugcam-traca-*.AppImage
```

Checklist post-build (cf. CLAUDE.md § 12) :
- [ ] L'AppImage se lance sur une Rocky Linux 9 fraîche sans installation.
- [ ] Taille < 100 Mo.
- [ ] Icône Eurekam dans la barre des tâches KDE.
- [ ] Les fichiers `data_options/` sont accessibles en écriture
      (sinon ils sont copiés dans `~/.drugcam-traca/data_options/` au 1er lancement).

---

## 7 — Maintenance des fichiers `data_options`

Les 8 fichiers `src/data_options/*.json` listent les options des menus
déroulants. **Pour ajouter ou retirer une option, pas besoin de recompiler.**

### Format

```json
{
  "label": "Modèle de souris",
  "options": [
    { "display": "Logitech M185", "value": "logitech_m185" },
    { "display": "Microsoft Basic Optical", "value": "ms_basic_optical" }
  ]
}
```

- `display` : ce que voit le technicien.
- `value` : ce qui est envoyé à Odoo (laisser identique au display si pas de
  raison de différencier).

### Surcharger les options sans toucher à l'AppImage

Copier le fichier modifié dans `~/.drugcam-traca/data_options/` — il sera
chargé en priorité au prochain lancement.

### Si un fichier JSON est invalide ou manquant

L'application affiche un avertissement et bascule le champ correspondant en
**saisie libre** au lieu de planter (cf. CLAUDE.md § 9).

---

## 8 — Limitations connues du prototype

Cf. CLAUDE.md § 15.

- **Pas de mise à jour automatique** de l'AppImage.
- **Pas de verrou multi-techniciens** : si deux techniciens lancent l'outil
  exactement en même temps sur des postes différents, ils peuvent se voir
  attribuer le même prochain numéro de série. Taux d'usage faible donc
  acceptable pour le prototype.
- **Pas de mode hors-ligne** : la connexion Odoo est requise au lancement.
- **Pas d'édition rétroactive** des fiches déjà créées (autre que via Odoo
  directement).
- **Interface en français uniquement** — pas de i18n.

### À régler côté Odoo avant la mise en production (cf. CLAUDE.md § 16)

- Compte de service Odoo `traca-bot@eurekam.fr` créé et clé API générée.
- Plan Odoo confirmé en **Custom** (sinon API externe inaccessible).
- Modèle Odoo `Traçabilité` créé (variable d'env `DRUGCAM_TRACA_MODEL_TRACABILITE`).
- Noms techniques exacts des champs `Postes clients` et `Traçabilité` validés.
- Étiquettes `res.partner.category` "Projet en cours" et "Clients en Prod"
  vérifiées (variables `CUSTOMER_CATEGORY_*` dans `src/config.py`).
