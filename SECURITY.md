# Security policy

This project operates at a biometric and secure-coprocessor boundary. A feature
that appears to work but weakens that boundary is a failure.

## Hard rules

- Never collect, upload, commit, or request fingerprint images or templates.
- Never publish SEP keys, session keys, device-unique secrets, serial numbers,
  firmware blobs, enrollment records, or decrypted biometric payloads.
- Never add an interface that exposes raw Mesa frames to ordinary userspace.
- Never write undocumented MMIO, SPI flash, SEP memory, or enrollment storage on
  a user's production installation.
- Never advertise this project as production authentication until the roadmap's
  security-review gate is complete.
- Preserve password and recovery authentication throughout development.

## Reporting vulnerabilities

Do not open a public issue for a vulnerability, secret, bypass, or potentially
identifying biometric artifact. Contact the maintainer privately through the
GitHub security advisory interface after the repository is published.

For non-sensitive bugs, attach only the JSON from `open_touchid_probe.py` after
reviewing it locally.

## Probe guarantees

The probe reads names and status metadata from `/proc` and `/sys`. It does not
open `/dev/input/event*`, `/dev/mem`, reserved-memory contents, SEP shared
memory, firmware images, fprint enrollment stores, or network interfaces.
