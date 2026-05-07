# Changelog

Toutes les modifications notables de l'outil de traçabilité Drugcam sont
documentées ici.

Format inspiré de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/),
versionnement sémantique simplifié `MAJOR.MINOR.PATCH` :
- **MAJOR** = changement de modèle Odoo cible incompatible (exigerait une
  migration côté serveur)
- **MINOR** = ajout de fonctionnalité ou évolution de schéma compatible
- **PATCH** = correction de bug, documentation, refactor sans impact

---

## [0.2.0] — 2026-05-06

> **Changement architectural majeur** suite à l'écrasement de la base
> staging et au repivot vers le module Scalizer existant.

### Changé (côté Odoo)
- **Bascule sur la nouvelle instance** `eurekam-recette.odoo.com` (l'ancienne
  staging `eurekam-staging-28517368` ayant été remplacée par une copie
  fraîche de la prod).
- **Abandon du modèle `x_customer_asset_installation_log`** (ancien
  modèle dédié à l'historique d'installations qui avait été créé en v0.1.3).
- Les **22 champs métier** sont désormais ajoutés directement sur le
  modèle `customer.asset.workstation` (module Scalizer
  `s6r_eurekam_customer_assets`) en mode `state='manual'`. Plus de modèle
  séparé : 1 fiche workstation = 1 jeu de valeurs (état actuel du poste).
- 3 nouvelles vues d'héritage côté Odoo :
  - vue **form** `customer.asset.workstation` enrichie avec 7 sections
    (Identification / UC / Bloc optique / Caméras A & B / Caméra de scène /
    Accessoires / Commentaires)
  - vue **list standalone** : 22 colonnes optionnelles
  - **list inline** dans l'onglet "SAV & Informations Techniques" de
    `res.partner` : les 22 colonnes apparaissent dans le sélecteur ⚙️
    du tableau "Postes Assist"

### Changé (côté code Python)
- **`PosteData`** enrichie de 22 attributs (avec defaults `""` pour
  rester rétro-compatible). Plus de `TracabiliteData` (supprimé).
- **`OdooClientBase.create_poste_client`** devient un **UPSERT** :
  recherche par `(partner_id, name=hostname)`, mise à jour si trouvé,
  création sinon. Retourne toujours l'ID workstation.
- **`find_poste_by_serial`** : recherche directe sur
  `customer.asset.workstation.x_pc_serial_number` (au lieu de l'ancien
  modèle log).
- **`next_*_serial`** : lecture sur `customer.asset.workstation`
  (champs `x_workstation_serial_number` et `x_optical_block_serial`).
- **Worker step3** : 1 seul appel API au lieu de 2. Plus de rollback
  transactionnel (l'UPSERT gère naturellement le re-run).
- **`InstallationDraft.to_poste_data()`** unique méthode de conversion
  (suppression de `to_tracabilite_data`).
- 38 tests pytest passent (au lieu de 36 : ajout d'un test de payload
  minimal).

### Trade-offs assumés (option A "tout sur workstation")
- ✅ **Plus simple** : 1 modèle, 1 appel API, pas de rollback, pas de
  Many2one inverse.
- ❌ **Pas d'historique structuré** : si tu remplaces une caméra ou
  changes un câble dans 6 mois, les anciennes valeurs sont écrasées.
  Mitigation : le **chatter Odoo natif** logge automatiquement les
  modifications (qui, quand, ancien/nouveau). Pas exploitable comme
  un tableau, mais consultable poste par poste.

---

## [0.1.4] — 2026-05-06

### Ajouté
- **Profils d'environnement Odoo** (`staging` / `prod`) dans `src/config.py`
  via le dictionnaire `PROFILES`. **Staging par défaut** pour empêcher les
  écritures accidentelles en production.
- Argument CLI `--env staging|prod` et variable d'environnement
  `DRUGCAM_TRACA_ENV` (priorité CLI > env > défaut staging).
- Fonctions utilitaires `config.apply_env()`, `config.is_production()`,
  `config.active_profile_label()`.
- **Bandeau coloré permanent** en haut de la fenêtre principale et de la
  barre des tâches KDE (`[STAGING]` / `[PROD]` dans le titre) :
  - 🟠 orange = staging
  - 🔴 rouge = production avec mention explicite « toute écriture impactera
    la base réelle »
  - 🧪 bleu = mode `--mock` / DRY-RUN
- **Sélecteur d'environnement** dans la boîte de dialogue de saisie
  initiale des credentials. Avertissement coloré contextuel selon le profil.
- Fichier `.env.example` documentant toutes les variables d'environnement
  reconnues par l'application.
- Section dédiée « Choix de l'environnement Odoo » dans le `README.md`.
- `CHANGELOG.md` (ce fichier).

### Modifié
- **Stockage des credentials par profil** : les credentials sont désormais
  sauvegardés dans `~/.drugcam-traca/credentials.<profile>.json` au lieu d'un
  unique `credentials.json`. Évite qu'une saisie en prod n'écrase la clé
  staging et inversement. Migration automatique de l'ancien fichier au
  premier démarrage.
- `load_credentials()` ignore désormais un fichier dont le `host` ne
  correspond pas au profil actif (anti-mismatch).
- `.gitignore` enrichi : `credentials.*.json`, `*.credentials.json`,
  `secrets/`, `*.key`, `*.pem`, `.env*` (sauf `.env.example`),
  `tool-results/`, `.claude/`.

### Sécurité
- Vérification automatisée pré-push GitHub :
  - `git check-ignore` confirme que tous les fichiers sensibles
    (`credentials.staging.json`, `credentials.prod.json`, `.env`, logs,
    AppImages) sont bien exclus.
  - `grep` confirme l'absence de tout secret hard-codé dans le code source.

---

## [0.1.3] — 2026-05-06

### Ajouté (côté Odoo)
- **17 nouveaux champs** sur le modèle `x_customer_asset_installation_log` :
  - 10 Selections (workstation_type, uc_model, optical_block_type,
    camera_a/b_model, camera_a/b_objective, mouse_model, power_supply_type,
    inox_plot_type, scene_camera_model)
  - 2 Selections supplémentaires (camera_a/b_cable)
  - 4 Char libres (workstation_name, workstation_serial_number,
    scene_camera_serial, snapshots OS)
  - 1 Text long (commentaires)
- 13 fichiers `data_options/*.json` alignés sur les valeurs techniques des
  Selections Odoo (clé `value` = valeur technique attendue).

### Modifié
- **Renommage des titres** de l'onglet "SAV & Informations Techniques"
  sur la fiche Contact :
  - "Environnements" → **"Serveur Control"**
  - "Postes" → **"Poste Assist"**
  - "Installation history (Drugcam)" → **"Historique installation Hardware"**
- Renommage `x_installation_type` (Char libre, type d'intervention) →
  `x_workstation_type` (Selection, type d'enceinte/hotte). Sémantique
  alignée sur les besoins métier de l'équipe.
- 9 champs Char transformés en Selection (impact destructif géré : la base
  staging ne contenait aucune donnée réelle).
- Step 2 (formulaire) : nouvelle section « Saisies libres » avec un
  `QTextEdit` pour les commentaires. Combos Selection désormais sans saisie
  libre (Odoo refuserait toute valeur hors liste).
- Step 3 (récap) : présentation structurée incluant tous les nouveaux
  champs (caméra de scène, S/N poste, type d'enceinte, commentaires).
- Vue list embarquée sur `res.partner` : retrait de `editable="bottom"`
  pour qu'un clic sur une ligne ouvre le formulaire complet, et tous les
  champs en `optional="show"`/`"hide"` pour permettre l'affichage/masquage
  via le sélecteur de colonnes.

### Refactor
- `TracabiliteData` (dataclass) : 8 nouveaux attributs, contrat « valeurs
  techniques snake_case » documenté.
- `InstallationDraft` : 11 nouveaux attributs, `required_missing()`
  étendu à 23 champs obligatoires.
- `odoorpc_impl.create_tracability_record` : mapping complet sur les 29
  champs métier, gestion `or False` pour les Selections vides.

---

## [0.1.2] — 2026-05-04

### Ajouté
- Découverte et intégration du modèle Odoo Eurekam existant
  `customer.asset.workstation` (383 enregistrements en staging — le « Postes
  clients » du CLAUDE.md). L'app utilise désormais ce modèle réel au lieu
  du `x_postes_clients` placeholder.
- Création du modèle Odoo `x_customer_asset_installation_log` (22 champs
  initiaux) lié à `customer.asset.workstation` via `x_workstation_id`, et
  remontant comme One2many `x_installation_log_ids` sur `res.partner`.
- Vues Odoo associées : list, form, héritage `res.partner` pour ajouter le
  tableau dans l'onglet « SAV & Informations Techniques ».
- ACL pour le nouveau modèle (Internal User : R/W/Create — Admin : tous
  droits dont unlink).
- Méthode `OdooClientBase.delete_poste_client(id)` pour rollback
  transactionnel en cas d'échec d'insertion Traçabilité.

### Modifié
- Étiquettes filtrées dans la liste des clients : `1- NEW` et `EN PROD`
  (noms réels Eurekam) au lieu de `Projet en cours` / `Clients en Prod`.
- `create_poste_client` : sémantique **lookup-or-create** par
  `(partner_id, name=hostname)`. Évite les doublons de fiches workstation
  en cas de réinstallation chez le même client.
- Résolution Many2one de `software_assist_version_id` (le champ Assist
  est un Many2one vers `customer.asset.software.version` côté Odoo, pas
  un Char). Création à la volée si la version n'existe pas encore.
- `find_poste_by_serial` cherche désormais dans les `installation_log`
  par `x_pc_serial_number` (au lieu de la fiche poste, sémantique plus
  juste pour la traçabilité historique).
- 16 enums Qt en forme courte (`Qt.AlignCenter`, `QMessageBox.Critical`...)
  → forme complète (`Qt.AlignmentFlag.AlignCenter`,
  `QMessageBox.Icon.Critical`...). Évite les `DeprecationWarning` Qt 6.x
  et garantit la compatibilité avec Qt 7.x.

### Corrigé
- 🔴 **Bloquant** : annulation du popup « Poste déjà enregistré »
  laissait l'UI cassée. `system_info` est maintenant remis à `None` pour
  relancer la collecte au prochain passage.
- 🔴 **Bloquant** : `QApplication(sys.argv)` interceptait les arguments
  métier (`--mock`, `-v`). Passage en `QApplication([sys.argv[0]])`.
- 🟠 **Race condition** : les threads de collecte écrivaient
  concurremment dans le même `SystemInfo`. Ajout d'un `threading.Lock`
  partagé pour protéger les écritures (`info.errors[]`, `setattr`).
- 🟠 **QThread destroyed while still running** : closeEvent qui fait
  `stop_workers()` sur chaque step + `wait(2000)` sur le worker login.
- 🟠 Vue Step 1 : message « aucun client » écrit sur le mauvais widget
  (jamais affiché). Désormais routé vers la vue d'erreur.

### Sécurité
- Test de cohérence credentials.json ↔ profil actif : ignore le fichier
  si le `host` ne match pas (prépare l'arrivée des profils en 0.1.4).

---

## [0.1.1] — 2026-04-30

### Corrigé
- 🔴 **Build AppImage cassé** : pin `PySide6>=6.6,<7.0` interprété par
  `/bin/sh` comme une redirection (le `<` est mangé). Passage à
  `PySide6>=6.6` sans pin haut.
- 🔴 **AppImage produite incorrecte** : le fichier `entrypoint.py` que
  python-appimage attend doit être un **script bash**, malgré l'extension
  `.py` (piège du nommage). Ré-écriture en `#! /bin/bash`.
- 🔴 **Wheel local non trouvé** par pip lors du build AppImage : pip
  cherchait dans `/tmp/python-appimage-XXX/` au lieu de la recette.
  Solution : copie du wheel dans `/tmp/drugcam-traca-wheel-XXX/` (chemin
  sans espace) et référence par chemin absolu dans `requirements.txt`.
- 🔴 **`data_options/*.json` introuvables** une fois l'app installée en
  wheel : le chemin était calculé via `PROJECT_ROOT`. Correction :
  `Path(__file__).parent / "data_options"` (fonctionne en dev ET dans le
  wheel installé).
- 🔴 **`dialog.Accepted` n'existe pas comme attribut d'instance** en
  PySide6 6.11. Remplacé par `QDialog.DialogCode.Accepted`.
- `pyproject.toml` : `py-modules = ["main", "config"]` pour que le wheel
  inclue les modules top-level.

### Ajouté
- Affichage de la version installée au démarrage (log
  `=== Démarrage drugcam-traca v0.1.1 ===`) — utile pour diagnostiquer un
  AppImage builée à partir d'un code source désynchronisé.
- Scripts d'aide Windows (`scripts/run_mock.bat`, `run_cli_collect.bat`,
  `run_cli_odoo.bat`) avec UTF-8 forcé pour le développement local.

---

## [0.1.0] — 2026-04-30

### Ajouté — Première version
- **Squelette projet** : structure src-layout, `pyproject.toml`,
  `requirements.txt`, `.gitignore`, `README.md`.
- **Module `system_info/`** (Rocky 9 only) : collecte parallèle des 8
  données système — N° série PC, version CPU, caméras Drugcam (avec règle
  S/N croissant pour la caméra A), hostname, version OS, version Assist,
  MAC enp\*, date d'installation. CLI de test `python -m system_info.cli`.
- **Module `odoo_client/`** : interface abstraite `OdooClientBase`,
  implémentation `odoorpc_impl`, mock `mock_impl`, factory de sélection
  selon `DRUGCAM_TRACA_DRY_RUN`. Logique d'incrémentation des numéros de
  série équipement (`AB000001+`) et bloc optique (`010001+`).
- **GUI PySide6** : fenêtre principale + 3 étapes (sélection client,
  formulaire prérempli avec collecte en arrière-plan, récap + envoi),
  dialogue de saisie credentials, gestion d'erreurs avec dialogues Qt.
- **8 fichiers `data_options/*.json`** éditables sans recompilation
  (souris, type installation, type bloc optique, type bloc alimentation,
  plots inox, modèle UC, objectif caméra A et B).
- **`build_appimage.sh`** + script de lancement Linux
  (`scripts/launch.sh`) + entrée `.desktop` KDE pour intégration menu.
- **34 tests pytest** sur les modules critiques (numbering, dmi, cameras,
  collector, mock_odoo, installation_draft).
- Documentation utilisateur en français (README), gestion des
  credentials en variable d'env ou fichier JSON local (perms 600).

### Périmètre initial selon `CLAUDE.md`
- Cible Rocky Linux 9 + KDE Plasma, livré en AppImage exécutée en root.
- Mode `DRY-RUN` (`--mock`) pour développer sans toucher à Odoo.
- Couche Odoo strictement isolée derrière `OdooClientBase` (anticipation
  de la migration vers la future External JSON-2 API en 2027).

---

[0.2.0]: https://github.com/Eurekam-17/Traca_Installation/releases/tag/v0.2.0
[0.1.4]: https://github.com/Eurekam-17/Traca_Installation/releases/tag/v0.1.4
[0.1.3]: https://github.com/Eurekam-17/Traca_Installation/releases/tag/v0.1.3
[0.1.2]: https://github.com/Eurekam-17/Traca_Installation/releases/tag/v0.1.2
[0.1.1]: https://github.com/Eurekam-17/Traca_Installation/releases/tag/v0.1.1
[0.1.0]: https://github.com/Eurekam-17/Traca_Installation/releases/tag/v0.1.0
