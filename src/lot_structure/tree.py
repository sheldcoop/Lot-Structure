"""The folder tree of a lot, and where it goes.

Same rules as Lot_Structure_v5.bat:

    Base\\Project\\PartNumber\\LotNumber\\<tool tree with build-ups>

    AOI\\BU-xx\\Post FET\\Panel-xx\\Front|Back
    HRM\\BU-01\\Post ADP | Post PFC                       \\Panel-xx\\Front|Back
    HRM\\BU-xx\\Post AOP | Post PFC                       \\Panel-xx\\Front|Back
    QVM\\BU-01\\Post ADP (Core Alignment) | Post PFC (PTV) | Post DSM (VTP)\\Panel-xx\\Front|Back
    QVM\\BU-xx\\Post PFC (PTV) | Post DSM (VTP)          \\Panel-xx\\Front|Back
    PRF\\BU-xx\\Post DSM\\Panel-xx\\Front|Back

Change from v5: QVM BU-01 also gets "Post ADP (Core Alignment)".

Nothing is ever overwritten or deleted - folders are only made when missing.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

# ============================================================
#   EDIT HERE - the two standard paths
# ============================================================
PATH_ENG = r'L:\ale\ics_htb3_rnd\130 - measurement results\02_Engineering lots'
PATH_CUST = r'L:\ale\ics_htb3_rnd\130 - measurement results\01_Customer shippable lots'
# ============================================================

TOOLS = ('AOI', 'HRM', 'QVM', 'PRF')
SIDES = ('Front', 'Back')
FIRST_LAYER = 'BU-01'

ENG, CUST, OTHER = 'eng', 'cust', 'other'


def layers(count: int) -> list[str]:
    return [f'BU-{i:02d}' for i in range(1, count + 1)]


def panels(count: int) -> list[str]:
    return [f'Panel-{i:02d}' for i in range(1, count + 1)]


def processes(tool: str, layer: str) -> tuple[str, ...]:
    """The process folders of one tool in one build-up."""
    first = layer == FIRST_LAYER
    if tool == 'AOI':
        return ('Post FET',)
    if tool == 'HRM':
        return ('Post ADP', 'Post PFC') if first else ('Post AOP', 'Post PFC')
    if tool == 'QVM':
        core = ('Post ADP (Core Alignment)',) if first else ()
        return core + ('Post PFC (PTV)', 'Post DSM (VTP)')
    if tool == 'PRF':
        return ('Post DSM',)
    raise ValueError(f'unknown tool {tool!r}')


def lot_folders(lot_root: Path, num_bu: int, num_panel: int) -> list[Path]:
    """Every end folder of the lot, in the same order as the .bat makes them."""
    folders = []
    for tool in TOOLS:
        for layer in layers(num_bu):
            for process in processes(tool, layer):
                for panel in panels(num_panel):
                    for side in SIDES:
                        folders.append(lot_root / tool / layer / process / panel / side)
    return folders


def subfolders(path: Path) -> list[str]:
    """The folder names inside path, sorted (empty when it cannot be read)."""
    try:
        names = [entry.name for entry in path.iterdir()
                 if entry.is_dir() and not entry.name.startswith('.')]
    except OSError:
        return []
    return sorted(names, key=str.casefold)


def clean_name(text: str) -> str:
    """A typed name without quotes and surrounding spaces."""
    return text.replace('"', '').strip()


def clean_path(text: str) -> str:
    """A typed / pasted path without quotes, surrounding spaces and a trailing backslash."""
    text = clean_name(text)
    while len(text) > 1 and text[-1] in '\\/' and not text.endswith(':\\'):
        text = text[:-1]
    return text


@dataclass
class Request:
    """What was filled in on the window."""
    new_project: bool | None          # None = not chosen yet
    base: str = ENG                   # ENG, CUST or OTHER
    other_path: str = ''
    project: str = ''
    part: str = ''
    lot: str = ''
    num_bu: int = 5
    num_panel: int = 5

    @property
    def part_from_path(self) -> bool:
        """New lot in a pasted / picked folder: that folder IS the part folder."""
        return self.new_project is False and self.base == OTHER


def base_path(req: Request, path_eng: str = PATH_ENG, path_cust: str = PATH_CUST) -> str:
    if req.base == ENG:
        return path_eng
    if req.base == CUST:
        return path_cust
    return clean_path(req.other_path)


def resolve(req: Request, path_eng: str = PATH_ENG,
            path_cust: str = PATH_CUST) -> tuple[Path | None, str]:
    """The lot folder, or (None, what is wrong) - the same checks as the .bat, in the same order."""
    if req.new_project is None:
        return None, 'Choose New project or New lot.'
    base_text = base_path(req, path_eng, path_cust)
    if not base_text:
        return None, 'Type, paste or browse to a folder.'
    base = Path(base_text)
    if not base.is_dir():
        return None, f'That folder does not exist:\n{base}'

    project, part = clean_name(req.project), clean_name(req.part)
    if req.part_from_path:
        part_root = base
    elif req.new_project:
        if not project:
            return None, 'Project name cannot be empty.'
        if not part:
            return None, 'Part Number cannot be empty.'
        part_root = base / project / part
    else:
        if not project:
            return None, 'Project name cannot be empty.'
        if not (base / project).is_dir():
            return None, (f'Project not found:\n{base / project}\n'
                          'Check the spelling, or choose New project.')
        if not part:
            return None, 'Part Number cannot be empty.'
        if not (base / project / part).is_dir():
            return None, f'Part Number not found:\n{base / project / part}'
        part_root = base / project / part

    lot = clean_name(req.lot)
    if not lot:
        return None, 'Lot Number cannot be empty.'
    if req.num_bu < 1:
        return None, 'Build-Ups must be a whole number of 1 or more.'
    if req.num_panel < 1:
        return None, 'Panels must be a whole number of 1 or more.'
    return part_root / lot, ''


def create(folders: list[Path],
           progress: Callable[[int], None] | None = None) -> tuple[int, list[tuple[Path, str]]]:
    """Make the folders that are missing. Returns (how many were made, [(folder, error)])."""
    made, failed = 0, []
    for number, folder in enumerate(folders, 1):
        try:
            if not folder.exists():
                folder.mkdir(parents=True, exist_ok=True)
                made += 1
        except OSError as exc:
            failed.append((folder, exc.strerror or str(exc)))
        if progress:
            progress(number)
    return made, failed
