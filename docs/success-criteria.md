# Release success criteria

Touch ID support is not “working” when Linux merely detects the sensor or
receives a match-looking message. A production recommendation requires every
criterion below.

## Supported authorization surfaces

- Unlock an already-running local desktop session.
- Authenticate local login after encrypted storage is available.
- Authorize `sudo` commands in an interactive terminal.
- Authorize polkit/admin prompts with an unambiguous visible request.
- Provide a narrow hardware-backed approval API that password managers and
  secret stores can use without learning fingerprints or SEP secrets.
- Optionally provide passkey/WebAuthn support through a separately reviewed
  FIDO2 platform-authenticator design.
- Provide polished Omarchy setup and authentication surfaces with finger
  placement guidance, progress, retry, timeout, lockout, and recovery states.

Touch ID authorizes release of an operation or credential. It must never expose
the user's saved passwords, biometric template, fingerprint image, or SEP key
to an application.

## Required security behavior

- Matching and templates remain inside the paired Secure Enclave boundary.
- Every request is bound to the correct user, session, operation, and visible
  prompt; background processes cannot “borrow” an unrelated finger scan.
- UI animation never predicts or fabricates success. Success motion begins only
  after a fresh, operation-bound positive result from the privileged broker.
- Replay, stale-result reuse, confused-deputy attacks, and prompt spoofing are
  covered by the protocol and test suite.
- Rate limits, lockout, cancellation, timeout, lid-close, suspend, hotplug, and
  sensor-error behavior fail closed.
- Enrollment, deletion, and user switching preserve account separation.
- A password or recovery credential remains available and tested.
- The integration has fuzzing, negative tests, a documented threat model, and
  independent security review.

## Password remains required for

- Decrypting the system at boot unless a separate reviewed hardware-backed disk
  unlock design is implemented.
- Recovery, biometric lockout, sensor failure, enrollment changes, and security
  policy changes.
- Any operation whose upstream security policy explicitly requires fresh
  knowledge-factor authentication.

This mirrors the core security principle behind mature biometric systems:
biometrics make strong credentials convenient; they do not erase recovery or
knowledge factors.
