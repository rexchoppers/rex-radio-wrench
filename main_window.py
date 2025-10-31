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
    QLineEdit,
    QTextEdit,
    QListWidget,
    QListWidgetItem,
    QFormLayout,
    QStackedWidget,
    QSplitter,
    QHBoxLayout,
    QGroupBox,
)

from dialogs.settings_dialog import DEFAULT_GENRE_LABELS, slugify


def build_default_settings() -> Dict:
    genres = [{"id": slugify(lbl), "label": lbl} for lbl in DEFAULT_GENRE_LABELS]
    return {
        "name": "Rex Radio Wrench",
        "description": "Utility to manage and authorize Rex Radio services from the desktop.",
        "genres": genres,
    }


class MainWindow(QMainWindow):
    """Main application window with inline settings subsection.

    - Edit Name, Description, and select multiple Genres directly in the main window.
    - Keeps in-memory mappings between human labels and machine IDs for the selected genres.
    """

    def __init__(self, hmac_key: Optional[str] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.hmac_key = hmac_key  # stored for future API usage
        self.settings: Dict = build_default_settings()
        self.label_to_id: Dict[str, str] = {}
        self.id_to_label: Dict[str, str] = {}

        self.setWindowTitle(self.settings["name"])  # initial title uses app name

        # Central UI: Sidebar navigation (left) + Stacked pages (right)
        self.nav_list = QListWidget()
        self.nav_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.nav_list.addItems([
            "Dashboard",
            "App Info",
            "Genres",
            "Connections",
            "Logs",
        ])

        # Pages container
        self.stack = QStackedWidget()

        # --- Build pages ---
        # Dashboard page (overview)
        self.page_dashboard = QWidget()
        dash_layout = QVBoxLayout(self.page_dashboard)
        self.title_label = QLabel()
        self.title_label.setObjectName("appTitle")
        self.title_label.setStyleSheet("#appTitle { font-size: 20px; font-weight: bold; }")
        self.description_label = QLabel(wordWrap=True)
        self.description_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        dash_layout.addWidget(self.title_label)
        dash_layout.addWidget(self.description_label)
        dash_layout.addStretch(1)

        # App Info page (name + description)
        self.page_appinfo = QWidget()
        appinfo_layout = QVBoxLayout(self.page_appinfo)
        self.name_edit = QLineEdit()
        self.desc_edit = QTextEdit()
        self.desc_edit.setFixedHeight(120)
        appinfo_form = QFormLayout()
        appinfo_form.addRow("Name:", self.name_edit)
        appinfo_form.addRow("Description:", self.desc_edit)
        appinfo_layout.addLayout(appinfo_form)
        appinfo_layout.addStretch(1)

        # Genres page (multi-select)
        self.page_genres = QWidget()
        genres_layout = QVBoxLayout(self.page_genres)
        intro_lbl = QLabel("Choose one or more genres:")
        self.genres_list = QListWidget()
        self.genres_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        genres_layout.addWidget(intro_lbl)
        genres_layout.addWidget(self.genres_list)

        # Connections page (placeholders)
        self.page_connections = QWidget()
        conn_layout = QVBoxLayout(self.page_connections)
        auth_group = QGroupBox("Authentication")
        auth_v = QVBoxLayout(auth_group)
        hmac_mask = "●" * 8 if (self.hmac_key or "") else "(not set)"
        self.hmac_label = QLabel(f"HMAC key: {hmac_mask}")
        auth_v.addWidget(self.hmac_label)
        conn_layout.addWidget(auth_group)
        conn_layout.addStretch(1)

        # Logs page
        self.page_logs = QWidget()
        logs_layout = QVBoxLayout(self.page_logs)
        self.logs_view = QTextEdit()
        self.logs_view.setPlaceholderText("Logs will appear here…")
        self.logs_view.setReadOnly(True)
        logs_layout.addWidget(self.logs_view)

        # Add all pages to the stack
        self.stack.addWidget(self.page_dashboard)   # 0
        self.stack.addWidget(self.page_appinfo)     # 1
        self.stack.addWidget(self.page_genres)      # 2
        self.stack.addWidget(self.page_connections) # 3
        self.stack.addWidget(self.page_logs)        # 4

        # Compose splitter
        splitter = QSplitter()
        nav_container = QWidget()
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.addWidget(self.nav_list)
        splitter.addWidget(nav_container)
        splitter.addWidget(self.stack)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setChildrenCollapsible(False)

        self.setCentralWidget(splitter)
        self.nav_list.setCurrentRow(0)

        # Menus and actions
        self._create_actions()
        self._create_menus()

        # Status bar
        self.statusBar().showMessage("Ready")

        # Populate controls and wire events
        self._populate_controls_from_settings()
        self._connect_signals()

        # Initialize view state
        self._rebuild_mappings()
        self._refresh_view()

        self.resize(900, 600)

    # ----- Menu/action setup
    def _create_actions(self) -> None:
        self.act_about = QAction("About", self)
        self.act_about.triggered.connect(self.show_about)

        self.act_quit = QAction("Quit", self)
        self.act_quit.setShortcut(QKeySequence.StandardKey.Quit)
        self.act_quit.triggered.connect(self.close)

    def _create_menus(self) -> None:
        menu_bar = self.menuBar()

        menu_file = menu_bar.addMenu("File")
        menu_file.addAction(self.act_quit)


        menu_help = menu_bar.addMenu("Help")
        menu_help.addAction(self.act_about)

    # ----- Actions
    # (No separate Settings dialog; inline controls are used.)

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

    # ----- Inline settings helpers
    def _populate_controls_from_settings(self) -> None:
        # Populate text fields
        self.name_edit.blockSignals(True)
        self.desc_edit.blockSignals(True)
        self.name_edit.setText(self.settings.get("name", ""))
        self.desc_edit.setPlainText(self.settings.get("description", ""))
        self.name_edit.blockSignals(False)
        self.desc_edit.blockSignals(False)

        # Populate genre list with all defaults and select those in settings
        selected_labels = {g.get("label", "") for g in self.settings.get("genres", [])}
        self.genres_list.blockSignals(True)
        self.genres_list.clear()
        for label in DEFAULT_GENRE_LABELS:
            item = QListWidgetItem(label)
            if label in selected_labels:
                item.setSelected(True)
            self.genres_list.addItem(item)
        self.genres_list.blockSignals(False)

    def _connect_signals(self) -> None:
        # Navigation
        self.nav_list.currentRowChanged.connect(self.stack.setCurrentIndex)
        # App Info
        self.name_edit.textChanged.connect(self.on_name_changed)
        self.desc_edit.textChanged.connect(self.on_desc_changed)
        # Genres
        self.genres_list.itemSelectionChanged.connect(self.on_genres_selection_changed)

    def on_name_changed(self, text: str) -> None:
        self.settings["name"] = text.strip()
        self._refresh_view()

    def on_desc_changed(self) -> None:
        self.settings["description"] = self.desc_edit.toPlainText().strip()
        self._refresh_view()

    def on_genres_selection_changed(self) -> None:
        labels = [item.text() for item in self.genres_list.selectedItems()]
        genres = [{"id": slugify(lbl), "label": lbl} for lbl in labels]
        self.settings["genres"] = genres
        self._rebuild_mappings()
        self.statusBar().showMessage(f"Selected {len(genres)} genre(s)", 2500)

    def _refresh_view(self) -> None:
        self.setWindowTitle(self.settings.get("name", "Rex Radio Wrench"))
        self.title_label.setText(self.settings.get("name", "Rex Radio Wrench"))
        self.description_label.setText(self.settings.get("description", ""))
