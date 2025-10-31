from __future__ import annotations

from typing import Dict, List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QLabel,
    QVBoxLayout,
    QMessageBox,
    QTableWidgetItem,
)

from dialogs.settings_dialog import SettingsDialog, DEFAULT_GENRE_LABELS, slugify


def build_default_settings() -> Dict:
    genres = [{"id": slugify(lbl), "label": lbl} for lbl in DEFAULT_GENRE_LABELS]
    return {
        "name": "Rex Radio Wrench",
        "description": "Utility to manage and authorize Rex Radio services from the desktop.",
        "genres": genres,
    }


class MainWindow(QMainWindow):
    """Main application dashboard.

    - Shows basic app info (name/description).
    - Provides a Settings… action to edit name, description, and genres.
    - Keeps in-memory mappings between human labels and machine IDs.
    """

    def __init__(self, hmac_key: Optional[str] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.hmac_key = hmac_key  # stored for future API usage
        self.settings: Dict = build_default_settings()
        self.label_to_id: Dict[str, str] = {}
        self.id_to_label: Dict[str, str] = {}

        self.setWindowTitle(self.settings["name"])  # initial title uses app name

        # Central UI
        self.title_label = QLabel()
        self.title_label.setObjectName("appTitle")
        self.title_label.setStyleSheet("#appTitle { font-size: 20px; font-weight: bold; }")

        self.description_label = QLabel(wordWrap=True)
        self.description_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.addWidget(self.title_label)
        layout.addWidget(self.description_label)
        layout.addStretch(1)
        self.setCentralWidget(central)

        # Menus and actions
        self._create_actions()
        self._create_menus()

        # Status bar
        self.statusBar().showMessage("Ready")

        # Initialize view state
        self._rebuild_mappings()
        self._refresh_view()

        self.resize(900, 600)

    # ----- Menu/action setup
    def _create_actions(self) -> None:
        self.act_settings = QAction("Settings…", self)
        self.act_settings.setShortcut(QKeySequence.StandardKey.Preferences)
        self.act_settings.triggered.connect(self.open_settings)

        self.act_about = QAction("About", self)
        self.act_about.triggered.connect(self.show_about)

        self.act_quit = QAction("Quit", self)
        self.act_quit.setShortcut(QKeySequence.StandardKey.Quit)
        self.act_quit.triggered.connect(self.close)

    def _create_menus(self) -> None:
        menu_bar = self.menuBar()

        menu_file = menu_bar.addMenu("File")
        menu_file.addAction(self.act_quit)

        menu_edit = menu_bar.addMenu("Edit")
        menu_edit.addAction(self.act_settings)

        menu_help = menu_bar.addMenu("Help")
        menu_help.addAction(self.act_about)

    # ----- Actions
    def open_settings(self) -> None:
        dlg = SettingsDialog(self)
        # Prefill dialog from current settings
        # Prefill dialog from current settings
        dlg.name_edit.setText(self.settings.get("name", ""))
        dlg.desc_edit.setPlainText(self.settings.get("description", ""))
        # Rebuild the table
        dlg.genres_table.blockSignals(True)
        dlg.genres_table.setRowCount(0)
        for g in self.settings.get("genres", []):
            label = g.get("label", "")
            gid = g.get("id", slugify(label))
            row = dlg.genres_table.rowCount()
            dlg.genres_table.insertRow(row)
            dlg.genres_table.setItem(row, 0, QTableWidgetItem(label))
            dlg.genres_table.setItem(row, 1, QTableWidgetItem(gid))
        dlg.genres_table.blockSignals(False)

        if dlg.exec():
            new_settings = dlg.get_settings()
            self.apply_settings(new_settings)
            self.statusBar().showMessage("Settings updated", 4000)

    def show_about(self) -> None:
        QMessageBox.information(
            self,
            "About",
            f"{self.settings['name']}\n\n{self.settings['description']}\n\n"
            f"Genres: {len(self.settings.get('genres', []))} configured.",
        )

    # ----- State and view updates
    def apply_settings(self, new_settings: Dict) -> None:
        self.settings = {
            "name": new_settings.get("name", self.settings.get("name")),
            "description": new_settings.get("description", self.settings.get("description")),
            "genres": new_settings.get("genres", self.settings.get("genres", [])),
        }
        self._rebuild_mappings()
        self._refresh_view()

    def _rebuild_mappings(self) -> None:
        genres: List[Dict[str, str]] = self.settings.get("genres", [])
        self.label_to_id = {g["label"]: g["id"] for g in genres if "label" in g and "id" in g}
        self.id_to_label = {g["id"]: g["label"] for g in genres if "label" in g and "id" in g}

    def _refresh_view(self) -> None:
        self.setWindowTitle(self.settings.get("name", "Rex Radio Wrench"))
        self.title_label.setText(self.settings.get("name", "Rex Radio Wrench"))
        self.description_label.setText(self.settings.get("description", ""))
