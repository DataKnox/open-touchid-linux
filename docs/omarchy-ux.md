# Omarchy Touch ID UX specification

This UI is a future consumer of a reviewed privileged broker. QML, the lock
screen, and ordinary applications must never communicate with SEP or the sensor
directly.

## Trust boundary

```text
Omarchy UI ── operation + request ID ──> privileged broker ──> kernel/SEP
Omarchy UI <── signed state transition ─ privileged broker <── match result
```

The UI may display state, guidance, and recovery choices. It may not decide
that a match succeeded, cache a success, reuse one operation's success for
another, or receive biometric material.

## Setup flow

1. **Preflight** — explain supported uses and mandatory password fallback;
   verify the sensor, SEP service, broker, and recovery credential.
2. **Fresh password confirmation** — authorize enrollment with the existing
   knowledge factor.
3. **Choose finger** — name a slot such as “Right index”; do not infer identity
   from the finger name.
4. **Enroll** — show touch, hold, lift, and reposition guidance driven only by
   broker states. A segmented ring shows accepted enrollment stages, not an
   estimated timer.
5. **Verify** — require a separate match after enrollment.
6. **Choose uses** — unlock, local login, `sudo`, and polkit are independent
   toggles with plain-language risk descriptions.
7. **Recovery check** — confirm password fallback before completing setup.

## System Security → Touch ID panel

The settings surface presents Touch ID as a system capability, not a one-time
installer script.

- Master switch: **Use Touch ID on this account**.
- Finger list with user-chosen names such as “Right index” and “Left thumb.”
- Actions for **Add finger**, **Verify**, **Rename**, and **Remove**.
- Separate switches for session unlock, local login, `sudo`, polkit/admin
  prompts, password-manager approvals, and passkeys when that surface is ready.
- Persistent plain-language status for sensor health, SEP availability, last
  successful verification, lockout, and password fallback.

Adding or removing a finger and changing the master switch requires a fresh
password confirmation. A user can manage only that user's enrollment namespace;
administrator status does not grant access to another user's biometric records.

The Linux settings database stores only an opaque SEP enrollment identifier,
the user-chosen display name, enabled uses, and non-sensitive timestamps. The
template and sensor pairing material remain inside SEP-controlled storage.

## Finger enrollment animation

The enrollment surface centers a stylized fingerprint made of independently
addressable ridge segments. It is guidance, not a rendering of the user's real
fingerprint.

- On `awaiting-touch`, the next neutral ridge segment breathes slowly.
- On `stage-accepted`, the broker-acknowledged segment fills with the active
  theme color over 180 ms and remains filled.
- On `lift-finger`, the glyph moves upward by at most 6 px while a “Lift and
  reposition” label appears; reduced-motion mode uses opacity only.
- On `partial`, `too-fast`, or `move-finger`, no progress is added. The relevant
  edge of the generic glyph is highlighted with concrete text guidance.
- On completion, the accepted segments form one 240 ms sweep followed by a
  separate verification step. Completion animation never substitutes for
  verification.

The illustration must never be generated from, resemble, or encode captured
fingerprint data. Enrollment stage count and guidance come from the secure
broker; the UI does not invent progress from time or touch duration.

## Authentication state machine

| State | Visual behavior | Exit conditions |
|---|---|---|
| `idle` | Static fingerprint mark; no pulsing claim that a reader is active | Broker opens an operation-bound request |
| `awaiting-finger` | Slow 1.6 s breathing ring | Touch, cancel, timeout, lid close, or broker error |
| `reading` | Ring tightens over 180 ms; subtle haptic/audio cue if enabled | Broker reports progress or final result |
| `reposition` | Highlight a different ring segment and show one concrete instruction | New accepted stage, cancel, or timeout |
| `matched` | Green/active-theme sweep lasting 220 ms, then dismiss | Only a fresh positive broker result |
| `not-matched` | Neutral lateral nudge, 160 ms; never flash alarming red for a normal retry | Retry budget, fallback, or cancel |
| `timeout` | Motion stops; show Retry and Use password | User choice |
| `locked-out` | Locked static icon plus broker-provided retry time; password fallback prominent | Policy timer or recovery auth |
| `error` | Plain diagnosis and error code; no infinite spinner | Retry, fallback, or diagnostics |

## Motion rules

- Respect the desktop reduced-motion setting. Reduced mode uses opacity and
  color transitions of at most 120 ms with no translation, scale, or looping.
- Never run success motion speculatively while a match is pending.
- Keep loops low-frequency and pause them when the surface is hidden.
- Animation cannot delay cancellation, fallback, or security state changes.
- Theme colors must retain readable contrast; color is never the only status
  signal.
- Enrollment progress advances only for stages acknowledged by SEP.

## Prompt integrity

Every prompt shows the requesting surface and operation: for example,
“Unlock session,” “Authorize `pacman` through sudo,” or “Allow Password Manager
to release github.com credentials.” Generic “Touch sensor” prompts are not
acceptable for privileged operations.

The broker binds the result to user ID, session ID, request ID, operation digest,
prompt creation time, and a short expiry. The UI displays those broker-provided
details but cannot edit them.

## Failure and recovery

- Password fallback is always reachable with keyboard-only navigation.
- Three ordinary non-matches should suggest repositioning, not imply an attack.
- Rate limits and hard lockout come from the secure policy, never a QML counter.
- Suspend, lid close, user switch, compositor restart, broker restart, or screen
  removal cancels the request and invalidates late results.
- Setup remains incomplete until enrollment, verification, and recovery checks
  all succeed.

## Required test matrix

- Correct finger, wrong finger, partial touch, rapid touch/lift, and wet sensor.
- Cancel and password fallback from every nonterminal state.
- Lid close and suspend during every active state.
- Simultaneous lock-screen and polkit requests.
- Stale, duplicated, reordered, malformed, and cross-user broker messages.
- Reduced motion, screen reader labels, high contrast, keyboard-only control,
  and multiple display scales.
- Broker, compositor, and shell crashes with a request in flight.
