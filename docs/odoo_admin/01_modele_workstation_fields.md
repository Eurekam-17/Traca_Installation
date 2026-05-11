# Champs custom sur `customer.asset.workstation`

22 champs ont été ajoutés sur le modèle `customer.asset.workstation`
(module Scalizer `s6r_eurekam_customer_assets`) en mode `state='manual'`.

Tous sont gérés par le JSON déclaratif :
[`scripts/odoo_admin/odoo_extensions.json`](../../scripts/odoo_admin/odoo_extensions.json)
(section `fields`). Modifier le JSON puis relancer
`setup_drugcam_extensions.py` pour appliquer un changement.

## Inventaire complet

### Identification matérielle (3 champs)

| Nom technique | Libellé | Type | Selection / Notes |
|---|---|---|---|
| `x_workstation_type` | Type d'enceinte / hotte | selection | Iso JCE / Iso Sieve / Iso Eurobio / Iso Getinge / Hotte Faster / Hotte Thermofisher / Hotte ADS / Hotte Berner / Autres |
| `x_workstation_serial_number` | N° de série équipement | char | Format : `AB000001`, `AB000002`, … (auto-incrément géré par le logiciel) |
| `x_installation_date` | Date d'installation | date | Format ISO `YYYY-MM-DD` |

### UC (3 champs)

| Nom technique | Libellé | Type | Selection / Notes |
|---|---|---|---|
| `x_uc_model` | Type UC | selection | LIAN LI / eCW470 / eCW475 |
| `x_pc_serial_number` | N° de série PC | char | Issu de `dmidecode -t system` |
| `x_cpu_version` | Version CPU | char | Issu de `dmidecode -s processor-version` |

### Bloc optique (2 champs)

| Nom technique | Libellé | Type | Selection / Notes |
|---|---|---|---|
| `x_optical_block_type` | Type de bloc optique | selection | Sortie droite / Sortie latérale / Democom |
| `x_optical_block_serial` | N° de série bloc optique | char | Format : `010001`, `010002`, … (auto-incrément géré par le logiciel) |

### Caméra A (4 champs)

| Nom technique | Libellé | Type | Selection / Notes |
|---|---|---|---|
| `x_camera_a_model` | Type caméra A | selection | Fire wire / BU 130 / BU 160 / Alvium |
| `x_camera_a_serial` | N° caméra A | char | Détecté via `/sys/bus/usb/devices/`. La caméra A est celle au plus petit S/N. |
| `x_camera_a_objective` | Type objectif caméra A | selection | F8 / F12 (par défaut F8 dans le logiciel) |
| `x_camera_a_cable` | Type de câble caméra A | selection | FIRE WIRE / ALYSIUM / ALYSIUM V2 / ALYSIUM BLINDÉ POUR TELI / ALYSIUM BLINDÉ POUR ALVIUM |

### Caméra B (4 champs)

| Nom technique | Libellé | Type | Selection / Notes |
|---|---|---|---|
| `x_camera_b_model` | Type caméra B | selection | Idem caméra A |
| `x_camera_b_serial` | N° caméra B | char | Détecté via `/sys/bus/usb/devices/`. La caméra B est celle au plus grand S/N. |
| `x_camera_b_objective` | Type objectif caméra B | selection | F8 / F12 (par défaut F12 dans le logiciel) |
| `x_camera_b_cable` | Type de câble caméra B | selection | Idem caméra A |

### Caméra de scène (2 champs)

| Nom technique | Libellé | Type | Selection / Notes |
|---|---|---|---|
| `x_scene_camera_model` | Type caméra de scène | selection | Microsoft / ELP |
| `x_scene_camera_serial` | N° caméra de scène | char | Saisie libre |

### Accessoires (3 champs)

| Nom technique | Libellé | Type | Selection / Notes |
|---|---|---|---|
| `x_mouse_model` | Type de souris | selection | Sealshield / Silicone / Tactile / Induction |
| `x_power_supply_type` | Bloc d'alimentation | selection | C5 120W / FSP 120W / MEANWELL 80W / CWT 120W / MEAN WELL 120W |
| `x_inox_plot_type` | Plots inox | selection | Lohmann / 3M (⚠️ valeur technique : `_3m` car Odoo refuse les valeurs Selection commençant par un chiffre) |

### Texte libre (1 champ)

| Nom technique | Libellé | Type | Notes |
|---|---|---|---|
| `x_comments` | Commentaires | text | Texte multi-lignes |

## Champs Scalizer réutilisés (NON dupliqués)

Pour info — ces champs natifs du module Scalizer sont réutilisés tels
quels par le logiciel et n'ont pas été doublonnés en `x_*` :

| Champ Scalizer | Usage |
|---|---|
| `name` (Description) | Hostname (ex `assist1`) |
| `partner_id` | Client (Many2one `res.partner`) |
| `software_fedora_version` | Version OS (ex `Rocky Linux 9.3`) |
| `software_assist_version_id` | Version Assist (Many2one `customer.asset.software.version`) |
| `mac_address` | Adresses MAC `enp*` concaténées par `\|` |

## Tracking

**Tous les 22 champs** ont `tracking=100` activé : toute modification est
loguée automatiquement dans le chatter de la fiche poste (qui, quand,
ancienne valeur → nouvelle valeur). Cf. [`03_tracking.md`](03_tracking.md).

## Mode 'manual' — pourquoi

Tous les champs sont créés en `state='manual'` (préfixe obligatoire `x_`).
Cela signifie :
- ✅ Persistants même si le module Scalizer est mis à jour
- ✅ Modifiables via Studio par un admin
- ✅ Importables/exportables comme tout autre champ
- ❌ Non fournis par le code Python du module Scalizer (pas de défaut, pas
  de compute, etc. côté serveur — la logique métier reste dans
  l'application Drugcam Traca)
