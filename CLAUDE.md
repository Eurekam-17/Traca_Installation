# CLAUDE.md — Outil de traçabilité installations Drugcam (Eurekam)

> Spécifications projet à destination de Claude Code.
> **Auteur** : Loïc — Eurekam
> **Public cible du logiciel** : techniciens Eurekam en intervention chez les clients
> **Statut** : prototype initial à développer

---

## 1. Contexte métier

Eurekam développe **Drugcam**, un système de vision par ordinateur pour la vérification automatisée des préparations de chimiothérapie en pharmacie hospitalière. Lors de chaque installation chez un client, un technicien Eurekam déploie un poste « Assist » composé d'un PC sous Rocky Linux 9 + KDE Plasma, d'un bloc optique avec deux caméras (Allied Vision Alvium ou Toshiba-Teli), et de divers accessoires (souris, plots inox, bloc d'alimentation, etc.).

Aujourd'hui, l'enregistrement de la configuration matérielle de chaque poste installé se fait manuellement dans Odoo. C'est **chronophage**, **source d'erreurs** et **incohérent d'un technicien à l'autre**.

**Objectif du logiciel** : automatiser cette saisie via un assistant graphique qui :

1. **Récupère automatiquement** un maximum d'informations système.
2. **Présente un formulaire prérempli** où le technicien complète uniquement ce qui n'est pas auto-détectable (choix matériel, type d'installation…).
3. **Pousse les données dans Odoo** via l'API XML-RPC, dans deux tables (`Postes clients` et future `Traçabilité`).

---

## 2. Contraintes techniques (non négociables)

| Contrainte | Détail |
|------------|--------|
| OS cible | **Rocky Linux 9** (RHEL 9 family) |
| Environnement graphique | **KDE Plasma** (Qt natif → privilégier Qt) |
| Format de livrable | **AppImage** unique, exécutable sans installation |
| Mode d'exécution | Lancé en **root** (les commandes `dmidecode` l'exigent ; pas besoin de gérer `sudo` dans le code) |
| Langue de l'interface | **Français** uniquement |
| Contexte réseau | Le PC est branché au réseau client → l'API Odoo doit être joignable depuis le poste pendant l'installation |
| Domaine | Dispositif médical → **fiabilité, traçabilité, zéro perte de donnée** |

---

## 2bis. Prérequis Odoo (à valider AVANT toute ligne de code)

⚠️ **Trois points bloquants à vérifier impérativement** avant de lancer le développement. Si l'un des trois n'est pas réglé, le projet est à l'arrêt.

### A. Plan Odoo : "Custom" obligatoire

D'après la documentation officielle Odoo, **l'accès à l'API externe (XML-RPC / JSON-RPC) n'est disponible que sur les plans Odoo "Custom"**. Les plans "One App Free" et "Standard" **bloquent l'accès à l'API**, quelle que soit la librairie utilisée.

→ **Action** : Loïc doit confirmer qu'Eurekam est sur un plan Custom Odoo Online (ou que l'instance est self-hosted). Sinon, demander une migration de plan avant développement.

### B. Authentification : clé API plutôt que mot de passe

Sur Odoo Online, les utilisateurs n'ont pas de mot de passe local par défaut (auth via OAuth). Deux options :

1. **Recommandé : clé API** (disponible depuis Odoo 14)
   - Générée par l'utilisateur depuis son profil → Account Security → New API Key
   - Révocable à tout moment sans changer le mot de passe principal
   - À utiliser à la place du mot de passe dans odoorpc (`odoo.login(db, user, api_key)`)
2. Alternative : définir manuellement un mot de passe local via Settings → Users & Companies → Users → Action → Change Password

→ **Action** : créer un **compte de service Odoo dédié** à cet outil (login type `traca-bot@eurekam.fr`), avec uniquement les droits nécessaires (lecture sur `res.partner`, écriture sur `Postes clients` et `Traçabilité`). Générer une API key depuis ce compte. **Ne jamais utiliser le compte personnel d'un technicien.**

### C. Deadline migration API : fin 2027

Odoo a annoncé officiellement que **les endpoints `/xmlrpc`, `/xmlrpc/2` et `/jsonrpc` seront supprimés d'Odoo Online à partir de la version 21.1 (hiver 2027)**, et d'Odoo on-premise en version 22 (automne 2028). Ils seront remplacés par la nouvelle "External JSON-2 API".

→ **Conséquence architecturale** : la couche `src/odoo_client/` doit être **strictement isolée** du reste du code (interface abstraite, aucun import d'`odoorpc` en dehors de ce module). Quand la migration vers JSON-2 sera nécessaire (estimée 2027), seul ce module sera à réécrire — le reste de l'application restera inchangé.

---

## 3. Stack technique recommandée

> Loïc est débutant en programmation. Les choix ci-dessous privilégient la **simplicité**, la **maintenabilité** et un écosystème bien documenté en français.

| Brique | Choix recommandé | Justification |
|--------|------------------|---------------|
| Langage | **Python 3.11+** | Déjà utilisé sur d'autres projets Eurekam, large écosystème, lisible |
| GUI | **PySide6** (Qt for Python) | Natif sous KDE Plasma, rendu cohérent avec le reste du desktop, licence LGPL |
| Connexion Odoo | **`odoorpc`** (≥ 0.10) maintenu par l'OCA, en JSON-RPC | Couche **strictement isolée** dans `src/odoo_client/` derrière une interface abstraite (cf. § 2bis-C). Plan B documenté : `xmlrpc.client` (stdlib, zéro dépendance, plus verbeux) si odoorpc pose problème. |
| Packaging AppImage | **`python-appimage`** | Simple, conçu spécifiquement pour applis Python |
| Configuration | **Fichiers JSON** (cf. § 5) | Édition par les techniciens sans recompilation |
| Logs | **`logging`** stdlib + fichier dans `~/.drugcam-traca/logs/` | Indispensable pour debug à distance |
| Gestion d'erreurs | Pop-ups Qt explicites + log fichier | L'utilisateur doit comprendre ce qui ne va pas |

> **Important** : ne pas utiliser Tkinter (rendu daté), Electron (lourd et non natif Linux), ou GTK (incohérent sous KDE).

---

## 4. Architecture des fichiers

Structure attendue du projet :

```
drugcam-traca/
├── CLAUDE.md                         # ce fichier
├── README.md                         # documentation utilisateur (FR)
├── requirements.txt                  # dépendances Python
├── pyproject.toml                    # métadonnées projet
├── build_appimage.sh                 # script de build AppImage
│
├── src/
│   ├── main.py                       # point d'entrée (lance la GUI)
│   ├── config.py                     # constantes globales (URL Odoo, etc.)
│   │
│   ├── system_info/                  # collecte automatique des données système
│   │   ├── __init__.py
│   │   ├── dmi.py                    # dmidecode (S/N PC, CPU)
│   │   ├── cameras.py                # détection caméras Allied Vision / Toshiba-Teli
│   │   ├── network.py                # adresses MAC enp*
│   │   ├── os_release.py             # version OS, hostname, version drugcam-libs
│   │   └── collector.py              # orchestre la collecte complète
│   │
│   ├── odoo_client/                  # tout ce qui touche à Odoo
│   │   ├── __init__.py
│   │   ├── client.py                 # connexion + authentification
│   │   ├── customers.py              # liste des clients filtrée
│   │   ├── postes.py                 # CRUD table "Postes clients"
│   │   ├── tracabilite.py            # CRUD future table "Traçabilité"
│   │   └── numbering.py              # incrément auto numéros de série
│   │
│   ├── ui/                           # interface graphique PySide6
│   │   ├── __init__.py
│   │   ├── main_window.py            # fenêtre principale + navigation par étapes
│   │   ├── step1_customer.py         # sélection client
│   │   ├── step2_form.py             # formulaire prérempli
│   │   ├── step3_summary.py          # récap avant envoi
│   │   └── widgets.py                # widgets réutilisables
│   │
│   └── data_options/                 # JSON éditables par les techniciens
│       ├── souris.json
│       ├── type_installation.json
│       ├── type_bloc_optique.json
│       ├── type_bloc_alimentation.json
│       ├── type_plot_inox.json
│       ├── modele_uc.json
│       ├── objectif_a.json
│       └── objectif_b.json
│
├── scripts/
│   └── get_camera.sh                 # script bash existant (référence)
│
└── tests/
    ├── test_dmi.py
    ├── test_cameras.py
    └── test_odoo_mocks.py
```

---

## 5. Workflow utilisateur (à implémenter exactement dans cet ordre)

### Étape 0 — Préparation hors logiciel (par le technicien)
- Installation du poste avec l'ISO officielle DRUGCAM (procédure existante).
- Nommage du poste (`assist1`, `assist2`, etc.) via `hostnamectl`.
- Branchement du bloc optique au PC.

### Étape 1 — Lancement de l'AppImage
- Le technicien double-clique l'AppImage **en root** (`sudo ./drugcam-traca.AppImage`).
- Splash-screen Eurekam pendant l'initialisation.
- Test de connexion Odoo dès le lancement → si KO, message d'erreur explicite + bouton « Réessayer ».

### Étape 2 — Sélection du client
- Liste déroulante chargée depuis Odoo : tous les `res.partner` portant **au moins l'une** des étiquettes (`category_id`) **« Projet en cours »** ou **« Clients en Prod »**.
- Champ de recherche avec filtrage en temps réel (le nombre de clients peut être important).
- Bouton « Suivant » désactivé tant qu'aucun client n'est sélectionné.

### Étape 3 — Collecte automatique
- **Barre de progression** pendant la collecte (~5-10 secondes).
- Récupération en parallèle des 8 données système (cf. § 6).
- **Vérification immédiate de doublon** : si un poste avec le même numéro de série PC existe déjà dans Odoo → bloquer avec message clair :
  > « ⚠️ Cette machine est déjà enregistrée dans Odoo (poste : `<nom_existant>`, client : `<client_existant>`). Voulez-vous mettre à jour la fiche existante ou annuler ? »

### Étape 4 — Formulaire prérempli
- Tous les champs auto-détectables sont remplis et **affichés en lecture seule** (mais avec un petit bouton « ✏️ modifier » à côté pour les cas d'erreur de détection).
- Les 8 champs « manuels » sont des **listes déroulantes** chargées depuis les fichiers JSON correspondants.
- Les numéros de série (équipement et bloc optique) sont **préremplis avec le prochain disponible** (cf. § 7) mais restent éditables.
- Champs obligatoires : tous (à l'exception éventuelle de cas notés en commentaire). Marqueur visuel `*` rouge pour les champs obligatoires.
- Bouton « Valider et envoyer » en bas, désactivé tant que tous les obligatoires ne sont pas remplis.

### Étape 5 — Récapitulatif et envoi
- Récap de tous les champs avant envoi.
- Boutons « Modifier » (retour étape 4) et « Confirmer l'envoi ».
- À la confirmation : insertion dans les 2 tables Odoo (cf. § 8) dans une **transaction** (rollback si l'une des deux échoue).
- Écran de succès avec rappel des 2 numéros attribués + bouton « Nouvelle installation » et « Quitter ».

---

## 6. Données système à collecter automatiquement

| # | Donnée | Méthode | Notes |
|---|--------|---------|-------|
| 1 | N° de série PC | `dmidecode -t system \| grep "Serial Number"` | Attention : peut contenir plusieurs `Serial Number` (système, châssis, carte mère). Prendre **uniquement** celui de la section `System Information`. |
| 2 | Version CPU | `dmidecode -s processor-version` | Sortie type : `Intel(R) Core(TM) i5-10500 CPU @ 3.10GHz` |
| 3 | Caméras (modèle + S/N) | Cf. `scripts/get_camera.sh` → réimplémenter en Python | **Règle de tri impérative** : la caméra avec le **plus petit S/N** est la **caméra A**, la plus grande est la **caméra B**. |
| 4 | Nom du poste | `cat /etc/hostname` | Trim final `\n` |
| 5 | Version OS | `cat /etc/os-release` | Extraire le champ `PRETTY_NAME=` (sans guillemets) |
| 6 | Version Assist | `rpm -qa \| grep drugcam-libs` | Sortie type : `drugcam-libs-2.5.11.662-2.el9.x86_64` → extraire les 3 premiers blocs `2.5.11` via regex `r'drugcam-libs-(\d+\.\d+\.\d+)'` |
| 7 | Adresses MAC `enp*` | `ip -o link show \| grep "enp"` (plus stable que `ip addr` à parser) | Concaténer toutes les MAC trouvées séparées par `\|`. Format final attendu : `aa:bb:cc:dd:ee:ff\|11:22:33:44:55:66` |
| 8 | Date d'installation | `datetime.date.today()` | Format ISO `YYYY-MM-DD` côté Python ; le formatage final dépend du champ Odoo |

### Détection caméras (donnée 3) — algorithme

Le script bash fourni utilise `dmesg` qui peut être tronqué sur un système lancé depuis longtemps. **Privilégier `lsusb -v`** ou la lecture directe de `/sys/bus/usb/devices/*/` qui est plus fiable :

```python
# Pseudo-code à transcrire
for device_dir in glob.glob("/sys/bus/usb/devices/*"):
    manufacturer = read_file(f"{device_dir}/manufacturer")
    if manufacturer in ("Allied Vision", "Toshiba-Teli"):
        product = read_file(f"{device_dir}/product")
        serial = read_file(f"{device_dir}/serial")
        cameras.append({"manufacturer": ..., "product": ..., "serial": ...})

# Tri par serial number (string ou int selon format)
cameras.sort(key=lambda c: c["serial"])
camera_A = cameras[0]  # plus petit serial
camera_B = cameras[1]  # plus grand serial
```

Si moins de 2 caméras sont détectées → **erreur bloquante** avec message explicite (« Vérifier que le bloc optique est bien branché »).

Conserver le script bash existant dans `scripts/get_camera.sh` à des fins de référence et de fallback debug.

---

## 7. Incrémentation des numéros de série

Deux numéros à attribuer **automatiquement** :

| Numéro | Format | Origine |
|--------|--------|---------|
| N° de série équipement | `AB` + 6 chiffres (ex. `AB000123`) | `MAX(numéro existant) + 1` dans la table `Traçabilité`, colonne `N° DE SERIE` |
| N° bloc optique | `01` + 4 chiffres (ex. `010042`) | `MAX(numéro existant) + 1` dans la table `Traçabilité`, colonne `N° BLOC OPTIQUE` |

Logique :
1. Au moment d'afficher le formulaire (étape 4), faire un `search_read` Odoo trié desc sur chaque colonne.
2. Extraire la partie numérique avec une regex (`r'AB(\d+)'` et `r'01(\d+)'`).
3. Incrémenter de 1, formater avec `zfill(6)` et `zfill(4)`.
4. Préremplir les champs (mais **laisser éditable** au cas où).

⚠️ **Risque de collision** si deux techniciens utilisent l'outil en même temps. Pour le prototype, c'est acceptable (taux d'usage faible). À noter dans le README comme limitation connue.

---

## 8. Mapping Odoo

### Table `Postes clients` (existante — modèle Odoo à confirmer avec Loïc)
| Colonne Odoo | Source |
|--------------|--------|
| Client | Client sélectionné étape 2 (`partner_id`) |
| Description | Donnée 4 (hostname) |
| Version de Fedora | Donnée 5 (PRETTY_NAME OS) |
| Version de Assist | Donnée 6 (`2.5.11`) |
| Adresse MAC | Donnée 7 |

### Future table `Traçabilité` (à créer — voir Loïc avant d'implémenter)
| Colonne Odoo | Source |
|--------------|--------|
| N° DE SERIE | Auto incrément `ABxxxxxx` |
| CLIENT | Client sélectionné |
| N° BLOC OPTIQUE | Auto incrément `01xxxx` |
| NOM DU POSTE | Donnée 4 |
| TYPE | Information 2 (type installation) |
| MODELE | Information 3 (type bloc optique) |
| UC | Information 6 + ` ` + Donnée 1 (modèle UC + S/N PC séparés par espace) |
| VERSION CPU | Donnée 2 |
| MODÈLE CAM A | Donnée 3 — Product caméra A |
| MODÈLE CAM B | Donnée 3 — Product caméra B |
| N° CAM A | Donnée 3 — Serial caméra A |
| N° CAM B | Donnée 3 — Serial caméra B |
| OBJ CAM A | Information 7 |
| OBJ CAM B | Information 8 |
| SOURIS | Information 1 |
| BLOC ALIM | Information 4 |
| DATE D'INSTALLATION | Donnée 8 |
| PLOTS INOX | Information 5 |
| Version de Assist | Donnée 6 |
| Adresse MAC | Donnée 7 |

> ⚠️ **Le modèle Odoo `tracabilite` n'existe pas encore.** Il faudra :
> 1. Demander à Loïc le nom technique exact du modèle (`x_tracabilite` ? `eurekam.tracabilite` ?) une fois créé côté Odoo.
> 2. En attendant, prévoir un **mode mock** activé par variable d'environnement (`DRUGCAM_TRACA_DRY_RUN=1`) qui logge ce qui aurait été inséré au lieu d'appeler Odoo. Indispensable pour développer/tester sans dépendre de la création du modèle Odoo.

---

## 9. Format des fichiers JSON (data_options/)

Format standard pour tous les fichiers (avec libellé affiché distinct de la valeur Odoo si besoin) :

```json
{
  "label": "Modèle de souris",
  "options": [
    { "display": "Logitech M185", "value": "logitech_m185" },
    { "display": "Microsoft Basic Optical", "value": "ms_basic_optical" }
  ]
}
```

Chargement au démarrage : si un fichier est manquant, afficher un avertissement et permettre la saisie libre dans le champ correspondant. **Ne pas crasher.**

Initialiser chaque fichier JSON avec **au minimum 2-3 options réalistes** que Loïc complétera. Marquer dans le README la procédure d'ajout d'options (éditer le JSON, **pas besoin de recompiler**).

---

## 10. Configuration Odoo et architecture de la couche d'accès

### Connexion : exemple avec odoorpc + API key

```python
import odoorpc

odoo = odoorpc.ODOO('eurekam.odoo.com', protocol='jsonrpc+ssl', port=443)
odoo.login('eurekam', 'traca-bot@eurekam.fr', API_KEY)  # API key, pas mot de passe
```

### Fichier `src/config.py`

```python
ODOO_HOST = "eurekam.odoo.com"          # ou "odoo.eurekam.fr" si self-hosted — à confirmer
ODOO_DB = "eurekam"                      # à confirmer
ODOO_LOGIN = "traca-bot@eurekam.fr"      # compte de service dédié (cf. § 2bis-B)
ODOO_API_KEY = "..."                     # ⚠️ chargée depuis fichier externe ou env var
ODOO_PROTOCOL = "jsonrpc+ssl"
ODOO_PORT = 443
```

### Sécurité des credentials

Ne **jamais** commiter `ODOO_API_KEY` dans Git. Charger depuis l'une de ces sources, dans cet ordre de priorité :
1. Variable d'environnement `DRUGCAM_TRACA_API_KEY` (recommandé pour le déploiement)
2. Fichier `~/.drugcam-traca/credentials.json` (créé manuellement au premier lancement)

Si aucune source n'est trouvée, afficher un dialogue Qt demandant la clé API au technicien et la sauvegarder dans `~/.drugcam-traca/credentials.json` (avec permissions `600`).

### Interface abstraite (anticipation migration JSON-2 API en 2027)

Pour pouvoir migrer sans douleur quand l'endpoint `/jsonrpc` sera supprimé d'Odoo Online, **toute la communication Odoo passe par une interface abstraite** :

```python
# src/odoo_client/base.py — interface, pas d'import odoorpc ici
from abc import ABC, abstractmethod

class OdooClientBase(ABC):
    @abstractmethod
    def authenticate(self) -> None: ...

    @abstractmethod
    def list_active_customers(self) -> list[dict]: ...

    @abstractmethod
    def find_poste_by_serial(self, serial: str) -> dict | None: ...

    @abstractmethod
    def next_tracability_serial(self) -> str: ...

    @abstractmethod
    def next_optical_block_serial(self) -> str: ...

    @abstractmethod
    def create_poste_client(self, data: dict) -> int: ...

    @abstractmethod
    def create_tracability_record(self, data: dict) -> int: ...
```

Implémentations :
- `src/odoo_client/odoorpc_impl.py` → implémentation actuelle avec odoorpc (à coder maintenant)
- `src/odoo_client/json2_impl.py` → implémentation future avec External JSON-2 API (à coder mi-2027)
- `src/odoo_client/mock_impl.py` → implémentation factice pour `DRUGCAM_TRACA_DRY_RUN=1` et tests

Le reste de l'application n'importe **jamais** odoorpc directement — uniquement `OdooClientBase`.

---

## 11. Gestion des erreurs

Liste des cas à gérer **explicitement** (chacun = un message Qt clair, pas de stacktrace pour l'utilisateur) :

- Pas de connexion réseau / Odoo injoignable
- Identifiants Odoo invalides
- `dmidecode` absent ou en erreur (impossible si lancé en root sur Rocky 9, mais à logger)
- Moins de 2 caméras détectées
- Plus de 2 caméras détectées (avertir + laisser le technicien choisir A et B manuellement)
- Paquet `drugcam-libs` non installé (Donnée 6 manquante)
- Aucune interface réseau `enp*` trouvée (Donnée 7 manquante) → demander confirmation au technicien
- Doublon : poste déjà enregistré (cf. étape 3)
- Échec d'insertion Odoo en cours de transaction → rollback et message « Veuillez recommencer »

Toutes ces erreurs vont aussi dans le fichier de log `~/.drugcam-traca/logs/traca-YYYYMMDD.log`.

---

## 12. Build AppImage

Script `build_appimage.sh` à fournir :

```bash
#!/bin/bash
# Génère drugcam-traca-<version>-x86_64.AppImage
# Utilise python-appimage avec Python 3.11 embarqué
# Inclut PySide6 et toutes les dépendances de requirements.txt
```

**Checklist de validation post-build** :
- [ ] L'AppImage se lance sur une Rocky Linux 9 fraîche sans rien installer (sauf `dmidecode` et `pciutils` qui sont sur l'ISO Drugcam)
- [ ] L'AppImage fait moins de 100 Mo
- [ ] L'icône Eurekam s'affiche dans la barre des tâches KDE
- [ ] Les fichiers JSON `data_options/` sont accessibles **en écriture** depuis l'AppImage (sinon, prévoir une copie initiale dans `~/.drugcam-traca/data_options/` au premier lancement)

---

## 13. Conventions de code

- **Langue** : code en anglais (variables, fonctions), **commentaires et docstrings en français**, messages utilisateur en français.
- **Style** : PEP 8, formaté avec `black` et `ruff`.
- **Type hints** systématiques sur toutes les fonctions publiques.
- **Logging** : pas de `print()`, uniquement `logger.info/warning/error()`.
- **Tests** : `pytest`, utiliser `mock_impl.py` (cf. § 10) pour tester sans contacter l'instance Odoo de prod. Aucun test ne doit nécessiter une connexion réseau.
- **Pas de dépendance superflue** : avant d'ajouter un paquet, vérifier qu'il n'existe pas déjà une solution dans la stdlib.

---

## 14. Roadmap suggérée pour Claude Code

À faire dans cet ordre, en validant chaque étape avec Loïc avant de passer à la suivante :

0. **Vérifications préalables Odoo (cf. § 2bis)** — bloquant : confirmer plan Custom, créer compte de service + API key, valider que `odoorpc.ODOO(...).version` répond bien depuis un script Python à 5 lignes. **Ne pas commencer le code applicatif tant que cette étape n'est pas verte.**
1. **Initialiser le squelette du projet** (structure de fichiers § 4, `pyproject.toml`, `requirements.txt`, `.gitignore`).
2. **Module `system_info/`** seul, avec un script CLI de test qui affiche toutes les données collectées dans un terminal (pas de GUI). → Permet à Loïc de tester sur un vrai poste Drugcam avant d'aller plus loin.
3. **Module `odoo_client/`** : d'abord l'interface abstraite `OdooClientBase`, puis l'implémentation `odoorpc_impl.py`, puis l'implémentation `mock_impl.py`. Script CLI de test qui se connecte et liste les clients filtrés. Mode `DRY_RUN` pour les inserts.
4. **Squelette GUI PySide6** : navigation entre les 5 étapes avec des écrans factices.
5. **Branchement** des modules sur la GUI, étape par étape (1 → 2 → 3 → 4 → 5).
6. **Gestion d'erreurs** systématique sur tous les chemins.
7. **Build AppImage** + test sur poste vierge.
8. **Documentation utilisateur** (README) + procédure de mise à jour des JSON.

---

## 15. Hors périmètre du prototype (à noter dans le README, pas à implémenter)

- Mise à jour automatique de l'AppImage.
- Multi-utilisateur / multi-technicien simultané (verrou sur les numéros de série).
- Mode hors-ligne (cache local + synchro différée).
- Édition rétroactive d'une fiche existante (autre que le cas doublon).
- Internationalisation (i18n) : tout reste en français.

---

## 16. Questions ouvertes à clarifier avec Loïc avant développement

### 🔴 Bloquantes — à régler AVANT toute ligne de code (cf. § 2bis)
- [ ] **Plan Odoo** : confirmer plan Custom (sinon API externe inaccessible).
- [ ] **Hébergement** : Odoo Online (`*.odoo.com`) ou self-hosted ? URL exacte de l'instance.
- [ ] **Compte de service** dédié créé côté Odoo (login + API key générée).
- [ ] **Droits du compte de service** : a minima lecture sur `res.partner` et `res.partner.category`, écriture sur `Postes clients` et future `Traçabilité`.

### 🟠 Structurantes — à régler avant le module `odoo_client/`
- [ ] Nom technique exact du modèle Odoo pour la table `Traçabilité` (modèle à créer côté Odoo).
- [ ] Noms techniques exacts des champs Odoo de la table `Postes clients` existante.
- [ ] Noms exacts des étiquettes (`res.partner.category`) « Projet en cours » et « Clients en Prod ».
- [ ] Format précis des dates dans les champs Odoo (`Date` ou `Datetime` ?).

### 🟡 Fonctionnelles — à régler avant l'étape concernée
- [ ] L'étape de mise à jour d'une fiche existante (cas doublon) est-elle vraiment souhaitée pour le prototype, ou simple blocage ?
