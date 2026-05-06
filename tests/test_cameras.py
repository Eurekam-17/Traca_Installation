"""Tests de la détection caméras et règle de tri A < B (§ 6)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from system_info import cameras


def _make_fake_usb_tree(tmp_path: Path, devices: list[dict[str, str]]) -> Path:
    """Construit une arborescence /sys/bus/usb/devices factice dans tmp_path."""
    root = tmp_path / "usb_devices"
    root.mkdir()
    for i, dev in enumerate(devices):
        ddir = root / f"1-{i}"
        ddir.mkdir()
        for attr, value in dev.items():
            (ddir / attr).write_text(value)
    return root


class TestSerialSortKey:
    def test_numeric_serials_sort_numerically(self) -> None:
        keys = [cameras._serial_sort_key(s) for s in ["10", "2", "100"]]
        # 2 < 10 < 100 (et non 10 < 100 < 2 comme en lexicographique brut)
        assert sorted(zip(keys, ["10", "2", "100"]))[0][1] == "2"
        assert sorted(zip(keys, ["10", "2", "100"]))[2][1] == "100"

    def test_alpha_serials_sort_lexicographically(self) -> None:
        keys = [cameras._serial_sort_key(s) for s in ["Z", "A", "M"]]
        sorted_pairs = sorted(zip(keys, ["Z", "A", "M"]))
        assert [p[1] for p in sorted_pairs] == ["A", "M", "Z"]


class TestDetectCameras:
    def test_returns_only_supported_manufacturers(self, tmp_path) -> None:
        root = _make_fake_usb_tree(tmp_path, [
            {"manufacturer": "Allied Vision", "product": "Alvium 1800", "serial": "00050"},
            {"manufacturer": "Logitech", "product": "Mouse", "serial": "X1"},
            {"manufacturer": "Toshiba-Teli", "product": "BU-238M", "serial": "00010"},
        ])
        with patch.object(cameras, "USB_DEVICES_PATH", root):
            detected = cameras.detect_cameras()
        assert len(detected) == 2
        assert {c.manufacturer for c in detected} == {"Allied Vision", "Toshiba-Teli"}

    def test_skips_devices_without_serial(self, tmp_path) -> None:
        root = _make_fake_usb_tree(tmp_path, [
            {"manufacturer": "Allied Vision", "product": "Alvium"},  # pas de serial
            {"manufacturer": "Allied Vision", "product": "Alvium", "serial": "00100"},
        ])
        with patch.object(cameras, "USB_DEVICES_PATH", root):
            detected = cameras.detect_cameras()
        assert len(detected) == 1
        assert detected[0].serial == "00100"


class TestGetCameraPair:
    def test_smaller_serial_is_camera_a(self, tmp_path) -> None:
        root = _make_fake_usb_tree(tmp_path, [
            {"manufacturer": "Allied Vision", "product": "Alvium 1800",
             "serial": "00100"},
            {"manufacturer": "Allied Vision", "product": "Alvium 1800",
             "serial": "00050"},
        ])
        with patch.object(cameras, "USB_DEVICES_PATH", root):
            pair = cameras.get_camera_pair()
        # Règle impérative § 6 : plus petit S/N = caméra A
        assert pair.camera_a.serial == "00050"
        assert pair.camera_b.serial == "00100"

    def test_raises_when_less_than_two(self, tmp_path) -> None:
        root = _make_fake_usb_tree(tmp_path, [
            {"manufacturer": "Allied Vision", "product": "Alvium", "serial": "00001"},
        ])
        with patch.object(cameras, "USB_DEVICES_PATH", root):
            with pytest.raises(cameras.NotEnoughCamerasError):
                cameras.get_camera_pair()

    def test_raises_when_more_than_two(self, tmp_path) -> None:
        root = _make_fake_usb_tree(tmp_path, [
            {"manufacturer": "Allied Vision", "product": "Alvium", "serial": "00001"},
            {"manufacturer": "Allied Vision", "product": "Alvium", "serial": "00002"},
            {"manufacturer": "Toshiba-Teli", "product": "BU-238M", "serial": "00003"},
        ])
        with patch.object(cameras, "USB_DEVICES_PATH", root):
            with pytest.raises(cameras.TooManyCamerasError):
                cameras.get_camera_pair()
