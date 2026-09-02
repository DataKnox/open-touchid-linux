# Getting started on a Mac

This guide is for people running Linux on Apple hardware who want to understand
Touch ID support without risking their login setup.

## 1. Check whether this project covers your Mac

Run:

```bash
uname -m
cat /proc/device-tree/model 2>/dev/null; echo
```

This project currently targets **Apple Silicon** Macs: M1, M2, M3, and newer
M-series systems, normally reported as `aarch64` or `arm64`.

Intel Macs with T1 or T2 chips have a different architecture and need different
drivers. Their findings are welcome for comparison, but do not apply patches
from this project to them.

## 2. Know what works today

- The physical power button can already produce a normal Linux input event.
- A power-button press is not proof of identity and must not be used as login.
- Built-in Apple Silicon Touch ID is not currently available to `fprintd`.
- Installing fingerprint PAM modules cannot create the missing kernel, SIO,
  Mesa, or SEP protocol support.
- Your password remains the correct authentication method for now.

If another guide claims that installing `fprintd` alone enables M-series Touch
ID, stop before editing `/etc/pam.d`. That advice is for a different reader or
Mac generation.

## 3. Run the safe probe

```bash
git clone https://github.com/ELI3GANT/open-touchid-linux.git
cd open-touchid-linux
python3 src/open_touchid_probe.py > touchid-report.json
```

The probe needs neither `sudo` nor extra packages. Open the report locally:

```bash
python3 -m json.tool touchid-report.json
```

Common statuses:

| Status | Meaning |
|---|---|
| `sep-transport-bound-sensor-not-exposed` | SEP boot support is present, but Linux cannot reach the fingerprint sensor yet. This is expected on the tested M1 baseline. |
| `sep-described-but-driver-unbound` | The kernel knows the SEP hardware exists, but its driver did not bind. Compare your kernel and device tree with a supported Asahi release. |
| `sensor-node-exposed-research-only` | A Mesa-looking node is visible. This is interesting research metadata, not proof that authentication works. |
| `not-apple-silicon` | The system is outside the current M-series scope. |

Every status deliberately reports `touchid_authentication_available: false`
until an end-to-end implementation passes the project's security gates.

## 4. Share a useful report

Read the JSON before uploading it, then open a **Probe report** issue in this
repository and paste the content. The tool excludes known serial-number and MAC
address properties and never reads biometric data, but you should still review
anything you publish.

Include:

- Mac model shown in the report;
- Linux distribution and kernel package name;
- whether the report was collected after a normal boot;
- the complete probe JSON.

Do not include:

- fingerprint images or templates;
- Apple firmware or SEP shared-memory dumps;
- device keys, session keys, serial numbers, or enrollment records;
- `/dev/mem` or raw MMIO captures.

## 5. Help with the driver effort

Useful contributions include:

- probe reports from different M-series Mac models;
- review of the probe's privacy guarantees;
- Linux Rust, mailbox, DMA/IOMMU, SPI, and Asahi device-tree expertise;
- protocol documentation that cleanly separates observation from inference;
- threat modeling and fuzzing before any authentication integration.

Read the [architecture notes](architecture.md), [roadmap](roadmap.md),
[success criteria](success-criteria.md), and [security policy](../SECURITY.md)
before low-level experimentation.

## FAQ

### Can I enable it with an Omarchy or Arch command?

No. Those distributions can configure supported fingerprint readers, but the
built-in Apple Silicon sensor is not exposed as one yet.

### Can the power button replace my password?

No. Linux can observe that anyone pressed the button; it cannot infer whose
finger pressed it. A future implementation needs a positive match result from
the paired Secure Enclave.

### Will the finished project remove every password prompt?

It should cover routine unlock, `sudo`, polkit, and approved secret-manager or
passkey operations. A recovery password remains necessary for boot-time disk
decryption, lockout, hardware failure, and sensitive policy changes unless a
separate secure design is completed.

### Is there an ETA?

No. The sensor channel is undocumented, hardware-paired, and encrypted. Follow
the checked milestones in the roadmap rather than promises about dates.
