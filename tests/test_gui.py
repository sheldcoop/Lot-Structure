"""The window: filling it in and pressing Create makes the folders."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
QtWidgets = pytest.importorskip('PySide6.QtWidgets')

from lot_structure import gui, tree  # noqa: E402


def settings(tmp_path):
    from PySide6.QtCore import QSettings
    return QSettings(str(tmp_path / 'settings.ini'), QSettings.Format.IniFormat)


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
    opened = []
    monkeypatch.setattr(gui, 'open_folder', opened.append)
    win = gui.Window(str(eng), str(cust), settings(tmp_path))
    win.open_pressed = False
    monkeypatch.setattr(win, 'done', lambda text, warning=False: shown.append(text) or win.open_pressed)
    win.shown = shown
    win.opened = opened
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


def test_open_folder_after_create(window, tmp_path):
    window.new_lot.setChecked(True)
    window.project.setText('Proj')
    window.part.setText('Part')
    window.lot.setText('19178.02')
    window.create()
    assert window.opened == []                          # Close pressed
    window.open_pressed = True
    window.create()
    assert window.opened == [tmp_path / 'eng' / 'Proj' / 'Part' / '19178.02']


def test_done_message_has_open_folder_button(tmp_path, monkeypatch):
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    win = gui.Window(str(tmp_path), str(tmp_path), settings(tmp_path))
    seen = {}

    def press(box):
        seen['buttons'] = [b.text() for b in box.buttons()]
        box.defaultButton().click()
        return 0

    monkeypatch.setattr(QtWidgets.QMessageBox, 'exec', press)
    assert win.done('Done.') is True
    assert 'Open folder' in seen['buttons']
    win.close()
    app.processEvents()


def test_remembers_last_choices(tmp_path):
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    first = gui.Window(str(tmp_path), str(tmp_path), settings(tmp_path))
    assert first.eng.isChecked() and first.num_bu.value() == 5     # nothing saved yet
    first.new_lot.setChecked(True)
    first.cust.setChecked(True)
    first.project.setText('Proj')
    first.part.setText('Part')
    first.lot.setText('19178.02')
    first.num_bu.setValue(7)
    first.num_panel.setValue(3)
    first.close()

    second = gui.Window(str(tmp_path), str(tmp_path), settings(tmp_path))
    assert second.cust.isChecked()
    assert (second.project.text(), second.part.text()) == ('Proj', 'Part')
    assert (second.num_bu.value(), second.num_panel.value()) == (7, 3)
    assert second.lot.text() == ''                                  # lot starts empty
    assert not second.new_project.isChecked() and not second.new_lot.isChecked()
    second.close()
    app.processEvents()


def preview_texts(window):
    found = []

    def walk(item, path):
        path = path + (item.text(0),)
        found.append(('/'.join(path), item.foreground(0).color().name()))
        for i in range(item.childCount()):
            walk(item.child(i), path)

    for i in range(window.preview.topLevelItemCount()):
        walk(window.preview.topLevelItem(i), ())
    return dict(found)


def test_preview_matches_what_create_makes(window, tmp_path):
    names = preview_texts(window)
    leaves = {name for name in names if name.endswith(('/Front', '/Back'))}
    assert leaves == {p.relative_to(tmp_path).as_posix() for p in tree.lot_folders(tmp_path, 5, 5)}
    assert 'QVM/BU-01/Post ADP (Core Alignment)' in names
    assert window.preview_count.text() == '310 end folders, all new'
    window.num_bu.setValue(1)
    window.num_panel.setValue(1)
    assert window.preview_count.text() == f'{len(tree.lot_folders(tmp_path, 1, 1))} end folders, all new'


def test_preview_shows_existing_folders_grey(window, tmp_path):
    window.new_lot.setChecked(True)
    window.project.setText('Proj')
    window.part.setText('Part')
    window.lot.setText('1')
    window.num_bu.setValue(1)
    window.create()
    total = len(tree.lot_folders(tmp_path, 1, 5))
    assert window.preview_count.text() == f'{total} end folders: 0 new, {total} already exist'
    window.num_bu.setValue(2)
    added = len(tree.lot_folders(tmp_path, 2, 5)) - total
    assert window.preview_count.text() == f'{total + added} end folders: {added} new, {total} already exist'
    names = preview_texts(window)
    assert names['AOI/BU-01'] == '#9aa5b1'                 # all there: grey
    assert names['AOI/BU-02'] != '#9aa5b1'                 # new
    assert names['AOI'] != '#9aa5b1'                       # partly new
