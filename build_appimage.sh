#!/bin/bash
# Construit drugcam-traca-<version>-x86_64.AppImage à partir de python-appimage.
#
# Stratégie :
#   1. On build un wheel local du projet (drugcam_traca-X.Y.Z-py3-none-any.whl).
#   2. On le copie dans une recette python-appimage avec les autres dépendances
#      (PySide6, odoorpc) listées dans requirements.txt.
#   3. entrypoint.py est un script SHELL (et non Python — piège du nommage)
#      qui appelle "python -m main" — la fonction main() de notre module main.
#   4. python-appimage produit l'AppImage finale.
#
# Pré-requis :
#   - Linux x86_64 (Rocky 9 recommandé pour rester proche de la cible).
#   - python3 (>= 3.9 pour python-appimage qui télécharge un Python 3.11 isolé).
#   - pip + venv (paquets python3-pip / python3-venv).
#   - libfuse2 (pour exécuter l'AppImage produit).
#
# Usage :   ./build_appimage.sh
#
# Sortie :  dist/drugcam-traca-<version>-x86_64.AppImage

set -euo pipefail

# -- Paramètres -------------------------------------------------------------
APP_NAME="drugcam-traca"
PYTHON_VERSION="3.11"
WORK_DIR="$(cd "$(dirname "$0")" && pwd)"
# BUILD_DIR contient un venv et l'AppDir de python-appimage, qui reposent sur
# des liens symboliques. Si le projet vit sur un partage VirtualBox (vboxsf)
# ou un FS sans symlinks, la création échoue ("Operation not permitted").
# On peut alors pointer BUILD_DIR vers un FS réel : BUILD_DIR=~/traca-build ./build_appimage.sh
BUILD_DIR="${BUILD_DIR:-${WORK_DIR}/appimage-build}"
DIST_DIR="${WORK_DIR}/dist"
VENV_DIR="${BUILD_DIR}/venv"

# Extrait la version depuis pyproject.toml
VERSION=$(grep -E '^version' "${WORK_DIR}/pyproject.toml" | head -1 \
    | sed -E 's/version\s*=\s*"([^"]+)"/\1/')
APPIMAGE_OUT="${DIST_DIR}/${APP_NAME}-${VERSION}-x86_64.AppImage"

echo "=== Build AppImage ${APP_NAME} version ${VERSION} ==="

# -- Préparation environnement ---------------------------------------------
mkdir -p "${BUILD_DIR}" "${DIST_DIR}"
rm -rf "${BUILD_DIR}/AppDir" "${BUILD_DIR}/recipe" "${BUILD_DIR}/wheels"
# On efface aussi les wheels du projet pour partir propre
rm -rf "${WORK_DIR}/dist"/*.whl 2>/dev/null || true

# Crée un venv pour isoler python-appimage et build
if [[ ! -d "${VENV_DIR}" ]]; then
    python3 -m venv "${VENV_DIR}"
fi
# shellcheck source=/dev/null
source "${VENV_DIR}/bin/activate"
pip install --upgrade pip
pip install python-appimage build

# -- 1. Build du wheel du projet -------------------------------------------
echo ""
echo "=== Build du wheel drugcam_traca ==="
cd "${WORK_DIR}"
python -m build --wheel --outdir "${BUILD_DIR}/wheels"
PROJECT_WHEEL=$(ls -1 "${BUILD_DIR}/wheels"/drugcam_traca-*.whl | head -1)
echo "Wheel produit : ${PROJECT_WHEEL}"

# -- 2. Génération de la recette python-appimage ---------------------------
RECIPE_DIR="${BUILD_DIR}/recipe"
mkdir -p "${RECIPE_DIR}"
PROJECT_WHEEL_BASENAME=$(basename "${PROJECT_WHEEL}")

# python-appimage exécute pip depuis un dossier temp /tmp/python-appimage-XXX/
# et NON depuis la recette. Pour que pip trouve notre wheel, il faut un
# chemin absolu. On copie le wheel dans /tmp/ avec un nom de dossier sans
# espace (le projet vit dans "Traca Installation/" qui contient un espace,
# ce qui casserait le parsing requirements.txt).
WHEEL_STAGING="/tmp/drugcam-traca-wheel-$$"
rm -rf "${WHEEL_STAGING}"
mkdir -p "${WHEEL_STAGING}"
cp "${PROJECT_WHEEL}" "${WHEEL_STAGING}/"
WHEEL_ABSPATH="${WHEEL_STAGING}/${PROJECT_WHEEL_BASENAME}"

# requirements.txt — pip lit ce fichier ligne par ligne.
# NB : on évite "<" dans les specifiers, car python-appimage les passe à pip
# via /bin/sh sans quoting et "<" est interprété comme redirection.
cat > "${RECIPE_DIR}/requirements.txt" <<EOF
PySide6>=6.6
odoorpc>=0.10.1
${WHEEL_ABSPATH}
EOF

# entrypoint.py est en réalité un script BASH, malgré l'extension .py
# (c'est la convention de python-appimage — l'extension .py est trompeuse).
# Les placeholders {{ python-executable }} sont remplacés au build par le
# chemin vers le Python embarqué.
cat > "${RECIPE_DIR}/entrypoint.py" <<'EOF'
#! /bin/bash
exec {{ python-executable }} -s -m main "$@"
EOF

# -- 3. Construction de l'AppImage -----------------------------------------
echo ""
echo "=== Construction de l'AppImage via python-appimage ==="
cd "${BUILD_DIR}"
# --linux-tag manylinux2014_x86_64 force la compatibilité large (Rocky 9 OK).
# --extra-data pour packager les options data si besoin (déjà dans le wheel).
python -m python_appimage build app \
    --python-version "${PYTHON_VERSION}" \
    --linux-tag manylinux2014_x86_64 \
    --name "${APP_NAME}" \
    "${RECIPE_DIR}"

# python-appimage produit son AppImage dans le répertoire courant
PRODUCED=$(ls -1 *.AppImage 2>/dev/null | head -1)
if [[ -z "${PRODUCED}" ]]; then
    echo "❌ Aucun fichier .AppImage produit." >&2
    exit 1
fi
mv "${PRODUCED}" "${APPIMAGE_OUT}"

echo ""
echo "✅ AppImage construite : ${APPIMAGE_OUT}"
echo "   Taille : $(du -h "${APPIMAGE_OUT}" | cut -f1)"
echo ""
echo "Pour lancer (en root) :"
echo "    sudo ${APPIMAGE_OUT}"

# Nettoyage du staging temporaire
rm -rf "${WHEEL_STAGING}"
