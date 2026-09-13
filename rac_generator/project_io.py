from __future__ import annotations

import json
import math
from dataclasses import asdict, fields
from pathlib import Path

from .file_io import atomic_text_file
from .models import DeviceRecord, ExtraParameter


PROJECT_FORMAT = "rac-generator-project"
PROJECT_VERSION = 1
FORM_FIELDS = (
    "site", "device_prefix", "engine", "trunk", "controller_part", "template", "definition",
    "network_type", "instance_mode", "fqr_mode", "dhcp", "subnet", "router",
    "prefix", "separator", "start", "end", "digits", "start_address", "served_by",
    "manufacturer", "inlet", "maxflow", "clgmin", "htgmin",
)
INTEGER_FIELDS = {"mac_address", "ip_controller_number", "instance", "inlet_size"}
FLOAT_FIELDS = {"sa_area", "sa_kfactor", "clg_maxflow", "clg_minflow", "htg_minflow"}
BOOLEAN_FIELDS = {"dhcp_enabled", "box_heat", "supplemental_heat"}


def project_data(settings: dict, records: list[DeviceRecord]) -> dict:
    return {
        "format": PROJECT_FORMAT,
        "version": PROJECT_VERSION,
        "settings": dict(settings),
        "records": [asdict(record) for record in records],
    }


def _record_from_data(data: object, number: int) -> DeviceRecord:
    prefix = f"Device {number}"
    allowed = {item.name for item in fields(DeviceRecord)}
    if not isinstance(data, dict) or set(data) - allowed:
        raise ValueError(f"{prefix}: unrecognized device fields or invalid device data.")
    values = dict(data)
    for name, value in values.items():
        if name in INTEGER_FIELDS:
            valid = value is None or type(value) is int
        elif name in FLOAT_FIELDS:
            valid = value is None or (type(value) in (int, float) and math.isfinite(value))
        elif name in BOOLEAN_FIELDS:
            valid = value is None or type(value) is bool
        elif name == "preserve_imported_values":
            valid = type(value) is bool
        elif name == "parameters":
            valid = isinstance(value, dict)
        elif name == "extra_parameters":
            valid = isinstance(value, list)
        else:
            valid = isinstance(value, str)
        if not valid:
            raise ValueError(f"{prefix}: invalid value for {name}.")
    parameters = []
    seen = set()
    for item in values.get("extra_parameters", []):
        if not isinstance(item, dict) or set(item) != {"name", "attribute_id", "attribute_type", "value"}:
            raise ValueError(f"{prefix}: invalid additional parameter.")
        if not all(isinstance(value, str) for value in item.values()):
            raise ValueError(f"{prefix}: additional parameter values must be text.")
        key = (item["attribute_id"], item["attribute_type"])
        if not all(key) or key in seen:
            raise ValueError(f"{prefix}: missing or duplicate additional parameter identifier.")
        seen.add(key)
        parameters.append(ExtraParameter(**item))
    values["extra_parameters"] = parameters
    return DeviceRecord(**values)


def decode_project(data: object) -> tuple[dict, list[DeviceRecord]]:
    if not isinstance(data, dict) or data.get("format") != PROJECT_FORMAT:
        raise ValueError("This is not a RAC Generator project file. Use Import Schedule for an SCT CSV or RAC workbook.")
    if type(data.get("version")) is not int or data["version"] != PROJECT_VERSION:
        raise ValueError("This project uses an unsupported file version. Open it with the version of RAC Generator that saved it.")
    if set(data) - {"format", "version", "settings", "records"}:
        raise ValueError("The project contains unrecognized data and cannot be opened without losing it.")
    settings = data.get("settings")
    if not isinstance(settings, dict) or set(settings) - (set(FORM_FIELDS) | {"existing_equipment"}):
        raise ValueError("The project contains invalid or unrecognized editing settings.")
    for name, value in settings.items():
        if (name == "dhcp" and type(value) is not bool) or (name != "dhcp" and not isinstance(value, str)):
            raise ValueError(f"Invalid project setting: {name}.")
    choices = {
        "network_type": {"MSTP", "IP"},
        "instance_mode": {"Generate using workbook convention", "Leave blank for SCT"},
        "fqr_mode": {"Device Name (SCT recommended)", "Custom workbook convention"},
    }
    for name, options in choices.items():
        if name in settings and settings[name] not in options:
            raise ValueError(f"Unsupported project setting: {name}.")
    rows = data.get("records")
    if not isinstance(rows, list):
        raise ValueError("The project must contain a device list.")
    return dict(settings), [_record_from_data(row, i) for i, row in enumerate(rows, start=1)]


def save_project(path: str | Path, settings: dict, records: list[DeviceRecord]) -> None:
    data = project_data(settings, records)
    decode_project(data)
    # Incomplete forms are intentional drafts. Only file integrity is validated here.
    contents = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    with atomic_text_file(path) as handle:
        handle.write(contents)


def _reject_constant(value):
    raise ValueError(f"Invalid numeric value in project: {value}.")


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate field in project: {key}.")
        result[key] = value
    return result


def load_project(path: str | Path) -> tuple[dict, list[DeviceRecord]]:
    with Path(path).open(encoding="utf-8-sig") as handle:
        data = json.load(handle, parse_constant=_reject_constant, object_pairs_hook=_unique_keys)
    return decode_project(data)
