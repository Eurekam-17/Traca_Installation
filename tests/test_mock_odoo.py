"""Tests du MockOdooClient utilisé en DRY_RUN et dans les tests d'intégration."""

from __future__ import annotations

import pytest

from odoo_client.base import PosteData, TracabiliteData
from odoo_client.mock_impl import MockOdooClient


@pytest.fixture
def authenticated_client() -> MockOdooClient:
    client = MockOdooClient()
    client.authenticate()
    return client


def _sample_poste() -> PosteData:
    return PosteData(
        customer_id=101,
        description="assist1",
        os_version="Rocky Linux 9.3 (Blue Onyx)",
        assist_version="2.5.11",
        mac_addresses="aa:bb:cc:dd:ee:ff",
    )


def _sample_traca(serial: str = "AB000042", block: str = "010013") -> TracabiliteData:
    return TracabiliteData(
        # Identification
        serial_number=serial,
        workstation_id=3337,
        optical_block_serial=block,
        workstation_name="assist1",
        workstation_type="iso_jce",
        workstation_serial_number="EQ-001",
        installation_date="2026-04-30",
        # UC
        uc_model="lian_li",
        pc_serial_number="ABC1234",
        cpu_version="Intel(R) Core(TM) i5-10500 CPU @ 3.10GHz",
        # Bloc optique
        type_bloc_optique="sortie_droite",
        # Caméra A
        camera_a_model="alvium",
        camera_a_serial="00050",
        camera_a_objective="f8",
        camera_a_cable="alysium",
        # Caméra B
        camera_b_model="alvium",
        camera_b_serial="00100",
        camera_b_objective="f8",
        camera_b_cable="alysium",
        # Caméra de scène
        scene_camera_model="microsoft",
        scene_camera_serial="SC-001",
        # Accessoires
        souris="sealshield",
        bloc_alim="c5_120w",
        plots_inox="lohmann",
        # Snapshots
        assist_version="2.5.11",
        mac_addresses="aa:bb:cc:dd:ee:ff",
        os_version="Rocky Linux 9.3 (Blue Onyx)",
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


class TestCreate:
    def test_create_poste_records_data(self, authenticated_client) -> None:
        poste = _sample_poste()
        new_id = authenticated_client.create_poste_client(poste)
        assert new_id > 0
        assert authenticated_client.created_postes == [poste]

    def test_create_traca_records_data_and_updates_pool(self, authenticated_client) -> None:
        traca = _sample_traca(serial="AB000042", block="010013")
        new_id = authenticated_client.create_tracability_record(traca)
        assert new_id > 0
        assert authenticated_client.created_tracabilite == [traca]
        # Le prochain numéro doit avoir été incrémenté
        assert authenticated_client.next_tracability_serial() == "AB000043"
        assert authenticated_client.next_optical_block_serial() == "010014"


class TestRollback:
    def test_delete_poste_client_returns_true(self, authenticated_client) -> None:
        # Le mock accepte toujours la suppression, retourne True
        new_id = authenticated_client.create_poste_client(_sample_poste())
        assert authenticated_client.delete_poste_client(new_id) is True

    def test_delete_requires_authentication(self) -> None:
        client = MockOdooClient()
        with pytest.raises(RuntimeError, match="authenticate"):
            client.delete_poste_client(42)
