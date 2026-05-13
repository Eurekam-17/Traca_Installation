# Documentation des extensions Odoo Drugcam

À partir de la **v0.3.0** du projet, les extensions Odoo nécessaires au
logiciel Drugcam Traca sont implémentées sous forme de **vrai module
Odoo** : [`odoo_module/eurekam_drugcam_traca/`](../../odoo_module/eurekam_drugcam_traca/).

→ **C'est là que tout se passe désormais.** Le module contient :
- Les 22 champs métier en Python (Selections + Char + Date + Text)
- Les 5 vues d'héritage en XML
- Les tests unitaires
- Le manifest avec sa dépendance vers `s6r_eurekam_customer_assets`
- Sa propre documentation : [`odoo_module/eurekam_drugcam_traca/README.md`](../../odoo_module/eurekam_drugcam_traca/README.md)

## Historique

Avant la v0.3.0, les extensions étaient gérées via **Odoo Studio** (champs
`state='manual'` avec préfixe `x_*`) et un système maison de scripts
Python (`setup_drugcam_extensions.py` / `verify_drugcam_extensions.py`)
piloté par un fichier déclaratif JSON.

Cette ancienne approche est **archivée** dans
[`legacy_studio/`](legacy_studio/) — voir le `STATUS.md` du dossier pour
comprendre ce qui a été remplacé.
