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
VERSION = "0.2.0"
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

    for path in iter_paths(dt_root):
        try:
            relative = path.relative_to(dt_root)
        except ValueError:
            continue
        if any(part in SENSITIVE_DT_NAMES for part in relative.parts):
            continue
        if path.is_dir():
            lowered = path.name.lower()
            if any(term in lowered for term in ("sep", "mesa", "sio", "spi")):
                node_name = "/" + relative.as_posix()
                nodes.append(node_name)
                node_status[node_name] = read_text(path / "status") or "okay (implicit)"
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

    return {
        "sep_node": any("/sep@" in node for node in lowered_nodes)
        or "apple,sep" in lowered_compatibles,
        "sio_node": any("/sio@" in node for node in lowered_nodes),
        "mesa_sensor_node": any("mesa" in node for node in lowered_nodes)
        or "biosensor,mesa" in lowered_compatibles,
        "relevant_nodes": node_set,
        "node_status": {key: node_status[key] for key in sorted(node_status)},
        "relevant_compatibles": compatible_set,
    }


def driver_state(sys_root: Path, driver: str) -> dict[str, object]:
    root = sys_root / "bus" / "platform" / "drivers" / driver
    present = root.exists()
    ignored = {"bind", "uevent", "unbind", "module", "new_id", "remove_id"}
    bound: list[str] = []
    if present:
        try:
            bound = sorted(entry.name for entry in root.iterdir() if entry.name not in ignored)
        except (PermissionError, OSError):
            pass
    return {"present": present, "bound_devices": bound}


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
    *,
    kernel_release: str | None = None,
    machine: str | None = None,
) -> dict[str, object]:
    release = kernel_release or platform.release()
    architecture = machine or platform.machine()
    dt_root = proc_root / "device-tree"
    dt = dt_inventory(dt_root)
    model = read_text(dt_root / "model") or read_text(
        sys_root / "devices" / "virtual" / "dmi" / "id" / "product_name"
    )
    sep_driver = driver_state(sys_root, "apple_sep")
    config = kernel_config(config_path or find_config(proc_root, release))

    apple_silicon = architecture in {"aarch64", "arm64"} and bool(
        model and model.lower().startswith("apple ")
    )
    sep_bound = bool(sep_driver["bound_devices"])
    sensor_exposed = bool(dt["mesa_sensor_node"])

    if not apple_silicon:
        status = "not-apple-silicon"
    elif sensor_exposed:
        status = "sensor-node-exposed-research-only"
    elif sep_bound:
        status = "sep-transport-bound-sensor-not-exposed"
    elif dt["sep_node"]:
        status = "sep-described-but-driver-unbound"
    else:
        status = "sep-not-described"

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
            "drivers": {
                "apple_sep": sep_driver,
                "apple_mailbox": driver_state(sys_root, "apple-mailbox"),
                "apple_sart": driver_state(sys_root, "apple-sart"),
                "apple_sio": driver_state(sys_root, "apple-sio"),
                "apple_spi": driver_state(sys_root, "apple-spi"),
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
            "next_boundary": (
                "Mesa/SIO exposure and the SEP-backed encrypted biometric protocol"
                if apple_silicon and not sensor_exposed
                else "Confirm the sensor transport without reading biometric payloads"
            ),
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
