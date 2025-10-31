from __future__ import annotations

from typing import Dict, List, Optional
import hmac
import hashlib
import base64
import time
import json
import urllib.request
import urllib.error
import urllib.parse

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
    QPushButton,
    QSizePolicy,
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
        self.api_base_url: str = "http://localhost:8000"  # placeholder; can be made configurable
        self.settings: Dict = build_default_settings()
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

        # Station Information page (name, description, genres)
        self.page_appinfo = QWidget()
        appinfo_layout = QVBoxLayout(self.page_appinfo)
        self.name_edit = QLineEdit()
        # Make fields expand nicely
        self.name_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.desc_edit = QTextEdit()
        self.desc_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.desc_edit.setMinimumHeight(150)
        appinfo_form = QFormLayout()
        appinfo_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        appinfo_form.setLabelAlignment(Qt.AlignmentFlag.AlignTop)
        appinfo_form.addRow("Station name:", self.name_edit)
        appinfo_form.addRow("Description:", self.desc_edit)
        appinfo_layout.addLayout(appinfo_form)

        # Genres (multi-select)
        genres_lbl = QLabel("Genres (select one or more):")
        self.genres_list = QListWidget()
        self.genres_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.genres_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.genres_list.setMinimumHeight(200)
        appinfo_layout.addWidget(genres_lbl)
        appinfo_layout.addWidget(self.genres_list, 1)

        # Bottom action row
        appinfo_layout.addStretch(1)
        self.btn_apply = QPushButton("Apply")
        actions_row = QHBoxLayout()
        actions_row.addStretch(1)
        actions_row.addWidget(self.btn_apply)
        appinfo_layout.addLayout(actions_row)


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

        # Station actions
        self.act_reload = QAction("Reload Station Information", self)
        self.act_reload.setShortcut(QKeySequence("Ctrl+R"))
        self.act_reload.triggered.connect(self.on_load_clicked)

    def _create_menus(self) -> None:
        menu_bar = self.menuBar()

        menu_file = menu_bar.addMenu("File")
        menu_file.addAction(self.act_quit)

        menu_station = menu_bar.addMenu("Station")
        menu_station.addAction(self.act_reload)

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
        self.nav_list.currentRowChanged.connect(self.on_nav_changed)
        # App Info
        self.name_edit.textChanged.connect(self.on_name_changed)
        self.desc_edit.textChanged.connect(self.on_desc_changed)
        # Genres
        self.genres_list.itemSelectionChanged.connect(self.on_genres_selection_changed)
        # Actions
        self.btn_apply.clicked.connect(self.on_apply_clicked)

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

    def on_nav_changed(self, index: int) -> None:
        # Switch stacked page when the left nav selection changes
        self.stack.setCurrentIndex(index)
        # When entering Station Information, fetch latest from API
        if index == 1:
            self.on_load_clicked()

    def build_station_payload_for_api(self) -> Dict:
        """Build the payload shape expected by the API when sending station info.
        - Genres are sent as a list of machine-readable IDs
        - Name and description are sent as plain strings
        """
        payload = {
            "name": self.settings.get("name", ""),
            "description": self.settings.get("description", ""),
            "genres": [g.get("id", "") for g in self.settings.get("genres", []) if g.get("id")],
        }
        return payload

    def _refresh_view(self) -> None:
        self.setWindowTitle(self.settings.get("name", "Rex Radio Wrench"))
        self.title_label.setText(self.settings.get("name", "Rex Radio Wrench"))
        self.description_label.setText(self.settings.get("description", ""))

    # ----- Apply action
    def on_apply_clicked(self) -> None:
        # Ensure settings reflect current UI values
        self.settings["name"] = self.name_edit.text().strip()
        self.settings["description"] = self.desc_edit.toPlainText().strip()
        labels = [item.text() for item in self.genres_list.selectedItems()]
        self.settings["genres"] = [{"id": slugify(lbl), "label": lbl} for lbl in labels]

        # Rebuild mappings and reflect changes in the UI
        self._rebuild_mappings()
        self._refresh_view()

        # Build the API payload (machine-readable IDs for genres)
        payload = self.build_station_payload_for_api()

        self.statusBar().showMessage("Changes applied", 3000)
        # For visibility, log the payload and mapping sizes
        try:
            compact = json.dumps(payload, separators=(",", ":"))
            self.logs_view.append(f"[APPLY] Payload to API: {compact}")
            self.logs_view.append(
                f"[MAPPINGS] label->id: {len(self.label_to_id)} items, id->label: {len(self.id_to_label)} items"
            )
        except Exception:
            pass

    # ----- HMAC + simple GET helper matching provided shell script
    def _generate_hmac_signature(self, method: str, path: str, body: str, timestamp: str) -> str:
        if not (self.hmac_key or ""):  # pragma: no cover
            return ""
        message = f"{timestamp}{method}{path}{body}".encode("utf-8")
        key_bytes = (self.hmac_key or "").encode("utf-8")
        digest = hmac.new(key_bytes, message, hashlib.sha512).digest()
        return base64.b64encode(digest).decode("ascii").strip()

    def _auth_headers(self, method: str, path: str, body: str = "") -> Dict[str, str]:
        ts = str(int(time.time()))
        sig = self._generate_hmac_signature(method.upper(), path, body, ts)
        return {
            "x-signature": sig,
            "x-timestamp": ts,
            "Content-Type": "application/json",
        }

    def get_current_config(self, field: str) -> Optional[Dict]:
        """GET /config/{field} — returns a dict or empty-value dict on 400, None on other errors."""
        base = self.api_base_url.rstrip("/")
        path = f"/config/{urllib.parse.quote(field)}"
        url = f"{base}{path}"
        headers = self._auth_headers("GET", path, "")
        req = urllib.request.Request(url, method="GET", headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read().decode("utf-8")
                return json.loads(data) if data else {}
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            if e.code == 400:
                # Field doesn't exist, return empty value
                return {"field": field, "value": ""}
            QMessageBox.critical(self, "Error", f"Failed to fetch configuration. HTTP {e.code}")
            return None
        except Exception as ex:  # pragma: no cover
            QMessageBox.critical(self, "Error", f"Failed to fetch configuration. {ex}")
            return None

    def get_station_config(self) -> Optional[Dict]:
        """Fetch station configuration by calling GET /config/{field} for name, description, and genres.

        Returns a dict with keys: name (str), description (str), genres (list[{id,label}]).
        Returns None if a non-recoverable error occurs (e.g., network/server error).
        """
        # Fetch individual fields
        name_resp = self.get_current_config("name")
        desc_resp = self.get_current_config("description")
        genres_resp = self.get_current_config("genres")

        # If a request failed (non-400), abort gracefully. 400s are handled inside get_current_config().
        if name_resp is None or desc_resp is None or genres_resp is None:
            return None

        def _val(resp, default=""):
            # Extract value from various possible response shapes
            if isinstance(resp, dict):
                if "value" in resp:
                    return resp.get("value", default)
                for k in ("name", "description", "genres"):
                    if k in resp:
                        return resp.get(k, default)
                return default
            return resp if resp is not None else default

        name_val = _val(name_resp, "")
        desc_val = _val(desc_resp, "")
        genres_raw = _val(genres_resp, [])
        genres_list = self._coerce_genres_from_payload(genres_raw)

        return {
            "name": name_val if isinstance(name_val, str) else "",
            "description": desc_val if isinstance(desc_val, str) else "",
            "genres": genres_list,
        }

    def _humanize_slug(self, s: str) -> str:
        if not s:
            return ""
        label = s.replace("_", " ")
        # turn 'drum and bass' into 'Drum & Bass' best-effort
        label = label.replace(" and ", " & ")
        return label.title()

    def _coerce_genres_from_payload(self, genres_payload) -> List[Dict[str, str]]:
        """Normalize incoming genres into a list of {id,label} dicts.
        Accepts list[str] (IDs) or list[dict{id,label}]."""
        default_id_to_label = {slugify(lbl): lbl for lbl in DEFAULT_GENRE_LABELS}
        result: List[Dict[str, str]] = []
        if not genres_payload:
            return result
        if isinstance(genres_payload, list):
            for item in genres_payload:
                if isinstance(item, str):
                    gid = item
                    label = default_id_to_label.get(gid) or self.id_to_label.get(gid) or self._humanize_slug(gid)
                    result.append({"id": gid, "label": label})
                elif isinstance(item, dict):
                    gid = item.get("id") or slugify(item.get("label", ""))
                    if not gid:
                        continue
                    label = item.get("label") or default_id_to_label.get(gid) or self._humanize_slug(gid)
                    result.append({"id": gid, "label": label})
        return result

    def on_load_clicked(self) -> None:
        """Load station information via GET /config/{field} and populate the UI."""
        self.statusBar().showMessage("Loading station information…", 1500)

        # Fetch individual fields
        name_resp = self.get_current_config("name")
        desc_resp = self.get_current_config("description")
        genres_resp = self.get_current_config("genres")

        # If a request failed (non-400), abort gracefully. 400s are handled in get_current_config.
        if name_resp is None or desc_resp is None or genres_resp is None:
            self.statusBar().showMessage("Failed to load one or more fields.", 3000)
            return

        def _val(resp, default=""):
            # Extract value from various possible response shapes
            if isinstance(resp, dict):
                if "value" in resp:
                    return resp.get("value", default)
                # Sometimes servers return {field: value}
                for k in ("name", "description", "genres"):
                    if k in resp:
                        return resp.get(k, default)
                return default
            return resp if resp is not None else default

        name_val = _val(name_resp, self.settings.get("name"))
        desc_val = _val(desc_resp, self.settings.get("description"))
        genres_raw = _val(genres_resp, [])
        genres_list = self._coerce_genres_from_payload(genres_raw)

        new_settings = {
            "name": name_val if isinstance(name_val, str) else self.settings.get("name"),
            "description": desc_val if isinstance(desc_val, str) else self.settings.get("description"),
            "genres": genres_list,
        }
        self.apply_settings(new_settings)
        # Sync controls with the newly loaded settings
        self._populate_controls_from_settings()
        self._rebuild_mappings()
        self._refresh_view()
        self.statusBar().showMessage("Station information loaded", 3000)
        try:
            snippet = json.dumps({"name": new_settings.get("name", ""), "genres_count": len(new_settings.get("genres", []))})
            self.logs_view.append("[GET /config/name] ok")
            self.logs_view.append("[GET /config/description] ok")
            self.logs_view.append(f"[GET /config/genres] {len(new_settings.get('genres', []))} item(s)")
            self.logs_view.append(f"[APPLIED] {snippet}")
        except Exception:
            pass
