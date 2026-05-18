# Changelog du module `eurekam_drugcam_traca`

Format inspiré de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/).
Versionnement : `<odoo_major>.<minor>.<patch>` (convention Odoo).

---

## [18.0.3.0.0] — 2026-05-15

### Modifié
- **`mouse_model`** : `Selection` → `Many2one('product.template')`.
  - Domaine : `name =ilike "Souris %"`.
  - Exclut "Tapis de souris" / "Tapis de souris avec logo" (ne commencent
    pas par "Souris ").
- Tracking conservé. Désormais **7 champs Many2one** product.template au
  total (les 6 de v18.0.2.0.0 + mouse_model).

---

## [18.0.2.0.0] — 2026-05-15

### Modifié
- **6 champs Selection transformés en Many2one vers `product.template`** :
  - `camera_a_model`, `camera_b_model`, `scene_camera_model` →
    `Many2one('product.template')` avec domaine
    `name =ilike "CAMERA %"` OR `name =ilike "Caméra %"`
  - `uc_model` → `Many2one('product.template')` avec domaine
    `name =ilike "PC %"`
  - `camera_a_objective`, `camera_b_objective` →
    `Many2one('product.template')` avec domaine `name =ilike "Objectif %"`
- Avantage : enrichir le catalogue produits Drugcam dans Odoo (ajouter
  une nouvelle référence caméra/PC/objectif) **sans toucher au code du
  module**.
- Cohérence avec les autres modules Odoo (achats, stocks, facturation
  exploitent déjà `product.template`).

### Compatibilité
- Le module ne propose **pas** de migration automatique des anciennes
  valeurs Selection. Comme aucune fiche n'avait encore de valeurs
  remplies sur ces 6 champs côté sandbox/recette, c'est sans impact.
- Pré-requis côté Odoo : créer les articles correspondants dans
  `product.template` avec les bons préfixes de nom (cf. README §
  "Pré-requis catalogue produit").

### Côté logiciel `drugcam-traca` (Python/Qt)
- Adaptation simultanée en v0.4.0 (cf. CHANGELOG global du repo).

---

## [18.0.1.0.0] — 2026-05-11

### Ajouté
- **Premier release** du module en tant que vraie addon Odoo (Python +
  XML), suite à la décision de migrer depuis l'ancienne approche
  Studio/API (`state='manual'` + 22 champs `x_*`) vers un module versionnable.
- 22 champs métier sur `customer.asset.workstation` :
  - 13 Selections (workstation_type, uc_model, optical_block_type,
    camera_a/b_model, camera_a/b_objective, camera_a/b_cable,
    scene_camera_model, mouse_model, power_supply_type, inox_plot_type)
  - 7 Char (workstation_serial_number, optical_block_serial,
    pc_serial_number, cpu_version, camera_a/b_serial, scene_camera_serial)
  - 1 Date (installation_date)
  - 1 Text (comments)
- Tous avec `tracking=True` → audit dans le chatter.
- 5 vues d'héritage :
  - 2 sur `customer.asset.workstation` (form + list)
  - 3 sur `res.partner` (renommage titres SAV, colonnes optionnelles
    dans le tableau Postes Assist, retrait `editable="bottom"`)
- Suite de tests Odoo basiques (`tests/test_customer_asset_workstation.py`).

### Migration depuis l'ancien système (`state='manual'`)
- Les noms techniques **n'ont plus le préfixe `x_`** : `workstation_type`
  au lieu de `x_workstation_type`. Cohérent avec les champs natifs
  Scalizer.
- Aucune donnée à migrer : la sandbox/recette précédente avait été
  écrasée et n'avait pas de données réelles dans ces champs.
- Les anciens scripts `setup_drugcam_extensions.py` et
  `verify_drugcam_extensions.py` du repo principal sont **archivés** dans
  `docs/odoo_admin/legacy_studio/` (référence historique).
