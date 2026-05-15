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
    # Champs Selection : valeurs techniques snake_case (data_options/*.json)
    draft.workstation_type = "iso_jce"
    draft.type_bloc_optique = "sortie_droite"
    draft.cable_a = "alysium"
    draft.cable_b = "alysium"
    draft.souris = "sealshield"
    draft.type_bloc_alim = "c5_120w"
    draft.type_plot_inox = "lohmann"
    # Champs Many2one product.template (depuis v0.4.0) : ID Odoo (int)
    draft.modele_uc_id = 2101
    draft.type_camera_a_id = 2001
    draft.type_camera_b_id = 2001
    draft.objectif_a_id = 2201
    draft.objectif_b_id = 2201
    draft.scene_camera_model_id = 2004
    draft.serial_number = "AB000042"
    draft.optical_block_serial = "010013"
    return draft


class TestValidation:
    def test_empty_draft_lists_all_required(self) -> None:
        missing = InstallationDraft().required_missing()
        assert "Client" in missing
        assert "N° de série équipement" in missing
        assert len(missing) >= 15

    def test_objectifs_have_no_default_id(self) -> None:
        """Depuis v0.4.0 (Many2one product), les objectifs n'ont plus de
        default métier (impossible sans connaître les IDs Odoo). Le
        technicien doit les saisir explicitement à chaque installation."""
        draft = InstallationDraft()
        assert draft.objectif_a_id == 0
        assert draft.objectif_b_id == 0
        missing = draft.required_missing()
        assert "Objectif caméra A" in missing
        assert "Objectif caméra B" in missing

    def test_filled_draft_is_complete(self) -> None:
        assert _filled_draft().required_missing() == []

    def test_missing_only_serials(self) -> None:
        draft = _filled_draft()
        draft.serial_number = ""
        missing = draft.required_missing()
        assert missing == ["N° de série équipement"]


class TestPayloadConversion:
    """En v0.2.0, to_poste_data() construit un PosteData enrichi qui contient
    TOUT (matériel + accessoires + snapshot). Plus de TracabiliteData séparé."""

    def test_to_poste_data_contains_native_scalizer_fields(self) -> None:
        poste = _filled_draft().to_poste_data()
        assert poste.customer_id == 101
        assert poste.description == "assist1"
        assert poste.os_version == "Rocky Linux 9.3 (Blue Onyx)"
        assert poste.assist_version == "2.5.11"
        assert poste.mac_addresses == "aa:bb:cc:dd:ee:ff"

    def test_to_poste_data_contains_identification_fields(self) -> None:
        poste = _filled_draft().to_poste_data()
        assert poste.workstation_serial_number == "AB000042"
        assert poste.workstation_type == "iso_jce"

    def test_to_poste_data_contains_uc_and_optical_block(self) -> None:
        poste = _filled_draft().to_poste_data()
        # uc_model est désormais un id Odoo product.template (Many2one)
        assert poste.uc_model_id == 2101
        assert poste.pc_serial_number == "ABC1234"
        assert poste.cpu_version.startswith("Intel(R) Core(TM)")
        assert poste.optical_block_serial == "010013"
        assert poste.optical_block_type == "sortie_droite"

    def test_to_poste_data_contains_cameras(self) -> None:
        poste = _filled_draft().to_poste_data()
        # Caméra A : modèle/objectif = Many2one product (id), S/N = collecte sysfs
        assert poste.camera_a_model_id == 2001
        assert poste.camera_a_serial == "00050"
        assert poste.camera_a_objective_id == 2201
        assert poste.camera_a_cable == "alysium"
        assert poste.camera_b_serial == "00100"

    def test_to_poste_data_contains_accessories(self) -> None:
        poste = _filled_draft().to_poste_data()
        assert poste.souris == "sealshield"
        assert poste.bloc_alim == "c5_120w"
        assert poste.plots_inox == "lohmann"

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
