# Safe update and distribution model

Touch ID participates in login and privilege authorization. Its updater must be
held to a higher standard than an ordinary desktop utility.

## Principles

- Never install through `curl | sh` or execute an unsigned remote script.
- Never overwrite the only known-good kernel or authentication stack.
- Never activate components whose protocol or state versions are incompatible.
- Never remove password/recovery fallback as part of an update.
- Never upload enrollment data, identifiers, hardware metadata, or usage events
  during update checks.

## Components and compatibility

Every release manifest declares versions and compatibility ranges for:

- kernel SEP/SIO/Mesa support;
- privileged broker and secure protocol;
- system service API;
- Omarchy setup, lock-screen, and prompt UI;
- fprintd/PAM adapter, if used;
- settings database schema;
- probe/report schema.

The broker is the compatibility authority. If any required range fails, it
refuses biometric authentication, records a non-secret diagnostic, and leaves
password authentication available. UI and PAM adapters must treat an unknown
broker response as failure.

## Release channels

| Channel | Audience | Activation policy |
|---|---|---|
| `stable` | ordinary users | signed, reproducible artifacts; security review; full upgrade and rollback matrix |
| `beta` | opt-in testers | signed artifacts; supported rollback; explicit diagnostic consent |
| `nightly` | developers | isolated test systems only; never promoted automatically to stable |

Moving to a less stable channel requires explicit confirmation. Updates never
change channels automatically.

## Delivery

Userspace should be delivered through distribution packages—Arch/Omarchy first—
with package signatures and pinned source commits. Kernel work should go
upstream through Asahi/Linux review. Until then, experimental kernels use a
distinct package name and release suffix and coexist with the known-good kernel.

`open-touchid update --check` may report an available package, compatibility,
release notes, and security notices. `open-touchid update --apply` delegates to
the system package manager; it does not implement a second privileged downloader.

## Transaction

1. Verify repository/package signatures and the signed release manifest.
2. Preflight compatibility, free space, recovery password, and known-good boot
   entry.
3. Download and verify without changing the active stack.
4. Stage schema migrations in a copy and validate them.
5. Install components inactive, preserving the previous versions.
6. Activate at a safe session boundary; never swap PAM or the broker beneath an
   authentication request.
7. Run health checks with password auth still active.
8. Mark the release healthy only after broker, UI, fallback, and suspend tests.
9. Roll back automatically on failure.

## Enrollment migrations

Templates remain inside SEP. Linux may persist only opaque enrollment handles,
user labels, policy toggles, and non-sensitive timestamps. Compatible migrations
preserve those handles transactionally. A change to pairing, account isolation,
template format, or trust boundary requires explicit re-enrollment and explains
why before removing the old mapping.

## Recovery

Every stable release documents one offline recovery path that:

- boots the known-good kernel;
- disables Touch ID adapters without deleting enrollment;
- restores password-only PAM and lock-screen behavior;
- rolls back the broker/UI/settings package set;
- produces a privacy-safe diagnostic report.

Recovery steps must be tested from interrupted installs, failed boots, broker
crashes, incompatible schemas, and biometric lockout.
