from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .exporters import export_rac_csv, export_rac_workbook
from .logic import (
    find_duplicate_values,
    generate_group_records,
    load_manufacturer_data,
    recalculate_record,
)
from .models import DeviceRecord, EquipmentGroup, ProjectDefaults


def resource_path(relative: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / relative


class RACGeneratorApp(tk.Tk):
    DISPLAY_COLUMNS = [
        ("equipment_name", "Equipment", 110),
        ("device_name", "Device", 130),
        ("room_number", "Room", 80),
        ("leaf_space", "Leaf Space", 150),
        ("mac_address", "MAC", 60),
        ("ip_controller_number", "IP Ctrl #", 70),
        ("instance", "Instance", 90),
        ("fqr", "FQR", 100),
        ("manufacturer", "Manufacturer", 140),
        ("inlet_size", "Inlet", 60),
        ("sa_area", "SA Area", 70),
        ("sa_kfactor", "K Factor", 70),
        ("clg_maxflow", "Max CFM", 75),
        ("clg_minflow", "Clg Min", 70),
        ("htg_minflow", "Htg Min", 70),
        ("controller_template", "Template", 105),
    ]

    EDITABLE_COLUMNS = {
        "equipment_name", "device_name", "room_number", "leaf_space", "mac_address",
        "ip_controller_number", "manufacturer", "inlet_size", "clg_maxflow",
        "clg_minflow", "htg_minflow", "controller_template",
    }

    def __init__(self):
        super().__init__()
        self.title("RAC Generator")
        self.geometry("1220x760")
        self.minsize(950, 620)

        self.template_path = resource_path("resources/RAC Schedule_Template_Updated.xlsx")
        try:
            self.manufacturer_data = load_manufacturer_data(self.template_path)
        except Exception as exc:
            self.manufacturer_data = {"Generic": {}}
            messagebox.showwarning(
                "Template warning",
                f"Could not load manufacturer data from the RAC template.\n\n{exc}",
            )

        self.records: list[DeviceRecord] = []
        self._editor: tk.Entry | None = None

        self._build_style()
        self._build_ui()

    def _build_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Title.TLabel", font=("TkDefaultFont", 18, "bold"))
        style.configure("Section.TLabelframe.Label", font=("TkDefaultFont", 11, "bold"))
        style.configure("Treeview", rowheight=26)

    def _build_ui(self):
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="RAC Generator", style="Title.TLabel").pack(anchor="w", pady=(0, 8))

        notebook = ttk.Notebook(outer)
        notebook.pack(fill="both", expand=True)

        self.project_tab = ttk.Frame(notebook, padding=12)
        self.group_tab = ttk.Frame(notebook, padding=12)
        self.devices_tab = ttk.Frame(notebook, padding=12)
        notebook.add(self.project_tab, text="1. Project & Network")
        notebook.add(self.group_tab, text="2. Equipment Group")
        notebook.add(self.devices_tab, text="3. Devices & Export")

        self._build_project_tab()
        self._build_group_tab()
        self._build_devices_tab()

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(outer, textvariable=self.status_var, anchor="w").pack(fill="x", pady=(8, 0))

    def _labeled_entry(self, parent, label, row, col, variable, width=22, colspan=1):
        ttk.Label(parent, text=label).grid(row=row, column=col, sticky="w", padx=6, pady=(6, 2))
        entry = ttk.Entry(parent, textvariable=variable, width=width)
        entry.grid(row=row + 1, column=col, columnspan=colspan, sticky="ew", padx=6, pady=(0, 8))
        return entry

    def _build_project_tab(self):
        frame = ttk.LabelFrame(self.project_tab, text="Project / Network Defaults", style="Section.TLabelframe", padding=10)
        frame.pack(fill="x")
        for col in range(4):
            frame.columnconfigure(col, weight=1, uniform="project")

        self.site_var = tk.StringVar()
        self.device_prefix_var = tk.StringVar(value="MR-")
        self.engine_var = tk.StringVar()
        self.trunk_var = tk.StringVar()
        self.controller_part_var = tk.StringVar(value="M4-CVM03050-0")
        self.template_var = tk.StringVar(value="VAV-RH")
        self.definition_var = tk.StringVar(value="VAV")
        self.network_type_var = tk.StringVar(value="MSTP")
        self.instance_mode_var = tk.StringVar(value="Generate using workbook convention")
        self.dhcp_var = tk.BooleanVar(value=True)
        self.subnet_var = tk.StringVar()
        self.router_var = tk.StringVar()

        self._labeled_entry(frame, "Site / Building / Floor", 0, 0, self.site_var, colspan=2)
        self._labeled_entry(frame, "Device Prefix", 0, 2, self.device_prefix_var)
        self._labeled_entry(frame, "Controller Part #", 0, 3, self.controller_part_var)

        self._labeled_entry(frame, "Engine Name", 2, 0, self.engine_var)
        self._labeled_entry(frame, "Trunk Name", 2, 1, self.trunk_var)
        self._labeled_entry(frame, "Controller Template", 2, 2, self.template_var)
        self._labeled_entry(frame, "Equipment Definition", 2, 3, self.definition_var)

        ttk.Label(frame, text="Network Type").grid(row=4, column=0, sticky="w", padx=6, pady=(6, 2))
        network_combo = ttk.Combobox(
            frame, textvariable=self.network_type_var, values=["MSTP", "IP"], state="readonly", width=18
        )
        network_combo.grid(row=5, column=0, sticky="ew", padx=6, pady=(0, 8))

        ttk.Label(frame, text="BACnet Instance").grid(row=4, column=1, sticky="w", padx=6, pady=(6, 2))
        ttk.Combobox(
            frame,
            textvariable=self.instance_mode_var,
            values=["Generate using workbook convention", "Leave blank for SCT"],
            state="readonly",
        ).grid(row=5, column=1, sticky="ew", padx=6, pady=(0, 8))

        ttk.Checkbutton(frame, text="DHCP Enabled (IP only)", variable=self.dhcp_var).grid(
            row=5, column=2, sticky="w", padx=6, pady=(0, 8)
        )
        self._labeled_entry(frame, "Subnet Mask (IP only)", 6, 0, self.subnet_var)
        self._labeled_entry(frame, "IP Router (IP only)", 6, 1, self.router_var)

        note = (
            "The supplied RAC workbook recommends leaving Instance blank for SCT to assign automatically, "
            "but your current scratchpad also contains a deterministic project convention. This app supports both."
        )
        ttk.Label(frame, text=note, wraplength=950, foreground="#555555").grid(
            row=8, column=0, columnspan=4, sticky="w", padx=6, pady=(8, 4)
        )

    def _build_group_tab(self):
        frame = ttk.LabelFrame(self.group_tab, text="Create an Equipment Group", style="Section.TLabelframe", padding=10)
        frame.pack(fill="x")
        for col in range(6):
            frame.columnconfigure(col, weight=1, uniform="group")

        self.prefix_var = tk.StringVar(value="VAV")
        self.separator_var = tk.StringVar(value="-")
        self.start_var = tk.StringVar(value="1")
        self.end_var = tk.StringVar(value="20")
        self.digits_var = tk.StringVar(value="2")
        self.start_address_var = tk.StringVar(value="1")
        self.served_by_var = tk.StringVar()
        self.manufacturer_var = tk.StringVar(value=self._default_manufacturer())
        self.inlet_var = tk.StringVar()
        self.maxflow_var = tk.StringVar()
        self.clgmin_var = tk.StringVar()
        self.htgmin_var = tk.StringVar()

        self._labeled_entry(frame, "Equipment Prefix", 0, 0, self.prefix_var)
        self._labeled_entry(frame, "Separator", 0, 1, self.separator_var, width=8)
        self._labeled_entry(frame, "Start", 0, 2, self.start_var, width=8)
        self._labeled_entry(frame, "End", 0, 3, self.end_var, width=8)
        self._labeled_entry(frame, "Digits", 0, 4, self.digits_var, width=8)
        self._labeled_entry(frame, "Starting MAC / IP Ctrl #", 0, 5, self.start_address_var, width=10)

        self._labeled_entry(frame, "Served By", 2, 0, self.served_by_var, colspan=2)

        ttk.Label(frame, text="Manufacturer").grid(row=2, column=2, sticky="w", padx=6, pady=(6, 2))
        manufacturers = sorted(self.manufacturer_data.keys())
        self.manufacturer_combo = ttk.Combobox(
            frame, textvariable=self.manufacturer_var, values=manufacturers, state="readonly"
        )
        self.manufacturer_combo.grid(row=3, column=2, sticky="ew", padx=6, pady=(0, 8))
        self.manufacturer_combo.bind("<<ComboboxSelected>>", lambda _e: self._update_inlet_sizes())

        ttk.Label(frame, text="Inlet Size (in.)").grid(row=2, column=3, sticky="w", padx=6, pady=(6, 2))
        self.inlet_combo = ttk.Combobox(frame, textvariable=self.inlet_var, state="readonly", width=10)
        self.inlet_combo.grid(row=3, column=3, sticky="ew", padx=6, pady=(0, 8))
        self._update_inlet_sizes()

        self._labeled_entry(frame, "CLG Max Flow", 4, 0, self.maxflow_var)
        self._labeled_entry(frame, "Cooling Min Flow", 4, 1, self.clgmin_var)
        self._labeled_entry(frame, "Heating Min Flow", 4, 2, self.htgmin_var)

        ttk.Button(frame, text="Add Equipment Group", command=self.add_group).grid(
            row=5, column=4, columnspan=2, sticky="e", padx=6, pady=(12, 8)
        )

        explanation = (
            "This creates one row per controller. You can edit room numbers, leaf spaces, addresses, flows, "
            "and other values later on the Devices tab. FQR, BACnet Instance, Area, and K Factor recalculate automatically."
        )
        ttk.Label(frame, text=explanation, wraplength=1000, foreground="#555555").grid(
            row=6, column=0, columnspan=6, sticky="w", padx=6, pady=8
        )

    def _build_devices_tab(self):
        toolbar = ttk.Frame(self.devices_tab)
        toolbar.pack(fill="x", pady=(0, 8))
        ttk.Button(toolbar, text="Recalculate", command=self.recalculate_all).pack(side="left", padx=(0, 6))
        ttk.Button(toolbar, text="Delete Selected", command=self.delete_selected).pack(side="left", padx=6)
        ttk.Button(toolbar, text="Clear All", command=self.clear_all).pack(side="left", padx=6)
        ttk.Button(toolbar, text="Export RAC Workbook (.xlsx)", command=self.export_workbook).pack(side="right", padx=(6, 0))
        ttk.Button(toolbar, text="Export SCT CSV", command=self.export_csv).pack(side="right", padx=6)

        tree_frame = ttk.Frame(self.devices_tab)
        tree_frame.pack(fill="both", expand=True)

        columns = [c[0] for c in self.DISPLAY_COLUMNS]
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="extended")
        for key, heading, width in self.DISPLAY_COLUMNS:
            self.tree.heading(key, text=heading)
            self.tree.column(key, width=width, minwidth=50, anchor="center" if width < 100 else "w")

        xscroll = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        yscroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(xscrollcommand=xscroll.set, yscrollcommand=yscroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", self._begin_edit)
        ttk.Label(
            self.devices_tab,
            text="Tip: double-click an editable cell to change it. Derived fields such as Instance, FQR, SA Area, and K Factor are recalculated.",
            foreground="#555555",
        ).pack(anchor="w", pady=(6, 0))

    def _default_manufacturer(self):
        for candidate in ("Titus", "Generic"):
            if candidate in self.manufacturer_data:
                return candidate
        return next(iter(self.manufacturer_data), "Generic")

    def _update_inlet_sizes(self):
        sizes = sorted(self.manufacturer_data.get(self.manufacturer_var.get(), {}).keys())
        valid = [str(s) for s in sizes if self.manufacturer_data[self.manufacturer_var.get()][s] != (None, None)]
        self.inlet_combo["values"] = valid
        if self.inlet_var.get() not in valid:
            self.inlet_var.set(valid[0] if valid else "")

    @staticmethod
    def _optional_float(value: str):
        text = value.strip()
        return None if text == "" else float(text)

    def _project_defaults(self) -> ProjectDefaults:
        return ProjectDefaults(
            site_hierarchy=self.site_var.get().strip(),
            device_prefix=self.device_prefix_var.get(),
            engine_name=self.engine_var.get().strip(),
            trunk_name=self.trunk_var.get().strip(),
            controller_part=self.controller_part_var.get().strip(),
            controller_template=self.template_var.get().strip(),
            equipment_definition=self.definition_var.get().strip(),
            network_type=self.network_type_var.get(),
            generate_instance=self.instance_mode_var.get().startswith("Generate"),
            dhcp_enabled=self.dhcp_var.get(),
            subnet_mask=self.subnet_var.get().strip(),
            ip_router=self.router_var.get().strip(),
        )

    def add_group(self):
        try:
            defaults = self._project_defaults()
            inlet = int(self.inlet_var.get()) if self.inlet_var.get().strip() else None
            group = EquipmentGroup(
                equipment_prefix=self.prefix_var.get().strip(),
                separator=self.separator_var.get(),
                start=int(self.start_var.get()),
                end=int(self.end_var.get()),
                digits=int(self.digits_var.get()),
                start_address=int(self.start_address_var.get()),
                served_by=self.served_by_var.get().strip(),
                manufacturer=self.manufacturer_var.get(),
                inlet_size=inlet,
                clg_maxflow=self._optional_float(self.maxflow_var.get()),
                clg_minflow=self._optional_float(self.clgmin_var.get()),
                htg_minflow=self._optional_float(self.htgmin_var.get()),
            )
            new_records = generate_group_records(defaults, group, self.manufacturer_data)
        except Exception as exc:
            messagebox.showerror("Cannot add group", str(exc))
            return

        self.records.extend(new_records)
        self._refresh_tree()
        self.status_var.set(f"Added {len(new_records)} devices. Total: {len(self.records)}")

    def _value_for_tree(self, value):
        if value is None:
            return ""
        if isinstance(value, float):
            return f"{value:g}"
        return str(value)

    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        for index, record in enumerate(self.records):
            values = [self._value_for_tree(getattr(record, key)) for key, _h, _w in self.DISPLAY_COLUMNS]
            self.tree.insert("", "end", iid=str(index), values=values)
        duplicates = find_duplicate_values(self.records)
        if duplicates:
            summary = "; ".join(f"{k}: {', '.join(map(str, sorted(v, key=str)))}" for k, v in duplicates.items())
            self.status_var.set(f"Warning — duplicate identifiers: {summary}")

    def _begin_edit(self, event):
        if self._editor is not None:
            self._editor.destroy()
            self._editor = None

        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        row_id = self.tree.identify_row(event.y)
        column_id = self.tree.identify_column(event.x)
        if not row_id or not column_id:
            return

        col_index = int(column_id.replace("#", "")) - 1
        key = self.DISPLAY_COLUMNS[col_index][0]
        if key not in self.EDITABLE_COLUMNS:
            return

        bbox = self.tree.bbox(row_id, column_id)
        if not bbox:
            return
        x, y, width, height = bbox
        current = self.tree.set(row_id, key)

        editor = ttk.Entry(self.tree)
        editor.insert(0, current)
        editor.select_range(0, tk.END)
        editor.place(x=x, y=y, width=width, height=height)
        editor.focus_set()
        self._editor = editor

        def save(_event=None):
            self._save_edit(int(row_id), key, editor.get())
            editor.destroy()
            self._editor = None

        def cancel(_event=None):
            editor.destroy()
            self._editor = None

        editor.bind("<Return>", save)
        editor.bind("<FocusOut>", save)
        editor.bind("<Escape>", cancel)

    def _save_edit(self, record_index: int, key: str, text: str):
        record = self.records[record_index]
        try:
            if key in {"mac_address", "ip_controller_number", "inlet_size"}:
                value = None if text.strip() == "" else int(text)
            elif key in {"clg_maxflow", "clg_minflow", "htg_minflow"}:
                value = None if text.strip() == "" else float(text)
            else:
                value = text
            setattr(record, key, value)

            # Maintain the MAC/IP mutual-exclusion rule.
            if key == "mac_address" and value is not None:
                record.ip_controller_number = None
            elif key == "ip_controller_number" and value is not None:
                record.mac_address = None

            recalculate_record(
                record,
                self.manufacturer_data,
                self.instance_mode_var.get().startswith("Generate"),
            )
            self._refresh_tree()
        except Exception as exc:
            messagebox.showerror("Invalid value", str(exc))

    def recalculate_all(self):
        for record in self.records:
            recalculate_record(
                record,
                self.manufacturer_data,
                self.instance_mode_var.get().startswith("Generate"),
            )
        self._refresh_tree()
        self.status_var.set(f"Recalculated {len(self.records)} devices.")

    def delete_selected(self):
        selected = sorted((int(i) for i in self.tree.selection()), reverse=True)
        for index in selected:
            del self.records[index]
        self._refresh_tree()
        self.status_var.set(f"Deleted {len(selected)} device(s). Total: {len(self.records)}")

    def clear_all(self):
        if not self.records:
            return
        if messagebox.askyesno("Clear devices", "Remove all generated devices?"):
            self.records.clear()
            self._refresh_tree()
            self.status_var.set("All devices cleared.")

    def _validate_before_export(self) -> bool:
        if not self.records:
            messagebox.showwarning("Nothing to export", "Add at least one equipment group first.")
            return False
        duplicates = find_duplicate_values(self.records)
        if duplicates:
            details = "\n".join(f"{key}: {', '.join(map(str, values))}" for key, values in duplicates.items())
            return messagebox.askyesno(
                "Duplicate identifiers",
                f"The following duplicates were found:\n\n{details}\n\nExport anyway?",
            )
        return True

    def export_workbook(self):
        if not self._validate_before_export():
            return
        path = filedialog.asksaveasfilename(
            title="Export RAC Workbook",
            defaultextension=".xlsx",
            filetypes=[("Excel Workbook", "*.xlsx")],
            initialfile="RAC Schedule_Generated.xlsx",
        )
        if not path:
            return
        try:
            export_rac_workbook(path, self.template_path, self.records)
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc))
            return
        self.status_var.set(f"Workbook exported: {path}")
        messagebox.showinfo("Export complete", f"RAC workbook created:\n{path}")

    def export_csv(self):
        if not self._validate_before_export():
            return
        path = filedialog.asksaveasfilename(
            title="Export SCT Rapid Archive CSV",
            defaultextension=".csv",
            filetypes=[("CSV File", "*.csv")],
            initialfile="Rapid Archive Schedule.csv",
        )
        if not path:
            return
        try:
            export_rac_csv(path, self.records)
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc))
            return
        self.status_var.set(f"CSV exported: {path}")
        messagebox.showinfo("Export complete", f"SCT Rapid Archive CSV created:\n{path}")


def run_app():
    app = RACGeneratorApp()
    app.mainloop()
