from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from .logic import build_dependency_levels, normalize_existing_equipment, split_served_by
from .models import DeviceRecord


def validate_project_for_sct(
    records: Iterable[DeviceRecord],
    existing_equipment: str | Iterable[str] = (),
) -> tuple[list[str], list[str]]:
    """SCT-aware preflight validation, including legitimate multi-equipment controllers."""
    records = list(records)
    existing = normalize_existing_equipment(existing_equipment)
    errors: list[str] = []
    warnings: list[str] = []
    if not records:
        return ["No devices have been generated."], []

    required = {
        "Site/Building/Floor": "site_hierarchy",
        "Device Name": "device_name",
        "Device FQR Reference": "fqr",
        "Equipment Name": "equipment_name",
        "Engine Name": "engine_name",
        "Trunk Name": "trunk_name",
        "Controller Template Name": "controller_template",
    }
    for index, record in enumerate(records, start=1):
        label = record.equipment_name or record.device_name or f"row {index}"
        for display, field_name in required.items():
            if not str(getattr(record, field_name) or "").strip():
                errors.append(f"{label}: {display} is required for this generator's SCT workflow.")
        if not record.leaf_space.strip():
            warnings.append(
                f"{label}: Leaf Space is blank. This is only expected when the equipment serves the whole campus/site."
            )
        if record.mac_address is not None and not 4 <= record.mac_address <= 127:
            errors.append(f"{label}: JCI MS/TP MAC address must be between 4 and 127.")
        if record.instance is not None and not 0 <= record.instance <= 4_194_302:
            errors.append(f"{label}: BACnet Instance must be between 0 and 4,194,302.")

    # Equipment names identify Equipment objects and must be unique.
    by_equipment: dict[str, list[DeviceRecord]] = defaultdict(list)
    for record in records:
        if record.equipment_name.strip():
            by_equipment[record.equipment_name.strip()].append(record)
    for name, rows in by_equipment.items():
        if len(rows) > 1:
            errors.append(f"Duplicate Equipment Name '{name}'. Equipment names should uniquely identify Equipment objects.")

    # A controller may legitimately appear in multiple RAC rows when it controls multiple equipment objects.
    by_device: dict[str, list[DeviceRecord]] = defaultdict(list)
    for record in records:
        if record.device_name.strip():
            by_device[record.device_name.strip()].append(record)
    for device, rows in by_device.items():
        if len(rows) <= 1:
            continue
        equipment_names = {r.equipment_name.strip() for r in rows}
        same_fqr = len({r.fqr for r in rows}) == 1
        same_instance = len({r.instance for r in rows}) == 1
        same_location = len({(r.engine_name, r.trunk_name, r.mac_address, r.ip_controller_number) for r in rows}) == 1
        if len(equipment_names) == len(rows) and same_fqr and same_instance and same_location:
            warnings.append(
                f"Controller '{device}' appears in {len(rows)} rows for multiple equipment objects. This is supported by SCT; confirm the pairings are intentional."
            )
        else:
            errors.append(
                f"Duplicate Device Name '{device}' has inconsistent FQR/instance/network data. Repeated controller rows must describe the same physical controller."
            )

    # FQR/Instance duplicates are only acceptable within the same repeated controller.
    for attr, label in (("fqr", "FQR"), ("instance", "BACnet Instance")):
        values: dict[object, set[str]] = defaultdict(set)
        for record in records:
            value = getattr(record, attr)
            if value in (None, ""):
                continue
            values[value].add(record.device_name.strip())
        for value, devices in values.items():
            if len(devices) > 1:
                errors.append(f"Duplicate {label} '{value}' is used by multiple controllers: {', '.join(sorted(devices))}.")

    seen_mac: dict[tuple[str, str, int], str] = {}
    for record in records:
        if record.mac_address is None:
            continue
        key = (record.engine_name.strip(), record.trunk_name.strip(), record.mac_address)
        previous = seen_mac.get(key)
        if previous and previous != record.device_name:
            errors.append(
                f"Duplicate MS/TP address {record.mac_address} on {record.engine_name}/{record.trunk_name}: {previous} and {record.device_name}."
            )
        else:
            seen_mac[key] = record.device_name

    generated_names = set(by_equipment)
    for record in records:
        for parent in split_served_by(record.served_by):
            if parent not in generated_names and parent not in existing:
                errors.append(
                    f"{record.equipment_name}: Served By '{parent}' is neither generated by this project nor listed as already existing in SCT."
                )

    try:
        build_dependency_levels(records, existing)
    except ValueError as exc:
        errors.append(str(exc))

    if any(r.ip_controller_number is not None for r in records):
        warnings.append(
            "IP controller support is still partial: verify DHCP/static IP settings and IP addresses in SCT before saving the Rapid Archive wizard."
        )
    if any(r.equipment_definition.strip() for r in records):
        warnings.append(
            "Equipment Definition Name is reference-only in the RAC schedule. Verify each Controller Template's Definition Link in SCT."
        )

    return _dedupe(errors), _dedupe(warnings)


def _dedupe(values: Iterable[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
