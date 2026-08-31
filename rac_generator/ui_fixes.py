from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .exporters import SCT_SETUP_GUIDE
from .ui import RACGeneratorApp


class ImprovedRACGeneratorApp(RACGeneratorApp):
    """UI refinements for long-form SCT guidance and validation results."""

    def _build_guide_tab(self):
        """Build a readable, scrollable SCT guide instead of a non-wrapping Treeview."""
        self.guide_tab.rowconfigure(1, weight=1)
        self.guide_tab.columnconfigure(0, weight=1)

        header = ttk.Frame(self.guide_tab)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(
            header,
            text="SCT prerequisites and Rapid Archive order",
            style="Title.TLabel",
        ).pack(anchor="w")
        ttk.Label(
            header,
            text=(
                "These steps are based on the Johnson Controls SCT Rapid Archive workflow. "
                "Complete or verify them before importing the generated staged CSV files."
            ),
            wraplength=900,
            justify="left",
        ).pack(anchor="w", fill="x", pady=(4, 0))

        body = ttk.Frame(self.guide_tab)
        body.grid(row=1, column=0, sticky="nsew")
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1)

        guide_text = tk.Text(
            body,
            wrap="word",
            padx=14,
            pady=12,
            relief="solid",
            borderwidth=1,
            highlightthickness=0,
        )
        scrollbar = ttk.Scrollbar(body, orient="vertical", command=guide_text.yview)
        guide_text.configure(yscrollcommand=scrollbar.set)
        guide_text.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        guide_text.tag_configure("step", font=("TkDefaultFont", 11, "bold"), spacing1=10)
        guide_text.tag_configure("action", font=("TkDefaultFont", 10, "bold"), lmargin1=18, lmargin2=18)
        guide_text.tag_configure("detail", lmargin1=36, lmargin2=36, spacing3=8)
        guide_text.tag_configure("rule", font=("TkDefaultFont", 10, "bold"), spacing1=12)

        for step, action, detail in SCT_SETUP_GUIDE:
            guide_text.insert("end", f"Step {step}\n", "step")
            guide_text.insert("end", f"{action}\n", "action")
            guide_text.insert("end", f"{detail}\n", "detail")

        guide_text.insert(
            "end",
            "Import rule: Level 01 → Save in Rapid Archive → Level 02 → Save → continue.\n",
            "rule",
        )
        guide_text.insert(
            "end",
            "Served By equipment must already exist in SCT at the time its child equipment is created.\n",
            "detail",
        )
        guide_text.configure(state="disabled")

        footer = ttk.Label(
            self.guide_tab,
            text="The guide scrolls vertically and automatically wraps to the available window width.",
            foreground="#555555",
        )
        footer.grid(row=2, column=0, sticky="w", pady=(8, 0))

    def _show_scrollable_dialog(self, title: str, text: str, *, ok_text: str = "OK") -> None:
        """Show long informational text in a resizable, scrollable modal dialog."""
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.geometry("760x520")
        dialog.minsize(520, 320)
        dialog.resizable(True, True)
        dialog.transient(self)
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)

        outer = ttk.Frame(dialog, padding=12)
        outer.pack(fill="both", expand=True)
        outer.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)

        text_frame = ttk.Frame(outer)
        text_frame.grid(row=0, column=0, sticky="nsew")
        text_frame.rowconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)

        text_widget = tk.Text(
            text_frame,
            wrap="word",
            padx=12,
            pady=10,
            relief="solid",
            borderwidth=1,
            highlightthickness=0,
        )
        yscroll = ttk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        xscroll = ttk.Scrollbar(text_frame, orient="horizontal", command=text_widget.xview)
        text_widget.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        text_widget.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")

        text_widget.insert("1.0", text)
        text_widget.configure(state="disabled")

        buttons = ttk.Frame(outer)
        buttons.grid(row=1, column=0, sticky="e", pady=(12, 0))
        ok_button = ttk.Button(buttons, text=ok_text, command=dialog.destroy)
        ok_button.pack(side="right")

        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        dialog.bind("<Return>", lambda _event: dialog.destroy())
        dialog.update_idletasks()
        ok_button.focus_set()
        dialog.grab_set()

    def show_preflight(self):
        errors, warnings = self._preflight_results()
        parts: list[str] = []

        if errors:
            parts.append("ERRORS — fix before export\n\n• " + "\n• ".join(errors))
        else:
            parts.append("No blocking SCT preflight errors found.")

        if warnings:
            parts.append("WARNINGS — confirm in SCT\n\n• " + "\n• ".join(warnings))

        self._show_scrollable_dialog("SCT Preflight", "\n\n".join(parts))

    def _preflight_results(self):
        from .logic import validate_records_for_sct

        return validate_records_for_sct(self.records, self._existing_equipment())


def run_app():
    ImprovedRACGeneratorApp().mainloop()
