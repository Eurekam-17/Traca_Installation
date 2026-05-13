# Eurekam Drugcam Traçabilité (module Odoo)

Module Odoo qui étend `customer.asset.workstation` (fourni par
`s6r_eurekam_customer_assets` de Scalizer) avec **22 champs métier**
nécessaires au logiciel `drugcam-traca` lancé par les techniciens
Eurekam lors des installations chez les clients hospitaliers.

> Logiciel client associé : https://github.com/Eurekam-17/Traca_Installation

## Pré-requis

- **Odoo 18.0** (Community ou Enterprise)
- Module **`s6r_eurekam_customer_assets`** (Scalizer) déjà installé sur l'instance
- Accès admin pour installer un module custom

## Champs ajoutés (22)

Tous avec `tracking=True` (audit Odoo natif dans le chatter).

| Section | Champs |
|---|---|
| Identification | `workstation_serial_number`, `workstation_type`, `installation_date` |
| UC | `uc_model`, `pc_serial_number`, `cpu_version` |
| Bloc optique | `optical_block_type`, `optical_block_serial` |
| Caméra A | `camera_a_model`, `camera_a_serial`, `camera_a_objective`, `camera_a_cable` |
| Caméra B | `camera_b_model`, `camera_b_serial`, `camera_b_objective`, `camera_b_cable` |
| Caméra de scène | `scene_camera_model`, `scene_camera_serial` |
| Accessoires | `mouse_model`, `power_supply_type`, `inox_plot_type` |
| Texte libre | `comments` |

Détail des Selections (libellés et valeurs techniques) : voir
[`models/customer_asset_workstation.py`](models/customer_asset_workstation.py).

## Vues étendues (5)

| Modèle | Vue parente Scalizer | Effet |
|---|---|---|
| `customer.asset.workstation` (form) | `view_customer_asset_workstations_form` | Ajoute 7 sections "Configuration matérielle Drugcam" |
| `customer.asset.workstation` (list) | `view_customer_asset_workstations_list` | Ajoute 22 colonnes optionnelles |
| `res.partner` (form) | `view_partner_form_inherit` | (×3) Renomme titres SAV, ajoute colonnes au tableau Postes Assist, retire editable="bottom" pour ouvrir le formulaire au clic |

## Installation

### Via Odoo.sh

1. Ajouter ce repo (ou ce sous-dossier) au dépôt Git lié à votre instance Odoo.sh.
2. Sur Odoo.sh : push → build → le module devient disponible.
3. Dans Odoo : **Apps → Mettre à jour la liste** → rechercher "Eurekam Drugcam" → **Installer**.

### Via instance self-hosted

```bash
# Copier le module dans le dossier addons d'Odoo
cp -r odoo_module/eurekam_drugcam_traca /path/to/odoo/addons/

# Mettre à jour la liste des modules
odoo -u all --stop-after-init -d <database>

# Ou via l'UI : Apps → Mettre à jour la liste → Installer le module
```

## Tests

```bash
odoo --test-tags eurekam_drugcam_traca \
     --stop-after-init \
     -u eurekam_drugcam_traca \
     -d <database>
```

Les tests vérifient :
- ✅ Présence des 22 champs sur le modèle
- ✅ Acceptation des 9 valeurs de Selection `workstation_type`
- ✅ Acceptation de la valeur `_3m` pour `inox_plot_type`
- ✅ Écriture d'un payload complet (UPSERT)
- ✅ Tracking dans le chatter

## Désinstallation

⚠️ La désinstallation **supprime les 22 champs** et **leurs valeurs**
sur toutes les fiches `customer.asset.workstation`. Faire un export /
backup avant si nécessaire.

```
Apps → Eurekam Drugcam Traçabilité → Désinstaller
```

## Mises à jour ultérieures (ajouter une option à une Selection, etc.)

1. Modifier [`models/customer_asset_workstation.py`](models/customer_asset_workstation.py).
2. Bumper la version dans [`__manifest__.py`](__manifest__.py).
3. Push Git.
4. Sur l'instance : **Apps → Eurekam Drugcam → Mettre à niveau**.

## Licence

LGPL-3.

## Auteur

Eurekam — https://eurekam.fr
