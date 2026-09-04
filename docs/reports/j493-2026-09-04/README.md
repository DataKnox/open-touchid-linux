# J493 (M2 MacBook Pro 13-inch, 2022) test-kernel boot, 2026-09-04

Raw artifacts behind the [M2 boot result](../../build-validation.md#j493-m2-boot-result),
reviewed for privacy: no serial numbers, MAC addresses, keys, firmware, or
biometric data. Physical memory ranges and partition UUIDs are redacted.

| File | What it is |
|---|---|
| `uname.txt` | kernel release of the test boot (`7.1.6-1-1-touchid`) |
| `cmdline-test-entry.txt` | command line of the test GRUB entry (no `initcall_blacklist`) |
| `probe-test-kernel.json` | probe 0.3.0 output on the test kernel: `apple_sep` bound, alias and firmware handoff true |
| `probe-stock-kernel-sep-enabled-blacklisted.json` | probe 0.3.1 output on the stock kernel booted with the same device tree and `initcall_blacklist=__apple_sep_init`, for comparison |
| `interrupts-sep-mailbox.txt` | `/proc/interrupts` lines for the SEP mailbox after more than 75 s on the test kernel: all zero |
| `sep-node-properties.txt` | property names of the SEP node as seen on the test boot |
| `dmesg-sep-extended.txt` | every kernel log line mentioning the SEP device or its mailbox on the test boot |

Machine: `apple,j493` / `apple,t8112`, Omarchy 4.0.2 on Asahi Alarm, m1n1 v1.6.1,
U-Boot 2026.04, macOS firmware 13.5. Test kernel built from tag `asahi-7.1.6-1`
with the stock config (BTF off) plus patches 0001 and 0002.
