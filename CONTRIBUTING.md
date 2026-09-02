# Contributing

Start with a probe report and state the exact machine model and kernel commit.
Do not submit biometric captures, firmware, keys, templates, or reverse-
engineered material that you are not legally permitted to share.

## Development

```bash
python3 -m unittest discover -s tests -v
python3 src/open_touchid_probe.py
```

Changes to kernel instrumentation should identify the exact upstream commit,
pass `git diff --check`, and explain why every logged field is non-secret.

Protocol claims need a reproducible trace description and should distinguish
observation from inference. Authentication integration is out of scope until
the transport and SEP service phases have passed their security gates.
