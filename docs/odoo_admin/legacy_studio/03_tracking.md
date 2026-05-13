# Tracking activé sur les champs Drugcam

## C'est quoi ?

Le **tracking** est un mécanisme natif Odoo qui consigne dans le chatter
d'un enregistrement toute modification d'un champ tracké, avec :
- l'auteur de la modification
- la date et l'heure
- l'**ancienne** valeur
- la **nouvelle** valeur
- le libellé du champ concerné

C'est ce qui permet de voir, sur les fiches Contact, des entrées comme :
> Patrice ARSENAULT — 12 mars, 10:39
> • 614 → 621 (Version du catalogue flacon)

## Couverture

Les **22 champs custom** créés sur `customer.asset.workstation` ont tous
le tracking activé (`tracking=100`, comme les champs natifs Scalizer).
Vérification simple :

```
SELECT COUNT(*) FROM ir.model.fields
WHERE model='customer.asset.workstation'
  AND state='manual'
  AND name LIKE 'x_%' AND name NOT LIKE 'x_studio%'
  AND tracking != 0
→ doit retourner 22
```

## Format dans le chatter

Pour les champs Selection, le chatter affiche les **libellés humains**
plutôt que les valeurs techniques. Exemple :

> Loïc Tamarelle — 11 mai, 09:37
> • (vide) → **Iso JCE** (Type d'enceinte / hotte)
> • (vide) → **LIAN LI** (Type UC)
> • TEST-PC-001 → **TEST-PC-002** (N° de série PC)

Pour les Char libres : valeur affichée telle quelle. Pour les Date :
format ISO. Pour le champ Text long (`x_comments`), seules les ~50 premiers
caractères sont affichés dans le chatter (le reste est tronqué avec "…").

## Sources de modification trackées

Toute modification est tracée, quelle qu'en soit la source :
- ✅ Saisie manuelle dans l'interface Odoo
- ✅ Import CSV via le bouton "Importer des enregistrements"
- ✅ Écriture programmatique via l'API (incluant **le logiciel Drugcam Traca**)
- ✅ Modification via Studio

## Désactivation (si besoin)

Si pour une raison quelconque on souhaitait désactiver le tracking sur un
champ donné, il suffit de modifier le JSON déclaratif :

```json
{
  "model": "customer.asset.workstation",
  "name": "x_comments",
  "tracking": 0,    ← passer de 100 à 0
  ...
}
```

Puis relancer `setup_drugcam_extensions.py`. Le script détectera la
divergence et fera le `write` correspondant.

## Volume — attention si modifications massives

Le tracking génère **un enregistrement `mail.message` par save** sur la
fiche, plus **un `mail.tracking.value` par champ modifié**. Pour des
imports en masse de plusieurs centaines de fiches, le chatter de chaque
fiche restera lisible (1 entrée par import), mais les tables `mail.message`
et `mail.tracking.value` grossiront en proportion.

Pas un souci en pratique pour ce projet (volumétrie attendue : ~1000
postes max), mais bon à savoir.

## Vérification rapide via les scripts

```bash
# Audit complet (incluant le tracking) :
python scripts/odoo_admin/verify_drugcam_extensions.py --env staging

# Sortie attendue : tous les 22 champs en [OK]
# Si un champ apparaît [DIFF] avec "tracking: 0 != 100", relancer le setup.
```
