# Documentation Odoo — extensions Drugcam Traca

Ce dossier répertorie **tout** ce qui a été ajouté/modifié côté Odoo
au-delà du module prestataire `s6r_eurekam_customer_assets`. Il sert
de référence pour :
- Comprendre l'état attendu d'une instance Odoo qui héberge le projet.
- Réinstaller ces extensions sur une nouvelle instance (changement
  d'instance, migration de version Odoo, restauration de backup, etc.).
- Diagnostiquer une régression (champ qui a disparu, vue qui ne
  s'affiche pas, etc.).

## Structure

| Fichier | Contenu |
|---|---|
| [`README.md`](README.md) | Ce fichier — vue d'ensemble |
| [`01_modele_workstation_fields.md`](01_modele_workstation_fields.md) | Les **22 champs custom** créés sur `customer.asset.workstation` |
| [`02_vues_heritage.md`](02_vues_heritage.md) | Les **5 vues d'héritage** créées |
| [`03_tracking.md`](03_tracking.md) | Champs avec tracking activé (audit Odoo dans le chatter) |
| [`04_renommages_libelles.md`](04_renommages_libelles.md) | "Environnements"→"Serveurs Control", "Postes"→"Postes Assist" |
| [`05_migration_checklist.md`](05_migration_checklist.md) | Procédure pas-à-pas pour migrer vers une nouvelle instance |

## Source of truth = JSON déclaratif

Le fichier [`scripts/odoo_admin/odoo_extensions.json`](../../scripts/odoo_admin/odoo_extensions.json)
est la **source of truth** : il décrit toutes les entités attendues
(champs, vues, métadonnées). C'est ce fichier qui est lu par les
2 scripts d'admin :

| Script | Action | Code retour |
|---|---|---|
| [`setup_drugcam_extensions.py`](../../scripts/odoo_admin/setup_drugcam_extensions.py) | Crée/met à jour ce qui manque ou diverge (idempotent) | 0 = OK, ≥1 = erreur |
| [`verify_drugcam_extensions.py`](../../scripts/odoo_admin/verify_drugcam_extensions.py) | Lecture seule : compare l'état réel au JSON, sort un rapport | 0 = conforme, 1 = manquant, 2 = divergent |

### Cycle de vie

```
Modification côté Odoo (mode dev / Studio / via mon MCP)
        ↓
Mise à jour de odoo_extensions.json (manuelle, source of truth)
        ↓
Mise à jour de la doc Markdown correspondante
        ↓
Commit Git
        ↓
verify_drugcam_extensions.py CI = quality gate
```

## Pré-requis fonctionnels côté Odoo

- Plan **Custom** Odoo Online (ou self-hosted) pour avoir l'API XML-RPC/JSON-RPC.
- Module `s6r_eurekam_customer_assets` (Scalizer) **installé**.
- Compte de service Odoo `traca-bot@eurekam.fr` (ou équivalent) avec
  une **clé API** valide et les droits suivants :
  - Lecture/écriture sur `ir.model.fields`, `ir.ui.view` (admin Settings)
  - Lecture/écriture sur `customer.asset.workstation`
  - Lecture sur `res.partner`, `res.partner.category`

## Workflow recommandé en cas de migration

```bash
# 1. Sur la nouvelle instance, lancer un audit pour voir l'état initial
python scripts/odoo_admin/verify_drugcam_extensions.py --env staging
# (probable : tout en MISSING)

# 2. Lancer le setup en dry-run pour voir ce qui serait fait
python scripts/odoo_admin/setup_drugcam_extensions.py --env staging --dry-run

# 3. Si le plan est OK, lancer pour de vrai
python scripts/odoo_admin/setup_drugcam_extensions.py --env staging

# 4. Re-vérifier que tout est OK
python scripts/odoo_admin/verify_drugcam_extensions.py --env staging
# (attendu : tous en OK)

# 5. Tester en bout-en-bout via le logiciel principal
sudo -E ./dist/drugcam-traca-X.Y.Z-x86_64.AppImage --env staging
```

## Versions

- **0.2.3** : création de cette infrastructure (JSON + scripts + docs).
- Versions précédentes : modifications faites manuellement via l'API MCP
  ou Studio. La présente documentation rétrofitte tout.
