"""Tests de la logique de validation et de conversion d'InstallationDraft."""

from __future__ import annotations

import pytest

from odoo_client.base import Customer
from system_info import SystemInfo
from system_info.cameras import Camera, CameraPair
from ui.installation_draft import InstallationDraft


def _full_system_info() -> SystemInfo:
    info = SystemInfo()
    info.pc_serial_number = "ABC1234"
    info.cpu_version = "Intel(R) Core(TM) i5-10500 CPU @ 3.10GHz"
    info.hostname = "assist1"
    info.os_pretty_name = "Rocky Linux 9.3 (Blue Onyx)"
    info.assist_version = "2.5.11"
    info.mac_addresses = "aa:bb:cc:dd:ee:ff"
    info.camera_pair = CameraPair(
        camera_a=Camera("Allied Vision", "Alvium 1800", "00050", "/sys/x"),
        camera_b=Camera("Allied Vision", "Alvium 1800", "00100", "/sys/y"),
    )
    return info


def _filled_draft() -> InstallationDraft:
    draft = InstallationDraft()
    draft.customer = Customer(odoo_id=101, name="CHU Lille")
    draft.system_info = _full_system_info()
    # Toutes les valeurs sont des **valeurs techniques** (snake_case) telles
    # qu'attendues par les Selections Odoo correspondantes.
    draft.workstation_type = "iso_jce"
    draft.modele_uc = "lian_li"
    draft.type_bloc_optique = "sortie_droite"
    draft.type_camera_a = "alvium"
    draft.type_camera_b = "alvium"
    draft.objectif_a = "f8"
    draft.objectif_b = "f8"
    draft.cable_a = "alysium"
    draft.cable_b = "alysium"
    draft.souris = "sealshield"
    draft.type_bloc_alim = "c5_120w"
    draft.type_plot_inox = "lohmann"
    draft.serial_number = "AB000042"
    draft.optical_block_serial = "010013"
    return draft


class TestValidation:
    def test_empty_draft_lists_all_required(self) -> None:
        missing = InstallationDraft().required_missing()
        assert "Client" in missing
        assert "N° de série équipement" in missing
        assert len(missing) >= 15

    def test_filled_draft_is_complete(self) -> None:
        assert _filled_draft().required_missing() == []

    def test_missing_only_serials(self) -> None:
        draft = _filled_draft()
        draft.serial_number = ""
        missing = draft.required_missing()
        assert missing == ["N° de série équipement"]


class TestPayloadConversion:
    def test_to_poste_data(self) -> None:
        draft = _filled_draft()
        poste = draft.to_poste_data()
        assert poste.customer_id == 101
        assert poste.description == "assist1"
        assert poste.os_version == "Rocky Linux 9.3 (Blue Onyx)"
        assert poste.assist_version == "2.5.11"
        assert poste.mac_addresses == "aa:bb:cc:dd:ee:ff"

    def test_to_tracabilite_data(self) -> None:
        draft = _filled_draft()
        traca = draft.to_tracabilite_data(workstation_id=4242)
        assert traca.serial_number == "AB000042"
        assert traca.workstation_id == 4242
        assert traca.optical_block_serial == "010013"
        # Modèle UC et S/N PC sont 2 champs séparés (cf. modèle Odoo).
        assert traca.uc_model == "lian_li"
        assert traca.pc_serial_number == "ABC1234"
        # Caméra A : S/N depuis SystemInfo, type depuis le draft (Selection)
        assert traca.camera_a_model == "alvium"
        assert traca.camera_a_serial == "00050"  # plus petit S/N
        assert traca.camera_a_cable == "alysium"
        assert traca.camera_b_serial == "00100"
        # Snapshots
        assert traca.os_version == "Rocky Linux 9.3 (Blue Onyx)"
        # Workstation type et accessoires
        assert traca.workstation_type == "iso_jce"
        assert traca.souris == "sealshield"
        assert traca.plots_inox == "lohmann"
        # Nom du poste : retombe sur hostname si vide
        assert traca.workstation_name == "assist1"

    def test_overrides_take_precedence(self) -> None:
        draft = _filled_draft()
        draft.overrides["hostname"] = "assist1-corrected"
        poste = draft.to_poste_data()
        assert poste.description == "assist1-corrected"

    def test_to_poste_data_without_customer_raises(self) -> None:
        draft = _filled_draft()
        draft.customer = None
        with pytest.raises(ValueError):
            draft.to_poste_data()
