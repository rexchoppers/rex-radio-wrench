from __future__ import annotations

from typing import List, Dict

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
    QMessageBox,
)
import re
import unicodedata


DEFAULT_GENRE_LABELS: List[str] = [
    "Rock", "Pop", "Jazz", "Classical", "Electronic", "Hip-Hop", "Country",
    "R&B", "Blues", "Folk", "Reggae", "Punk", "Metal", "Indie", "Alternative",
    "Funk", "Soul", "Gospel", "Latin", "World", "Ambient", "Techno", "House",
    "Trance", "Drum & Bass", "Dubstep", "Trap", "Lo-Fi", "Experimental",
]


def slugify(label: str) -> str:
    s = unicodedata.normalize("NFKD", label)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = s.lower().strip()
    # normalize common cases first
    s = s.replace("&", " and ")
    s = s.replace("+", " and ")
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    # bespoke fix: r&b -> rnb
    if s == "r_b":
        s = "rb"
    if s == "r_and_b":
        s = "rnb"
    return s


class SettingsDialog(QDialog):
    """Settings dialog for editing name, description, and genres.

    Genres are represented as rows with two columns: Label (human) and ID (machine).
    The ID is auto-generated from the label when left blank or when adding new rows.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)

        # Widgets
        self.name_edit = QLineEdit()
        self.desc_edit = QTextEdit()
        self.desc_edit.setFixedHeight(100)

        self.genres_table = QTableWidget(0, 2)
        self.genres_table.setHorizontalHeaderLabels(["Label", "ID"])
        self.genres_table.horizontalHeader().setStretchLastSection(True)
        self.genres_table.verticalHeader().setVisible(False)
        self.genres_table.setSelectionBehavior(self.genres_table.SelectionBehavior.SelectRows)
        self.genres_table.setEditTriggers(self.genres_table.EditTrigger.DoubleClicked | self.genres_table.EditTrigger.EditKeyPressed | self.genres_table.EditTrigger.AnyKeyPressed)

        self.btn_add = QPushButton("Add Genre")
        self.btn_remove = QPushButton("Remove Selected")
        self.btn_reset = QPushButton("Reset to Defaults")

        self.btn_cancel = QPushButton("Cancel")
        self.btn_ok = QPushButton("OK")

        # Layout
        form = QGridLayout()
        form.addWidget(QLabel("App name:"), 0, 0)
        form.addWidget(self.name_edit, 0, 1)
        form.addWidget(QLabel("Description:"), 1, 0, Qt.AlignmentFlag.AlignTop)
        form.addWidget(self.desc_edit, 1, 1)

        btns_row = QHBoxLayout()
        btns_row.addWidget(self.btn_add)
        btns_row.addWidget(self.btn_remove)
        btns_row.addStretch(1)
        btns_row.addWidget(self.btn_reset)

        root = QVBoxLayout(self)
        root.addLayout(form)
        root.addWidget(QLabel("Genres:"))
        root.addWidget(self.genres_table)
        root.addLayout(btns_row)

        action_row = QHBoxLayout()
        action_row.addStretch(1)
        action_row.addWidget(self.btn_cancel)
        action_row.addWidget(self.btn_ok)
        root.addLayout(action_row)

        # Behavior
        self.btn_add.clicked.connect(self.on_add_genre)
        self.btn_remove.clicked.connect(self.on_remove_selected)
        self.btn_reset.clicked.connect(self.on_reset_defaults)
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

        self.genres_table.itemChanged.connect(self.on_table_item_changed)

        # Prefill sensible defaults
        self.name_edit.setText("Rex Radio Wrench")
        self.desc_edit.setPlainText("Utility to manage and authorize Rex Radio services from the desktop.")
        self.populate_with_defaults()

        self.resize(720, 520)

    # ----- Table helpers
    def populate_with_defaults(self) -> None:
        self.genres_table.blockSignals(True)
        self.genres_table.setRowCount(0)
        for label in DEFAULT_GENRE_LABELS:
            self._append_genre(label, slugify(label))
        self.genres_table.blockSignals(False)

    def _append_genre(self, label: str = "", gid: str | None = None) -> None:
        row = self.genres_table.rowCount()
        self.genres_table.insertRow(row)

        label_item = QTableWidgetItem(label)
        id_item = QTableWidgetItem(gid if gid is not None else slugify(label))

        # Make them editable
        label_item.setFlags(label_item.flags() | Qt.ItemFlag.ItemIsEditable)
        id_item.setFlags(id_item.flags() | Qt.ItemFlag.ItemIsEditable)

        self.genres_table.setItem(row, 0, label_item)
        self.genres_table.setItem(row, 1, id_item)

    # ----- Slots
    def on_add_genre(self) -> None:
        self._append_genre("New Genre", "")

    def on_remove_selected(self) -> None:
        rows = sorted({idx.row() for idx in self.genres_table.selectionModel().selectedRows()}, reverse=True)
        for r in rows:
            self.genres_table.removeRow(r)

    def on_reset_defaults(self) -> None:
        confirm = QMessageBox.question(
            self,
            "Reset genres",
            "Reset the genre list to defaults? This will replace current entries.",
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.populate_with_defaults()

    def on_table_item_changed(self, item: QTableWidgetItem) -> None:
        # If label changed and ID cell is empty, auto-fill the ID with slug
        if item.column() == 0:
            row = item.row()
            label = item.text().strip()
            id_item = self.genres_table.item(row, 1)
            if id_item is None:
                id_item = QTableWidgetItem()
                self.genres_table.setItem(row, 1, id_item)
            if (id_text := id_item.text().strip()) == "":
                self.genres_table.blockSignals(True)
                id_item.setText(slugify(label))
                self.genres_table.blockSignals(False)

    # ----- Data extraction and validation
    def validate(self) -> bool:
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "App name cannot be empty.")
            return False

        # Collect genres and validate
        seen_ids = set()
        for row in range(self.genres_table.rowCount()):
            label_item = self.genres_table.item(row, 0)
            id_item = self.genres_table.item(row, 1)
            label = (label_item.text() if label_item else "").strip()
            gid = (id_item.text() if id_item else "").strip()
            if not label and not gid:
                # allow fully empty row
                continue
            if not label:
                QMessageBox.warning(self, "Validation", f"Row {row+1}: Label is required.")
                return False
            if not gid:
                QMessageBox.warning(self, "Validation", f"Row {row+1}: ID is required.")
                return False
            # enforce slug pattern
            slugged = slugify(label)
            if gid != slugged:
                # allow custom IDs but warn on duplicates below
                pass
            if gid in seen_ids:
                QMessageBox.warning(self, "Validation", f"Duplicate ID '{gid}' at row {row+1}.")
                return False
            seen_ids.add(gid)
        return True

    def accept(self) -> None:  # type: ignore[override]
        if not self.validate():
            return
        super().accept()

    def get_settings(self) -> Dict:
        """Return settings as a dict: { name, description, genres:[{id,label},...] }"""
        genres: List[Dict[str, str]] = []
        for row in range(self.genres_table.rowCount()):
            label_item = self.genres_table.item(row, 0)
            id_item = self.genres_table.item(row, 1)
            label = (label_item.text() if label_item else "").strip()
            gid = (id_item.text() if id_item else "").strip()
            if not label and not gid:
                continue
            if label and gid:
                genres.append({"id": gid, "label": label})

        return {
            "name": self.name_edit.text().strip(),
            "description": self.desc_edit.toPlainText().strip(),
            "genres": genres,
        }
