from __future__ import annotations

import csv
import shutil
from copy import copy
from pathlib import Path
from typing import Iterable

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .logic import VAV_SD_PARAMETERS
from .models import DeviceRecord


BASE_RAC_HEADERS = [
    "RAC-4096", "RAC-4112", "RAC-4128", "RAC-4144", "RAC-4160", "RAC-4166",
    "RAC-4170", "RAC-4176", "RAC-4192", "RAC-4208", "RAC-4224", "RAC-4240",
    "RAC-4256", "RAC-4272", "RAC-4288", "RAC-4304", "RAC-4311", "RAC-4320",
    "RAC-4336", "RAC-4352", "RAC-4368", "RAC-4384", "RAC-4400", "RAC-4416",
    "RAC-4432", "RAC-4448",
]


BASE_FIELD_NAMES = [
    "Site/Building/Floor\n(Required)",
    "Room Number\n(Optional)",
    "Leaf Space (e.g. Room)\n(Required)",
    "Device Name\n(Required)",
    "Device FQR Reference \n(Required)",
    "Device Description\n(Optional)",
    "Equipment Name\n(Required)",
    "Served By Equipment Name\n(Optional)",
    "Controller Part #\n(Optional)",
    "Engine Name\n(Required)",
    "Trunk Name\n(Required)",
    "Controller Host Name \n(Future)",
    "JCI MAC  Address",
    "IP Controller Number",
    "ZIGBEE PAN Offset",
    "Instance # (BACoid)",
    "N2Address",
    "DHCP Enabled ",
    "IP Address ",
    "Subnet Mask",
    "IP Router",
    "ETH-1\n(Optional)",
    "ETH-2\n(Optional)",
    "Equipment Definition Name",
    "Controller Template Name",
    None,
]


def _record_base_values(record: DeviceRecord) -> list[object]:
    return [
        record.site_hierarchy,
        record.room_number,
        record.leaf_space,
        record.device_name,
        record.fqr,
        record.device_description,
        record.equipment_name,
        record.served_by,
        record.controller_part,
        record.engine_name,
        record.trunk_name,
        record.controller_host_name,
        record.mac_address,
        record.ip_controller_number,
        record.zigbee_pan_offset,
        record.instance,
        record.n2_address,
        record.dhcp_enabled,
        record.ip_address,
        record.subnet_mask,
        record.ip_router,
        record.eth1,
        record.eth2,
        record.equipment_definition,
        record.controller_template,
    ]


def _parameters_in_use(records: Iterable[DeviceRecord]):
    records = list(records)
    used = []
    for name, attr_id, attr_type, field_name in VAV_SD_PARAMETERS:
        if any(getattr(r, field_name) is not None for r in records):
            used.append((name, attr_id, attr_type, field_name))
    return used


def export_rac_csv(path: str | Path, records: list[DeviceRecord]) -> None:
    """Create an SCT Rapid Archive CSV including the six RAC header rows."""
    path = Path(path)
    params = _parameters_in_use(records)
    total_cols = 25 + max(1, len(params))

    rows: list[list[object]] = []

    row1 = BASE_RAC_HEADERS[:25] + ["RAC-4448"]
    if len(params) > 1:
        row1 += [None] * (len(params) - 1)
    rows.append(row1)

    rows.append(["v3"] + [None] * (total_cols - 1))

    row3 = [None] * total_cols
    row3[0] = "Space Information"
    row3[3] = "Network / Equipment Tree Information"
    row3[9] = "Network Information (MSTP and IP)"
    row3[23] = "Definitions and Templates"
    row3[25] = "Parameters"
    rows.append(row3)

    row4 = BASE_FIELD_NAMES[:25]
    if params:
        row4 += [p[0] for p in params]
    else:
        row4 += [None]
    rows.append(row4)

    row5 = [None] * total_cols
    row6 = [None] * total_cols
    for idx, param in enumerate(params, start=25):
        row5[idx] = param[1]
        row6[idx] = param[2]
    row5[3] = "Attribute ID"
    row6[3] = "Attribute Type"
    rows.extend([row5, row6])

    for record in records:
        values = _record_base_values(record)
        if params:
            values += [getattr(record, p[3]) for p in params]
        else:
            values += [None]
        rows.append(values)

    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerows(rows)


def _copy_row_style(source_ws, target_ws, source_row: int, target_row: int, max_col: int) -> None:
    for col in range(1, max_col + 1):
        src = source_ws.cell(source_row, col)
        dst = target_ws.cell(target_row, col)
        if src.has_style:
            dst._style = copy(src._style)
        if src.number_format:
            dst.number_format = src.number_format
        if src.alignment:
            dst.alignment = copy(src.alignment)
        if src.font:
            dst.font = copy(src.font)
        if src.fill:
            dst.fill = copy(src.fill)
        if src.border:
            dst.border = copy(src.border)


def export_rac_workbook(
    output_path: str | Path,
    template_path: str | Path,
    records: list[DeviceRecord],
) -> None:
    """Copy the supplied template and fill the RAC sheet plus a generated scratchpad."""
    output_path = Path(output_path)
    template_path = Path(template_path)
    shutil.copy2(template_path, output_path)

    wb = load_workbook(output_path)
    rac = wb["Rapid Archive Schedule"]

    params = _parameters_in_use(records)
    total_cols = 25 + max(1, len(params))

    # Clear old generated data area while leaving the template header intact.
    for row in rac.iter_rows(min_row=7, max_row=max(rac.max_row, 7), min_col=1, max_col=max(rac.max_column, total_cols)):
        for cell in row:
            cell.value = None

    # Parameter headers start at Z (column 26).
    rac.cell(1, 26).value = "RAC-4448"
    rac.cell(3, 26).value = "Parameters"
    for idx, param in enumerate(params, start=26):
        rac.cell(1, idx).value = "RAC-4448" if idx == 26 else None
        rac.cell(4, idx).value = param[0]
        rac.cell(5, idx).value = param[1]
        rac.cell(6, idx).value = param[2]

    if not params:
        rac.cell(4, 26).value = None
        rac.cell(5, 26).value = None
        rac.cell(6, 26).value = None

    # Clear any stale parameter headers to the right.
    for col in range(26 + len(params), max(rac.max_column, 26 + len(params)) + 1):
        if col > 26:
            for row in (1, 4, 5, 6):
                rac.cell(row, col).value = None

    for row_index, record in enumerate(records, start=7):
        values = _record_base_values(record)
        for col, value in enumerate(values, start=1):
            rac.cell(row_index, col).value = value
        for param_index, param in enumerate(params, start=26):
            rac.cell(row_index, param_index).value = getattr(record, param[3])

    # Build a richer engineering scratchpad without overwriting the reference scratchpad.
    if "Generated Scratchpad" in wb.sheetnames:
        del wb["Generated Scratchpad"]
    scratch = wb.create_sheet("Generated Scratchpad", 5)

    scratch_headers = [
        "Site/Building/Floor", "Room Number", "Leaf Space", "Device Name", "Device FQR Reference",
        "Device Description", "Equipment Name", "Mechanical Drawing", "Served By Equipment Name",
        "JCI Ctrl Dwg No.", "Controller Part #", "Engine Name", "Trunk Name", "Controller Host Name",
        "JCI MAC Address", "IP Controller Number", "ZigBee PAN Offset", "Instance # (BACoid)",
        "N2 Address", "DHCP Enabled", "IP Address", "Subnet Mask", "IP Router", "ETH-1", "ETH-2",
        "Equipment Definition Name", "Controller Template Name", "Sensor Code No.", "Box Heat",
        "Supplemental Heat", "Inlet Size", "SA-AREA", "SA-KFACTOR", "CLG-MAXFLOW",
        "CLGOCC-MINFLOW", "HTGOCC-MINFLOW", "Comments",
    ]

    for col, header in enumerate(scratch_headers, start=1):
        cell = scratch.cell(1, col, header)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F4E78")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for row_index, record in enumerate(records, start=2):
        values = [
            record.site_hierarchy, record.room_number, record.leaf_space, record.device_name, record.fqr,
            record.device_description, record.equipment_name, record.mechanical_drawing, record.served_by,
            record.jci_ctrl_dwg_no, record.controller_part, record.engine_name, record.trunk_name,
            record.controller_host_name, record.mac_address, record.ip_controller_number,
            record.zigbee_pan_offset, record.instance, record.n2_address, record.dhcp_enabled,
            record.ip_address, record.subnet_mask, record.ip_router, record.eth1, record.eth2,
            record.equipment_definition, record.controller_template, record.sensor_code_no, record.box_heat,
            record.supplemental_heat, record.inlet_size, record.sa_area, record.sa_kfactor,
            record.clg_maxflow, record.clg_minflow, record.htg_minflow, record.comments,
        ]
        for col, value in enumerate(values, start=1):
            scratch.cell(row_index, col).value = value

    scratch.freeze_panes = "A2"
    scratch.auto_filter.ref = f"A1:{get_column_letter(len(scratch_headers))}{max(1, len(records) + 1)}"
    for col in range(1, len(scratch_headers) + 1):
        width = 18
        if col in (1, 3, 4, 5, 6, 7, 9, 26, 27, 37):
            width = 24
        scratch.column_dimensions[get_column_letter(col)].width = width
    scratch.row_dimensions[1].height = 45

    wb.save(output_path)
