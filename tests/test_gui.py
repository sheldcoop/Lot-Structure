"""The window: filling it in and pressing Create makes the folders."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
QtWidgets = pytest.importorskip('PySide6.QtWidgets')

from lot_structure import gui, tree  # noqa: E402


@pytest.fixture()
def window(tmp_path, monkeypatch):
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    eng, cust = tmp_path / 'eng', tmp_path / 'cust'
    (eng / 'Proj' / 'Part').mkdir(parents=True)
    cust.mkdir()
    shown = []
    monkeypatch.setattr(QtWidgets.QMessageBox, 'question',
                        lambda *a, **k: QtWidgets.QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(QtWidgets.QMessageBox, 'information', lambda _w, _t, text: shown.append(text))
    monkeypatch.setattr(QtWidgets.QMessageBox, 'warning', lambda _w, _t, text: shown.append(text))
    win = gui.Window(str(eng), str(cust))
    win.shown = shown
    yield win
    win.close()
    app.processEvents()


def test_starts_asking_new_project_or_lot(window):
    assert window.eng.isChecked()
    assert window.target.text() == 'Choose New project or New lot.'


def test_new_lot_creates_tree(window, tmp_path):
    window.new_lot.setChecked(True)
    window.project.setText('Proj')
    window.part.setText('Part')
    window.lot.setText('19621')
    lot = tmp_path / 'eng' / 'Proj' / 'Part' / '19621'
    assert str(lot) in window.target.text()
    window.create()
    assert window.shown[-1].startswith('Done. Created 310 new folders.')
    assert (lot / 'QVM' / 'BU-01' / 'Post ADP (Core Alignment)' / 'Panel-05' / 'Back').is_dir()
    assert 'already exists' in window.note.text()
    window.create()
    assert window.shown[-1].startswith('Done. Created 0 new folders.')


def test_new_lot_in_picked_folder(window, tmp_path):
    window.new_lot.setChecked(True)
    window.other_path.setText(str(tmp_path / 'eng' / 'Proj' / 'Part'))
    window.other.setChecked(True)
    assert not window.project.isEnabled()
    assert window.other_hint.isVisibleTo(window)
    window.lot.setText('1')
    window.num_bu.setValue(1)
    window.num_panel.setValue(1)
    window.create()
    assert window.shown[-1].startswith(f'Done. Created {len(tree.lot_folders(tmp_path, 1, 1))} new')


def test_missing_input_is_shown_not_created(window, tmp_path):
    window.new_project.setChecked(True)
    window.project.setText('New')
    window.lot.setText('1')
    assert window.target.text() == 'Part Number cannot be empty.'
    window.create()
    assert window.shown[-1] == 'Part Number cannot be empty.'
    assert not (tmp_path / 'eng' / 'New').exists()


def items(box):
    return [box.itemText(i) for i in range(box.count())]


def test_new_lot_dropdowns_list_existing_folders(window, tmp_path):
    (tmp_path / 'eng' / 'Proj' / 'Part2').mkdir()
    (tmp_path / 'eng' / 'Other').mkdir()
    (tmp_path / 'cust' / 'CustProj').mkdir()
    window.new_project.setChecked(True)
    assert items(window.project) == []                 # new project: typed
    window.new_lot.setChecked(True)
    assert items(window.project) == ['Other', 'Proj']
    assert items(window.part) == []
    window.project.setCurrentIndex(1)                  # pick Proj
    assert window.project.text() == 'Proj'
    assert items(window.part) == ['Part', 'Part2']
    window.part.setText('Part2')                       # typing still works
    window.lot.setText('1')
    assert str(tmp_path / 'eng' / 'Proj' / 'Part2' / '1') in window.target.text()
    window.cust.setChecked(True)
    assert items(window.project) == ['CustProj']
    assert window.project.text() == 'Proj'             # what was typed is kept
    assert items(window.part) == []
