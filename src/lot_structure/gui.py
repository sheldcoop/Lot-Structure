"""The Lot Structure window (PySide6 / Qt) - same look as PRF Insight."""

from __future__ import annotations

import sys
import traceback
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QUrl
from PySide6.QtGui import QCloseEvent, QDesktopServices
from PySide6.QtWidgets import (QApplication, QButtonGroup, QComboBox, QCompleter, QFileDialog,
                               QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                               QProgressBar, QPushButton, QRadioButton, QSpinBox, QVBoxLayout,
                               QWidget)

from lot_structure import VERSION
from lot_structure import tree
from lot_structure.tree import CUST, ENG, OTHER, Request

APP = 'Lot Structure'

STYLE = """
QWidget { font-size: 10pt; }
#Title { font-size: 15pt; font-weight: 600; }
#Hint { color: #5d6b7a; }
#Error { color: #a4262c; }
#Target { font-weight: 600; }
#Note { color: #9a6700; }
QGroupBox { font-weight: 600; border: 1px solid #c9d3de; border-radius: 8px;
            margin-top: 10px; padding: 10px 8px 6px 8px; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
QPushButton { padding: 6px 12px; }
QPushButton#Primary { background: #2f6da8; color: white; border-radius: 4px; font-weight: 600;
                      padding: 8px 24px; }
QPushButton#Primary:disabled { background: #9db5cc; }
"""


def hint(text: str = '') -> QLabel:
    label = QLabel(text)
    label.setObjectName('Hint')
    label.setWordWrap(True)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return label


class FolderBox(QComboBox):
    """A name you can type, or pick from the folders that are already there."""

    def __init__(self) -> None:
        super().__init__()
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.setMaxVisibleItems(20)
        completer = QCompleter(self.model(), self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.setCompleter(completer)
        self._names: list[str] = []

    def text(self) -> str:
        return self.currentText()

    def setText(self, text: str) -> None:  # noqa: N802
        self.setEditText(text)

    def setPlaceholderText(self, text: str) -> None:  # noqa: N802
        self.lineEdit().setPlaceholderText(text)

    def set_names(self, names: list[str]) -> None:
        """Fill the list, keeping what is typed."""
        if names == self._names:
            return
        self._names = names
        text = self.currentText()
        self.blockSignals(True)
        self.clear()
        self.addItems(names)
        self.setCurrentIndex(-1)
        self.setEditText(text)
        self.blockSignals(False)


class Window(QWidget):
    def __init__(self, path_eng: str = tree.PATH_ENG, path_cust: str = tree.PATH_CUST,
                 settings: QSettings | None = None) -> None:
        super().__init__()
        # last choices, per Windows user (registry); a test passes its own file
        self.settings = settings if settings is not None else QSettings('Lot Structure', APP)
        self.path_eng, self.path_cust = path_eng, path_cust
        self.setWindowTitle(f'{APP} {VERSION}')
        self.setMinimumWidth(640)

        title = QLabel('Create a measurement lot folder tree')
        title.setObjectName('Title')

        # ---------- 1. New project or new lot ----------
        self.new_project = QRadioButton('NEW PROJECT  -  type project, part number and lot')
        self.new_lot = QRadioButton('NEW LOT  -  add a lot to a project that already exists')
        self.what = QButtonGroup(self)
        for button in (self.new_project, self.new_lot):
            self.what.addButton(button)
        what_box = QGroupBox('1.  What do you want to create?')
        what_layout = QVBoxLayout(what_box)
        what_layout.addWidget(self.new_project)
        what_layout.addWidget(self.new_lot)

        # ---------- 2. Base folder ----------
        self.eng = QRadioButton('Engineering lots')
        self.cust = QRadioButton('Customer shippable lots')
        self.other = QRadioButton('Other folder')
        self.eng.setChecked(True)
        self.where = QButtonGroup(self)
        for button in (self.eng, self.cust, self.other):
            self.where.addButton(button)
        self.other_path = QLineEdit()
        self.other_path.setPlaceholderText('Type / paste a path, or Browse')
        self.browse = QPushButton('Browse...')
        self.browse.clicked.connect(self.pick_folder)
        other_row = QHBoxLayout()
        other_row.addWidget(self.other)
        other_row.addWidget(self.other_path, 1)
        other_row.addWidget(self.browse)
        self.other_hint = hint('This folder is taken as the part folder: '
                               'the new lot is created directly in it.')
        where_box = QGroupBox('2.  Where?')
        where_layout = QVBoxLayout(where_box)
        where_layout.addWidget(self.eng)
        where_layout.addWidget(hint(f'      {path_eng}'))
        where_layout.addWidget(self.cust)
        where_layout.addWidget(hint(f'      {path_cust}'))
        where_layout.addLayout(other_row)
        where_layout.addWidget(self.other_hint)

        # ---------- 3. Lot ----------
        self.project = FolderBox()
        self.part = FolderBox()
        self.lot = QLineEdit()
        self.lot.setPlaceholderText('e.g. 19555 or 19178.01')
        self.num_bu = QSpinBox()
        self.num_panel = QSpinBox()
        for spin in (self.num_bu, self.num_panel):
            spin.setRange(1, 99)
            spin.setValue(5)
            spin.setFixedWidth(80)
        lot_box = QGroupBox('3.  Lot')
        form = QFormLayout(lot_box)
        form.addRow('Project name', self.project)
        form.addRow('Part Number', self.part)
        form.addRow('Lot Number', self.lot)
        form.addRow('Build-Ups', self.num_bu)
        form.addRow('Panels', self.num_panel)

        # ---------- Result ----------
        self.target = QLabel()
        self.target.setObjectName('Target')
        self.target.setWordWrap(True)
        self.target.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.note = QLabel()
        self.note.setWordWrap(True)
        self.progress = QProgressBar()
        self.progress.hide()
        self.create_button = QPushButton('Create')
        self.create_button.setObjectName('Primary')
        self.create_button.clicked.connect(self.create)
        button_row = QHBoxLayout()
        button_row.addWidget(self.progress, 1)
        button_row.addStretch()
        button_row.addWidget(self.create_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.addWidget(title)
        layout.addWidget(hint('Nothing is ever overwritten or deleted - only missing folders are '
                              'made. Running it again on an existing lot only ADDS missing folders.'))
        layout.addWidget(what_box)
        layout.addWidget(where_box)
        layout.addWidget(lot_box)
        layout.addWidget(self.target)
        layout.addWidget(self.note)
        layout.addStretch()
        layout.addLayout(button_row)

        self._listed: dict[Path, list[str]] = {}
        for button in (self.new_project, self.new_lot, self.eng, self.cust, self.other):
            button.toggled.connect(self._listed.clear)   # read the folders again
            button.toggled.connect(self.refresh)
        for edit in (self.other_path, self.lot):
            edit.textChanged.connect(self.refresh)
        for box in (self.project, self.part):
            box.editTextChanged.connect(self.refresh)
        for spin in (self.num_bu, self.num_panel):
            spin.valueChanged.connect(self.refresh)
        self.other_path.textEdited.connect(lambda: self.other.setChecked(True))
        self.load_choices()
        self.refresh()

    # ---------- reading the window ----------
    def request(self) -> Request:
        if self.new_project.isChecked():
            new_project = True
        elif self.new_lot.isChecked():
            new_project = False
        else:
            new_project = None
        base = ENG if self.eng.isChecked() else CUST if self.cust.isChecked() else OTHER
        return Request(new_project=new_project, base=base, other_path=self.other_path.text(),
                       project=self.project.text(), part=self.part.text(), lot=self.lot.text(),
                       num_bu=self.num_bu.value(), num_panel=self.num_panel.value())

    def resolve(self) -> tuple[Path | None, str]:
        return tree.resolve(self.request(), self.path_eng, self.path_cust)

    def refresh(self) -> None:
        req = self.request()
        from_path = req.part_from_path
        self.other_hint.setVisible(from_path)
        for edit in (self.project, self.part):
            edit.setEnabled(not from_path)
        if from_path:
            self.project.setPlaceholderText('(from path)')
            self.part.setPlaceholderText('(from path)')
        elif req.new_project is False:
            self.project.setPlaceholderText('Existing project name')
            self.part.setPlaceholderText('Existing Part Number')
        else:
            self.project.setPlaceholderText('e.g. Chiplet4Future')
            self.part.setPlaceholderText('e.g. FHR0089')
        self.fill_lists(req)

        lot_root, problem = self.resolve()
        if lot_root is None:
            self.target.setObjectName('Error')
            self.target.setText(problem)
            self.note.setText('')
        else:
            self.target.setObjectName('Target')
            self.target.setText(f'Will be created in:\n{lot_root}')
            if lot_root.is_dir():
                self.note.setObjectName('Note')
                self.note.setText('NOTE: this lot already exists. Only missing folders will be '
                                  'added, nothing existing is changed or deleted.')
            else:
                self.note.setText('')
        for label in (self.target, self.note):
            label.style().unpolish(label)
            label.style().polish(label)

    def fill_lists(self, req: Request) -> None:
        """NEW LOT: the dropdowns list the projects / part numbers that are already there."""
        projects, parts = [], []
        if req.new_project is False and not req.part_from_path:
            base = Path(tree.base_path(req, self.path_eng, self.path_cust))
            projects = self.listing(base)
            project = tree.clean_name(req.project)
            if project in projects:
                parts = self.listing(base / project)
        self.project.set_names(projects)
        self.part.set_names(parts)

    # ---------- last choices ----------
    def load_choices(self) -> None:
        """The choices of last time. New project / New lot is asked every time; Lot starts empty."""
        value = self.settings.value
        {CUST: self.cust, OTHER: self.other}.get(value('base', ENG), self.eng).setChecked(True)
        self.other_path.setText(str(value('other_path', '')))
        self.project.setText(str(value('project', '')))
        self.part.setText(str(value('part', '')))
        for spin, key in ((self.num_bu, 'num_bu'), (self.num_panel, 'num_panel')):
            try:
                spin.setValue(int(value(key, 5)))
            except (TypeError, ValueError):
                spin.setValue(5)

    def save_choices(self) -> None:
        req = self.request()
        for key, val in (('base', req.base), ('other_path', req.other_path),
                         ('project', req.project), ('part', req.part),
                         ('num_bu', req.num_bu), ('num_panel', req.num_panel)):
            self.settings.setValue(key, val)
        self.settings.sync()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        self.save_choices()
        super().closeEvent(event)

    def listing(self, path: Path) -> list[str]:
        """The folders in path, read once (not again for every key typed)."""
        if path not in self._listed:
            self._listed[path] = tree.subfolders(path)
        return self._listed[path]

    def pick_folder(self) -> None:
        start = tree.clean_path(self.other_path.text()) or self.path_eng
        folder = QFileDialog.getExistingDirectory(self, 'Select the folder', start)
        if folder:
            self.other_path.setText(str(Path(folder)))
            self.other.setChecked(True)

    # ---------- making the folders ----------
    def summary(self, req: Request, lot_root: Path) -> str:
        mode = 'NEW PROJECT' if req.new_project else 'NEW LOT in an existing project'
        lines = [f'Mode:\t{mode}',
                 f'Folder:\t{lot_root}',
                 f'Build-ups:\t{" ".join(tree.layers(req.num_bu))}',
                 f'Panels:\t{" ".join(tree.panels(req.num_panel))}',
                 f'Sides:\t{", ".join(tree.SIDES)}',
                 f'Tools:\t{", ".join(tree.TOOLS)}']
        if lot_root.is_dir():
            lines += ['', 'NOTE: this lot already exists. Only missing folders will be added,',
                      'nothing existing is changed or deleted.']
        return '\n'.join(lines)

    def create(self) -> None:
        req = self.request()
        lot_root, problem = self.resolve()
        if lot_root is None:
            QMessageBox.warning(self, APP, problem)
            return
        answer = QMessageBox.question(self, f'{APP} - please check before creating',
                                      self.summary(req, lot_root) + '\n\nCreate?')
        if answer != QMessageBox.StandardButton.Yes:
            return

        folders = tree.lot_folders(lot_root, req.num_bu, req.num_panel)
        self.setEnabled(False)
        self.progress.setRange(0, len(folders))
        self.progress.setValue(0)
        self.progress.show()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        def step(number: int) -> None:
            self.progress.setValue(number)
            QApplication.processEvents()

        try:
            made, failed = tree.create(folders, step)
        finally:
            QApplication.restoreOverrideCursor()
            self.setEnabled(True)
            self.progress.hide()
        self._listed.clear()
        self.save_choices()
        self.refresh()

        text = f'Done. Created {made} new folders.'
        if made == 0 and not failed:
            text += '\n(Everything already existed - nothing was overwritten.)'
        if failed:
            shown = '\n'.join(f'{folder}\n    {error}' for folder, error in failed[:10])
            more = f'\n... and {len(failed) - 10} more' if len(failed) > 10 else ''
            text += f'\n\n{len(failed)} folders could not be made:\n{shown}{more}'
        else:
            text += f'\n\n{lot_root}'
        if self.done(text, warning=bool(failed)) and lot_root.is_dir():
            open_folder(lot_root)

    def done(self, text: str, warning: bool = False) -> bool:
        """The result, with an Open folder button. True when Open folder was pressed."""
        box = QMessageBox(QMessageBox.Icon.Warning if warning else QMessageBox.Icon.Information,
                          APP, text, parent=self)
        open_button = box.addButton('Open folder', QMessageBox.ButtonRole.AcceptRole)
        box.addButton(QMessageBox.StandardButton.Close)
        box.setDefaultButton(open_button)
        box.exec()
        return box.clickedButton() is open_button


def open_folder(path: Path) -> None:
    """Show the folder in Explorer (Finder / file manager elsewhere)."""
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

def start(project_dir: Path) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(APP)
    app.setStyle('Fusion')
    app.setStyleSheet(STYLE)
    log = project_dir / 'window_errors.log'

    def report(kind, error, tb) -> None:
        """The window has no console: unexpected errors are shown and written to a log."""
        text = ''.join(traceback.format_exception(kind, error, tb))
        try:
            with log.open('a', encoding='utf-8') as handle:
                handle.write(f'--- {datetime.now():%Y-%m-%d %H:%M:%S}\n{text}\n')
        except OSError:
            pass
        QMessageBox.warning(None, APP, f'Something went wrong in the window:\n'
                                       f'{kind.__name__}: {error}\n\nDetails were written to {log}')

    sys.excepthook = report
    window = Window()
    window.show()
    return int(app.exec())
