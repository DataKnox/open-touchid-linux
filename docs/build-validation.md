# Kernel patch build validation

Date: 2026-09-02

This validation proves that the RFC endpoint-advertisement patch compiles. It
does not prove that a patched kernel boots, that the SEP advertises a biometric
service, or that Touch ID authentication works.

## Environment

| Item | Value |
|---|---|
| Host | Apple MacBook Air M1 (J313) |
| Architecture | aarch64 |
| Running kernel | `7.1.6-1-1-ARCH` |
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

## Result

```text
Rust is available!
RUSTC drivers/soc/apple/sep.o
exit code: 0
```

One unrelated pre-existing unused-import warning appeared in
`rust/kernel/soc/apple/rtkit.rs`. The patched `sep.rs` emitted no diagnostic.

## Next runtime gate

The patch must be built into a separately named test kernel, installed without
replacing the known-good kernel, and booted with a documented rollback path.
Only the four-byte endpoint advertisement and endpoint number may be collected;
shared memory and message payloads remain out of scope.
