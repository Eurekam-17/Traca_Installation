# Vues d'héritage Odoo

5 vues d'héritage ont été créées pour intégrer les 22 champs Drugcam dans
les écrans existants (module Scalizer + onglet SAV de la fiche Contact).

Toutes sont gérées par le JSON déclaratif :
[`scripts/odoo_admin/odoo_extensions.json`](../../scripts/odoo_admin/odoo_extensions.json)
(section `views`).

## Vue d'ensemble

| Nom technique | Modèle | Vue parente héritée | Effet |
|---|---|---|---|
| `customer.asset.workstation.form.eurekam_traca` | `customer.asset.workstation` | `customer.asset.workstation.form` | Ajoute 7 sections de champs Drugcam dans le formulaire d'un poste |
| `customer.asset.workstation.list.eurekam_traca` | `customer.asset.workstation` | `customer.asset.workstation.list` | Ajoute 22 colonnes optionnelles dans la list standalone du module Parc Client |
| `res.partner.form.eurekam_traca_workstation_columns` | `res.partner` | `res.partner.form.inherit` (celle qui ajoute l'onglet SAV) | Ajoute 22 colonnes optionnelles dans la list inline du tableau "Postes Assist" |
| `res.partner.form.eurekam_traca_section_titles` | `res.partner` | idem | Renomme "Environnements" → "Serveurs Control" et "Postes" → "Postes Assist" |
| `res.partner.form.eurekam_traca_workstation_clickable` | `res.partner` | idem | Retire `editable="bottom"` du tableau "Postes Assist" pour qu'un clic ouvre le formulaire complet du poste |

## Détail par vue

### 1. Vue form du poste — ajout des sections Drugcam

**Nom** : `customer.asset.workstation.form.eurekam_traca`
**Hérite** : `customer.asset.workstation.form` (du module Scalizer)
**Priorité** : 20

Ajoute, après le `<group>` principal du formulaire d'un poste, 7 sections :

```
┌─ Configuration matérielle Drugcam ────────────┐
│ ┌─ Identification ──┐ ┌─ UC ────────────────┐ │
│ │ Type d'enceinte   │ │ Type UC             │ │
│ │ N° série équip.   │ │ N° série PC         │ │
│ │ Date installation │ │ Version CPU         │ │
│ └───────────────────┘ └─────────────────────┘ │
└───────────────────────────────────────────────┘

┌─ Bloc optique ────────┐ ┌─ Caméra de scène ──┐
│ Type bloc optique     │ │ Type caméra scène  │
│ N° série bloc optique │ │ N° série cam scène │
└───────────────────────┘ └────────────────────┘

┌─ Caméra A (plus petit S/N) ┐ ┌─ Caméra B (plus grand S/N) ┐
│ Type cam A                  │ │ Type cam B                 │
│ N° cam A                    │ │ N° cam B                   │
│ Type objectif cam A         │ │ Type objectif cam B        │
│ Type câble cam A            │ │ Type câble cam B           │
└─────────────────────────────┘ └────────────────────────────┘

┌─ Accessoires ─────────────────────────────────┐
│ Type souris    │ Bloc d'alimentation │ Plots │
└───────────────────────────────────────────────┘

┌─ Commentaires ────────────────────────────────┐
│ (zone de texte multi-lignes)                  │
└───────────────────────────────────────────────┘
```

### 2. Vue list standalone — colonnes optionnelles

**Nom** : `customer.asset.workstation.list.eurekam_traca`
**Hérite** : `customer.asset.workstation.list` (du module Scalizer)
**Priorité** : 20

Ajoute les 22 colonnes Drugcam **après** la colonne `access_type`, en mode
`optional="hide"` : invisibles par défaut mais présentes dans le menu
sélecteur de colonnes (icône ⚙️ en haut à droite du tableau).

### 3. Vue list inline — onglet SAV res.partner

**Nom** : `res.partner.form.eurekam_traca_workstation_columns`
**Hérite** : `res.partner.form.inherit` (filtré par contenu `workstation_ids`)
**Priorité** : 25

Même contenu que la vue list standalone, mais ciblée sur la `<list>` inline
qui est embarquée dans `<field name="workstation_ids">` à l'intérieur de
l'onglet "SAV & Informations Techniques" de `res.partner.form`. Les 22
champs apparaissent dans le sélecteur de colonnes du tableau "Postes Assist".

### 4. Renommages de titres

**Nom** : `res.partner.form.eurekam_traca_section_titles`
**Hérite** : idem (3)
**Priorité** : 26

Surcharge les attributs `string` des deux groupes du onglet SAV :
- `<group string="Environments">` → "Serveurs Control"
- `<group string="Workstations">` → "Postes Assist"

Détail dans [`04_renommages_libelles.md`](04_renommages_libelles.md).

### 5. Tableau cliquable

**Nom** : `res.partner.form.eurekam_traca_workstation_clickable`
**Hérite** : idem (3)
**Priorité** : 27

Retire l'attribut `editable="bottom"` de la list inline `workstation_ids`.
Conséquence : un clic sur une ligne du tableau "Postes Assist" ouvre la
**vue formulaire complète** du poste (en modal) au lieu de passer en mode
édition inline.

## Pourquoi 3 vues séparées sur res.partner et pas une seule ?

Chaque vue a une responsabilité unique :
- 25 = colonnes
- 26 = libellés
- 27 = comportement clic

→ Si on doit revenir en arrière sur l'un sans toucher aux autres, on
supprime juste la vue concernée. Plus facile à débugguer et à diff.

## Identification de la vue parente — robustesse

Dans `odoo_extensions.json`, les vues parentes ne sont pas référencées par
ID brut (qui change entre instances) mais par leur **nom technique** + un
**critère de contenu** optionnel (`inherit_view_arch_contains`). Cela permet
au script `setup_drugcam_extensions.py` de retrouver la bonne vue parente
sur n'importe quelle instance.

Pour l'onglet SAV `res.partner`, plusieurs vues s'appellent
`res.partner.form.inherit` (héritage Odoo standard). On utilise donc le
filtre supplémentaire `inherit_view_arch_contains: "workstation_ids"`
pour cibler **précisément** celle qui ajoute le tableau Postes Assist.
