# Checklist de migration — porter le projet sur une nouvelle instance Odoo

À utiliser quand vous :
- Changez d'instance Odoo (ex : recette → nouvelle recette, ou prod → nouvelle prod après écrasement)
- Migrez vers une nouvelle version d'Odoo (ex : Odoo 18 → 19/20/21)
- Provisionnez un nouvel environnement (ex : pré-prod, démo client, …)
- Restaurez un backup sur une instance vierge

## ☑️ Pré-requis sur la nouvelle instance

- [ ] L'instance Odoo est **accessible** depuis votre poste de travail.
- [ ] Le plan Odoo est **Custom** (sinon pas d'API XML-RPC/JSON-RPC — cf. CLAUDE.md § 2bis-A).
- [ ] Le module prestataire **`s6r_eurekam_customer_assets`** (Scalizer) est **installé**.
  Vérification : Apps → recherche "Customer Assets" ou "Scalizer Eurekam". Si absent, contacter Scalizer pour le redéployer.
- [ ] Un **compte de service** Odoo (par défaut `traca-bot@eurekam.fr`) existe avec :
  - Une clé API valide (Profil → Account Security → New API Key)
  - Les droits suivants au minimum :
    - Settings / Access Rights
    - Lecture sur `res.partner`, `res.partner.category`
    - Lecture/écriture sur `customer.asset.workstation`
    - Lecture/écriture sur `ir.model.fields`, `ir.ui.view` (pour le setup)

## 1️⃣ Configurer le profil côté logiciel

Dans [`src/config.py`](../../src/config.py), section `PROFILES`, ajouter
(ou modifier) le profil correspondant à la nouvelle instance :

```python
PROFILES = {
    "staging": {
        "label": "Recette (NOM_DE_L_INSTANCE)",
        "host": "NOUVELLE_URL.odoo.com",
        "db": "NOUVELLE_DB",
        ...
    },
    "prod": { ... },
}
```

Commit + push.

## 2️⃣ Sauvegarder la clé API

Sur le poste de l'admin, pour chaque profil concerné :

```bash
# Soit via variable d'env (ponctuel)
export DRUGCAM_TRACA_API_KEY="votre-cle-ici"

# Soit via fichier persistant (recommandé)
cat > ~/.drugcam-traca/credentials.staging.json <<EOF
{
  "host": "NOUVELLE_URL.odoo.com",
  "db": "NOUVELLE_DB",
  "login": "traca-bot@eurekam.fr",
  "api_key": "votre-cle-ici",
  "protocol": "jsonrpc+ssl",
  "port": 443
}
EOF
chmod 600 ~/.drugcam-traca/credentials.staging.json
```

## 3️⃣ Audit avant intervention

```bash
python scripts/odoo_admin/verify_drugcam_extensions.py --env staging
```

Sortie attendue sur une instance vierge :
```
=== Audit de l'instance ... ===
─── Champs ───────
  ❌ [MISSING] customer.asset.workstation.x_workstation_type
  ❌ [MISSING] customer.asset.workstation.x_uc_model
  ... (22 champs MISSING)
─── Vues ──────
  ❌ [MISSING] customer.asset.workstation.form.eurekam_traca
  ... (5 vues MISSING)
=== Bilan : 0 OK, 0 divergentes, 27 manquantes ===
```

## 4️⃣ Plan d'application — dry-run

Toujours commencer par un **dry-run** pour voir ce qui sera fait :

```bash
python scripts/odoo_admin/setup_drugcam_extensions.py --env staging --dry-run
```

Lire attentivement le journal. Si une opération paraît surprenante,
**stopper** et investiguer. Sinon, lancer pour de vrai.

## 5️⃣ Application réelle

```bash
python scripts/odoo_admin/setup_drugcam_extensions.py --env staging
```

Le script va :
1. Pour chaque champ : vérifier s'il existe → créer si non, mettre à jour si divergent, sinon laisser tel quel.
2. Pour chaque vue : pareil (avec recherche de la vue parente par nom).

⚠️ **Si vous ciblez la prod**, le script demande une **confirmation explicite** par "OUI" tapé manuellement.

## 6️⃣ Vérification post-installation

```bash
python scripts/odoo_admin/verify_drugcam_extensions.py --env staging
```

Sortie attendue :
```
=== Bilan : 27 OK, 0 divergentes, 0 manquantes ===
```

Code retour `0` = tout est conforme au JSON déclaratif.

## 7️⃣ Test fonctionnel via le logiciel

```bash
# Sur le poste Drugcam Linux
sudo -E ./dist/drugcam-traca-X.Y.Z-x86_64.AppImage --env staging
```

- ✅ La GUI démarre, le bandeau orange est affiché.
- ✅ La liste des clients est filtrée (étiquettes `1- NEW` / `EN PROD`).
- ✅ La collecte système se fait normalement.
- ✅ L'envoi vers Odoo crée/met à jour bien une fiche `customer.asset.workstation`.
- ✅ Sur Odoo, ouvrir la fiche du client → onglet "SAV & Informations Techniques" → tableau "Postes Assist" → cliquer une ligne → la fiche s'ouvre avec toutes les sections Drugcam visibles.

## 8️⃣ Cas particuliers

### Vue parente Scalizer absente

Si le script `setup` lève l'erreur :
> Vue parent 'customer.asset.workstation.form' (model=...) introuvable

→ Le module Scalizer n'est pas installé (ou son nom de vue a changé).
Réinstaller le module ou demander à Scalizer le nouveau nom de la vue,
puis mettre à jour `inherit_view_name` dans le JSON déclaratif.

### Les étiquettes `1- NEW` / `EN PROD` ne sont pas trouvées

Vérifier qu'elles existent dans `Contacts → Configuration → Étiquettes
des contacts`. Si elles ont des noms différents sur la nouvelle instance,
mettre à jour [`src/config.py`](../../src/config.py) :

```python
CUSTOMER_CATEGORY_PROJET = "Nouveau nom étiquette projet"
CUSTOMER_CATEGORY_PROD = "Nouveau nom étiquette prod"
```

### Restauration de backup avec fiches existantes

Si la nouvelle base contient déjà des fiches `customer.asset.workstation`
créées avec des champs Drugcam, **ne PAS exécuter le script de setup
sans vérifier d'abord** : la création d'un champ Selection avec un même
nom mais une liste de valeurs différente peut casser les valeurs
existantes (Odoo refusera les valeurs hors liste).

→ Lancer le `verify` d'abord, et si des champs apparaissent en `[DIFF]`,
inspecter manuellement avant de relancer `setup`.

## 9️⃣ Quand mettre à jour le JSON déclaratif

Le JSON est **la source of truth**. À mettre à jour à chaque fois que :
- Un champ est ajouté/renommé/supprimé sur `customer.asset.workstation`
- Une nouvelle vue d'héritage est créée
- La sélection d'un champ Selection est étendue (nouvelle option)
- Le tracking d'un champ est activé/désactivé
- Une vue est modifiée (XML arch)

Workflow type :
1. Faire la modification (via Studio ou via mon MCP ou directement via Python)
2. Mettre à jour `odoo_extensions.json`
3. Mettre à jour la doc Markdown correspondante (cf. README.md de ce dossier)
4. Bump version dans `pyproject.toml`
5. Update CHANGELOG.md
6. Commit Git + push

## 🆘 En cas de blocage

- Lancer `python scripts/odoo_admin/verify_drugcam_extensions.py --env staging -v`
  pour avoir les logs DEBUG.
- Vérifier les logs Odoo (Apps → Settings → Technical → Logging).
- Le script `setup_drugcam_extensions.py` est **idempotent** : on peut le
  relancer autant de fois que nécessaire sans casser les fiches existantes.
- Si une vue se charge mal après création, c'est généralement un xpath
  invalide (la vue parente a changé). Inspecter la vue parente dans
  Settings → Technical → Views.
