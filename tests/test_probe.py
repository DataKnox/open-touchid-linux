import tempfile
import unittest
from pathlib import Path

from src.open_touchid_probe import VERSION, collect


class ProbeTests(unittest.TestCase):
    def test_version_is_exposed(self):
        self.assertEqual(VERSION, "0.3.1")

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
        mbox = self.proc / "device-tree" / "soc" / "mbox@242408000"
        mbox.mkdir()
        (mbox / "phandle").write_bytes(b"\x00\x00\x00\x2a")
        (self.proc / "device-tree" / "soc" / "sep@242400000" / "mboxes").write_bytes(
            b"\x00\x00\x00\x2a"
        )
        (self.proc / "interrupts").write_text(
            "           CPU0       CPU1\n"
            " 61:         12          3     AIC2 65815 Level     242408000.mbox-recv\n"
            " 62:          4          0     AIC2 65812 Level     242408000.mbox-send\n"
        )
        (self.proc / "bus" / "input" / "devices").write_text(
            'N: Name="Apple SMC power/lid events"\nH: Handlers=kbd event0\n'
        )
        sep_driver = self.sys / "bus" / "platform" / "drivers" / "apple_sep"
        (sep_driver / "242400000.sep").mkdir(parents=True)
        self.config = self.root / "config"
        self.config.write_text(
            "CONFIG_APPLE_SEP=y\nCONFIG_APPLE_MAILBOX=y\nCONFIG_APPLE_SART=y\n"
        )
        self.modules = self.root / "modules"

    def tearDown(self):
        self.temp.cleanup()

    def test_m1_sep_bound_without_sensor(self):
        report = collect(
            self.proc,
            self.sys,
            self.config,
            self.modules,
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
        self.assertFalse(
            report["kernel"]["drivers"]["apple_sio"]["loadable_module_available"]
        )
        self.assertTrue(report["kernel"]["config"]["CONFIG_APPLE_SEP"])
        self.assertEqual(
            report["assessment"]["status"],
            "sep-transport-bound-sensor-not-exposed",
        )
        self.assertFalse(report["assessment"]["touchid_authentication_available"])
        self.assertFalse(report["privacy"]["contains_biometric_data"])
        self.assertEqual(report["assessment"]["warnings"], [])
        self.assertEqual(report["hardware"]["device_tree"]["sep_mailbox"], "242408000")
        self.assertEqual(report["kernel"]["sep_mailbox_interrupts"], 19)

    def test_bound_driver_with_silent_mailbox_warns(self):
        (self.proc / "interrupts").write_text(
            "           CPU0       CPU1\n"
            " 61:          0          0     AIC2 65815 Level     242408000.mbox-recv\n"
            " 62:          0          0     AIC2 65812 Level     242408000.mbox-send\n"
        )
        report = collect(
            self.proc,
            self.sys,
            self.config,
            self.modules,
            kernel_release="7.1-test",
            machine="aarch64",
        )
        self.assertEqual(report["assessment"]["status"], "sep-transport-bound-sensor-not-exposed")
        self.assertEqual(report["kernel"]["sep_mailbox_interrupts"], 0)
        self.assertEqual(len(report["assessment"]["warnings"]), 1)
        self.assertIn("mailbox-silent", report["assessment"]["warnings"][0])

    def _make_m2_j493_layout(self):
        """Mirror the M2 MacBook Pro 13-inch (J493) as seen on linux-asahi 7.1.6."""
        dt = self.proc / "device-tree"
        (dt / "model").write_bytes(b"Apple MacBook Pro (13-inch, M2, 2022)\0")
        (dt / "compatible").write_bytes(b"apple,j493\0apple,t8112\0apple,arm-platform\0")
        (dt / "aliases").mkdir()
        (dt / "aliases" / "touchbar0").write_bytes(b"/soc/spi@23510c000/touchbar@0\0")
        sep = dt / "soc" / "sep@25e400000"
        sep.mkdir()
        (sep / "compatible").write_bytes(b"apple,sep\0")
        (sep / "status").write_bytes(b"disabled\0")
        (dt / "soc" / "sio@236400000" / "compatible").write_bytes(
            b"apple,t8112-sio\0apple,sio\0"
        )
        # The M2 driver directory exists but has no bound device.
        for entry in (self.sys / "bus" / "platform" / "drivers" / "apple_sep").iterdir():
            entry.rmdir()
        module = self.modules / "kernel" / "drivers" / "dma" / "apple-sio.ko.zst"
        module.parent.mkdir(parents=True)
        module.touch()

    def test_m2_sep_disabled_in_device_tree(self):
        import shutil

        shutil.rmtree(self.proc / "device-tree" / "soc" / "sep@242400000")
        self._make_m2_j493_layout()
        report = collect(
            self.proc,
            self.sys,
            self.config,
            self.modules,
            kernel_release="7.1-test",
            machine="aarch64",
        )
        dt = report["hardware"]["device_tree"]
        self.assertTrue(dt["sep_node"])
        self.assertEqual(dt["sep_status"], "disabled")
        self.assertFalse(dt["sep_alias"])
        self.assertFalse(dt["sep_firmware_region"])
        self.assertFalse(dt["sep_boot_manifests"])
        self.assertEqual(dt["sio_status"], "disabled")
        self.assertFalse(dt["sio_alias"])
        self.assertFalse(dt["sio_firmware_params"])
        self.assertEqual(
            dt["platform_compatibles"], ["apple,j493", "apple,t8112", "apple,arm-platform"]
        )
        self.assertTrue(report["kernel"]["drivers"]["apple_sep"]["present"])
        self.assertEqual(report["kernel"]["drivers"]["apple_sep"]["bound_devices"], [])
        self.assertTrue(report["kernel"]["drivers"]["apple_sio"]["loadable_module_available"])
        self.assertEqual(report["assessment"]["status"], "sep-disabled-in-device-tree")
        self.assertEqual(report["assessment"]["warnings"], [])
        self.assertIn("sep alias", report["assessment"]["next_boundary"])
        self.assertFalse(report["assessment"]["touchid_authentication_available"])

    def test_enabled_sep_without_firmware_region_is_unbound_with_warning(self):
        sep = self.proc / "device-tree" / "soc" / "sep@242400000"
        (sep / "status").write_bytes(b"okay\0")
        for entry in (self.sys / "bus" / "platform" / "drivers" / "apple_sep").iterdir():
            entry.rmdir()
        report = collect(
            self.proc,
            self.sys,
            self.config,
            self.modules,
            kernel_release="7.1-test",
            machine="aarch64",
        )
        self.assertEqual(report["assessment"]["status"], "sep-described-but-driver-unbound")
        self.assertEqual(len(report["assessment"]["warnings"]), 1)
        self.assertIn("sep alias", report["assessment"]["warnings"][0])

    def test_bootloader_sep_handoff_is_detected_by_name_only(self):
        dt = self.proc / "device-tree"
        sep = dt / "soc" / "sep@242400000"
        (dt / "aliases").mkdir()
        (dt / "aliases" / "sep").write_bytes(b"/soc/sep@242400000\0")
        (dt / "reserved-memory" / "sep-firmware@800000000").mkdir(parents=True)
        (sep / "memory-region").write_bytes(b"\x00\x00\x00\x2a")
        (sep / "local-policy-manifest").write_bytes(b"SECRET-LPOL-BLOB")
        (sep / "iboot-manifest").write_bytes(b"SECRET-IBOT-BLOB")
        report = collect(
            self.proc,
            self.sys,
            self.config,
            self.modules,
            kernel_release="7.1-test",
            machine="aarch64",
        )
        dt_report = report["hardware"]["device_tree"]
        self.assertTrue(dt_report["sep_alias"])
        self.assertTrue(dt_report["sep_firmware_region"])
        self.assertTrue(dt_report["sep_boot_manifests"])
        rendered = str(report)
        self.assertNotIn("SECRET-LPOL-BLOB", rendered)
        self.assertNotIn("SECRET-IBOT-BLOB", rendered)
        self.assertNotIn("800000000", rendered)

    def test_mesa_node_is_detected_but_not_claimed_working(self):
        mesa = self.proc / "device-tree" / "soc" / "spi@1" / "fingerprint@0"
        mesa.mkdir(parents=True)
        (mesa / "compatible").write_bytes(b"biosensor,mesa\0")
        report = collect(
            self.proc,
            self.sys,
            self.config,
            self.modules,
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
            self.modules,
            kernel_release="7.1-test",
            machine="aarch64",
        )
        rendered = str(report)
        self.assertNotIn("SECRET-SERIAL", rendered)

    def test_unbound_sio_module_is_reported_as_available(self):
        module = self.modules / "kernel" / "drivers" / "dma" / "apple-sio.ko.zst"
        module.parent.mkdir(parents=True)
        module.touch()
        report = collect(
            self.proc,
            self.sys,
            self.config,
            self.modules,
            kernel_release="7.1-test",
            machine="aarch64",
        )
        state = report["kernel"]["drivers"]["apple_sio"]
        self.assertFalse(state["present"])
        self.assertEqual(state["bound_devices"], [])
        self.assertTrue(state["loadable_module_available"])

    def test_fallback_display_warns_about_degraded_performance(self):
        fallback = (
            self.sys
            / "bus"
            / "platform"
            / "drivers"
            / "simple-framebuffer"
            / "framebuffer0"
        )
        fallback.mkdir(parents=True)
        report = collect(
            self.proc,
            self.sys,
            self.config,
            self.modules,
            kernel_release="7.1-test",
            machine="aarch64",
        )
        self.assertEqual(
            report["assessment"]["warnings"],
            [
                "apple-dcp-unbound-display-using-simple-framebuffer; "
                "expect degraded display performance"
            ],
        )


if __name__ == "__main__":
    unittest.main()
