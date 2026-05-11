# Guide d'import Excel/CSV — Postes Assist

Ce dossier contient les outils pour importer en masse des fiches
`customer.asset.workstation` dans Odoo via le bouton **"Importer des
enregistrements"** du module Parc Client.

## Fichiers fournis

| Fichier | Rôle |
|---|---|
| `template_postes_assist.csv` | Template prêt à l'emploi : 35 colonnes + 1 ligne d'exemple |
| `valeurs_selections.csv` | Référence des valeurs techniques acceptées pour les 13 champs Selection |
| `guide_import.md` | Ce fichier |

---

## Procédure d'import (simple)

1. Ouvrir le module **Parc Client → Parc → Postes clients**.
2. Cliquer sur l'icône ⚙️ à côté du bouton "Nouveau" → **Importer des enregistrements**.
3. Cliquer sur **Charger un modèle pour les Workstations** (ou téléverser
   directement le fichier `template_postes_assist.csv` fourni ici).
4. Remplir les lignes selon les besoins.
5. **Téléverser** le fichier rempli, **Tester** d'abord (bouton "Tester"),
   puis **Importer** une fois que le test passe sans erreur.

---

## Règles métier importantes

### Champs natifs Scalizer

| Colonne | Type | Notes |
|---|---|---|
| `partner_id` | Many2one (`res.partner`) | Le client. Mettre le **nom exact** du contact (Odoo fait la résolution) — ex `Hôpital Fleyriat`. Obligatoire. |
| `name` | char | Description du poste (= hostname). Convention : `assist1`, `assist2`… |
| `software_fedora_version` | char | Version OS, ex `Rocky Linux 9.3` |
| `software_assist_version_id` | Many2one | Mettre la version texte (ex `2.5.7`). Si la version n'existe pas encore, créer d'abord la fiche dans **Parc → Configuration → Versions** ou laisser le champ vide. |
| `mac_address` | char | Si plusieurs MAC, séparer par `\|` |
| `access_ip` à `access_ntp` | char | IP réseau du poste |
| `is_filter` | boolean | `1` ou `0` (ou `True`/`False`) |
| `access_type` | selection | `ip_fix` ou `dhcp` |

### Champs Drugcam (les 22 nouveaux `x_*`)

#### Selections — **utiliser la valeur technique** (cf. `valeurs_selections.csv`)

⚠️ Pour ces champs, Odoo accepte les **valeurs techniques** (ex `iso_jce`)
**OU** les libellés (ex `Iso JCE`). Pour éviter les pièges (accents, casse,
espaces), **on recommande la valeur technique**.

| Colonne | Exemples de valeurs |
|---|---|
| `x_workstation_type` | `iso_jce`, `iso_sieve`, `hotte_faster`, `autres`… (9 options) |
| `x_uc_model` | `lian_li`, `ecw470`, `ecw475` |
| `x_optical_block_type` | `sortie_droite`, `sortie_laterale`, `democom` |
| `x_camera_a_model`, `x_camera_b_model` | `fire_wire`, `bu_130`, `bu_160`, `alvium` |
| `x_camera_a_objective`, `x_camera_b_objective` | `f8`, `f12` |
| `x_camera_a_cable`, `x_camera_b_cable` | `fire_wire`, `alysium`, `alysium_v2`, `alysium_blinde_teli`, `alysium_blinde_alvium` |
| `x_scene_camera_model` | `microsoft`, `elp` |
| `x_mouse_model` | `sealshield`, `silicone`, `tactile`, `induction` |
| `x_power_supply_type` | `c5_120w`, `fsp_120w`, `meanwell_80w`, `cwt_120w`, `mean_well_120w` |
| `x_inox_plot_type` | `lohmann`, `_3m` (⚠️ underscore obligatoire — Odoo refuse les valeurs commençant par un chiffre) |

La liste complète est dans `valeurs_selections.csv` — pratique à filtrer
dans Excel quand on remplit le template.

#### Char libres

`x_workstation_serial_number`, `x_pc_serial_number`, `x_cpu_version`,
`x_optical_block_serial`, `x_camera_a_serial`, `x_camera_b_serial`,
`x_scene_camera_serial` : champs texte libres, aucune contrainte.

#### Date

`x_installation_date` : format **ISO `YYYY-MM-DD`** (ex `2025-09-15`).
Excel peut parfois reformater en `MM/DD/YYYY` lors de la sauvegarde —
penser à formater la colonne en **Texte** avant de coller la date.

#### Texte long

`x_comments` : multi-lignes possibles, mais attention dans le CSV : si tu
veux un retour à la ligne dans une cellule, l'entourer de guillemets
doubles `"...\n..."`.

---

## Astuces et pièges

### UPSERT vs création

Le système d'import natif Odoo crée toujours **un nouvel enregistrement**
par ligne du CSV. Il **n'y a pas de logique UPSERT** (mise à jour si déjà
existant) sauf si tu utilises la colonne spéciale `id` ou `External ID`
avec un identifiant unique.

→ Si tu veux **mettre à jour** des fiches existantes en masse :
1. Exporter d'abord les fiches via "Tout exporter" (bouton ⚙️) en cochant
   l'option **"Je veux mettre à jour les données"** — ça inclut une
   colonne `External ID`.
2. Modifier le CSV exporté.
3. Réimporter le même fichier.

### Encodage

- **Encodage** : UTF-8 (avec BOM si possible pour qu'Excel reconnaisse
  les accents). Le fichier template fourni est en UTF-8 sans BOM —
  ouvrir-puis-réenregistrer dans Excel pour ajouter le BOM si besoin.
- **Séparateur** : virgule par défaut (standard Odoo). Si Excel français
  utilise le point-virgule, configurer "Délimiteur" = `;` lors de l'import.

### Tracking

Tous les champs Drugcam ont **le tracking activé** (cf. CHANGELOG v0.2.1+).
Quand vous importez, chaque modification est loguée dans le **chatter**
de la fiche du poste — vous gardez l'historique de qui a importé quoi.

### Validation avant import

Toujours utiliser le bouton **"Tester"** d'Odoo avant le vrai "Importer".
Il signale ligne par ligne les erreurs (valeurs Selection invalides,
clients inexistants, etc.) sans rien écrire en base.

### Bug fréquent : "Veuillez configurer un moyen de mappage"

Si Odoo ne reconnaît pas un en-tête, c'est souvent à cause :
- d'une faute de frappe dans le nom technique (ex `x_workstaiton_type`)
- d'un espace en début/fin de cellule
- d'un caractère invisible (apostrophes courbes au lieu de droites)

→ Toujours partir du `template_postes_assist.csv` fourni et copier les
en-têtes tels quels.

---

## Liste exhaustive des 35 colonnes du template

Dans l'ordre du fichier :

```
1.  partner_id                    11. access_ntp                   21. x_optical_block_type
2.  name                          12. is_filter                    22. x_camera_a_model
3.  software_fedora_version       13. access_type                  23. x_camera_a_serial
4.  software_assist_version_id    14. x_workstation_serial_number  24. x_camera_a_objective
5.  mac_address                   15. x_workstation_type           25. x_camera_a_cable
6.  access_ip                     16. x_installation_date          26. x_camera_b_model
7.  access_gateway                17. x_uc_model                   27. x_camera_b_serial
8.  access_mask                   18. x_pc_serial_number           28. x_camera_b_objective
9.  access_dns1                   19. x_cpu_version                29. x_camera_b_cable
10. access_dns2                   20. x_optical_block_serial       30. x_scene_camera_model
                                                                   31. x_scene_camera_serial
                                                                   32. x_mouse_model
                                                                   33. x_power_supply_type
                                                                   34. x_inox_plot_type
                                                                   35. x_comments
```

---

## En cas de problème

1. Lancer "Tester" et lire **précisément** le message d'erreur Odoo (en
   général il pointe la ligne et la colonne).
2. Vérifier la valeur technique de la Selection contre `valeurs_selections.csv`.
3. Vérifier que `partner_id` correspond bien au nom **exact** d'un contact
   (sensible aux accents et casse — copier-coller depuis Odoo si besoin).
4. Si tu bloques, contacter Loïc (qui peut me solliciter pour adapter le
   template ou diagnostiquer un cas particulier).
