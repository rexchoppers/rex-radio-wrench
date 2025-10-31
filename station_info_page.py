from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple
import json
import re

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QSizePolicy,
    QMessageBox,
)

from dialogs.settings_dialog import DEFAULT_GENRE_LABELS, slugify
from api_client import ApiClient


def _build_default_settings() -> Dict[str, Any]:
    return {
        "name": "Rex Radio Wrench",
        "description": "Utility to manage and authorize Rex Radio services from the desktop.",
        "genres": [{"id": slugify(lbl), "label": lbl} for lbl in DEFAULT_GENRE_LABELS],
    }


class StationInformationPage(QWidget):
    def __init__(
        self,
        api: ApiClient,
        log_cb: Optional[Callable[[str], None]] = None,
        status_cb: Optional[Callable[[str, int], None]] = None,
        on_settings_changed: Optional[Callable[[Dict[str, Any]], None]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.api = api
        self.log_cb = log_cb or (lambda _msg: None)
        self.status_cb = status_cb or (lambda _msg, _ms=0: None)
        self.on_settings_changed = on_settings_changed

        self.settings: Dict[str, Any] = _build_default_settings()

        root = QVBoxLayout(self)
        self.name_edit = QLineEdit()
        self.name_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.desc_edit = QTextEdit()
        self.desc_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.desc_edit.setMinimumHeight(150)
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignTop)
        form.addRow("Station name:", self.name_edit)
        form.addRow("Description:", self.desc_edit)
        root.addLayout(form)

        root.addWidget(QLabel("Genres (select one or more):"))
        self.genres_list = QListWidget()
        self.genres_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.genres_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.genres_list.setMinimumHeight(200)
        root.addWidget(self.genres_list, 1)

        root.addStretch(1)
        self.btn_apply = QPushButton("Apply")
        actions = QHBoxLayout()
        actions.addStretch(1)
        actions.addWidget(self.btn_apply)
        root.addLayout(actions)

        self._populate_controls_from_settings()
        self._connect_signals()

    # --- Public API
    def get_settings(self) -> Dict[str, Any]:
        return {
            "name": self.settings.get("name", ""),
            "description": self.settings.get("description", ""),
            "genres": list(self.settings.get("genres", [])),
        }

    def set_settings(self, s: Dict[str, Any]) -> None:
        self.settings.update({
            "name": s.get("name", self.settings.get("name", "")),
            "description": s.get("description", self.settings.get("description", "")),
            "genres": s.get("genres", self.settings.get("genres", [])),
        })
        self._populate_controls_from_settings()
        self._emit_settings_changed()

    def load_from_api(self) -> None:
        self._status("Loading station information…", 1500)
        name_resp = self.api.get_config_field("name")
        desc_resp = self.api.get_config_field("description")
        genres_resp = self.api.get_config_field("genres")
        if name_resp is None or desc_resp is None or genres_resp is None:
            self._status("Failed to load one or more fields.", 3000)
            return
        name_val = self._extract_value(name_resp, self.settings.get("name", ""))
        desc_val = self._extract_value(desc_resp, self.settings.get("description", ""))
        genres_raw = self._extract_value(genres_resp, [])
        genres_list = self._coerce_genres_from_payload(genres_raw)
        self.settings.update({
            "name": name_val if isinstance(name_val, str) else self.settings.get("name", ""),
            "description": desc_val if isinstance(desc_val, str) else self.settings.get("description", ""),
            "genres": genres_list,
        })
        self._populate_controls_from_settings()
        self._status("Station information loaded", 3000)
        try:
            self._log("[GET /config/name] ok")
            self._log("[GET /config/description] ok")
            self._log(f"[GET /config/genres] {len(genres_list)} item(s)")
            sel_ids = [g.get("id") for g in genres_list if g.get("id")]
            self._log(f"[UI] selected genres: {sel_ids}")
            self._log(f"[APPLIED] {json.dumps({'name': self.settings.get('name',''), 'genres_count': len(genres_list)})}")
        except Exception:
            pass
        self._emit_settings_changed()

    def apply_and_save(self) -> None:
        name = self.name_edit.text().strip()
        description = self.desc_edit.toPlainText().strip()
        items = self.genres_list.selectedItems()
        genres: List[Dict[str, str]] = []
        for it in items:
            label = it.text()
            gid = it.data(Qt.ItemDataRole.UserRole) or slugify(label)
            genres.append({"id": gid, "label": label})
        genre_ids = [g["id"] for g in genres]

        self.settings.update({"name": name, "description": description, "genres": genres})
        updates: List[Tuple[str, Any]] = [("name", name), ("description", description), ("genres", genre_ids)]

        self._status("Saving station information…", 3000)
        self._set_inputs_enabled(False)
        try:
            try:
                body_preview = json.dumps([{"field": f, "value": v} for (f, v) in updates], separators=(",", ":"))
                self._log(f"[PATCH /config] body: {body_preview}")
            except Exception:
                pass
            ok, status, text = self.api.patch_config_bulk(updates)
            if ok:
                self._log(f"[PATCH /config] {status} ok")
                self._status("Station information saved", 3000)
            else:
                snippet = (text or "").strip()
                if len(snippet) > 500:
                    snippet = snippet[:500] + "…"
                self._log(f"[PATCH /config] {status} fail: {snippet}")
                QMessageBox.warning(self, "Save failed", f"Failed to save station information. HTTP {status}\n{snippet}")
        finally:
            self._set_inputs_enabled(True)
            self._emit_settings_changed()

    # --- Internals
    def _connect_signals(self) -> None:
        self.name_edit.textChanged.connect(self._on_name_changed)
        self.desc_edit.textChanged.connect(self._on_desc_changed)
        self.genres_list.itemSelectionChanged.connect(self._on_genres_selection_changed)
        self.btn_apply.clicked.connect(self.apply_and_save)

    def _populate_controls_from_settings(self) -> None:
        self.name_edit.blockSignals(True)
        self.desc_edit.blockSignals(True)
        self.name_edit.setText(self.settings.get("name", ""))
        self.desc_edit.setPlainText(self.settings.get("description", ""))
        self.name_edit.blockSignals(False)
        self.desc_edit.blockSignals(False)

        selected_ids = {g.get("id", "") for g in self.settings.get("genres", []) if g.get("id")}
        default_ids = {slugify(lbl) for lbl in DEFAULT_GENRE_LABELS}
        self.genres_list.blockSignals(True)
        self.genres_list.clear()
        for label in DEFAULT_GENRE_LABELS:
            gid = slugify(label)
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, gid)
            self.genres_list.addItem(item)
            if gid in selected_ids:
                item.setSelected(True)
        for g in self.settings.get("genres", []):
            gid = g.get("id")
            if not gid or gid in default_ids:
                continue
            label = g.get("label") or self._humanize_slug(gid)
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, gid)
            self.genres_list.addItem(item)
            item.setSelected(True)
        self.genres_list.blockSignals(False)

    def _on_name_changed(self, text: str) -> None:
        self.settings["name"] = text.strip()
        self._emit_settings_changed()

    def _on_desc_changed(self) -> None:
        self.settings["description"] = self.desc_edit.toPlainText().strip()
        self._emit_settings_changed()

    def _on_genres_selection_changed(self) -> None:
        items = self.genres_list.selectedItems()
        genres: List[Dict[str, str]] = []
        for it in items:
            label = it.text()
            gid = it.data(Qt.ItemDataRole.UserRole) or slugify(label)
            genres.append({"id": gid, "label": label})
        self.settings["genres"] = genres
        self._emit_settings_changed()

    def _set_inputs_enabled(self, enabled: bool) -> None:
        self.btn_apply.setEnabled(enabled)
        self.name_edit.setEnabled(enabled)
        self.desc_edit.setEnabled(enabled)
        self.genres_list.setEnabled(enabled)

    def _extract_value(self, resp: Any, default: Any) -> Any:
        if isinstance(resp, dict):
            if "value" in resp:
                return resp.get("value", default)
            for k in ("name", "description", "genres"):
                if k in resp:
                    return resp.get(k, default)
            return default
        return resp if resp is not None else default

    def _humanize_slug(self, s: str) -> str:
        if not s:
            return ""
        label = s.replace("_", " ")
        label = label.replace(" and ", " & ")
        return label.title()

    def _coerce_genres_from_payload(self, genres_payload: Any) -> List[Dict[str, str]]:
        default_id_to_label = {slugify(lbl): lbl for lbl in DEFAULT_GENRE_LABELS}
        result: List[Dict[str, str]] = []
        if genres_payload is None:
            return result
        if isinstance(genres_payload, str):
            s = genres_payload.strip()
            if s.startswith("[") or s.startswith("{"):
                try:
                    genres_payload = json.loads(s)
                except Exception:
                    pass
            if isinstance(genres_payload, str):
                parts = [p.strip() for p in re.split(r"[\s,]+", s) if p.strip()]
                genres_payload = parts
        if isinstance(genres_payload, dict):
            try:
                items = [v for k, v in sorted(genres_payload.items(), key=lambda kv: int(kv[0]))]
            except Exception:
                items = list(genres_payload.values())
            genres_payload = items
        if isinstance(genres_payload, list):
            for item in genres_payload:
                if isinstance(item, str):
                    gid = item.strip()
                    if not gid:
                        continue
                    label = default_id_to_label.get(gid) or self._humanize_slug(gid)
                    result.append({"id": gid, "label": label})
                elif isinstance(item, dict):
                    gid = (item.get("id") or slugify(item.get("label", ""))).strip()
                    if not gid:
                        continue
                    label = item.get("label") or default_id_to_label.get(gid) or self._humanize_slug(gid)
                    result.append({"id": gid, "label": label})
        return result

    def _log(self, msg: str) -> None:
        try:
            self.log_cb(msg)
        except Exception:
            pass

    def _status(self, msg: str, ms: int = 3000) -> None:
        try:
            self.status_cb(msg, ms)
        except Exception:
            pass

    def _emit_settings_changed(self) -> None:
        if self.on_settings_changed:
            try:
                self.on_settings_changed(self.get_settings())
            except Exception:
                pass
