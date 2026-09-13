import os
import sys
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from tkinter import ttk
from unittest.mock import patch

from rac_generator.exporters import export_rac_csv
from rac_generator.importers import import_rac_schedule
from rac_generator.models import DeviceRecord, ExtraParameter
from rac_generator.project_io import load_project, save_project
from rac_generator.ui_fixes import ImprovedRACGeneratorApp


class UITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
            raise unittest.SkipTest("Tk UI tests need a display; run with xvfb-run on Linux.")

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        data = {
            "Titus": {8: (0.35, 2.39), 10: (0.55, 2.31)},
            "Other": {8: (0.36, 3.1), 12: (0.8, 2.7)},
            "Incomplete": {8: (0.35, None)},
            "Unavailable": {8: (None, None)},
        }
        with patch("rac_generator.ui.load_manufacturer_data", return_value=data):
            self.app = ImprovedRACGeneratorApp()
        self.addCleanup(self.app.destroy)
        self.callback_errors = []
        self.app.report_callback_exception = lambda _t, error, _tb: self.callback_errors.append(error)
        self.app.update()
        self.app.focus_force()

    def tearDown(self):
        self.app.update()
        self.assertEqual(self.callback_errors, [])

    def generate_devices(self, count=3):
        self.app.site_var.set("Site/Building/Floor")
        self.app.engine_var.set("SNE03")
        self.app.trunk_var.set("FC-1")
        self.app.end_var.set(str(count))
        self.app.add_group()
        self.app.notebook.select(self.app.devices_tab)
        self.app.update()

    def edit(self, row, column, text):
        index = [key for key, _h, _w in self.app.DISPLAY_COLUMNS].index(column)
        self.app._open_cell_editor(str(row), index)
        self.app.update()
        self.set_text(text)

    def set_text(self, text):
        self.app._editor.delete(0, "end")
        self.app._editor.insert(0, text)

    def press(self, sequence):
        self.assertIs(self.app.focus_get(), self.app._editor)
        self.app._editor.event_generate(sequence)
        self.app.update()

    def assert_editing(self, row, column):
        index = [key for key, _h, _w in self.app.DISPLAY_COLUMNS].index(column)
        self.assertEqual(self.app._edit_cell, (str(row), index))
        self.assertIs(self.app.focus_get(), self.app._editor)

    def test_network_switch_preserves_settings_and_omits_them_from_mstp_records(self):
        self.assertFalse(self.app.dhcp_check.winfo_ismapped())
        self.assertFalse(self.app.ip_settings_frame.winfo_ismapped())
        self.app.network_type_var.set("IP")
        self.app.update()
        self.assertTrue(self.app.dhcp_check.winfo_ismapped())
        self.assertTrue(self.app.ip_settings_frame.winfo_ismapped())
        self.app.subnet_var.set("255.255.255.0")
        self.app.router_var.set("192.168.1.1")
        self.app.dhcp_var.set(False)
        self.app.network_type_var.set("MSTP")
        self.app.update()
        self.assertFalse(self.app.dhcp_check.winfo_ismapped())
        self.assertFalse(self.app.ip_settings_frame.winfo_ismapped())
        self.generate_devices(1)
        record = self.app.records[0]
        self.assertEqual((record.dhcp_enabled, record.subnet_mask, record.ip_router), (None, "", ""))
        self.app.network_type_var.set("IP")
        self.assertEqual(self.app.subnet_var.get(), "255.255.255.0")
        self.assertEqual(self.app.router_var.get(), "192.168.1.1")
        self.assertFalse(self.app.dhcp_var.get())

    def test_preview_tracks_both_selections_and_matches_generated_values(self):
        self.assertEqual((self.app.group_area_var.get(), self.app.group_kfactor_var.get()), ("0.35", "2.39"))
        self.app.inlet_var.set("10")
        self.assertEqual((self.app.group_area_var.get(), self.app.group_kfactor_var.get()), ("0.55", "2.31"))
        self.app.inlet_var.set("8")
        self.app.manufacturer_var.set("Other")
        self.assertEqual((self.app.group_area_var.get(), self.app.group_kfactor_var.get()), ("0.36", "3.1"))
        self.app.inlet_var.set("12")
        self.generate_devices(1)
        self.assertEqual((self.app.records[0].sa_area, self.app.records[0].sa_kfactor), (0.8, 2.7))
        self.app.manufacturer_var.set("Incomplete")
        self.assertEqual(self.app.inlet_var.get(), "8")
        self.assertEqual((self.app.group_area_var.get(), self.app.group_kfactor_var.get()), ("0.35", "—"))
        self.app.manufacturer_var.set("Unavailable")
        self.assertEqual(self.app.inlet_var.get(), "")
        self.assertEqual((self.app.group_area_var.get(), self.app.group_kfactor_var.get()), ("—", "—"))

    def test_enter_saves_each_row_and_stops_at_the_bottom(self):
        self.generate_devices()
        self.edit(0, "room_number", "101")
        for row in range(3):
            self.set_text(str(101 + row))
            self.press("<Return>")
            self.assertEqual(self.app.records[row].room_number, str(101 + row))
            if row < 2:
                self.assert_editing(row + 1, "room_number")
        self.assertIsNone(self.app._editor)
        self.assertEqual(len(self.app.records), 3)

    def test_tab_skips_calculated_columns_and_reveals_the_next_cell(self):
        self.generate_devices()
        self.edit(0, "ip_controller_number", "10")
        self.press("<Tab>")
        self.assert_editing(0, "manufacturer")
        self.assertEqual(self.app.records[0].ip_controller_number, 10)
        self.assertIsNone(self.app.records[0].mac_address)
        self.press("<Tab>")
        self.assert_editing(0, "inlet_size")
        self.set_text("10")
        self.press("<Tab>")
        self.assert_editing(0, "clg_maxflow")
        self.assertEqual((self.app.records[0].sa_area, self.app.records[0].sa_kfactor), (0.55, 2.31))
        editor = self.app._editor
        self.assertGreaterEqual(editor.winfo_x(), 0)
        self.assertLessEqual(editor.winfo_x() + editor.winfo_width(), self.app.tree.winfo_width())

    def test_tab_wrap_and_shift_navigation_respect_table_boundaries(self):
        self.generate_devices()
        self.edit(0, "controller_template", "VAV-RAD")
        self.press("<Tab>")
        self.assert_editing(1, "equipment_name")
        self.press("<Shift-Tab>")
        self.assert_editing(0, "controller_template")
        self.press("<Return>")
        self.assert_editing(1, "controller_template")
        self.press("<Shift-Return>")
        self.assert_editing(0, "controller_template")
        self.press("<Escape>")
        self.edit(0, "equipment_name", "VAV-01")
        self.press("<Shift-Tab>")
        self.assertIsNone(self.app._editor)
        self.edit(2, "controller_template", "VAV-RH")
        self.press("<Tab>")
        self.assertIsNone(self.app._editor)
        self.assertEqual(len(self.app.records), 3)

    def test_invalid_number_keeps_edit_and_original_data_until_corrected(self):
        self.generate_devices()
        self.edit(0, "mac_address", "invalid")
        editor = self.app._editor
        # A real error dialog takes focus while the save is still in progress.
        with patch("rac_generator.ui.messagebox.showerror", side_effect=lambda *_a, **_k: editor.event_generate("<FocusOut>")) as error:
            self.press("<Tab>")
        error.assert_called_once()
        self.assertIs(self.app._editor, editor)
        self.assertEqual(self.app.records[0].mac_address, 4)
        self.assertEqual(editor.get(), "invalid")
        self.set_text("7")
        self.press("<Return>")
        self.assertEqual(self.app.records[0].mac_address, 7)
        self.assert_editing(1, "mac_address")

    def test_escape_discards_changes_and_focusout_saves_once(self):
        self.generate_devices()
        self.edit(0, "room_number", "discard")
        self.press("<Escape>")
        self.assertEqual(self.app.records[0].room_number, "")
        self.edit(0, "room_number", "101")
        with patch.object(self.app, "_save_edit", wraps=self.app._save_edit) as save:
            self.app.tree.focus_set()
            self.app.update()
        save.assert_called_once()
        self.assertEqual(self.app.records[0].room_number, "101")
        self.assertIsNone(self.app._editor)

    @staticmethod
    def descendants(widget):
        for child in widget.winfo_children():
            yield child
            yield from UITests.descendants(child)

    def dismiss_dialog(self, action):
        dialog = next(w for w in self.app.winfo_children() if isinstance(w, tk.Toplevel))
        try:
            self.assertEqual(tuple(map(int, dialog.resizable())), (1, 1))
            text = next(w for w in self.descendants(dialog) if isinstance(w, tk.Text))
            self.assertEqual(str(text.cget("state")), "disabled")
            self.assertIn("Final item", text.get("1.0", "end"))
            if action in ("OK", "Export anyway", "Cancel"):
                button = next(w for w in self.descendants(dialog) if isinstance(w, ttk.Button) and w.cget("text") == action)
                button.invoke()
            elif action == "close":
                dialog.tk.eval(dialog.protocol("WM_DELETE_WINDOW"))
            else:
                dialog.event_generate(action)
                self.app.update()
            self.assertFalse(dialog.winfo_exists())
        finally:
            if dialog.winfo_exists():
                dialog.destroy()

    def test_export_warnings_require_acceptance_and_errors_always_block(self):
        messages = [f"Item {i}" for i in range(100)] + ["Final item"]
        for action, accepted in [("Export anyway", True), ("Cancel", False), ("close", False), ("<Escape>", False), ("<Return>", False)]:
            with self.subTest(action=action), patch.object(self.app, "_preflight_results", return_value=([], messages)):
                self.app.after(50, lambda action=action: self.dismiss_dialog(action))
                self.assertEqual(self.app._validate_before_export(), accepted)
        with patch.object(self.app, "_preflight_results", return_value=(messages, [])):
            self.app.after(50, lambda: self.dismiss_dialog("OK"))
            self.assertFalse(self.app._validate_before_export())

    def test_project_save_commits_cell_and_restores_incomplete_work_and_settings(self):
        self.generate_devices(1)
        self.app.manufacturer_var.set("Other")
        self.app.inlet_var.set("12")
        self.app.start_var.set("unfinished")
        self.app.maxflow_var.set("1.")
        self.app.site_var.set("")
        self.app.network_type_var.set("IP")
        self.app.dhcp_var.set(False)
        self.app.existing_equipment_text.insert("1.0", "AHU-01\nAHU-02\n")
        self.edit(0, "room_number", "001")
        path = self.directory / "unfinished.rac.json"
        with patch("rac_generator.project_ui.filedialog.asksaveasfilename", return_value=str(path)), \
             patch.object(self.app, "_validate_before_export", side_effect=AssertionError("Drafts must bypass preflight")):
            self.assertTrue(self.app.save_project())
        self.app.update()
        self.assertFalse(self.app._dirty)
        self.assertIsNone(self.app._editor)
        settings, records = load_project(path)
        self.assertEqual(records[0].room_number, "001")
        self.assertEqual(settings, self.app._capture_settings())
        self.app.manufacturer_var.set("Titus")
        self.app.records.clear()
        with patch("rac_generator.project_ui.filedialog.askopenfilename", return_value=str(path)), \
             patch("rac_generator.project_ui.messagebox.askyesnocancel", return_value=False):
            self.assertTrue(self.app.open_project())
        self.app.update()
        self.assertEqual(self.app.records, records)
        self.assertEqual(self.app._capture_settings(), settings)
        self.assertEqual((self.app.manufacturer_var.get(), self.app.inlet_var.get()), ("Other", "12"))
        self.assertFalse(self.app._dirty)
        self.assertNotIn(" *", self.app.title())

    def test_form_only_project_and_save_as_keep_both_files(self):
        first = self.directory / "first.rac.json"
        second = self.directory / "second.rac.json"
        self.app.engine_var.set("SNE03")
        with patch("rac_generator.project_ui.filedialog.asksaveasfilename", return_value=str(first)):
            self.assertTrue(self.app.save_project())
        self.app.engine_var.set("SNE04")
        with patch("rac_generator.project_ui.filedialog.asksaveasfilename", return_value=str(second)):
            self.assertTrue(self.app.save_project_as())
        self.app.engine_var.set("SNE05")
        self.assertTrue(self.app.save_project())
        self.assertEqual(load_project(first)[0]["engine"], "SNE03")
        self.assertEqual(load_project(second)[0]["engine"], "SNE05")
        self.assertEqual(load_project(second)[1], [])
        self.assertEqual(self.app.project_path, second)

    def test_cancelled_or_failed_save_blocks_replacing_and_closing_project(self):
        self.generate_devices(1)
        records = list(self.app.records)
        with patch("rac_generator.project_ui.messagebox.askyesnocancel", return_value=None), \
             patch.object(self.app, "destroy") as destroy:
            self.app.new_project()
            self.app.close_project_window()
            destroy.assert_not_called()
        with patch("rac_generator.project_ui.messagebox.askyesnocancel", return_value=True), \
             patch("rac_generator.project_ui.filedialog.asksaveasfilename", return_value=""), \
             patch.object(self.app, "destroy") as destroy:
            self.app.new_project()
            self.app.close_project_window()
            destroy.assert_not_called()
        with patch("rac_generator.project_ui.messagebox.askyesnocancel", return_value=True), \
             patch("rac_generator.project_ui.filedialog.asksaveasfilename", return_value=str(self.directory / "save.rac.json")), \
             patch("rac_generator.project_ui.save_project", side_effect=OSError("Disk unavailable")), \
             patch("rac_generator.project_ui.messagebox.showerror") as error, \
             patch.object(self.app, "destroy") as destroy:
            self.app.new_project()
            self.app.close_project_window()
            self.assertEqual(error.call_count, 2)
            destroy.assert_not_called()
        self.assertEqual(self.app.records, records)
        self.assertTrue(self.app._dirty)
        self.assertIsNone(self.app.project_path)

    def test_opening_same_project_after_saving_keeps_latest_changes(self):
        path = self.directory / "same.rac.json"
        self.app.site_var.set("Original")
        with patch("rac_generator.project_ui.filedialog.asksaveasfilename", return_value=str(path)):
            self.assertTrue(self.app.save_project())
        self.app.site_var.set("Latest")
        with patch("rac_generator.project_ui.filedialog.askopenfilename", return_value=str(path)), \
             patch("rac_generator.project_ui.messagebox.askyesnocancel", return_value=True):
            self.assertTrue(self.app.open_project())
        self.assertEqual(self.app.site_var.get(), "Latest")
        self.assertFalse(self.app._dirty)

    def test_cancelled_open_and_invalid_file_keep_current_project(self):
        self.generate_devices(1)
        records = list(self.app.records)
        path = self.directory / "other.rac.json"
        save_project(path, {}, [])
        with patch("rac_generator.project_ui.filedialog.askopenfilename", return_value=str(path)), \
             patch("rac_generator.project_ui.messagebox.askyesnocancel", return_value=None):
            self.assertFalse(self.app.open_project())
        path.write_text("invalid project", encoding="utf-8")
        with patch("rac_generator.project_ui.filedialog.askopenfilename", return_value=str(path)), \
             patch("rac_generator.project_ui.messagebox.showerror") as error:
            self.assertFalse(self.app.open_project())
        error.assert_called_once()
        self.assertEqual(self.app.records, records)
        self.assertTrue(self.app._dirty)

    def test_working_csv_saves_before_preflight_and_can_be_resumed(self):
        self.generate_devices(1)
        self.app.records[0].controller_template = ""
        self.edit(0, "room_number", "001")
        path = self.directory / "working.csv"
        with patch("rac_generator.project_ui.filedialog.asksaveasfilename", return_value=str(path)), \
             patch.object(self.app, "_validate_before_export", side_effect=AssertionError("Drafts must bypass preflight")):
            self.assertTrue(self.app.save_working_csv())
        self.assertTrue(self.app._dirty)  # Only Save Project includes all editing settings.
        self.assertEqual(import_rac_schedule(path)[0].room_number, "001")
        with patch("rac_generator.project_ui.messagebox.askyesnocancel", return_value=False):
            self.app.new_project()
        self.assertEqual(self.app.records, [])
        self.assertFalse(self.app._dirty)
        with patch("rac_generator.project_ui.filedialog.askopenfilenames", return_value=(str(path),)):
            self.assertTrue(self.app.import_schedules())
        self.assertEqual(self.app.records[0].room_number, "001")
        self.assertEqual(self.app.records[0].controller_template, "")
        self.assertEqual(self.app.engine_var.get(), "SNE03")
        self.assertEqual(self.app.working_csv_path, path)
        self.assertTrue(self.app._dirty)

    def test_imported_identifiers_survive_navigation_edits_and_recalculate(self):
        path = self.directory / "existing.csv"
        record = DeviceRecord(
            device_name="Existing", equipment_name="VAV-X", room_number="001", leaf_space="Office", fqr="Custom.Path",
            device_description="Custom description", instance=54321, sa_area=0.375, sa_kfactor=2.77,
            extra_parameters=[ExtraParameter("OTHER", "AV9999", "Default Value", "001")],
        )
        export_rac_csv(path, [record])
        with patch("rac_generator.project_ui.filedialog.askopenfilenames", return_value=(str(path),)):
            self.assertTrue(self.app.import_schedules())
        with patch("rac_generator.project_ui.filedialog.asksaveasfilename", return_value=str(self.directory / "import.rac.json")):
            self.assertTrue(self.app.save_project())
        self.edit(0, "room_number", "001")
        self.press("<Return>")
        self.assertFalse(self.app._dirty)
        self.assertEqual(self.app.records[0].device_description, "Custom description")
        self.edit(0, "room_number", "002")
        self.press("<Return>")
        self.app.recalculate_all()
        actual = self.app.records[0]
        self.assertEqual((actual.fqr, actual.instance, actual.sa_area, actual.sa_kfactor),
                         ("Custom.Path", 54321, 0.375, 2.77))
        self.assertEqual(actual.extra_parameters, record.extra_parameters)
        self.assertIn("002", actual.device_description)
        self.edit(0, "fqr", "Explicit.Correction")
        self.press("<Return>")
        self.edit(0, "instance", "123456")
        self.press("<Return>")
        self.edit(0, "sa_area", "0.333333333333")
        self.press("<Return>")
        area_column = [key for key, _heading, _width in self.app.DISPLAY_COLUMNS].index("sa_area")
        self.app._open_cell_editor("0", area_column)
        self.app.update()
        self.assertEqual(self.app._editor.get(), "0.333333333333")
        self.press("<Tab>")
        self.assert_editing(0, "sa_kfactor")
        self.app._finish_edit()
        self.app.recalculate_all()
        self.assertEqual((self.app.records[0].fqr, self.app.records[0].instance, self.app.records[0].sa_area),
                         ("Explicit.Correction", 123456, 0.333333333333))

    def test_multiple_imports_append_only_when_all_files_are_valid(self):
        self.generate_devices(1)
        original = list(self.app.records)
        first, second = self.directory / "first.csv", self.directory / "second.csv"
        export_rac_csv(first, [DeviceRecord(equipment_name="AHU-01", device_name="AHU")])
        second.write_text("not an SCT CSV", encoding="utf-8")
        with patch("rac_generator.project_ui.filedialog.askopenfilenames", return_value=(str(first), str(second))), \
             patch("rac_generator.project_ui.messagebox.showerror") as error:
            self.assertFalse(self.app.import_schedules())
        error.assert_called_once()
        self.assertEqual(self.app.records, original)
        export_rac_csv(second, [DeviceRecord(equipment_name="AHU-02", device_name="AHU2")])
        with patch("rac_generator.project_ui.filedialog.askopenfilenames", return_value=(str(first), str(second))):
            self.assertTrue(self.app.import_schedules())
        self.assertEqual([record.equipment_name for record in self.app.records], [original[0].equipment_name, "AHU-01", "AHU-02"])


if __name__ == "__main__":
    unittest.main()
