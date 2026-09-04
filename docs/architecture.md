# Architecture and evidence

## Security model

Apple documents a strict split between the application processor, the built-in
Touch ID sensor, and the Secure Enclave. The application processor forwards
sensor traffic but cannot read it. The built-in sensor and its paired Secure
Enclave negotiate a session key from a unique factory-provisioned shared key;
transport confidentiality and authentication use AES-CCM.

This is why a generic `libfprint` device driver is not the first missing piece.
The safe end state should ask SEP to enroll or match and receive a narrow result;
it should not expose images or templates to Linux.

Primary reference: [Apple Platform Security — Biometric security](https://support.apple.com/en-ca/guide/security/-sec067eb0c9e/web).

## Observed M1 path

```text
Power-button input ──────────────> Apple SMC input ──> Linux input event

Fingerprint sensor (Mesa)
        │ factory-paired encrypted channel
        ▼
SIO / SPI transport ─────────────> Secure Enclave (sepOS)
                                         │
                                         ▼
                               match / no-match result
                                         │
                                         ▼
                              future Linux auth service
                                         │
                                         ▼
                              fprintd / PAM integration
```

The power-button event already visible to Linux is separate from a fingerprint
match. Treating a button press as authentication would provide no identity
proof.

## Linux kernel state inspected

Source: Asahi Linux kernel branch `asahi`, commit
`77cb8f24c2381a8abb7272d7bbdec548d6426a8a`.

The Rust driver at `drivers/soc/apple/sep.rs`:

1. Builds SEP shared memory containing panic, local-policy, and iBoot manifest
   regions.
2. Boots TZ0 and the SEP firmware image through an Apple mailbox.
3. Receives endpoint advertisements on endpoint `0xFD`.
4. Silently discards the advertised service name and endpoint number.
5. Describes itself as `Secure enclave processor stub driver`.

On the tested J313, the live kernel has `CONFIG_APPLE_SEP=y` and binds
`apple_sep` to `242400000.sep`. This proves firmware bring-up reaches the stub;
it does not prove any biometric service is usable.

The instrumentation patch was subsequently booted as the separately named
`7.1.9-open-touchid-test1+` kernel. SEP advertised `hibe`, `stac`, `cntl`,
`xars`, `xarm`, `pnon`, and `hdcp`. None has an obvious biometric or Mesa name.
That does not establish absence: the relevant function could sit behind a
non-obvious service, require SIO/sensor initialization first, or be withheld
from this boot identity.

## m1n1 research state inspected

Source: m1n1 commit `60e53e7078c5cb7efce32d64bf50829e9401e44f`.

`proxyclient/hv/trace_mesa.py` locates a `biosensor,mesa` child beneath an Apple
SPI controller, traces SIO endpoints `0x18` and `0x19`, and follows DART-backed
buffers. Its leading research note says the command buffer is encrypted after
the power-on sequence and that the key was not found through an older SEP
tracer.

The Linux device tree presented on the tested machine contains the SEP node and
a disabled `apple,t8103-sio` node. Asahi already ships
`drivers/dma/apple-sio.c` as `apple-sio.ko`; it boots the SIO RTKit endpoint and
provides cyclic DMA channels. It is not registered or bound on the live J313
because the platform node remains disabled. The node also lacks the
`apple,sio-firmware-params` consumed by that driver and has no Mesa child.

Enabling the fingerprint path therefore means extending and enabling an existing
SIO foundation, adding the model-specific firmware parameters and Mesa
description, and implementing the missing biometric client/protocol. It does
not require rewriting the SIO DMA engine from zero.

The probe's driver `present` field means registered in the running kernel's
sysfs driver model; `false` does not mean that no loadable module exists.

## Bootloader handoff and why M2 differs

The `apple_sep` stub cannot bind on device-tree description alone. In its
`probe()` it looks up a reserved-memory region named `sepfw` and reads two
byte-array properties, `local-policy-manifest` and `iboot-manifest`. None of
those exist in the kernel's static device tree. m1n1 injects them in
`dt_set_sep()` (`src/kboot.c`, added in commit `62ff43f095`, "kboot: Pass
through SEPFW and boot object manifests") only when the FDT has a `sep`
alias; without it m1n1 logs `FDT: sep alias not found in devtree` and skips.
(The reserved-memory node it creates is named plain `sep-firmware`, with no unit
address.)

The kernel side follows the same pattern: `t8103.dtsi` and `t8112.dtsi` both
declare the SEP node with `status = "disabled"`, and a board file must opt in.
The driver was added to unlock the microphone secure-disable on certain M1
laptops (commit `55098df5a4`, "soc: apple: Add SEP driver"), so at
`asahi-7.1.6-1` only `t8103-j293.dts` and `t8103-j313.dts` carry the alias,
and only those plus the M1 iMacs `t8103-j456`/`t8103-j457` enable the node.
No `t8112`, `t600x`, or `t602x` board does either.

On the tested M2 MacBook Pro 13-inch (J493) this yields
`sep-disabled-in-device-tree`: the node, its mailbox, and its DART are all
present and the mailbox driver is bound, but the node is disabled, has no
`sep` alias, no `sepfw` region, and no manifests. Nothing indicates that the
SEP cannot be booted on t8112; it is simply unused there. See the
[M2 baseline](m2-j493-baseline.md) for the observed tree and the RFC
device-tree patch that supplies the alias and enablement.

SIO is gated the same way. m1n1's `dt_set_sio_fwdata()` adds the
`sio-firmware-data` regions and `apple,sio-firmware-params` only for FDT
aliases `sio` and `sio1`, which today exist only on boards with HDMI audio
(`t8103-j274`, `t8112-j473`, `t600x-j314-j316`, `t600x-j375`, `t6022-j475d`).

## Unknowns to resolve

- Which advertised SEP endpoint owns biometric policy or key negotiation?
- Does the SEP firmware boot on t8112 under the stub driver once the board
  device tree enables it, and does the endpoint inventory differ from M1?
- Where is the Mesa sensor on t8112? Linux describes only `spi1` and `spi3`
  on the M2 laptops; the undescribed controller at the `spi2` slot is the
  candidate suggested by m1n1's tracer, but this is unverified without the
  Apple device tree.
- Is the relevant match API available to third-party boot identities, or does
  sepOS restrict it to an Apple-authorized environment?
- Which SIO and Mesa initialization steps can Linux perform without accessing
  plaintext biometric material?
- Can enrollment templates be namespaced to the Linux boot identity without
  weakening macOS enrollment isolation?
- What anti-replay, rate-limit, lockout, and password-fallback semantics does
  SEP expose?
