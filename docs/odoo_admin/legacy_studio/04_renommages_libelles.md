# Renommages de libellés dans l'onglet "SAV & Informations Techniques"

## Contexte

L'onglet "SAV & Informations Techniques" sur la fiche Contact (`res.partner`)
contient deux tableaux fournis par le module Scalizer :
- **`environement_ids`** (One2many vers `customer.asset.environment`) — les serveurs Control
- **`workstation_ids`** (One2many vers `customer.asset.workstation`) — les postes Assist

Les libellés natifs Scalizer sont en anglais (`Environments`, `Workstations`)
et sont **traduits** en français par Odoo automatiquement vers `Environnements`
et `Postes`. Loïc a demandé des libellés plus parlants côté Eurekam.

## Renommages effectués

| Avant (traduction Odoo de l'anglais) | Après (surcharge Eurekam) |
|---|---|
| Environnements | **Serveurs Control** |
| Postes | **Postes Assist** |

## Mécanisme

C'est la vue 4 de la doc `02_vues_heritage.md` qui fait ce renommage :
`res.partner.form.eurekam_traca_section_titles`. Elle utilise un xpath
de type `position="attributes"` :

```xml
<xpath expr="//field[@name='environement_ids']/.." position="attributes">
    <attribute name="string">Serveurs Control</attribute>
</xpath>
<xpath expr="//field[@name='workstation_ids']/.." position="attributes">
    <attribute name="string">Postes Assist</attribute>
</xpath>
```

## Pourquoi pas modifier les traductions ?

Alternative : modifier les chaînes de traduction Odoo (`Environments` →
`Serveurs Control` côté FR_FR). Inconvénients :
- Affecte **tout** Odoo, pas que ce contexte précis (risque collatéral)
- Difficile à tracer en Git (pas dans un fichier déclaratif)
- Disparaît si on régénère les traductions du module

→ La surcharge par vue d'héritage est plus localisée et explicite.

## Modifier ces libellés à l'avenir

Éditer le JSON déclaratif :

```json
{
  "name": "res.partner.form.eurekam_traca_section_titles",
  "arch": "<data>\n    <xpath expr=\"//field[@name='environement_ids']/..\" position=\"attributes\">\n        <attribute name=\"string\">NOUVEAU LIBELLÉ</attribute>\n    </xpath>\n    ...\n</data>"
}
```

Puis relancer `setup_drugcam_extensions.py` qui détectera la divergence et
mettra à jour la vue.
