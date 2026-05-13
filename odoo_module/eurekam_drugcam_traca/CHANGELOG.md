# Changelog du module `eurekam_drugcam_traca`

Format inspiré de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/).
Versionnement : `<odoo_major>.<minor>.<patch>` (convention Odoo).

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
