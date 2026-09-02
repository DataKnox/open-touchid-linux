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

## Unknowns to resolve

- Which advertised SEP endpoint owns biometric policy or key negotiation?
- Is the relevant match API available to third-party boot identities, or does
  sepOS restrict it to an Apple-authorized environment?
- Which SIO and Mesa initialization steps can Linux perform without accessing
  plaintext biometric material?
- Can enrollment templates be namespaced to the Linux boot identity without
  weakening macOS enrollment isolation?
- What anti-replay, rate-limit, lockout, and password-fallback semantics does
  SEP expose?
