# M2 MacBook Pro 13-inch (J493) baseline

Date: 2026-09-04

This is the first t8112 data point. It records what a stock Asahi Alarm kernel
exposes on an M2 laptop, explains why the `apple_sep` stub never binds there,
and ships the device-tree change that a J493 endpoint inventory needs. It does
not prove that SEP firmware boots on t8112; that is the next reboot.

```text
SEP device tree node       yes, disabled (no sep alias, no firmware region)
apple_sep driver bound     no (driver registered, zero devices)
SIO device tree node       yes, disabled (driver module exists but is unbound)
Mesa fingerprint node      no
Touch ID authentication    no
Research boundary          board DT enablement, then Mesa/SIO + SEP protocol
```

## Environment

| Item | Value |
|---|---|
| Host | Apple MacBook Pro (13-inch, M2, 2022), board `apple,j493`, SoC `apple,t8112` |
| Distribution | Omarchy 4.0.2 (omarchy-mac) on Asahi Alarm (Arch Linux ARM) |
| Kernel package | `linux-asahi 7.1.6.asahi1-1` from asahi-alarm/PKGBUILDs, release `7.1.6-1-1-ARCH` |
| Kernel source | Asahi Linux tag `asahi-7.1.6-1` |
| Boot chain | m1n1 v1.6.1 stage 2 → U-Boot 2026.04.asahi2 → GRUB 2.14 (EFI) |
| macOS firmware | os-fw 13.5, iBoot-8422.141.2 |
| Probe | `open_touchid_probe.py` 0.3.0 after a normal boot, no root |

## Probe result

Reviewed locally; contains node names with MMIO offsets, kernel release, and
model string only.

```json
{
  "assessment": {
    "next_boundary": "Board device tree: add the sep alias and enable the SEP node so the bootloader passes firmware, then collect the SEP endpoint inventory",
    "status": "sep-disabled-in-device-tree",
    "touchid_authentication_available": false,
    "warnings": []
  },
  "generated_at": "2026-09-04T17:30:51.291610+00:00",
  "hardware": {
    "device_tree": {
      "mesa_sensor_node": false,
      "node_status": {
        "/soc/pinctrl@23c100000/spi1-pins": "okay (implicit)",
        "/soc/pinctrl@23c100000/spi3-pins": "okay (implicit)",
        "/soc/sep@25e400000": "disabled",
        "/soc/sio@236400000": "disabled",
        "/soc/spi@235104000": "okay",
        "/soc/spi@23510c000": "okay"
      },
      "platform_compatibles": [
        "apple,j493",
        "apple,t8112",
        "apple,arm-platform"
      ],
      "relevant_compatibles": [
        "apple,sep",
        "apple,sio",
        "apple,spi",
        "apple,t8112-sio",
        "apple,t8112-spi"
      ],
      "relevant_nodes": [
        "/soc/pinctrl@23c100000/spi1-pins",
        "/soc/pinctrl@23c100000/spi3-pins",
        "/soc/sep@25e400000",
        "/soc/sio@236400000",
        "/soc/spi@235104000",
        "/soc/spi@23510c000"
      ],
      "sep_alias": false,
      "sep_boot_manifests": false,
      "sep_firmware_region": false,
      "sep_node": true,
      "sep_status": "disabled",
      "sio_alias": false,
      "sio_firmware_params": false,
      "sio_node": true,
      "sio_status": "disabled"
    },
    "power_button_input_visible": true
  },
  "kernel": {
    "config": {
      "CONFIG_APPLE_MAILBOX": true,
      "CONFIG_APPLE_SART": true,
      "CONFIG_APPLE_SEP": true,
      "CONFIG_RUST_APPLE_MAILBOX": true
    },
    "drivers": {
      "apple_dcp": {
        "bound_devices": [
          "231c00000.dcp"
        ],
        "loadable_module_available": true,
        "present": true
      },
      "apple_mailbox": {
        "bound_devices": [
          "206408000.mbox",
          "231c08000.mbox",
          "236408000.mbox",
          "23bc08000.mbox",
          "23e408000.mbox",
          "24a408000.mbox",
          "24e408000.mbox",
          "25e408000.mbox",
          "277408000.mbox"
        ],
        "loadable_module_available": false,
        "present": true
      },
      "apple_sart": {
        "bound_devices": [
          "27bc50000.sart"
        ],
        "loadable_module_available": false,
        "present": true
      },
      "apple_sep": {
        "bound_devices": [],
        "loadable_module_available": false,
        "present": true
      },
      "apple_sio": {
        "bound_devices": [],
        "loadable_module_available": true,
        "present": false
      },
      "apple_spi": {
        "bound_devices": [
          "235104000.spi",
          "23510c000.spi"
        ],
        "loadable_module_available": false,
        "present": true
      },
      "simple_framebuffer": {
        "bound_devices": [],
        "loadable_module_available": false,
        "present": true
      }
    }
  },
  "privacy": {
    "contains_biometric_data": false,
    "contains_serial_numbers": false,
    "safe_to_attach_to_public_issue_after_review": true
  },
  "schema_version": 1,
  "system": {
    "apple_silicon": true,
    "architecture": "aarch64",
    "kernel_release": "7.1.6-1-1-ARCH",
    "model": "Apple MacBook Pro (13-inch, M2, 2022)"
  },
  "userspace": {
    "fprintd_installed": false
  }
}
```

## Device tree observations

Everything below comes from `/proc/device-tree` names, `status` strings, and
property presence. No property contents were read beyond `status`,
`compatible`, and `model`.

- `/soc/sep@25e400000`: compatible `apple,sep`, status `disabled`. Properties
  present: `compatible`, `iommus`, `mboxes`, `mbox-names`, `name`, `reg`,
  `status`. There is no `memory-region`, `local-policy-manifest`, or
  `iboot-manifest`.
- `/aliases` contains `atcphy0 atcphy1 bluetooth0 dcp disp0 disp0_piodma gpu
  isp keyboard nvram serial0 serial2 touchbar0 wifi0`. There is no `sep` and
  no `sio` alias.
- `/reserved-memory` has the usual `asc-firmware`, `dcp_data`, `flash`,
  `framebuffer`, `hw-cal-*`, `isp-heap`, and `uat-*` regions. There is no
  `sep-firmware` and no `sio-firmware-data` node.
- The SEP support blocks are present and enabled: the mailbox
  `mbox@25e408000` (`apple,t8112-asc-mailbox`) is bound by `apple-mailbox`
  as `25e408000.mbox`, and the DART `iommu@25d2c0000` (`apple,t8112-dart`)
  is enabled.
- `/soc/sio@236400000`: compatible `apple,t8112-sio`, status `disabled`.
  Properties present: `compatible`, `#dma-cells`, `dma-channels`, `iommus`,
  `mboxes`, `name`, `phandle`, `power-domains`, `reg`, `resets`, `status`.
  There is no `apple,sio-firmware-params`. `apple-sio.ko` exists under
  `/usr/lib/modules` but the driver is not registered.
- SPI: `spi@235104000` (`spi1`) is enabled with child `flash@0`;
  `spi@23510c000` (`spi3`) is enabled with child `touchbar@0`
  (`apple,j493-touchbar`). Both are bound by `apple-spi`. No node anywhere
  is named or compatible with `biosensor`, `mesa`, `touchid`, or
  `fingerprint`.
- Drivers: `apple_sep` is registered with zero bound devices; `apple-dcp` is
  bound to `231c00000.dcp`, so there is no simple-framebuffer fallback.
- Kernel config: `CONFIG_APPLE_SEP=y`, `CONFIG_APPLE_SIO=m`,
  `CONFIG_APPLE_MAILBOX=y`, `CONFIG_APPLE_SART=y`,
  `CONFIG_RUST_APPLE_MAILBOX=y`, `CONFIG_SPI_APPLE=y`, `CONFIG_RUST=y`.
  `/proc/kallsyms` lists `__apple_sep_init` and `__apple_sep_exit`.

## Why `apple_sep` is unbound on J493

Observation, from the Asahi kernel and m1n1 sources at the versions above:

1. `arch/arm64/boot/dts/apple/t8112.dtsi` declares `sep: sep@25e400000` with
   `status = "disabled"`, exactly like `t8103.dtsi` does for
   `sep@242400000`. A board file has to opt in.
2. `t8112-j493.dts` neither enables `&sep` nor lists `sep` in `aliases`.
   At `asahi-7.1.6-1` the only board files with the alias are
   `t8103-j293.dts` and `t8103-j313.dts`; `&sep { status = "okay"; }` also
   appears in `t8103-j456.dts` and `t8103-j457.dts`. No `t8112`, `t600x`, or
   `t602x` board does either.
3. m1n1's `dt_set_sep()` in `src/kboot.c` (commit `62ff43f095`, 2024-11-11,
   "kboot: Pass through SEPFW and boot object manifests") starts with
   `fdt_get_alias(dt, "sep")`. Without the alias it prints
   `FDT: sep alias not found in devtree` and returns. With it, it reserves
   the ADT `SEPFW` range as `/reserved-memory/sep-firmware@...`
   (`apple,asc-mem`), adds a `memory-region` named `sepfw` to the node, and
   copies the ADT `lpol` and `ibot` manifests into `local-policy-manifest`
   and `iboot-manifest` properties. m1n1 v1.6.1 contains this code.
4. `drivers/soc/apple/sep.rs` `probe()` calls
   `reserved_mem_region_to_resource_byname(c"sepfw")` and `build_shmem()`
   reads both manifest properties. None exist on J493, so even an enabled
   node would fail to probe until m1n1 sees the alias.
5. The driver's own commit (`55098df5a4`, "soc: apple: Add SEP driver") says
   it "only boots the firmware, which is needed to unlock the mic secure
   disable on certain laptop models". That explains the M1-laptop-only opt-in.

Inference: nothing in these sources suggests SEP cannot be booted on t8112;
the M2 boards simply never needed it. The M1 endpoint inventory exists as a
side effect of the microphone workaround, not because M1 is closer to Touch
ID than M2. Whether `TZ0`/`IMG4` boot completes on t8112 is unknown until the
patched kernel below is booted.

## Where t8112 differs from t8103 in the kernel tree

- `t8103.dtsi` describes `spi0` (`0x235100000`), `spi1` (`0x235104000`), and
  `spi3` (`0x23510c000`). `t8112.dtsi` describes only `spi1` and `spi3`.
  Neither describes the `0x235108000` slot that the `0x4000` stride leaves
  for `spi2`. (Observation from the dts sources.)
- m1n1's `proxyclient/hv/trace_mesa.py` looks for a `biosensor,mesa` child
  under a `spi-1,spimc` controller and labels SIO endpoints `0x18`/`0x19`
  as "SPI2 DMA channels". (Observation from the m1n1 source.)
- Inference: on J493 the sensor most likely hangs off the undescribed `spi2`
  controller and uses SIO DMA, so Phase 1 on t8112 needs a `spi2` node, a
  `biosensor,mesa` child, and an enabled `sio` node with the `sio` alias so
  m1n1 passes `apple,sio-firmware-params`. This is unverified without the
  Apple device tree; m1n1 proxy access or a macOS `ioreg` dump would confirm
  the bus and pins.
- SIO firmware data is alias-gated exactly like SEP: m1n1's
  `dt_set_sio_fwdata()` only acts on FDT aliases `sio` and `sio1`, which at
  this tag exist on `t8103-j274`, `t8112-j473`, `t600x-j314-j316`,
  `t600x-j375`, and `t6022-j475d`, all machines with HDMI audio.

## Required change for the J493 endpoint inventory

[`patches/0002-arm64-dts-apple-t8112-j493-enable-sep.patch`](../patches/0002-arm64-dts-apple-t8112-j493-enable-sep.patch)
adds `sep = &sep;` to the J493 `aliases` block and appends
`&sep { status = "okay"; };`. It applies to tag `asahi-7.1.6-1` and to the
`asahi` branch at `77cb8f24c2381a8abb7272d7bbdec548d6426a8a` with only a line
offset in the second hunk. Together with patch 0001 it should make the stub
bind, boot the firmware, and log the advertised endpoints.

The dts file is `GPL-2.0+ OR MIT`; the patch carries the same dual license.

## Test plan on Asahi Alarm / Omarchy

The boot chain constrains the experiment. `update-m1n1` (asahi-scripts)
concatenates m1n1, every `.dtb` from the newest `/lib/modules/*-ARCH/dtbs`,
and U-Boot into one `m1n1/boot.bin` on the EFI system partition, and a pacman
hook reruns it whenever a kernel package installs DTBs. m1n1 applies its
fixups to that embedded DTB before U-Boot and GRUB run. Consequently:

- A DTB change is global: every GRUB entry, stock kernel included, boots with
  the SEP node enabled once the modified DTB is embedded.
- GRUB's `devicetree` command is not an alternative, because a DTB loaded
  from disk skips m1n1's fixups (memory, framebuffer, firmware regions).
- The stock kernel can still be shielded: `initcall_blacklist=__apple_sep_init`
  on its command line skips the built-in driver's initcall. Verify the symbol
  first with `grep __apple_sep_init /proc/kallsyms`.

Steps used for J493 (all writes need root; nothing below touches SEP memory,
sensors, or enrollment storage):

1. Build a separately named kernel package from the asahi-alarm
   `linux-asahi` PKGBUILD with both patches, `CONFIG_LOCALVERSION="-touchid"`
   so its module directory does not match the `*-ARCH` glob, and
   `CONFIG_DEBUG_INFO_BTF` disabled. `makepkg` produces
   `linux-asahi-touchid-7.1.6.asahi1-1-aarch64.pkg.tar.zst`.
2. `pacman -U` the package. The mkinitcpio hook creates
   `/boot/vmlinuz-linux-asahi-touchid` and its initramfs; the m1n1 hook runs
   but still embeds the stock DTBs because of the module-directory name.
   Run `grub-mkconfig -o /boot/grub/grub.cfg` so the new entry exists.
3. Add `initcall_blacklist=__apple_sep_init` to `GRUB_CMDLINE_LINUX_DEFAULT`
   in `/etc/default/grub` and regenerate `grub.cfg`. This applies to both
   entries; for the test entry, remove it interactively with GRUB's `e`
   editor, or keep a custom entry in `/etc/grub.d/40_custom` without it.
4. Opt into the patched DTBs:
   `echo 'DTBS="/lib/modules/7.1.6-1-1-touchid/dtbs/*.dtb"' > /etc/default/update-m1n1`
   then `update-m1n1`. It keeps the previous image as `boot.bin.old`.
5. Reboot into the stock entry first. Confirm the machine boots normally,
   that `/proc/device-tree/soc/sep@25e400000/status` now reads `okay`, that
   `/proc/device-tree/reserved-memory` contains a `sep-firmware@` node, and
   that `apple_sep` stayed unbound because of the blacklist.
6. Reboot into the test entry. Collect only
   `dmesg | grep -E 'apple_sep|sep@|Got endpoint'` and the probe JSON.
7. Return to the stock entry. To roll back completely, remove
   `/etc/default/update-m1n1`, rerun `update-m1n1`, drop the blacklist, and
   regenerate `grub.cfg`.

If Linux stops booting after step 4, the recovery path is restoring
`m1n1/boot.bin.old` on the EFI system partition from macOS or recoveryOS, or
reflashing m1n1 through the m1n1 proxy over USB. Do not run this on a machine
without one of those paths.

## Open questions this data raises

- Does SEP firmware boot (TZ0 acknowledgements, IMG4 load) on t8112 under
  the stub driver, and does it advertise the same seven services as J313?
- Does booting SEP change microphone behavior on J493, which would explain
  whether Asahi has a reason to enable it on M2 laptops upstream?
- Which controller carries the Mesa sensor on J493, and what are its clocks,
  power domain, GPIOs, and DART stream?
