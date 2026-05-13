# -*- coding: utf-8 -*-
"""Tests Odoo du module eurekam_drugcam_traca.

À exécuter via :
    odoo --test-tags eurekam_drugcam_traca --stop-after-init -u eurekam_drugcam_traca
"""

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "eurekam_drugcam_traca")
class TestCustomerAssetWorkstation(TransactionCase):
    """Vérifie la présence et le bon fonctionnement des 22 champs Drugcam."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Test Hospital"})
        cls.workstation = cls.env["customer.asset.workstation"].create({
            "name": "test-assist1",
            "partner_id": cls.partner.id,
        })

    def test_22_fields_exist(self):
        """Les 22 champs Drugcam doivent être présents sur le modèle."""
        expected_fields = {
            # Identification
            "workstation_serial_number", "workstation_type", "installation_date",
            # UC
            "uc_model", "pc_serial_number", "cpu_version",
            # Bloc optique
            "optical_block_type", "optical_block_serial",
            # Caméras A & B
            "camera_a_model", "camera_a_serial", "camera_a_objective", "camera_a_cable",
            "camera_b_model", "camera_b_serial", "camera_b_objective", "camera_b_cable",
            # Caméra de scène
            "scene_camera_model", "scene_camera_serial",
            # Accessoires
            "mouse_model", "power_supply_type", "inox_plot_type",
            # Texte libre
            "comments",
        }
        actual_fields = set(self.env["customer.asset.workstation"]._fields)
        missing = expected_fields - actual_fields
        self.assertFalse(missing, f"Champs manquants : {missing}")

    def test_selection_values_workstation_type(self):
        """Les 9 valeurs de Selection workstation_type doivent être acceptées."""
        valid_values = [
            "iso_jce", "iso_sieve", "iso_eurobio", "iso_getinge",
            "hotte_faster", "hotte_thermofisher", "hotte_ads", "hotte_berner",
            "autres",
        ]
        for value in valid_values:
            self.workstation.write({"workstation_type": value})
            self.assertEqual(self.workstation.workstation_type, value)

    def test_inox_plot_type_3m_value(self):
        """La valeur '3M' (technique '_3m') doit être acceptée."""
        self.workstation.write({"inox_plot_type": "_3m"})
        self.assertEqual(self.workstation.inox_plot_type, "_3m")
        # Le libellé affiché doit être "3M"
        selection_dict = dict(
            self.workstation._fields["inox_plot_type"]._description_selection(self.env)
        )
        self.assertEqual(selection_dict["_3m"], "3M")

    def test_full_payload_write(self):
        """Écrire un payload complet sur les 22 champs doit fonctionner."""
        self.workstation.write({
            "workstation_serial_number": "AB000042",
            "workstation_type": "iso_jce",
            "installation_date": "2026-05-15",
            "uc_model": "lian_li",
            "pc_serial_number": "ABC1234",
            "cpu_version": "Intel(R) Core(TM) i5-10500 CPU @ 3.10GHz",
            "optical_block_serial": "010013",
            "optical_block_type": "sortie_droite",
            "camera_a_model": "alvium",
            "camera_a_serial": "00050",
            "camera_a_objective": "f8",
            "camera_a_cable": "alysium",
            "camera_b_model": "alvium",
            "camera_b_serial": "00100",
            "camera_b_objective": "f12",
            "camera_b_cable": "alysium_v2",
            "scene_camera_model": "microsoft",
            "scene_camera_serial": "SC-001",
            "mouse_model": "sealshield",
            "power_supply_type": "c5_120w",
            "inox_plot_type": "_3m",
            "comments": "Test installation complète",
        })
        self.assertEqual(self.workstation.workstation_serial_number, "AB000042")
        self.assertEqual(self.workstation.uc_model, "lian_li")
        self.assertEqual(self.workstation.inox_plot_type, "_3m")

    def test_tracking_logs_changes_in_chatter(self):
        """Une modification doit générer un message tracking dans le chatter."""
        initial_count = self.env["mail.message"].search_count(
            [("model", "=", "customer.asset.workstation"),
             ("res_id", "=", self.workstation.id)]
        )
        self.workstation.write({"workstation_type": "hotte_faster"})
        # Force la création des messages tracking (parfois différée)
        self.workstation.flush_recordset()
        new_count = self.env["mail.message"].search_count(
            [("model", "=", "customer.asset.workstation"),
             ("res_id", "=", self.workstation.id)]
        )
        self.assertGreater(
            new_count, initial_count,
            "Le tracking doit avoir créé au moins un message dans le chatter.",
        )
