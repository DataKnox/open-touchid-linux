#!/usr/bin/env python3
"""Privacy-safe Apple Silicon Touch ID readiness probe.

The probe reads public kernel metadata only. It never opens input event nodes,
reserved memory, MMIO, SEP shared memory, or biometric enrollment data.
"""

from __future__ import annotations

import argparse
import gzip
import json
import platform
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

SCHEMA_VERSION = 1
VERSION = "0.3.1"
SENSITIVE_DT_NAMES = {
    "serial-number",
    "system-id",
    "unique-chip-id",
    "wifi-mac-address",
    "bluetooth-mac-address",
}


def read_bytes(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except (FileNotFoundError, PermissionError, IsADirectoryError, OSError):
        return None


def read_text(path: Path) -> str | None:
    data = read_bytes(path)
    if data is None:
        return None
    return data.replace(b"\x00", b" ").decode("utf-8", "replace").strip() or None


def iter_paths(root: Path) -> Iterable[Path]:
    try:
        yield from root.rglob("*")
    except (FileNotFoundError, PermissionError, OSError):
        return


def dt_inventory(dt_root: Path) -> dict[str, object]:
    nodes: list[str] = []
    compatibles: list[str] = []
    node_status: dict[str, str] = {}
    node_dirs: dict[str, Path] = {}

    for path in iter_paths(dt_root):
        try:
            relative = path.relative_to(dt_root)
        except ValueError:
            continue
        if any(part in SENSITIVE_DT_NAMES for part in relative.parts):
            continue
        if relative.parts and relative.parts[0] == "reserved-memory":
            # Reserved-region node names embed physical addresses; only the
            # boolean handoff check below may look at them.
            continue
        if path.is_dir():
            lowered = path.name.lower()
            if any(term in lowered for term in ("sep", "mesa", "sio", "spi")):
                node_name = "/" + relative.as_posix()
                nodes.append(node_name)
                node_status[node_name] = read_text(path / "status") or "okay (implicit)"
                node_dirs[node_name] = path
        elif path.name == "compatible":
            value = read_text(path)
            if value and any(
                term in value.lower()
                for term in ("apple,sep", "biosensor,mesa", "apple,sio", "apple,spi")
            ):
                compatibles.extend(value.split())

    node_set = sorted(set(nodes))
    compatible_set = sorted(set(compatibles))
    lowered_nodes = [node.lower() for node in node_set]
    lowered_compatibles = [value.lower() for value in compatible_set]

    sep_nodes = [node for node in node_set if "/sep@" in node.lower()]
    sio_nodes = [node for node in node_set if "/sio@" in node.lower()]
    sep_dir = node_dirs.get(sep_nodes[0]) if sep_nodes else None
    sio_dir = node_dirs.get(sio_nodes[0]) if sio_nodes else None
    platform = read_text(dt_root / "compatible")
    sep_mailbox = mailbox_unit_address(dt_root, sep_dir)

    return {
        "sep_node": any("/sep@" in node for node in lowered_nodes)
        or "apple,sep" in lowered_compatibles,
        "sep_status": node_status.get(sep_nodes[0]) if sep_nodes else None,
        "sep_alias": alias_target(dt_root, "sep") is not None,
        "sep_firmware_region": bootloader_firmware_handoff(dt_root, sep_dir, "sep-firmware"),
        "sep_boot_manifests": property_present(sep_dir, "local-policy-manifest")
        and property_present(sep_dir, "iboot-manifest"),
        "sep_mailbox": sep_mailbox,
        "sio_node": any("/sio@" in node for node in lowered_nodes),
        "sio_status": node_status.get(sio_nodes[0]) if sio_nodes else None,
        "sio_alias": alias_target(dt_root, "sio") is not None,
        "sio_firmware_params": property_present(sio_dir, "apple,sio-firmware-params"),
        "mesa_sensor_node": any("mesa" in node for node in lowered_nodes)
        or "biosensor,mesa" in lowered_compatibles,
        "platform_compatibles": platform.split() if platform else [],
        "relevant_nodes": node_set,
        "node_status": {key: node_status[key] for key in sorted(node_status)},
        "relevant_compatibles": compatible_set,
    }


def mailbox_unit_address(dt_root: Path, node_dir: Path | None) -> str | None:
    """Resolve the node's first ``mboxes`` phandle to the mailbox unit address.

    Only the unit address (for example ``25e408000``) is returned so the
    interrupt counters for that mailbox can be looked up in /proc/interrupts.
    """
    if node_dir is None:
        return None
    phandle = read_bytes(node_dir / "mboxes")
    if not phandle or len(phandle) < 4:
        return None
    wanted = phandle[:4]
    for candidate in iter_paths(dt_root / "soc"):
        if candidate.name != "phandle" or read_bytes(candidate) != wanted:
            continue
        name = candidate.parent.name
        if "@" in name:
            return name.split("@", 1)[1]
    return None


def mailbox_interrupts(proc_root: Path, unit_address: str | None) -> int | None:
    """Sum the interrupt counters of ``<unit_address>.mbox-*`` lines.

    Zero after a SEP driver has bound means the coprocessor never answered
    the boot message; the stub driver itself logs nothing in that case.
    """
    if unit_address is None:
        return None
    text = read_text(proc_root / "interrupts")
    if text is None:
        return None
    lines = text.splitlines()
    if not lines:
        return None
    # The header names one column per CPU; only those columns are counters.
    # Later columns (chip, hardware IRQ number, trigger, name) are not.
    cpu_columns = sum(1 for field in lines[0].split() if field.startswith("CPU"))
    total = None
    for line in lines[1:]:
        fields = line.split()
        if len(fields) < 3 or not fields[-1].startswith(f"{unit_address}.mbox"):
            continue
        counts = [int(field) for field in fields[1 : 1 + cpu_columns] if field.isdigit()]
        total = (total or 0) + sum(counts)
    return total


def alias_target(dt_root: Path, alias: str) -> str | None:
    """Return the node path an /aliases entry points at, without reading the node."""
    return read_text(dt_root / "aliases" / alias)


def property_present(node_dir: Path | None, name: str) -> bool:
    """Report only whether a property exists; its value is never read."""
    if node_dir is None:
        return False
    try:
        return (node_dir / name).is_file()
    except OSError:
        return False


def bootloader_firmware_handoff(dt_root: Path, node_dir: Path | None, region: str) -> bool:
    """True when the bootloader attached a firmware memory-region to the node.

    m1n1 only creates ``/reserved-memory/<region>@...`` and the node's
    ``memory-region`` phandle when the board device tree carries the matching
    alias. Only names are inspected; addresses and contents are not reported.
    """
    if property_present(node_dir, "memory-region"):
        return True
    try:
        return any(
            entry.is_dir() and entry.name.split("@", 1)[0] == region
            for entry in (dt_root / "reserved-memory").iterdir()
        )
    except (FileNotFoundError, NotADirectoryError, PermissionError, OSError):
        return False


def loadable_module_available(module_root: Path, module: str) -> bool:
    try:
        return any(module_root.rglob(f"{module}.ko*"))
    except (FileNotFoundError, PermissionError, OSError):
        return False


def driver_state(
    sys_root: Path,
    driver: str,
    *,
    module_root: Path | None = None,
    module: str | None = None,
) -> dict[str, object]:
    root = sys_root / "bus" / "platform" / "drivers" / driver
    present = root.exists()
    ignored = {"bind", "uevent", "unbind", "module", "new_id", "remove_id"}
    bound: list[str] = []
    if present:
        try:
            bound = sorted(entry.name for entry in root.iterdir() if entry.name not in ignored)
        except (PermissionError, OSError):
            pass
    return {
        "present": present,
        "bound_devices": bound,
        "loadable_module_available": (
            loadable_module_available(module_root, module)
            if module_root is not None and module is not None
            else False
        ),
    }


def kernel_config(config_path: Path | None) -> dict[str, bool | None]:
    wanted = {
        "CONFIG_APPLE_SEP": None,
        "CONFIG_APPLE_MAILBOX": None,
        "CONFIG_APPLE_SART": None,
        "CONFIG_RUST_APPLE_MAILBOX": None,
    }
    if config_path is None or not config_path.exists():
        return wanted
    try:
        if config_path.suffix == ".gz":
            with gzip.open(config_path, "rt", encoding="utf-8", errors="replace") as handle:
                lines = handle.readlines()
        else:
            lines = config_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except (PermissionError, OSError, gzip.BadGzipFile):
        return wanted

    for raw_line in lines:
        line = raw_line.strip()
        for key in wanted:
            if line == f"{key}=y" or line == f"{key}=m":
                wanted[key] = True
            elif line == f"# {key} is not set":
                wanted[key] = False
    return wanted


def find_config(proc_root: Path, kernel_release: str) -> Path | None:
    candidates = [
        proc_root / "config.gz",
        Path("/boot") / f"config-{kernel_release}",
    ]
    return next((path for path in candidates if path.exists()), None)


def power_button_visible(proc_root: Path) -> bool:
    text = read_text(proc_root / "bus" / "input" / "devices") or ""
    return "power" in text.lower() and "event" in text.lower()


def collect(
    proc_root: Path = Path("/proc"),
    sys_root: Path = Path("/sys"),
    config_path: Path | None = None,
    module_root: Path | None = None,
    *,
    kernel_release: str | None = None,
    machine: str | None = None,
) -> dict[str, object]:
    release = kernel_release or platform.release()
    modules = module_root or Path("/usr/lib/modules") / release
    architecture = machine or platform.machine()
    dt_root = proc_root / "device-tree"
    dt = dt_inventory(dt_root)
    model = read_text(dt_root / "model") or read_text(
        sys_root / "devices" / "virtual" / "dmi" / "id" / "product_name"
    )
    sep_driver = driver_state(sys_root, "apple_sep")
    dcp_driver = driver_state(
        sys_root,
        "apple-dcp",
        module_root=modules,
        module="appledrm",
    )
    simple_framebuffer = driver_state(sys_root, "simple-framebuffer")
    config = kernel_config(config_path or find_config(proc_root, release))

    apple_silicon = architecture in {"aarch64", "arm64"} and bool(
        model and model.lower().startswith("apple ")
    )
    sep_bound = bool(sep_driver["bound_devices"])
    sep_disabled = dt["sep_status"] == "disabled"
    sep_irqs = mailbox_interrupts(proc_root, dt["sep_mailbox"])
    sensor_exposed = bool(dt["mesa_sensor_node"])
    display_fallback = not bool(dcp_driver["bound_devices"]) and bool(
        simple_framebuffer["bound_devices"]
    )

    if not apple_silicon:
        status = "not-apple-silicon"
    elif sensor_exposed:
        status = "sensor-node-exposed-research-only"
    elif sep_bound:
        status = "sep-transport-bound-sensor-not-exposed"
    elif dt["sep_node"] and sep_disabled:
        status = "sep-disabled-in-device-tree"
    elif dt["sep_node"]:
        status = "sep-described-but-driver-unbound"
    else:
        status = "sep-not-described"

    warnings: list[str] = []
    if display_fallback:
        warnings.append(
            "apple-dcp-unbound-display-using-simple-framebuffer; "
            "expect degraded display performance"
        )
    if dt["sep_node"] and not sep_disabled and not sep_bound and not dt["sep_firmware_region"]:
        warnings.append(
            "sep-node-enabled-without-firmware-region; the bootloader did not "
            "attach sepfw, so check that the board device tree has a sep alias"
        )
    if sep_bound and sep_irqs == 0:
        warnings.append(
            "sep-bound-but-mailbox-silent; apple_sep sent its boot message but "
            "the SEP mailbox has raised no interrupts, so the SEP never answered"
        )

    if not apple_silicon:
        next_boundary = "Confirm the sensor transport without reading biometric payloads"
    elif sensor_exposed:
        next_boundary = "Confirm the sensor transport without reading biometric payloads"
    elif sep_disabled and not sep_bound:
        next_boundary = (
            "Board device tree: add the sep alias and enable the SEP node so the "
            "bootloader passes firmware, then collect the SEP endpoint inventory"
        )
    else:
        next_boundary = "Mesa/SIO exposure and the SEP-backed encrypted biometric protocol"

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "privacy": {
            "contains_biometric_data": False,
            "contains_serial_numbers": False,
            "safe_to_attach_to_public_issue_after_review": True,
        },
        "system": {
            "architecture": architecture,
            "kernel_release": release,
            "model": model,
            "apple_silicon": apple_silicon,
        },
        "kernel": {
            "config": config,
            "sep_mailbox_interrupts": sep_irqs,
            "drivers": {
                "apple_sep": sep_driver,
                "apple_dcp": dcp_driver,
                "apple_mailbox": driver_state(sys_root, "apple-mailbox"),
                "apple_sart": driver_state(sys_root, "apple-sart"),
                "apple_sio": driver_state(
                    sys_root,
                    "apple-sio",
                    module_root=modules,
                    module="apple-sio",
                ),
                "apple_spi": driver_state(sys_root, "apple-spi"),
                "simple_framebuffer": simple_framebuffer,
            },
        },
        "hardware": {
            "device_tree": dt,
            "power_button_input_visible": power_button_visible(proc_root),
        },
        "userspace": {
            "fprintd_installed": shutil.which("fprintd-enroll") is not None,
        },
        "assessment": {
            "status": status,
            "touchid_authentication_available": False,
            "warnings": warnings,
            "next_boundary": next_boundary,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect privacy-safe Apple Silicon Touch ID readiness metadata."
    )
    parser.add_argument("--proc-root", type=Path, default=Path("/proc"), help=argparse.SUPPRESS)
    parser.add_argument("--sys-root", type=Path, default=Path("/sys"), help=argparse.SUPPRESS)
    parser.add_argument("--config", type=Path, help="Override the kernel config path.")
    parser.add_argument("--compact", action="store_true", help="Emit compact JSON.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = collect(args.proc_root, args.sys_root, args.config)
    print(json.dumps(report, indent=None if args.compact else 2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
