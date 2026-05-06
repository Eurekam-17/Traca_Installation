#!/bin/bash
# Script bash de référence pour la détection des caméras Drugcam.
# Conservé à des fins de debug / fallback (cf. CLAUDE.md § 6).
#
# La logique officielle est désormais implémentée en Python dans
# src/system_info/cameras.py qui utilise /sys/bus/usb/devices/ plutôt
# que dmesg (plus fiable car non tronqué après uptime long).
#
# Usage : sudo ./get_camera.sh
set -euo pipefail

echo "=== Caméras Drugcam détectées (lecture sysfs) ==="

shopt -s nullglob
found=0

for device in /sys/bus/usb/devices/*/; do
    if [[ ! -f "${device}manufacturer" ]]; then
        continue
    fi

    manufacturer=$(<"${device}manufacturer")
    if [[ "$manufacturer" != "Allied Vision" && "$manufacturer" != "Toshiba-Teli" ]]; then
        continue
    fi

    product="(inconnu)"
    [[ -f "${device}product" ]] && product=$(<"${device}product")

    serial="(absent)"
    [[ -f "${device}serial" ]] && serial=$(<"${device}serial")

    echo "  • $manufacturer | $product | S/N: $serial"
    found=$((found + 1))
done

echo "Total : $found caméra(s)"

if [[ $found -lt 2 ]]; then
    echo "⚠️  ERREUR : moins de 2 caméras détectées." >&2
    echo "    Vérifier que le bloc optique est bien branché." >&2
    exit 1
fi
