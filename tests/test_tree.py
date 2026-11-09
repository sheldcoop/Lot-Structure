"""The folder tree and the checks - the same as Lot_Structure_v5.bat, plus QVM BU-01 Post ADP."""

from __future__ import annotations

from pathlib import Path

import pytest

from lot_structure import tree
from lot_structure.tree import CUST, ENG, OTHER, Request


def relative(lot_root: Path, num_bu: int = 5, num_panel: int = 5) -> set[str]:
    return {p.relative_to(lot_root).as_posix() for p in tree.lot_folders(lot_root, num_bu, num_panel)}


def test_names_are_zero_padded():
    assert tree.layers(3) == ['BU-01', 'BU-02', 'BU-03']
    assert tree.panels(12)[-1] == 'Panel-12'


def test_processes_per_tool():
    assert tree.processes('AOI', 'BU-01') == ('Post FET',)
    assert tree.processes('AOI', 'BU-03') == ('Post FET',)
    assert tree.processes('HRM', 'BU-01') == ('Post ADP', 'Post PFC')
    assert tree.processes('HRM', 'BU-02') == ('Post AOP', 'Post PFC')
    assert tree.processes('QVM', 'BU-01') == ('Post ADP (Core Alignment)', 'Post PFC (PTV)',
                                              'Post DSM (VTP)')
    assert tree.processes('QVM', 'BU-02') == ('Post PFC (PTV)', 'Post DSM (VTP)')
    assert tree.processes('PRF', 'BU-05') == ('Post DSM',)


def test_default_lot_has_310_end_folders():
    # per build-up and panel: 2 sides. AOI 1, HRM 2, QVM 2 (+1 in BU-01), PRF 1 process
    folders = tree.lot_folders(Path('lot'), 5, 5)
    assert len(folders) == 5 * 5 * 2 * (1 + 2 + 2 + 1) + 5 * 2
    assert len(set(folders)) == len(folders)


def test_example_paths():
    names = relative(Path('lot'))
    assert 'AOI/BU-01/Post FET/Panel-01/Front' in names
    assert 'HRM/BU-01/Post ADP/Panel-05/Back' in names
    assert 'HRM/BU-02/Post AOP/Panel-01/Front' in names
    assert 'HRM/BU-02/Post ADP/Panel-01/Front' not in names
    assert 'QVM/BU-01/Post ADP (Core Alignment)/Panel-03/Back' in names
    assert 'QVM/BU-02/Post ADP (Core Alignment)/Panel-03/Back' not in names
    assert 'QVM/BU-05/Post DSM (VTP)/Panel-05/Front' in names
    assert 'PRF/BU-04/Post DSM/Panel-02/Back' in names
    assert not any(name.split('/')[1] == 'BU-06' for name in names)


def test_create_never_overwrites(tmp_path):
    lot = tmp_path / 'lot'
    folders = tree.lot_folders(lot, 2, 2)
    keep = lot / 'PRF' / 'BU-01' / 'Post DSM' / 'Panel-01' / 'Front' / 'Site001.txt'
    keep.parent.mkdir(parents=True)
    keep.write_text('measurement')

    made, failed = tree.create(folders)
    assert failed == []
    assert made == len(folders) - 1
    assert keep.read_text() == 'measurement'
    assert all(folder.is_dir() for folder in folders)

    again, failed = tree.create(folders)
    assert (again, failed) == (0, [])


def test_create_adds_only_missing_build_ups(tmp_path):
    lot = tmp_path / 'lot'
    tree.create(tree.lot_folders(lot, 2, 2))
    made, _ = tree.create(tree.lot_folders(lot, 3, 2))
    assert made == len(tree.lot_folders(lot, 3, 2)) - len(tree.lot_folders(lot, 2, 2))


def test_create_reports_failures_and_goes_on(tmp_path):
    lot = tmp_path / 'lot'
    (lot / 'AOI').parent.mkdir(parents=True)
    (lot / 'AOI').write_text('a file where a folder should be')
    folders = tree.lot_folders(lot, 1, 1)
    made, failed = tree.create(folders)
    assert len(failed) == 2                       # AOI Front and Back
    assert made == len(folders) - 2


@pytest.mark.parametrize('typed, cleaned', [
    ('"C:\\data\\lots\\"', 'C:\\data\\lots'),
    ('  C:\\data  ', 'C:\\data'),
    ('C:\\', 'C:\\'),
    ('/home/x/', '/home/x'),
])
def test_clean_path(typed, cleaned):
    assert tree.clean_path(typed) == cleaned


# ---------- where the lot goes ----------

@pytest.fixture()
def bases(tmp_path):
    eng, cust = tmp_path / 'eng', tmp_path / 'cust'
    (eng / 'Chiplet4Future' / 'FHR0089').mkdir(parents=True)
    cust.mkdir()
    return str(eng), str(cust)


def resolve(req, bases):
    return tree.resolve(req, *bases)


def test_must_choose_project_or_lot(bases):
    assert resolve(Request(new_project=None, lot='1'), bases) == (None, 'Choose New project or New lot.')


def test_new_project_in_engineering(bases):
    req = Request(new_project=True, project=' "NewProj" ', part='P1', lot='19555')
    assert resolve(req, bases) == (Path(bases[0]) / 'NewProj' / 'P1' / '19555', '')


def test_new_project_in_customer(bases):
    req = Request(new_project=True, base=CUST, project='A', part='B', lot='19178.01')
    assert resolve(req, bases) == (Path(bases[1]) / 'A' / 'B' / '19178.01', '')


@pytest.mark.parametrize('field, message', [
    ('project', 'Project name cannot be empty.'),
    ('part', 'Part Number cannot be empty.'),
    ('lot', 'Lot Number cannot be empty.'),
])
def test_new_project_required_fields(bases, field, message):
    values = {'project': 'A', 'part': 'B', 'lot': '1', field: '  '}
    assert resolve(Request(new_project=True, **values), bases) == (None, message)


def test_new_lot_needs_existing_project_and_part(bases):
    root = Path(bases[0])
    lot, problem = resolve(Request(new_project=False, project='Nope', part='FHR0089', lot='1'), bases)
    assert lot is None and problem.startswith('Project not found')
    lot, problem = resolve(Request(new_project=False, project='Chiplet4Future', part='X', lot='1'), bases)
    assert lot is None and problem.startswith('Part Number not found')
    req = Request(new_project=False, project='Chiplet4Future', part='FHR0089', lot='19621')
    assert resolve(req, bases) == (root / 'Chiplet4Future' / 'FHR0089' / '19621', '')


def test_new_lot_in_other_folder_is_the_part_folder(bases):
    part = Path(bases[0]) / 'Chiplet4Future' / 'FHR0089'
    req = Request(new_project=False, base=OTHER, other_path=f'"{part}\\"', lot='19621')
    assert req.part_from_path
    assert resolve(req, bases) == (part / '19621', '')


def test_new_project_in_other_folder_is_the_base(bases):
    req = Request(new_project=True, base=OTHER, other_path=bases[1], project='A', part='B', lot='1')
    assert resolve(req, bases) == (Path(bases[1]) / 'A' / 'B' / '1', '')


def test_base_must_exist(bases, tmp_path):
    lot, problem = resolve(Request(new_project=True, base=OTHER, other_path=str(tmp_path / 'missing'),
                                   project='A', part='B', lot='1'), bases)
    assert lot is None and problem.startswith('That folder does not exist')
    lot, problem = resolve(Request(new_project=True, base=OTHER, project='A', part='B', lot='1'), bases)
    assert lot is None and problem == 'Type, paste or browse to a folder.'


def test_subfolders_sorted_folders_only(tmp_path):
    for name in ('b', 'A', 'c', '.hidden'):
        (tmp_path / name).mkdir()
    (tmp_path / 'file.txt').write_text('x')
    assert tree.subfolders(tmp_path) == ['A', 'b', 'c']
    assert tree.subfolders(tmp_path / 'missing') == []


@pytest.mark.parametrize('lot', ['19178/02', '19178\\02', '19:02', 'a*b', 'a?b', 'a<b', 'a>b', 'a|b'])
def test_lot_with_character_windows_does_not_allow(bases, lot):
    found, problem = resolve(Request(new_project=True, project='A', part='B', lot=lot), bases)
    assert found is None
    assert problem.startswith('Lot Number: character ')


@pytest.mark.parametrize('lot', ['19178.02', '19555', '19178.01 rework', '19178_02-A'])
def test_lot_names_that_are_fine(bases, lot):
    req = Request(new_project=True, project='A', part='B', lot=lot)
    assert resolve(req, bases) == (Path(bases[0]) / 'A' / 'B' / lot, '')


def test_project_and_part_with_character_windows_does_not_allow(bases):
    _, problem = resolve(Request(new_project=True, project='A/B', part='P', lot='1'), bases)
    assert problem.startswith('Project name: character /')
    _, problem = resolve(Request(new_project=True, project='A', part='P:1', lot='1'), bases)
    assert problem.startswith('Part Number: character :')
    _, problem = resolve(Request(new_project=False, project='Chiplet4Future', part='F|1', lot='1'), bases)
    assert problem.startswith('Part Number: character |')
