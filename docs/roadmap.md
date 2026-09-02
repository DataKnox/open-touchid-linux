# Roadmap

No phase may claim completion based only on log output. Each phase needs a
reproducible test and a review of the new attack surface.

## Phase 0 — Evidence and safe instrumentation

- [x] Publish a privacy-safe readiness probe.
- [x] Record a J313/M1 baseline.
- [x] Identify the exact SEP stub and Mesa tracing code in upstream projects.
- [x] Prepare a patch that exposes four-byte SEP endpoint advertisements.
- [x] Compile the instrumentation patch against the inspected Asahi commit and
  the J313 host kernel configuration.
- [x] Boot the instrumentation patch as a separate disposable test kernel and
  record the J313 endpoint inventory.
- [ ] Compare endpoint inventories across M1, M2, and M3 devices.

Exit criterion: endpoint metadata can be collected without dumping shared
memory, keys, firmware, or biometric payloads.

## Phase 1 — Transport description

- [ ] Identify the SIO and Mesa nodes in Apple's device tree through m1n1.
- [x] Confirm that Asahi's existing `apple-sio` DMA module supports the SIO
  RTKit endpoint and cyclic DMA but is unbound while J313 SIO is disabled.
- [ ] Document clocks, power domains, GPIO, interrupts, DART streams, and SPI
  topology for J313 without writing undocumented registers from production
  Linux.
- [ ] Propose minimal Linux device-tree bindings upstream.
- [ ] Implement sensor presence/power-state reporting only.

Exit criterion: Linux can identify the paired sensor and transition it through
a reviewed, non-capture lifecycle.

## Phase 2 — SEP service protocol

- [ ] Trace service discovery and narrow request/response metadata under macOS.
- [ ] Identify enrollment and matching operations without recording images,
  templates, session keys, or user-identifying values.
- [ ] Determine whether sepOS authorizes those operations for an Asahi boot
  identity.
- [ ] Specify anti-replay, timeout, lockout, cancellation, and suspend behavior.

Exit criterion: a public protocol specification explains a safe match request
and result, and independent reviewers agree it does not require secret export.

## Phase 3 — Kernel and userspace API

- [ ] Implement a narrow kernel interface with no raw-frame access.
- [ ] Add a privileged broker that maps SEP results to a standard biometric API.
- [ ] Add cancellation, lid/suspend handling, rate limits, and audit events.
- [ ] Fuzz parsers and test malformed SEP/SIO messages.

Exit criterion: enrollment and matching work in a test harness without PAM.

## Phase 4 — Authentication integration

- [ ] Threat-model lock screen, login, polkit, and `sudo` separately.
- [ ] Integrate with `fprintd` only if its API preserves the SEP trust boundary.
- [ ] Support session unlock, local login after the encrypted system is mounted,
  `sudo`, and polkit/admin authorization with clear UI and cancellation.
- [ ] Implement and test the [Omarchy interaction state machine](omarchy-ux.md),
  including enrollment guidance, success/failure motion, reduced-motion mode,
  timeouts, lockout, and password fallback.
- [ ] Implement the per-user Security → Touch ID panel for multi-finger add,
  verify, rename, removal, health status, and per-surface enablement.
- [ ] Define a hardware-backed authorization API for password managers and
  secret stores; applications receive approval, never biometric material.
- [ ] Evaluate a platform FIDO2/WebAuthn authenticator for passkeys as a
  separate reviewed surface rather than treating PAM as browser authentication.
- [ ] Keep password/recovery fallback and never make first boot depend solely on
  biometrics.
- [ ] Commission external security review before recommending daily use.

Exit criterion: reviewed end-to-end authentication with documented recovery and
known limitations.

## Phase 5 — Distribution and safe updates

- [x] Publish a machine-readable CLI version.
- [ ] Publish signed stable, beta, and nightly release manifests with explicit
  kernel, broker, protocol, UI, and database compatibility ranges.
- [ ] Package supported userspace components for Arch/Omarchy; pursue upstream
  kernel delivery instead of silently replacing distribution kernels.
- [ ] Add preflight, staged activation, health verification, automatic rollback,
  and a known-good recovery command.
- [ ] Preserve opaque SEP enrollment identifiers across compatible migrations;
  require deliberate re-enrollment when a security boundary changes.
- [ ] Test upgrades, downgrades, interrupted upgrades, incompatible components,
  and rollback while the screen is locked.

Exit criterion: an ordinary user can update and recover without disabling
authentication, losing the password fallback, or being stranded at login.
