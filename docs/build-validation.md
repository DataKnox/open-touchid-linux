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
