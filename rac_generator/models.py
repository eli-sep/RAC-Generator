from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProjectDefaults:
    site_hierarchy: str = ""
    device_prefix: str = "MR-"
    engine_name: str = ""
    trunk_name: str = ""
    controller_part: str = ""
    controller_template: str = ""
    equipment_definition: str = ""
    network_type: str = "MSTP"  # MSTP or IP
    generate_instance: bool = True
    dhcp_enabled: bool = True
    subnet_mask: str = ""
    ip_router: str = ""


@dataclass
class EquipmentGroup:
    equipment_prefix: str
    separator: str
    start: int
    end: int
    digits: int = 2
    start_address: int = 1
    served_by: str = ""
    manufacturer: str = "Generic"
    inlet_size: Optional[int] = None
    clg_maxflow: Optional[float] = None
    clg_minflow: Optional[float] = None
    htg_minflow: Optional[float] = None


@dataclass
class DeviceRecord:
    site_hierarchy: str = ""
    room_number: str = ""
    leaf_space: str = ""
    device_name: str = ""
    fqr: str = ""
    device_description: str = ""
    equipment_name: str = ""
    served_by: str = ""
    controller_part: str = ""
    engine_name: str = ""
    trunk_name: str = ""
    controller_host_name: str = ""
    mac_address: Optional[int] = None
    ip_controller_number: Optional[int] = None
    zigbee_pan_offset: str = ""
    instance: Optional[int] = None
    n2_address: str = ""
    dhcp_enabled: Optional[bool] = None
    ip_address: str = ""
    subnet_mask: str = ""
    ip_router: str = ""
    eth1: str = ""
    eth2: str = ""
    equipment_definition: str = ""
    controller_template: str = ""

    # Engineering/reference fields from the scratchpad.
    mechanical_drawing: str = ""
    jci_ctrl_dwg_no: str = ""
    sensor_code_no: str = ""
    box_heat: Optional[bool] = None
    supplemental_heat: Optional[bool] = None
    manufacturer: str = "Generic"
    inlet_size: Optional[int] = None
    sa_area: Optional[float] = None
    sa_kfactor: Optional[float] = None
    clg_maxflow: Optional[float] = None
    clg_minflow: Optional[float] = None
    htg_minflow: Optional[float] = None
    comments: str = ""

    # Future/dynamic parameter support.
    parameters: dict[str, object] = field(default_factory=dict)
