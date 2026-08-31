# RAC Generator v0.1

A first working Python/Tkinter version of the RAC Generator based on the supplied **RAC Schedule Template**.

## What this version does

- Generates equipment groups such as `VAV-01` through `VAV-20`.
- Supports custom equipment prefix, separator, start/end numbers, and digit padding.
- Generates a device name using a configurable device prefix (for example `MR-VAV-01`).
- Supports MSTP or IP controller numbering.
- Reproduces the BACnet Instance convention found in the supplied `New Empty Scratchpad`.
- Reproduces the FQR convention found in the supplied workbook.
- Reads the VAV manufacturer Area / K Factor database directly from the workbook's `Manufacturer` sheet.
- Infers Box Heat / Supplemental Heat from the VAV controller template convention in the workbook.
- Supports the five Single-Duct VAV RAC parameters currently used by the scratchpad:
  - `SA-AREA` / `AV3111`
  - `SA-KFACTOR` / `AV3112`
  - `CLG-MAXFLOW` / `AV3108`
  - `CLGOCC-MINFLOW` / `AV3109`
  - `HTGOCC-MINFLOW` / `AV3110`
- Provides an editable device table. Double-click a supported cell to edit it.
- Exports:
  - a copy of the supplied RAC `.xlsx` template with the `Rapid Archive Schedule` filled in;
  - a `Generated Scratchpad` sheet containing the richer engineering data;
  - an SCT Rapid Archive `.csv` containing the six RAC header rows and generated devices.
- Warns about duplicate Equipment Names, Device Names, FQRs, and Instances.

## Important v0.1 limitations

This is deliberately a first usable build, not the final app.

- The dynamic parameter engine currently implements the **Single-Duct VAV** parameter set used by `New Empty Scratchpad`.
- The original `New Empty Scratchpad` sheet is left untouched. The app creates `Generated Scratchpad` so the reference sheet/formulas are not destroyed.
- Room number and Leaf Space are edited per-device in the Devices tab rather than generated from a naming rule.
- Static IP address sequencing is not automated yet.
- Controller Template / Equipment Definition lists are currently free-text, not pulled from a project database.
- The workbook's deterministic BACnet Instance convention is optional because the workbook's own `Column Descriptions` says SCT can assign an instance automatically.

## Run on your Mac

From the project folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

If you already created and activated `.venv`, you only need:

```bash
pip install -r requirements.txt
python main.py
```

## Run the tests

```bash
python -m unittest discover -s tests
```

## Suggested first test

Project & Network:

```text
Device Prefix:       MR-
Engine:              S3-SNE03
Trunk:               FC-1
Controller Part #:   M4-CVM03050-0
Controller Template: VAV-RH
Network:             MSTP
```

Equipment Group:

```text
Prefix:       VAV
Separator:    -
Start:        1
End:          5
Digits:       2
Starting MAC: 6
Manufacturer: Titus
Inlet:        8
```

The first record should calculate approximately:

```text
Equipment: VAV-01
Device:    MR-VAV-01
MAC:       6
Instance:  1003106
FQR:       031CV006
SA Area:   0.35
K Factor:  2.39
```

## Future build ideas

The next releases should add:

1. equipment-specific profiles (AHU, VAV, ERV, etc.);
2. dynamic parameter sets from `VAV SD Parms`, `VAV DD Parms`, `Heating Valves Parms`, and `Misc Parms`;
3. bulk room / leaf-space import and paste-from-Excel;
4. IP controller network addressing;
5. saved project files so you can stop and resume later;
6. better FQR scheme configuration;
7. validation against required SCT RAC fields;
8. a Windows standalone `.exe` via PyInstaller.

## Windows executable later

When the app is ready for Windows packaging, PyInstaller can bundle Python and the template into a standalone app. A typical build will be similar to:

```powershell
pyinstaller --noconsole --onefile --name "RAC Generator" --add-data "resources/RAC Schedule_Template_Updated.xlsx;resources" main.py
```

The exact packaging command can be finalized after the application features stabilize.
