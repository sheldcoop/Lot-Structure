# Lot Structure

Builds the measurement folder tree for a lot. This is the window version of `Lot_Structure_v5.bat`.

```
Base\Project\PartNumber\LotNumber\<tool tree with build-ups>
```

Nothing is ever overwritten or deleted: only missing folders are made. Running it again on an
existing lot only **adds** missing folders (e.g. a 6th build-up).

## Start
Double-click `Lot_Structure.bat` (Windows, Python 3.10+). The first start creates `.venv` and
installs PySide6, which takes a minute.

## Using it
1. **What**: NEW PROJECT (type project, part number and lot) or NEW LOT (add a lot to a project
   that already exists; the project and part folder must be there).
2. **Where**: Engineering lots (default), Customer shippable lots, or **Other folder** (type /
   paste a path or *Browse*). For a NEW LOT in an other folder, that folder **is** the part
   folder and the lot is made directly in it.
3. **Lot**: Lot Number (e.g. `19555` or `19178.01`), Build-Ups and Panels (5 each by default).

The window shows where the lot will go, or what is still missing. **Create** shows the summary to
check, then makes the folders and tells how many new folders were made.

## The tree
Every end folder has `Panel-01 … Panel-NN\Front|Back` under it.

| Tool | BU-01 | BU-02 … BU-NN |
|---|---|---|
| AOI | Post FET | Post FET |
| HRM | Post ADP, Post PFC | Post AOP, Post PFC |
| QVM | **Post ADP (Core Alignment)**, Post PFC (PTV), Post DSM (VTP) | Post PFC (PTV), Post DSM (VTP) |
| PRF | Post DSM | Post DSM |

No Solder Resist, no Core layer. 5 build-ups × 5 panels = 310 end folders.

**Change from v5:** QVM BU-01 also gets `Post ADP (Core Alignment)`.

## The two standard paths
At the top of `src/lot_structure/tree.py` (`PATH_ENG`, `PATH_CUST`).

## Development
```bash
.venv/bin/python -m pip install -e .[dev]
.venv/bin/python -m pytest
```
