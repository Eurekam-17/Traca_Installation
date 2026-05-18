"""Tests du MockOdooClient utilisé en DRY_RUN et dans les tests d'intégration."""

from __future__ import annotations

import pytest

from odoo_client.base import PosteData
from odoo_client.mock_impl import MockOdooClient


@pytest.fixture
def authenticated_client() -> MockOdooClient:
    client = MockOdooClient()
    client.authenticate()
    return client


def _full_poste(serial: str = "AB000042", block: str = "010013") -> PosteData:
    """Payload PosteData complet (les 27 champs) — équivalent v0.2.0 d'une
    fiche customer.asset.workstation entièrement remplie."""
    return PosteData(
        # Champs natifs Scalizer
        customer_id=101,
        description="assist1",
        os_version="Rocky Linux 9.3 (Blue Onyx)",
        assist_version="2.5.11",
        mac_addresses="aa:bb:cc:dd:ee:ff",
        # Identification matérielle
        workstation_serial_number=serial,
        workstation_type="iso_jce",
        installation_date="2026-05-06",
        # UC (Many2one product.template depuis v0.4.0)
        uc_model_id=2101,
        pc_serial_number="ABC1234",
        cpu_version="Intel(R) Core(TM) i5-10500 CPU @ 3.10GHz",
        # Bloc optique
        optical_block_serial=block,
        optical_block_type="sortie_droite",
        # Caméra A (modèle + objectif = Many2one product, S/N = libre)
        camera_a_model_id=2001,
        camera_a_serial="00050",
        camera_a_objective_id=2201,
        camera_a_cable="alysium",
        # Caméra B
        camera_b_model_id=2001,
        camera_b_serial="00100",
        camera_b_objective_id=2201,
        camera_b_cable="alysium",
        # Caméra de scène (Many2one product.template, même catégorie que cam A/B)
        scene_camera_model_id=2004,
        scene_camera_serial="SC-001",
        # Accessoires
        souris_id=2301,
        bloc_alim="c5_120w",
        plots_inox="lohmann",
        # Texte libre
        comments="Test installation",
    )


class TestAuthentication:
    def test_must_authenticate_before_any_call(self) -> None:
        client = MockOdooClient()
        with pytest.raises(RuntimeError, match="authenticate"):
            client.list_active_customers()


class TestCustomers:
    def test_returns_default_fake_customers(self, authenticated_client) -> None:
        customers = authenticated_client.list_active_customers()
        assert len(customers) >= 3
        assert all(c.odoo_id > 0 for c in customers)


class TestDuplicateLookup:
    def test_returns_none_when_no_match(self, authenticated_client) -> None:
        assert authenticated_client.find_poste_by_serial("UNKNOWN") is None

    def test_returns_existing_poste(self, authenticated_client) -> None:
        authenticated_client.add_existing_poste(
            poste_id=42, name="assist7", customer_name="CHU Lille", pc_serial="ABC1234",
        )
        found = authenticated_client.find_poste_by_serial("ABC1234")
        assert found is not None
        assert found["id"] == 42
        assert found["customer_name"] == "CHU Lille"


class TestSerialIncrement:
    def test_next_traca_uses_existing_max(self, authenticated_client) -> None:
        # Le MockOdooClient pré-rempli a AB000041 → next = AB000042
        assert authenticated_client.next_tracability_serial() == "AB000042"

    def test_next_optical_block_uses_existing_max(self, authenticated_client) -> None:
        # Pré-rempli avec 010012 → next = 010013
        assert authenticated_client.next_optical_block_serial() == "010013"


class TestUpsert:
    def test_create_poste_records_payload(self, authenticated_client) -> None:
        poste = _full_poste()
        new_id = authenticated_client.create_poste_client(poste)
        assert new_id > 0
        assert authenticated_client.upserted_postes == [poste]

    def test_create_poste_updates_serial_pools(self, authenticated_client) -> None:
        # Le prochain S/N équipement doit être incrémenté après UPSERT
        poste = _full_poste(serial="AB000042", block="010013")
        authenticated_client.create_poste_client(poste)
        assert authenticated_client.next_tracability_serial() == "AB000043"
        assert authenticated_client.next_optical_block_serial() == "010014"

    def test_minimal_poste_data(self, authenticated_client) -> None:
        """Vérifie que tous les champs métier sont optionnels (defaults '')."""
        minimal = PosteData(
            customer_id=101,
            description="assist-test",
            os_version="Rocky 9",
            assist_version="2.5.11",
            mac_addresses="aa:bb:cc",
        )
        new_id = authenticated_client.create_poste_client(minimal)
        assert new_id > 0
        # Sans serial fournis, les pools n'ont pas été modifiés
        assert authenticated_client.next_tracability_serial() == "AB000042"


class TestProductCatalog:
    """v0.4.0 : 3 nouvelles méthodes pour peupler les combos depuis Odoo."""

    def test_list_camera_products_returns_cameras(self, authenticated_client) -> None:
        cameras = authenticated_client.list_camera_products()
        assert len(cameras) >= 4  # 3 CAMERA + 1 Caméra de scène
        assert all(c.odoo_id > 0 for c in cameras)
        names = [c.name for c in cameras]
        # Vérifie qu'on a bien des CAMERA majuscule ET Caméra accent (cf. v0.4.0)
        assert any(n.startswith("CAMERA ") for n in names)
        assert any(n.startswith("Caméra ") for n in names)

    def test_list_pc_products_returns_pcs(self, authenticated_client) -> None:
        pcs = authenticated_client.list_pc_products()
        assert len(pcs) >= 2
        assert all(p.name.startswith("PC ") for p in pcs)

    def test_list_objective_products_returns_objectives(self, authenticated_client) -> None:
        objs = authenticated_client.list_objective_products()
        assert len(objs) >= 2
        assert all(o.name.startswith("Objectif ") for o in objs)

    def test_list_mouse_products_returns_mice(self, authenticated_client) -> None:
        mice = authenticated_client.list_mouse_products()
        assert len(mice) >= 3
        assert all(m.name.startswith("Souris ") for m in mice)

    def test_catalog_methods_require_authentication(self) -> None:
        client = MockOdooClient()
        with pytest.raises(RuntimeError, match="authenticate"):
            client.list_camera_products()
