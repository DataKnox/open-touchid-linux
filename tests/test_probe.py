import tempfile
import unittest
from pathlib import Path

from src.open_touchid_probe import VERSION, collect


class ProbeTests(unittest.TestCase):
    def test_version_is_exposed(self):
        self.assertEqual(VERSION, "0.2.0")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.proc = self.root / "proc"
        self.sys = self.root / "sys"
        (self.proc / "device-tree" / "soc" / "sep@242400000").mkdir(parents=True)
        (self.proc / "device-tree" / "model").write_bytes(b"Apple MacBook Air (M1, 2020)\0")
        (self.proc / "device-tree" / "soc" / "sep@242400000" / "compatible").write_bytes(
            b"apple,sep\0"
        )
        (self.proc / "device-tree" / "soc" / "sio@236400000").mkdir()
        (self.proc / "device-tree" / "soc" / "sio@236400000" / "compatible").write_bytes(
            b"apple,t8103-sio\0apple,sio\0"
        )
        (self.proc / "device-tree" / "soc" / "sio@236400000" / "status").write_bytes(
            b"disabled\0"
        )
        (self.proc / "bus" / "input").mkdir(parents=True)
        (self.proc / "bus" / "input" / "devices").write_text(
            'N: Name="Apple SMC power/lid events"\nH: Handlers=kbd event0\n'
        )
        sep_driver = self.sys / "bus" / "platform" / "drivers" / "apple_sep"
        (sep_driver / "242400000.sep").mkdir(parents=True)
        self.config = self.root / "config"
        self.config.write_text(
            "CONFIG_APPLE_SEP=y\nCONFIG_APPLE_MAILBOX=y\nCONFIG_APPLE_SART=y\n"
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_m1_sep_bound_without_sensor(self):
        report = collect(
            self.proc,
            self.sys,
            self.config,
            kernel_release="7.1-test",
            machine="aarch64",
        )
        self.assertTrue(report["system"]["apple_silicon"])
        self.assertTrue(report["kernel"]["drivers"]["apple_sep"]["present"])
        self.assertEqual(
            report["hardware"]["device_tree"]["node_status"]["/soc/sio@236400000"],
            "disabled",
        )
        self.assertFalse(report["kernel"]["drivers"]["apple_sio"]["present"])
        self.assertTrue(report["kernel"]["config"]["CONFIG_APPLE_SEP"])
        self.assertEqual(
            report["assessment"]["status"],
            "sep-transport-bound-sensor-not-exposed",
        )
        self.assertFalse(report["assessment"]["touchid_authentication_available"])
        self.assertFalse(report["privacy"]["contains_biometric_data"])

    def test_mesa_node_is_detected_but_not_claimed_working(self):
        mesa = self.proc / "device-tree" / "soc" / "spi@1" / "fingerprint@0"
        mesa.mkdir(parents=True)
        (mesa / "compatible").write_bytes(b"biosensor,mesa\0")
        report = collect(
            self.proc,
            self.sys,
            self.config,
            kernel_release="7.1-test",
            machine="aarch64",
        )
        self.assertTrue(report["hardware"]["device_tree"]["mesa_sensor_node"])
        self.assertEqual(
            report["assessment"]["status"], "sensor-node-exposed-research-only"
        )
        self.assertFalse(report["assessment"]["touchid_authentication_available"])

    def test_serial_number_property_is_never_reported(self):
        (self.proc / "device-tree" / "serial-number").write_text("SECRET-SERIAL")
        report = collect(
            self.proc,
            self.sys,
            self.config,
            kernel_release="7.1-test",
            machine="aarch64",
        )
        rendered = str(report)
        self.assertNotIn("SECRET-SERIAL", rendered)


if __name__ == "__main__":
    unittest.main()
