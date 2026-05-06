"""Tests du parsing dmidecode — sortie réelle simulée via subprocess mocké."""

from __future__ import annotations

import subprocess
from unittest.mock import patch

import pytest

from system_info import dmi


# Sortie type de "dmidecode -t system" sur un Dell OptiPlex
DMIDECODE_SYSTEM_OUTPUT = """\
# dmidecode 3.3
Getting SMBIOS data from sysfs.
SMBIOS 3.3.0 present.

Handle 0x0001, DMI type 1, 27 bytes
System Information
\tManufacturer: Dell Inc.
\tProduct Name: OptiPlex 7090
\tVersion: Not Specified
\tSerial Number: ABC1234
\tUUID: 4c4c4544-0030-3210-8051-c2c04f4d3232
\tWake-up Type: Power Switch
\tSKU Number: 0A87
\tFamily: OptiPlex

Handle 0x0002, DMI type 2, 15 bytes
Base Board Information
\tManufacturer: Dell Inc.
\tProduct Name: 0K7VK0
\tVersion: A00
\tSerial Number: /XYZ9999/CN1234567/
"""


def _mock_run(stdout: str, returncode: int = 0):
    """Construit un faux résultat subprocess.run."""
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")


class TestSystemSerial:
    @patch("system_info.dmi.shutil.which", return_value="/usr/sbin/dmidecode")
    @patch("system_info.dmi.subprocess.run")
    def test_returns_serial_from_system_section_only(self, mock_run, _mock_which) -> None:
        mock_run.return_value = _mock_run(DMIDECODE_SYSTEM_OUTPUT)
        # Doit récupérer ABC1234, pas /XYZ9999/CN1234567/ (qui est dans Base Board)
        assert dmi.get_system_serial_number() == "ABC1234"

    @patch("system_info.dmi.shutil.which", return_value=None)
    def test_raises_when_dmidecode_missing(self, _mock_which) -> None:
        with pytest.raises(dmi.DmiError, match="introuvable"):
            dmi.get_system_serial_number()

    @patch("system_info.dmi.shutil.which", return_value="/usr/sbin/dmidecode")
    @patch("system_info.dmi.subprocess.run")
    def test_raises_when_serial_section_missing(self, mock_run, _mock_which) -> None:
        mock_run.return_value = _mock_run("# dmidecode 3.3\nNo SMBIOS data found.\n")
        with pytest.raises(dmi.DmiError, match="System Information"):
            dmi.get_system_serial_number()


class TestProcessorVersion:
    @patch("system_info.dmi.shutil.which", return_value="/usr/sbin/dmidecode")
    @patch("system_info.dmi.subprocess.run")
    def test_returns_first_line(self, mock_run, _mock_which) -> None:
        mock_run.return_value = _mock_run("Intel(R) Core(TM) i5-10500 CPU @ 3.10GHz\n")
        assert dmi.get_processor_version() == "Intel(R) Core(TM) i5-10500 CPU @ 3.10GHz"

    @patch("system_info.dmi.shutil.which", return_value="/usr/sbin/dmidecode")
    @patch("system_info.dmi.subprocess.run")
    def test_handles_multi_cpu_output(self, mock_run, _mock_which) -> None:
        mock_run.return_value = _mock_run(
            "Intel(R) Xeon(R) Gold 6142\nIntel(R) Xeon(R) Gold 6142\n"
        )
        assert dmi.get_processor_version() == "Intel(R) Xeon(R) Gold 6142"
