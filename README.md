# RAC Generator v0.3

Python/Tkinter RAC Generator based on the supplied Johnson Controls **RAC Schedule Template** and reviewed against the SCT Release 18 Rapid Archive workflow.

## What this version does

- Saves and reopens complete, unfinished projects, including device data, manufacturer choices, group defaults, and equipment already in SCT.
- Saves working SCT CSVs before preflight and imports one or more SCT CSVs or existing RAC workbooks to continue editing.
- Preserves imported identifiers, network settings, and additional CAF parameters when saving and exporting.
- Generates equipment groups such as `VAV-01` through `VAV-20`.
- Supports custom equipment prefix, separator, start/end numbers, and digit padding.
- Generates device names from a configurable device prefix.
- Supports MS/TP or IP controller numbering.
- Shows DHCP, Subnet Mask, and IP Router controls only for IP networks; switching network type preserves entered settings.
- Supports either deterministic BACnet Instances or leaving Instance blank for SCT.
- Treats FQR separately from BACnet Instance:
  - **Device Name (SCT recommended)** is the default FQR mode.
  - the original custom workbook FQR convention remains optional.
- Reads VAV manufacturer Area / K Factor data from the workbook's `Manufacturer` sheet.
- Previews SA Area and K Factor beside the manufacturer/inlet selections in Equipment Group. Both values update immediately when either selection changes; unavailable values display a dash.
- Supports spreadsheet-style device editing: Enter saves and moves down, Tab saves and moves to the next editable column, and Shift reverses direction. Tab wraps between rows and skips calculated fields. Escape cancels the current edit; invalid values stay open for correction.
- Supports the five current Single-Duct VAV RAC parameters:
  - `SA-AREA` / `AV3111`
  - `SA-KFACTOR` / `AV3112`
  - `CLG-MAXFLOW` / `AV3108`
  - `CLGOCC-MINFLOW` / `AV3109`
  - `HTGOCC-MINFLOW` / `AV3110`
- Lets the user specify equipment that **already exists in SCT** so `Served By` references can be validated correctly.
- Builds a dependency graph from `Served By Equipment Name` and automatically calculates the required top-down SCT import order.
- Detects circular `Served By` relationships and unresolved serving equipment.
- Performs SCT preflight validation for required fields, FQRs, parent relationships, BACnet Instance range, MS/TP MAC range, duplicates, and duplicate MS/TP addresses on the same engine/trunk.
- Displays preflight results and export warnings in resizable, scrollable dialogs. Export warnings offer **Export anyway** and **Cancel**; closing the dialog cancels the export.
- Exports a master RAC workbook that includes:
  - `SCT Setup Guide`
  - `SCT Import Plan`
  - populated `Rapid Archive Schedule`
  - `Generated Scratchpad`
- Exports **staged SCT Rapid Archive CSV files** such as:
  - `SCT_01_Level_0.csv`
  - `SCT_02_Level_1.csv`
  - `SCT_03_Level_2.csv`

## Save your work and resume later

Use **Save Project** while building a database, even if required SCT fields are still blank. The `.rac.json` file stores all device data and editing settings, including manufacturer/inlet selections, group defaults, and equipment already in SCT. Use **Open Project** to pick up where you left off. Projects with only form settings and no generated devices can also be saved.

| Action | File | What it does |
| --- | --- | --- |
| **Save Project / Open Project** | `.rac.json` | Preserves the complete editing session. Recommended for unfinished work. |
| **Save Working CSV** | `.csv` | Saves all current schedule rows using the same six-header SCT v3 format as the final CSV exports, without requiring preflight to pass. |
| **Import Schedule** | `.csv` or `.xlsx` | Adds schedule rows to the current project. Select multiple files to combine staged schedules. Excel files must contain a `Rapid Archive Schedule` sheet. |
| **Export Staged SCT CSVs** | `.csv` files | Runs preflight and creates the final schedules in the required parent-before-child import order. |
| **Export Master Workbook** | `.xlsx` | Creates the existing RAC workbook with the schedule, setup guide, import plan, and scratchpad. |

For a CSV workflow, choose **Save Working CSV**, then use **File > New Project** and **Import Schedule** when you want to reopen it as a separate project. Import appends rows, so importing the same schedule twice adds duplicate rows; SCT Preflight will flag conflicts. A working CSV can still be incomplete and is not necessarily ready to import into SCT.

CSV contains the SCT schedule fields, but not manufacturer names, inlet selections, drawing notes, generation defaults, or the list of equipment already in SCT. Excel import reads the `Rapid Archive Schedule` sheet only; it does not restore scratchpad notes or other app settings. Use **Save Project** to retain all of those details. Saving a working CSV leaves the project marked as unsaved until you also save a project file.

Imported FQRs, BACnet Instances, SA Area, and K Factor are retained when editing other cells or using Recalculate. You can edit these values directly on imported rows. Changing a manufacturer/inlet selection explicitly updates that row's Area and K Factor. Additional CAF parameters retain their Attribute ID, Attribute Type, and values through CSV, project, and workbook exports; their values are not currently editable in the table.

The title shows `*` for unsaved project changes. Closing the app, opening another project, or starting a new one offers **Save**, **Discard**, or **Cancel** through the standard Yes/No/Cancel dialog. File > Save Project As creates a separate copy. Keyboard shortcuts are Ctrl+S, Ctrl+Shift+S, Ctrl+O, and Ctrl+N (Cmd on macOS).

Imports accept SCT Rapid Archive **v3** headers, including comma-, semicolon-, or tab-separated CSVs. Keep the six original header rows. Unsupported columns, invalid numbers, and Excel formulas are rejected with an error instead of silently dropping data. When importing multiple files, every file must load successfully before any rows are added. Arbitrary CWD/Excel layouts require a separate mapping and are not accepted as RAC schedules.

## Why staged files matter

SCT Rapid Archive requires serving equipment to exist before its child equipment is created. Johnson Controls recommends a top-down device hierarchy and separate Rapid Archive schedules by hierarchy level.

Example:

```text
Plant
  ↓
AHU
  ↓
VAV
```

RAC Generator therefore produces an import plan such as:

```text
1. Import SCT_01_Level_0.csv → Save in Rapid Archive
2. Import SCT_02_Level_1.csv → Save in Rapid Archive
3. Import SCT_03_Level_2.csv → Save in Rapid Archive
```

The user can enter equipment groups in any order; RAC Generator calculates the proper import order.

## What must already exist in SCT

Before importing the generated Rapid Archive files, verify the following in the SCT archive:

1. The **Site / Site Director** exists.
2. The required **supervisory devices (SNE/NAE/etc.)** exist.
3. The required **integration trunks** exist. `Engine Name` and `Trunk Name` in RAC must match SCT exactly.
4. Required **Equipment Definitions** exist or are imported.
5. Required **Controller Templates** exist under `Configuration > SCT Controller Templates`.
6. Each Controller Template has the correct **Definition Link** to its Equipment Definition.
7. Any serving equipment not generated by this project already exists in SCT and is listed in the app's **Equipment already in SCT** field.

### Creating an Equipment Definition

SCT Release 18 workflow:

```text
Facility
  > Prepare Rapid Archive
    > Insert Equipment Definition
```

Choose the Definitions folder, name/configure the definition, and finish the wizard. Johnson Controls recommends creating Equipment Definitions **bottom-up**: terminal units first, then AHUs, then central plant.

### Creating a Controller Template

SCT workflow:

```text
Insert
  > Object
    > Controller Template
```

Set the destination to:

```text
Configuration > SCT Controller Templates
```

Give the template a unique identifier and use the **Definition Link** browse control to link it to the proper Equipment Definition. Points can then be populated from a CAF, an existing controller, or manually.

> **Important:** `Equipment Definition Name` in the RAC schedule is a reference-only field. The functional Equipment Definition relationship used by Rapid Archive comes from the Controller Template's Definition Link.

## SCT import procedure

For each generated hierarchy level:

1. In SCT, open **Facility > Rapid Archive**.
2. Click **Edit** and **Import**.
3. Import the next staged CSV file.
4. Review Supervisory Device, Integration, spaces, addresses, Controller Template, CAF parameters, and Served By relationships.
5. Click **Save**.
6. Only after that save completes, import the next hierarchy level.

This order is required so `Served By Equipment Name` can resolve to an equipment object that already exists in the archive.

## Important limitations

- Generation and table editing of CAF parameters currently implement the Single-Duct VAV set used by the supplied scratchpad. Imports also preserve additional parameter columns for later export.
- Room Number and Leaf Space are edited per-device rather than generated from a naming rule.
- Static IP address sequencing is not automated yet. IP projects receive a preflight warning to verify DHCP/static IP configuration in SCT.
- Controller Template / Equipment Definition names are free text; RAC Generator cannot directly query an SCT archive to prove they exist.
- One-controller-to-multiple-equipment rows are recognized as a possible future/general use case, but the UI is still optimized for the common one-controller/one-equipment VAV workflow.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Tests

```bash
python -m unittest discover -s tests
```

UI tests use real Tk widgets and keyboard events. On Linux without a display, they are skipped; run them with Xvfb installed:

```bash
xvfb-run -a python -m unittest discover -s tests -v
```

GitHub Actions runs the file round-trip, logic, and UI tests with a virtual display. File tests cover incomplete projects, SCT CSV and RAC workbook imports, extra CAF parameters, and preservation of a previous file when a save fails. UI tests also cover save/open, cancelled saves, and importing schedules without losing current work.

## Next improvements

1. equipment-specific profiles (AHU, VAV, ERV, central plant, etc.);
2. dynamic parameter sets from the additional parameter sheets;
3. bulk room / leaf-space import and paste-from-Excel;
4. complete static IP sequencing and validation;
5. project-specific FQR schemes;
6. explicit multi-equipment-per-controller workflow;
7. Windows standalone `.exe` packaging.
