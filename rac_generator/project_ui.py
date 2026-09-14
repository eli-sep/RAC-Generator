from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .exporters import export_rac_csv
from .importers import import_rac_schedule
from .project_io import FORM_FIELDS, load_project, save_project


# Older macOS Tk 8.6 builds abort when a compound extension such as
# "rac.json" cannot be converted to a UTType. Filter by the final suffix;
# the suggested filename can still be "RAC_Project.rac.json".
PROJECT_FILE_TYPES = [("RAC Generator Project", "*.json")]


class ProjectFilesMixin:
    """Project persistence and schedule import for the Tk application."""

    def _build_file_controls(self, parent):
        menu = tk.Menu(self)
        file_menu = tk.Menu(menu, tearoff=False)
        modifier = "Command" if self.tk.call("tk", "windowingsystem") == "aqua" else "Control"
        label = "Cmd" if modifier == "Command" else "Ctrl"
        for title, callback, key in (
            ("New Project", self.new_project, "n"),
            ("Open Project…", self.open_project, "o"),
            ("Save Project", self.save_project, "s"),
        ):
            file_menu.add_command(label=title, command=callback, accelerator=f"{label}+{key.upper()}")
            self.bind(f"<{modifier}-{key}>", lambda _event, callback=callback: self._file_shortcut(callback))
        file_menu.add_command(label="Save Project As…", command=self.save_project_as, accelerator=f"{label}+Shift+S")
        self.bind(f"<{modifier}-Shift-S>", lambda _event: self._file_shortcut(self.save_project_as))
        file_menu.add_separator()
        file_menu.add_command(label="Import Schedule(s)…", command=self.import_schedules)
        file_menu.add_command(label="Save Working CSV…", command=self.save_working_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.close_project_window)
        menu.add_cascade(label="File", menu=file_menu)
        self.configure(menu=menu)

        toolbar = ttk.Frame(parent)
        toolbar.pack(fill="x", pady=(0, 10))
        for title, callback in (
            ("Open Project", self.open_project), ("Save Project", self.save_project),
            ("Import Schedule", self.import_schedules), ("Save Working CSV", self.save_working_csv),
        ):
            ttk.Button(toolbar, text=title, command=callback).pack(side="left", padx=(0, 6))
        self.project_name_var = tk.StringVar(value="Untitled project")
        ttk.Label(toolbar, textvariable=self.project_name_var).pack(side="left", padx=10)

    @staticmethod
    def _file_shortcut(callback):
        callback()
        return "break"

    def _init_project_files(self):
        self.project_path: Path | None = None
        self.working_csv_path: Path | None = None
        self._dirty = False
        self._loading_project = False
        self._initial_settings = self._capture_settings()
        for field in FORM_FIELDS:
            getattr(self, f"{field}_var").trace_add("write", self._mark_dirty)
        self.existing_equipment_text.edit_modified(False)
        self.existing_equipment_text.bind("<<Modified>>", self._existing_equipment_changed)
        self.protocol("WM_DELETE_WINDOW", self.close_project_window)
        self._update_project_title()

    def _capture_settings(self) -> dict:
        settings = {field: getattr(self, f"{field}_var").get() for field in FORM_FIELDS}
        settings["existing_equipment"] = self.existing_equipment_text.get("1.0", "end-1c")
        return settings

    def _mark_dirty(self, *_args):
        if not self._loading_project:
            self._dirty = True
            self._update_project_title()

    def _existing_equipment_changed(self, _event=None):
        if self.existing_equipment_text.edit_modified():
            self.existing_equipment_text.edit_modified(False)
            self._mark_dirty()

    def _update_project_title(self):
        source = self.project_path or self.working_csv_path
        name = source.name if source else "Untitled project"
        label = f"{name}{' *' if self._dirty else ''}"
        self.project_name_var.set(label)
        self.title(f"RAC Generator — {label}")

    def _set_settings(self, settings):
        for field in FORM_FIELDS:
            getattr(self, f"{field}_var").set(settings.get(field, self._initial_settings[field]))
        self.existing_equipment_text.delete("1.0", "end")
        self.existing_equipment_text.insert("1.0", settings.get("existing_equipment", ""))
        self.existing_equipment_text.edit_modified(False)

    def _replace_project(self, settings, records, path=None):
        self._loading_project = True
        try:
            self._set_settings(settings)
            self.records = records
            self.project_path = Path(path) if path is not None else None
            self.working_csv_path = None
            self._refresh_tree()
            self.notebook.select(self.devices_tab if records else self.project_tab)
        finally:
            self._loading_project = False
        self._dirty = False
        self._update_project_title()

    def _confirm_save_changes(self) -> bool:
        if not self._finish_edit():
            return False
        # Read Text's modification flag too, in case its event has not been dispatched yet.
        if not self._dirty and not self.existing_equipment_text.edit_modified():
            return True
        answer = messagebox.askyesnocancel(
            "Save project changes?",
            "Save your changes before continuing?\n\nYes saves the complete project. No discards unsaved changes. Cancel keeps this project open.",
            parent=self,
        )
        if answer is None:
            return False
        return self.save_project() if answer else True

    def new_project(self):
        if self._confirm_save_changes():
            self._replace_project(dict(self._initial_settings), [])
            self.status_var.set("New project. You can save before completing the required SCT fields.")

    def close_project_window(self):
        if self._confirm_save_changes():
            self.destroy()

    def open_project(self):
        if not self._finish_edit():
            return False
        path = filedialog.askopenfilename(
            parent=self, title="Open RAC Generator Project",
            filetypes=PROJECT_FILE_TYPES,
        )
        if not path:
            return False
        try:
            settings, records = load_project(path)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Cannot open project", str(exc), parent=self)
            return False
        if not self._confirm_save_changes():
            return False
        # Saving the current project may have updated the file selected for reopening.
        if self.project_path is not None and Path(path).resolve() == self.project_path.resolve():
            try:
                settings, records = load_project(path)
            except (OSError, ValueError) as exc:
                messagebox.showerror("Cannot open project", str(exc), parent=self)
                return False
        self._replace_project(settings, records, path)
        self.status_var.set(f"Opened {Path(path).name}: {len(records)} devices. Continue editing or run SCT Preflight when ready.")
        return True

    def save_project(self, *, save_as=False) -> bool:
        if not self._finish_edit():
            return False
        path = self.project_path
        if save_as or path is None:
            chosen = filedialog.asksaveasfilename(
                parent=self, title="Save RAC Generator Project", defaultextension=".json",
                filetypes=PROJECT_FILE_TYPES,
                initialfile=path.name if path else "RAC_Project.rac.json",
            )
            if not chosen:
                return False
            path = Path(chosen)
        try:
            save_project(path, self._capture_settings(), self.records)
        except (OSError, ValueError, TypeError) as exc:
            messagebox.showerror("Cannot save project", str(exc), parent=self)
            return False
        self.project_path = path
        self._dirty = False
        self.existing_equipment_text.edit_modified(False)
        self._update_project_title()
        self.status_var.set(f"Saved complete project: {path.name}. Use Open Project to resume later.")
        return True

    def save_project_as(self):
        return self.save_project(save_as=True)

    def save_working_csv(self) -> bool:
        if not self._finish_edit():
            return False
        path = filedialog.asksaveasfilename(
            parent=self, title="Save Working SCT CSV", defaultextension=".csv",
            filetypes=[("SCT Rapid Archive CSV", "*.csv")],
            initialfile=self.working_csv_path.name if self.working_csv_path else "RAC_Working.csv",
        )
        if not path:
            return False
        try:
            export_rac_csv(path, self.records)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Cannot save working CSV", str(exc), parent=self)
            return False
        self.working_csv_path = Path(path)
        self._update_project_title()
        self.status_var.set("Working CSV saved without preflight. Save Project retains editing settings; use Export Staged SCT CSVs for final imports.")
        return True

    def import_schedules(self) -> bool:
        if not self._finish_edit():
            return False
        paths = filedialog.askopenfilenames(
            parent=self, title="Import SCT CSVs or RAC Workbooks (adds devices to this project)",
            filetypes=[("SCT Rapid Archive CSV", "*.csv"), ("RAC Workbook", "*.xlsx")],
        )
        if not paths:
            return False
        imported = []
        try:
            for path in paths:
                imported.extend(import_rac_schedule(path))
        except Exception as exc:
            messagebox.showerror("Cannot import schedule", f"{Path(path).name}\n\n{exc}\n\nNo devices were imported.", parent=self)
            return False
        fresh = not self.records and not self._dirty
        if fresh and imported:
            first = imported[0]
            settings = dict(self._initial_settings)
            for form, field in (
                ("site", "site_hierarchy"), ("engine", "engine_name"), ("trunk", "trunk_name"),
                ("controller_part", "controller_part"), ("template", "controller_template"),
                ("definition", "equipment_definition"), ("subnet", "subnet_mask"), ("router", "ip_router"),
            ):
                settings[form] = getattr(first, field)
            settings["network_type"] = "IP" if first.ip_controller_number is not None or first.ip_address or first.dhcp_enabled is not None else "MSTP"
            if first.dhcp_enabled is not None:
                settings["dhcp"] = first.dhcp_enabled
            self._loading_project = True
            try:
                self._set_settings(settings)
            finally:
                self._loading_project = False
        self.records.extend(imported)
        if fresh and len(paths) == 1 and Path(paths[0]).suffix.lower() == ".csv":
            self.working_csv_path = Path(paths[0])
        self._refresh_tree()
        self.notebook.select(self.devices_tab)
        self._mark_dirty()
        self.status_var.set(
            f"Imported {len(imported)} devices. Existing identifiers and parameters are retained. Save Project keeps all editing settings."
        )
        return True
