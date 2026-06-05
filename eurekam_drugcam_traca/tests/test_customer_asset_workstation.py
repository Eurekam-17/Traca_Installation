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
        # Articles factices pour tester les Many2one Type Caméra/PC/Objectif
        # On respecte les conventions de nommage Eurekam (préfixes).
        cls.product_camera = cls.env["product.template"].create({
            "name": "CAMERA TEST 1800 - test unitaire",
        })
        cls.product_camera_scene = cls.env["product.template"].create({
            "name": "Caméra TEST de scène - test unitaire",
        })
        cls.product_pc = cls.env["product.template"].create({
            "name": "PC TEST Fanless - test unitaire",
        })
        cls.product_objective = cls.env["product.template"].create({
            "name": "Objectif TEST F8 - test unitaire",
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

    def test_camera_uc_objective_are_many2one_to_product_template(self):
        """Les 6 champs caméra/PC/objectif doivent être des Many2one vers product.template."""
        m2o_fields = [
            "camera_a_model", "camera_b_model", "scene_camera_model",
            "uc_model",
            "camera_a_objective", "camera_b_objective",
        ]
        ws_fields = self.env["customer.asset.workstation"]._fields
        for field_name in m2o_fields:
            field = ws_fields[field_name]
            self.assertEqual(
                field.type, "many2one",
                f"{field_name} doit être Many2one (actuel : {field.type})",
            )
            self.assertEqual(
                field.comodel_name, "product.template",
                f"{field_name} doit pointer vers product.template "
                f"(actuel : {field.comodel_name})",
            )

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

    def test_inox_plot_type_aucun_value(self):
        """La valeur "Aucun" (technique 'aucun') doit être acceptée."""
        self.workstation.write({"inox_plot_type": "aucun"})
        self.assertEqual(self.workstation.inox_plot_type, "aucun")
        selection_dict = dict(
            self.workstation._fields["inox_plot_type"]._description_selection(self.env)
        )
        self.assertEqual(selection_dict["aucun"], "Aucun")

    def test_full_payload_write(self):
        """Écrire un payload complet sur les 22 champs doit fonctionner."""
        self.workstation.write({
            "workstation_serial_number": "AB000042",
            "workstation_type": "iso_jce",
            "installation_date": "2026-05-15",
            "uc_model": self.product_pc.id,
            "pc_serial_number": "ABC1234",
            "cpu_version": "Intel(R) Core(TM) i5-10500 CPU @ 3.10GHz",
            "optical_block_serial": "010013",
            "optical_block_type": "sortie_droite",
            "camera_a_model": self.product_camera.id,
            "camera_a_serial": "00050",
            "camera_a_objective": self.product_objective.id,
            "camera_a_cable": "alysium",
            "camera_b_model": self.product_camera.id,
            "camera_b_serial": "00100",
            "camera_b_objective": self.product_objective.id,
            "camera_b_cable": "alysium_v2",
            "scene_camera_model": self.product_camera_scene.id,
            "scene_camera_serial": "SC-001",
            "mouse_model": "sealshield",
            "power_supply_type": "c5_120w",
            "inox_plot_type": "_3m",
            "comments": "Test installation complète",
        })
        self.assertEqual(self.workstation.workstation_serial_number, "AB000042")
        self.assertEqual(self.workstation.uc_model, self.product_pc)
        self.assertEqual(self.workstation.camera_a_model, self.product_camera)
        self.assertEqual(self.workstation.scene_camera_model, self.product_camera_scene)
        self.assertEqual(self.workstation.inox_plot_type, "_3m")

    def test_camera_domain_filters_by_prefix(self):
        """Le domain caméra doit accepter CAMERA et Caméra mais pas SUPPORT CAMERAS."""
        camera_capital = self.env["product.template"].create({"name": "CAMERA TEST FILTER"})
        camera_accent = self.env["product.template"].create({"name": "Caméra TEST FILTER"})
        support = self.env["product.template"].create({"name": "DEMOCOM TEST - SUPPORT CAMERAS"})

        # Domain défini sur le champ camera_a_model
        domain = self.env["customer.asset.workstation"]._fields["camera_a_model"].domain
        # Si domain est une string, l'évaluer comme expression Python
        if isinstance(domain, str):
            domain = self.env.ref("base.user_admin").env["customer.asset.workstation"]._eval_domain(domain) \
                if hasattr(self.env["customer.asset.workstation"], "_eval_domain") else eval(domain)

        matches = self.env["product.template"].search(domain)
        self.assertIn(camera_capital, matches)
        self.assertIn(camera_accent, matches)
        self.assertNotIn(support, matches)

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
