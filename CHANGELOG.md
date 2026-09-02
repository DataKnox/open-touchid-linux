# Changelog

## 0.2.1 — 2026-09-02

- Fixed misleading SIO diagnostics by distinguishing a loadable kernel module
  from a registered or device-bound driver.
- Added regression coverage for an available but unbound `apple-sio` module.
- Added a runtime warning when a test kernel fails to bind Apple DCP and leaves
  the display on the slower simple-framebuffer path.

## 0.2.0 — 2026-09-02

- Added a versioned CLI and a safe long-term update/distribution contract.
- Added system-wide multi-finger management and enrollment animation behavior
  to the Omarchy UX specification.
- Compile-validated the SEP instrumentation against the J313 host config.
- Boot-validated the separately named test kernel and recorded the J313 SEP
  endpoint inventory without collecting payloads or biometric data.
- Confirmed and documented Asahi's existing but currently unbound Apple SIO DMA
  module, narrowing the missing transport work.

## 0.1.0 — 2026-09-02

- Added a dependency-free, privacy-safe Apple Silicon readiness probe.
- Added three fixture-based tests, including serial-number exclusion.
- Recorded the M1 MacBook Air SEP/SIO/Mesa baseline.
- Added an RFC patch to log SEP endpoint advertisements in Asahi's stub driver.
- Documented architecture, security policy, staged roadmap, release criteria,
  and a newcomer-focused Mac/Linux guide.
