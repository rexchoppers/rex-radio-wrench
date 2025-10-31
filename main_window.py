from __future__ import annotations

from typing import Any, Dict, Optional

from api_client import ApiClient
from station_info_page import StationInformationPage

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QLabel,
    QVBoxLayout,
    QMessageBox,
    QListWidget,
    QStackedWidget,
    QSplitter,
    QHBoxLayout,
    QGroupBox,
    QTextEdit,
)





class MainWindow(QMainWindow):
    """Main application window with inline settings subsection.

    - Edit Name, Description, and select multiple Genres directly in the main window.
    - Keeps in-memory mappings between human labels and machine IDs for the selected genres.
    """

    def __init__(self, hmac_key: Optional[str] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.hmac_key = hmac_key  # stored for future API usage
        self.api = ApiClient(self.hmac_key)
        self.settings: Dict = {"name": "Rex Radio Wrench", "description": "", "genres": []}
        self.label_to_id: Dict[str, str] = {}
        self.id_to_label: Dict[str, str] = {}

        self.setWindowTitle(self.settings["name"])  # initial title uses app name

        # Central UI: Sidebar navigation (left) + Stacked pages (right)
        self.nav_list = QListWidget()
        self.nav_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.nav_list.addItems([
            "Dashboard",
            "Station Information",
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

        # Station Information page widget
        self.station_page = StationInformationPage(
            api=self.api,
            log_cb=self._log,
            status_cb=self._status,
            on_settings_changed=self.on_station_settings_changed,
        )
        self.page_appinfo = self.station_page


        # Connections page (placeholders)
        self.page_connections = QWidget()
        conn_layout = QVBoxLayout(self.page_connections)
        auth_group = QGroupBox("Authentication")
        auth_v = QVBoxLayout(auth_group)
        hmac_mask = "●" * 8 if (self.hmac_key or "") else "(not set)"
        self.hmac_label = QLabel(f"HMAC key: {hmac_mask}")
        auth_v.addWidget(self.hmac_label)
        self.api_label = QLabel(f"API base URL: {self.api.base_url}")
        auth_v.addWidget(self.api_label)
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
        self.stack.addWidget(self.page_connections) # 2
        self.stack.addWidget(self.page_logs)        # 3

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

        # Wire events
        self._connect_signals()

        # Sync settings from the Station page and initialize view
        self.on_station_settings_changed(self.station_page.get_settings())

        self.resize(900, 600)

    # ----- Menu/action setup
    def _create_actions(self) -> None:
        self.act_about = QAction("About", self)
        self.act_about.triggered.connect(self.show_about)

        self.act_quit = QAction("Quit", self)
        self.act_quit.setShortcut(QKeySequence.StandardKey.Quit)
        self.act_quit.triggered.connect(self.close)

        # Station actions
        self.act_reload = QAction("Reload Station Information", self)
        self.act_reload.setShortcut(QKeySequence("Ctrl+R"))
        self.act_reload.triggered.connect(self.station_page.load_from_api)

    def _create_menus(self) -> None:
        menu_bar = self.menuBar()

        menu_file = menu_bar.addMenu("File")
        menu_file.addAction(self.act_quit)

        menu_station = menu_bar.addMenu("Station")
        menu_station.addAction(self.act_reload)

        menu_help = menu_bar.addMenu("Help")
        menu_help.addAction(self.act_about)

    def show_about(self) -> None:
        QMessageBox.information(
            self,
            "About",
            f"{self.settings['name']}\n\n{self.settings['description']}\n\n"
            f"Genres: {len(self.settings.get('genres', []))} configured.",
        )

    # ----- Status/log callbacks for StationInformationPage
    def _log(self, msg: str) -> None:
        try:
            self.logs_view.append(msg)
        except Exception:
            pass

    def _status(self, msg: str, ms: int = 3000) -> None:
        try:
            self.statusBar().showMessage(msg, ms)
        except Exception:
            pass

    def on_station_settings_changed(self, new_settings: Dict) -> None:
        # Sync settings from the Station page and refresh dashboard/mappings
        self.settings = {
            "name": new_settings.get("name", self.settings.get("name", "")),
            "description": new_settings.get("description", self.settings.get("description", "")),
            "genres": new_settings.get("genres", self.settings.get("genres", [])),
        }
        self._rebuild_mappings()
        self._refresh_view()

    # ----- State and view updates
    def _rebuild_mappings(self) -> None:
        genres = self.settings.get("genres", [])
        self.label_to_id = {g.get("label"): g.get("id") for g in genres if g.get("label") and g.get("id")}
        self.id_to_label = {g.get("id"): g.get("label") for g in genres if g.get("label") and g.get("id")}


    def _connect_signals(self) -> None:
        # Navigation only; the StationInformationPage manages its own signals
        self.nav_list.currentRowChanged.connect(self.on_nav_changed)

    def on_nav_changed(self, index: int) -> None:
        # Switch stacked page when the left nav selection changes
        self.stack.setCurrentIndex(index)
        # When entering Station Information, fetch latest from API
        if index == 1:
            self.station_page.load_from_api()

    def _refresh_view(self) -> None:
        self.setWindowTitle(self.settings.get("name", "Rex Radio Wrench"))
        self.title_label.setText(self.settings.get("name", "Rex Radio Wrench"))
        self.description_label.setText(self.settings.get("description", ""))
