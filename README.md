# Open Touch ID Linux

Research and bring-up tooling for Apple Silicon Touch ID on Linux.

> [!IMPORTANT]
> Touch ID authentication does **not** work yet. This project is an evidence-led
> starting point, not a driver release and not a PAM workaround.

## New to Linux on a Mac?

Start with the [plain-language getting-started guide](docs/getting-started.md).
It helps you identify your Mac, explains what works today, runs the safe probe,
and shows how to contribute a useful report without uploading private data.

## What exists today

- A privacy-safe probe that reports the Apple SEP, mailbox, SART, SPI, SIO, and
  Mesa exposure visible to a running Linux kernel.
- A tested M1 MacBook Air (`J313`, `MacBookAir10,1`) baseline.
- A minimal kernel instrumentation patch for printing SEP endpoint
  advertisements that the current stub driver silently discards.
- A security boundary and staged roadmap for actual driver work.

The September 2026 baseline is promising but incomplete:

- Asahi's kernel has an `apple_sep` driver and the M1 MacBook Air binds it.
- That driver identifies itself as a **stub driver** and only boots SEP firmware.
- The Linux device tree describes SIO but leaves it disabled, has no SIO driver,
  and does not expose the `biosensor,mesa` fingerprint child.
- m1n1's existing Mesa tracer says the command buffer becomes encrypted after
  sensor power-on.

That means the missing work is below `fprintd`: enabling and implementing the
SIO/Mesa transport plus the
SEP-backed encrypted biometric protocol must be understood first.

## Run the probe

No root access or dependencies are required:

```bash
python3 src/open_touchid_probe.py > touchid-report.json
```

The final `assessment.status` is the important line. On current M1 systems,
`sep-transport-bound-sensor-not-exposed` means your installation is healthy;
the missing support is in Linux, not a setting you configured incorrectly.

Review the JSON before sharing it. The probe deliberately excludes serial
numbers, MAC addresses, input events, firmware contents, memory addresses from
reserved regions, and biometric data.

Run the tests:

```bash
python3 -m unittest discover -s tests -v
```

## Current M1 result

On an M1 MacBook Air running Asahi kernel `7.1.6-1-1-ARCH`:

```text
SEP device tree node       yes
apple_sep driver bound     yes (242400000.sep)
SIO device tree node       yes, disabled (no driver)
Mesa fingerprint node      no
Touch ID authentication    no
Research boundary          Mesa/SIO + SEP encrypted protocol
```

See [the architecture notes](docs/architecture.md), [roadmap](docs/roadmap.md),
[release success criteria](docs/success-criteria.md), and
[security policy](SECURITY.md) before experimenting.

## Upstream evidence

- [Asahi M1 feature support](https://asahilinux.org/docs/platform/feature-support/m1/)
  currently lists Touch ID as `TBA`.
- [Asahi SEP stub at the inspected kernel commit](https://github.com/AsahiLinux/linux/blob/77cb8f24c2381a8abb7272d7bbdec548d6426a8a/drivers/soc/apple/sep.rs)
  boots firmware and observes endpoint discovery but implements no services.
- [m1n1's Mesa tracer at the inspected commit](https://github.com/AsahiLinux/m1n1/blob/60e53e7078c5cb7efce32d64bf50829e9401e44f/proxyclient/hv/trace_mesa.py)
  captures the sensor transport and records the encryption boundary.
- [Apple's biometric security documentation](https://support.apple.com/en-ca/guide/security/-sec067eb0c9e/web)
  describes a factory-paired sensor-to-SEP channel using authenticated
  encryption.

## Non-goals

- Capturing, exporting, or processing raw fingerprint images in Linux userspace.
- Replacing Secure Enclave matching with a weaker software matcher.
- Shipping authentication hooks before the protocol and threat model are
  reviewed.
- Redistributing Apple firmware, keys, templates, or other proprietary data.

## License

MIT for project-authored tooling and documentation. The exploratory kernel
patch targets dual MIT/GPL upstream code and carries the same dual license in
its patch metadata.
