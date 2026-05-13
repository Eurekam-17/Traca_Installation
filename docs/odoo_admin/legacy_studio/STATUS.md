# ⚠️ ARCHIVÉ — ne plus utiliser

Ce dossier contient l'**ancienne approche** des extensions Odoo Drugcam,
qui passait par des **champs `state='manual'`** (créés via Odoo Studio
ou via le script Python `setup_drugcam_extensions.py`).

À partir de la **v0.3.0** du projet, cette approche est **remplacée**
par un vrai module Odoo : voir
[`odoo_module/eurekam_drugcam_traca/`](../../../odoo_module/eurekam_drugcam_traca/).

## Pourquoi c'est archivé

- Recommandation du prestataire Eurekam : un vrai module est plus stable
  et plus pérenne face aux upgrades Odoo.
- Le module gère lui-même son installation, sa désinstallation, sa
  migration → plus besoin de scripts setup/verify côté Python.

## Contenu du dossier

| Fichier | Rôle (historique) |
|---|---|
| `README_legacy.md` | Ancienne vue d'ensemble |
| `01_modele_workstation_fields.md` | Inventaire des 22 champs (préfixe `x_*`) |
| `02_vues_heritage.md` | Les 5 vues d'héritage (style Studio) |
| `03_tracking.md` | Activation du tracking côté `ir.model.fields` |
| `04_renommages_libelles.md` | Renommages SAV (déjà repris dans le module) |
| `05_migration_checklist.md` | Procédure de migration entre instances |
| `odoo_extensions.json` | JSON déclaratif (source of truth de l'époque) |
| `setup_drugcam_extensions.py` | Script Python qui créait les champs/vues via API |
| `verify_drugcam_extensions.py` | Script d'audit (lecture seule) |

## En cas de besoin

Si tu dois restaurer l'ancien système (par exemple pour comparer) :

```bash
# Le script setup pointe sur src/config.py qui a été conservé
python docs/odoo_admin/legacy_studio/setup_drugcam_extensions.py --env staging --dry-run
```

⚠️ Mais ne le fais qu'en connaissance de cause — utiliser **simultanément**
les anciens `x_*` et le nouveau module (sans `x_`) sur la même instance
peut créer de la confusion (mais pas de bug technique : ce sont des
champs différents en base).
