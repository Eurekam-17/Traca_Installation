"""Tests de la logique d'incrémentation des numéros de série (§ 7)."""

from __future__ import annotations

from odoo_client import numbering


class TestTracabilitySerial:
    def test_first_serial_when_empty(self) -> None:
        assert numbering.next_tracability_serial([]) == "AB000001"

    def test_increment_max(self) -> None:
        existing = ["AB000001", "AB000041", "AB000007"]
        assert numbering.next_tracability_serial(existing) == "AB000042"

    def test_ignores_non_matching_values(self) -> None:
        existing = ["FOO", "", None, "AB000003", "12345"]  # type: ignore[list-item]
        assert numbering.next_tracability_serial(existing) == "AB000004"

    def test_format_zero_padded(self) -> None:
        assert numbering.next_tracability_serial(["AB000099"]) == "AB000100"


class TestOpticalBlockSerial:
    def test_first_serial_when_empty(self) -> None:
        assert numbering.next_optical_block_serial([]) == "010001"

    def test_increment_max(self) -> None:
        existing = ["010001", "010003", "010012"]
        assert numbering.next_optical_block_serial(existing) == "010013"

    def test_ignores_non_matching_values(self) -> None:
        existing = ["010005", "ZZZ", "AB000999"]
        assert numbering.next_optical_block_serial(existing) == "010006"
