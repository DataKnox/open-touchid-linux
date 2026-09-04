# Kernel patch build validation

Date: 2026-09-02

This validation proves that the RFC endpoint-advertisement patch compiles and
boots as a separately named test kernel. It also records the endpoint inventory
observed on J313. It does not prove that the SEP advertises a biometric service
or that Touch ID authentication works.

## Environment

| Item | Value |
|---|---|
| Host | Apple MacBook Air M1 (J313) |
| Architecture | aarch64 |
| Build host kernel | `7.1.6-1-1-ARCH` |
| Test kernel | `7.1.9-open-touchid-test1+` |
| Asahi source branch | `asahi` |
| Asahi source commit | `77cb8f24c2381a8abb7272d7bbdec548d6426a8a` |
| Rust | `1.98.0` |
| LLVM/Clang | `22.1.8` |
| rust-bindgen | `0.72.1` |

The build used the running kernel's `/proc/config.gz`, preserving
`CONFIG_APPLE_SEP=y`, `CONFIG_APPLE_MAILBOX=y`, `CONFIG_APPLE_SART=y`, and
`CONFIG_RUST_APPLE_MAILBOX=y`.

## Commands

```bash
make O=/tmp/open-touchid-linux-build olddefconfig
make O=/tmp/open-touchid-linux-build LLVM=1 rustavailable
make O=/tmp/open-touchid-linux-build LLVM=1 prepare
make O=/tmp/open-touchid-linux-build LLVM=1 drivers/soc/apple/sep.o
```

## Build result

```text
Rust is available!
RUSTC drivers/soc/apple/sep.o
exit code: 0
```

One unrelated pre-existing unused-import warning appeared in
`rust/kernel/soc/apple/rtkit.rs`. The patched `sep.rs` emitted no diagnostic.

## Boot result

The patched kernel was installed under the separate
`open-touchid-test1` boot entry and booted successfully. The known-good kernel
remained available as a rollback path. The running release reported by
`uname -r` was:

```text
7.1.9-open-touchid-test1+
```

The privacy-safe probe still reported
`sep-transport-bound-sensor-not-exposed`: SEP was bound, SIO remained disabled,
and no Mesa device-tree node was exposed.

Loading the test kernel's `apple_sio` module succeeded, but the driver had zero
bound devices. This confirms the module itself is usable and the immediate
blocker is the disabled/incomplete platform description rather than a missing
kernel object.

The boot also exposed a non-Touch-ID regression: `apple-dcp` failed to probe
with `-22`, leaving the internal panel on `simple-framebuffer`. This causes
degraded desktop performance, so this particular test kernel is not suitable
for daily use. Return to the stock kernel after collecting the endpoint
inventory. Future probe runs emit a warning for this fallback state.

The endpoint instrumentation produced:

```text
Got endpoint Ok("hibe") at 20
Got endpoint Ok("stac") at 24
Got endpoint Ok("cntl") at 0
Got endpoint Ok("xars") at 16
Got endpoint Ok("xarm") at 19
Got endpoint Ok("pnon") at 21
Got endpoint Ok("hdcp") at 14
```

No endpoint with an obvious biometric or Mesa name was advertised. This is an
observation, not proof that biometric functionality is absent: it may be hidden
behind another service, unavailable to this boot identity, or dependent on
sensor/SIO initialization that Linux has not performed.

Only the four-byte endpoint advertisement and endpoint number were collected;
shared memory and message payloads remained out of scope.

## J493 (M2) boot result

Date: 2026-09-04. Host: Apple MacBook Pro (13-inch, M2, 2022), `apple,j493` /
`apple,t8112`, Omarchy 4.0.2 on Asahi Alarm, m1n1 v1.6.1, U-Boot 2026.04, GRUB.

| Item | Value |
|---|---|
| Build host kernel | `7.1.6-1-1-ARCH` (linux-asahi 7.1.6.asahi1-1) |
| Test kernel | `7.1.6-1-1-touchid` |
| Source | tag `asahi-7.1.6-1`, stock config, `CONFIG_DEBUG_INFO_BTF` off |
| Patches | 0001 (endpoint logging) + 0002 (J493 sep alias and enable) |
| Toolchain | GCC 16.1.1, rustc 1.93.1, bindgen 0.72.1 (Asahi Alarm PKGBUILD flow, `makepkg`) |
| Boot chain change | patched `t8112-j493.dtb` embedded in the m1n1 image via `/etc/default/update-m1n1`; stock entry booted with `initcall_blacklist=__apple_sep_init` |

Verified before the test boot, on the stock kernel with the driver blacklisted:
the SEP node reported `okay`, m1n1 attached `memory-region` plus
`local-policy-manifest` and `iboot-manifest`, `/reserved-memory/sep-firmware`
existed, and `apple_sep` was absent from the driver list. Only one device tree
differed from the installed set (`t8112-j493.dtb`, the alias and the status).

Test boot: clean, `apple-dcp` bound, no simple-framebuffer fallback, desktop
normal. `apple_sep` bound to `25e400000.sep` and sent its TZ0 boot request.
Kernel log lines mentioning the device, in full:

```text
OF: reserved mem: 0x0000000804518000..0x0000000804ab7fff (5760 KiB) map non-reusable sep-firmware
platform 25e400000.sep: Adding to iommu group 5
```

No `Got endpoint` line, no `Unable to load firmware`, no `Unknown boot message`
appeared. The SEP mailbox interrupt counters after more than 75 seconds:

```text
 61:          0          0          0          0          0          0          0          0     AIC2 65815 Level     25e408000.mbox-recv
 62:          0          0          0          0          0          0          0          0     AIC2 65812 Level     25e408000.mbox-send
```

Zero on both `mbox-recv` and `mbox-send`: the SEP never acknowledged TZ0, so
the stub never loaded the firmware or reached endpoint discovery. The probe on
that boot reported `sep-transport-bound-sensor-not-exposed` with
`sep_alias`, `sep_firmware_region`, and `sep_boot_manifests` all true, which
is why 0.3.1 adds `sep_mailbox_interrupts` and the `sep-bound-but-mailbox-silent`
warning: "bound" and "answered" are different facts.

Ruled out: SEP power domain (always-on on both SoCs), mailbox driver (shared
with DCP and NVMe on t8112), device-tree handoff, and toolchain drift. Not yet
ruled out: a t8112-specific SEP boot protocol, or iBoot having already done the
TZ0 step so the request is ignored. The next evidence is an m1n1 hypervisor
trace of macOS booting SEP on J493. Details in the
[M2 baseline](m2-j493-baseline.md#boot-result-with-patches-0001--0002-2026-09-04).
