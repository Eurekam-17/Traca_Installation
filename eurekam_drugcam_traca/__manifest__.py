# -*- coding: utf-8 -*-
{
    "name": "Eurekam Drugcam Traçabilité",
    "summary": "Champs métier Drugcam Traca pour les postes Assist (matériel,"
               " caméras, accessoires, commentaires).",
    "description": """
Module d'extension pour le projet de traçabilité des installations Drugcam.

Étend le modèle ``customer.asset.workstation`` (fourni par le module
prestataire ``s6r_eurekam_customer_assets`` de Scalizer) avec 22 champs
métier nécessaires au logiciel ``drugcam-traca`` lancé par les techniciens
Eurekam lors de chaque installation chez un client.

Sections couvertes :
- Identification matérielle (type d'enceinte, n° série équipement, date)
- UC (modèle, n° série PC, version CPU)
- Bloc optique (type, n° série)
- Caméra A et B (type, n° série, objectif, câble)
- Caméra de scène (type, n° série)
- Accessoires (souris, bloc d'alim, plots inox)
- Commentaires libres

Toutes les modifications sont trackées dans le chatter (audit Odoo natif).

Logiciel client associé :
https://github.com/Eurekam-17/Traca_Installation
""",
    "version": "18.0.4.0.0",
    "category": "Customizations",
    "author": "Eurekam",
    "website": "https://eurekam.fr",
    "license": "LGPL-3",
    "depends": [
        "s6r_eurekam_customer_assets",
    ],
    "data": [
        "views/customer_asset_workstation_views.xml",
        "views/res_partner_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
