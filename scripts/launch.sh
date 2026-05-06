#!/bin/bash
# launch.sh — Lance drugcam-traca en root depuis une session KDE Wayland.
#
# Pourquoi : sur Wayland, root ne peut pas accéder au compositor de
# l'utilisateur. On force donc Qt à utiliser XWayland (le pont X11) via
# QT_QPA_PLATFORM=xcb. On préserve aussi DISPLAY/XAUTHORITY/DBus pour
# que la GUI s'affiche dans la session KDE de l'utilisateur courant.
#
# Usage :
#   ./scripts/launch.sh                          # lance l'AppImage la plus récente
#   ./scripts/launch.sh /chemin/vers/X.AppImage  # AppImage spécifique
#   ./scripts/launch.sh --mock                   # passe --mock à l'app
#   ./scripts/launch.sh /chemin/vers/X.AppImage --mock
set -euo pipefail

# -- Localiser l'AppImage --------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

APPIMAGE=""
APP_ARGS=()

# Si le 1er argument ressemble à un chemin .AppImage, c'est lui ; sinon on
# cherche le plus récent dans dist/. Tous les autres arguments sont passés à
# l'AppImage telle quelle (par ex. --mock, -v).
if [[ $# -gt 0 && "$1" == *.AppImage ]]; then
    APPIMAGE="$1"
    shift
fi
APP_ARGS=("$@")

if [[ -z "${APPIMAGE}" ]]; then
    APPIMAGE=$(ls -1t "${PROJECT_DIR}/dist"/drugcam-traca-*.AppImage 2>/dev/null | head -1 || true)
fi

if [[ -z "${APPIMAGE}" || ! -f "${APPIMAGE}" ]]; then
    echo "❌ Aucune AppImage trouvée."
    echo "   Lancer ./build_appimage.sh d'abord, ou indiquer un chemin :"
    echo "   $0 /chemin/vers/drugcam-traca-X.Y.Z-x86_64.AppImage"
    exit 1
fi

if [[ ! -x "${APPIMAGE}" ]]; then
    echo "ℹ️  AppImage non exécutable, ajout du flag +x..."
    chmod +x "${APPIMAGE}"
fi

echo "→ AppImage  : ${APPIMAGE}"
echo "→ Arguments : ${APP_ARGS[*]:-(aucun)}"
echo "→ Display   : ${DISPLAY:-(non défini)}  XAuth : ${XAUTHORITY:-(non défini)}"
echo ""

# -- Vérifications session graphique ---------------------------------------
if [[ -z "${DISPLAY:-}" ]]; then
    echo "⚠️  La variable DISPLAY n'est pas définie."
    echo "   Lance ce script depuis un terminal de TA session KDE, pas depuis ssh ou un tty."
    exit 2
fi

# -- Lancement en root via sudo -E ------------------------------------------
# -E préserve TOUT l'environnement utilisateur (DISPLAY, XAUTHORITY,
# DBUS_SESSION_BUS_ADDRESS, XDG_RUNTIME_DIR…), ce qui permet à la GUI Qt
# de s'afficher dans la session KDE.
# QT_QPA_PLATFORM=xcb force Qt à passer par XWayland (compatible Wayland)
# plutôt que de tenter une connexion native Wayland qui échouerait en root.

exec sudo -E env QT_QPA_PLATFORM=xcb "${APPIMAGE}" "${APP_ARGS[@]}"
