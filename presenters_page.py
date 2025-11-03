from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from PyQt6.QtCore import Qt, QTime
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QHBoxLayout,
    QCheckBox,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QGroupBox,
    QTimeEdit,
    QComboBox,
    QMessageBox,
)

from api_client import ApiClient


DAY_LABELS = [
    ("Mon", "mon"),
    ("Tue", "tue"),
    ("Wed", "wed"),
    ("Thu", "thu"),
    ("Fri", "fri"),
    ("Sat", "sat"),
    ("Sun", "sun"),
]

ROLE_LABELS = [
    ("News", "news"),
    ("Music", "music"),
    ("Sports", "sports"),
    ("Emergency", "emergency"),
]

VOICE_MODEL_DEFAULT = "eleven_multilingual_v2"
VOICE_IDS = [
    "British Radio Presenter 1",
]

class PresentersPage(QWidget):
    def __init__(
        self,
        api: ApiClient,
        log_cb: Optional[Callable[[str], None]] = None,
        status_cb: Optional[Callable[[str, int], None]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.api = api
        self._log_cb = log_cb or (lambda _m: None)
        self._status_cb = status_cb or (lambda _m, _ms=0: None)

        root = QVBoxLayout(self)

        # Existing presenters
        grp_list = QGroupBox("Existing Presenters")
        v_list = QVBoxLayout(grp_list)
        self.presenters_list = QListWidget()
        v_list.addWidget(self.presenters_list)
        self.btn_reload = QPushButton("Reload")
        row_reload = QHBoxLayout()
        row_reload.addStretch(1)
        row_reload.addWidget(self.btn_reload)
        v_list.addLayout(row_reload)
        root.addWidget(grp_list)

        # Create form
        grp_form = QGroupBox("Create Presenter")
        form = QFormLayout(grp_form)

        self.edit_name = QLineEdit()
        form.addRow("Name:", self.edit_name)

        # Days
        days_row = QHBoxLayout()
        self.day_checks: List[QCheckBox] = []
        for label, code in DAY_LABELS:
            cb = QCheckBox(label)
            cb.setProperty("code", code)
            self.day_checks.append(cb)
            days_row.addWidget(cb)
        days_row.addStretch(1)
        form.addRow("Days:", _wrap(days_row))

        # Times
        self.time_start = QTimeEdit()
        self.time_start.setDisplayFormat("HH:mm")
        self.time_start.setTime(QTime(9, 0))
        self.time_end = QTimeEdit()
        self.time_end.setDisplayFormat("HH:mm")
        self.time_end.setTime(QTime(12, 0))
        times_row = QHBoxLayout()
        times_row.addWidget(QLabel("Start"))
        times_row.addWidget(self.time_start)
        times_row.addSpacing(16)
        times_row.addWidget(QLabel("End"))
        times_row.addWidget(self.time_end)
        times_row.addStretch(1)
        form.addRow("Timespan:", _wrap(times_row))

        # Schedule blocks
        self.btn_add_block = QPushButton("Add Block")
        form.addRow("", self.btn_add_block)

        self.blocks_list = QListWidget()
        form.addRow("Schedule blocks:", self.blocks_list)

        blocks_actions = QHBoxLayout()
        self.btn_remove_block = QPushButton("Remove Selected")
        self.btn_clear_blocks = QPushButton("Clear Blocks")
        blocks_actions.addWidget(self.btn_remove_block)
        blocks_actions.addWidget(self.btn_clear_blocks)
        blocks_actions.addStretch(1)
        form.addRow("", _wrap(blocks_actions))

        # Roles
        roles_row = QHBoxLayout()
        self.role_checks: List[QCheckBox] = []
        for label, code in ROLE_LABELS:
            cb = QCheckBox(label)
            cb.setProperty("code", code)
            self.role_checks.append(cb)
            roles_row.addWidget(cb)
        roles_row.addStretch(1)
        form.addRow("Roles:", _wrap(roles_row))

        # Voice
        self.lbl_voice_model = QLabel(VOICE_MODEL_DEFAULT)
        self.lbl_voice_model.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.cmb_voice_id = QComboBox()
        self.cmb_voice_id.addItems(VOICE_IDS)
        form.addRow("Voice model:", self.lbl_voice_model)
        form.addRow("Voice ID:", self.cmb_voice_id)

        # Actions
        actions = QHBoxLayout()
        self.btn_clear = QPushButton("Clear")
        self.btn_create = QPushButton("Create Presenter")
        actions.addStretch(1)
        actions.addWidget(self.btn_clear)
        actions.addWidget(self.btn_create)
        root.addWidget(grp_form)
        root.addLayout(actions)
        root.addStretch(1)

        self.btn_reload.clicked.connect(self.load_presenters)
        self.btn_clear.clicked.connect(self.clear_form)
        self.btn_create.clicked.connect(self.create_presenter)
        self.btn_add_block.clicked.connect(self.on_add_block)
        self.btn_remove_block.clicked.connect(self.on_remove_block)
        self.btn_clear_blocks.clicked.connect(self.on_clear_blocks)

    # Public
    def load_presenters(self) -> None:
        self._status("Loading presenters…", 1500)
        data = self.api.get_presenters()
        if data is None:
            self._status("Failed to load presenters.", 3000)
            return
        presenters = self._coerce_presenters_list(data)
        self.presenters_list.clear()
        for p in presenters:
            name = p.get("name") or "(unnamed)"
            schedule = p.get("schedule")
            roles = p.get("roles") or []
            voice_id = p.get("voice_id") or ""
            sched_summary = ""
            if isinstance(schedule, list):
                parts = []
                for b in schedule:
                    if isinstance(b, dict):
                        days = b.get("days") or []
                        start = (b.get("start") or "").strip()
                        end = (b.get("end") or "").strip()
                        parts.append(f"{','.join(days)} {start}-{end}")
                sched_summary = " | ".join([p for p in parts if p.strip()])
            elif isinstance(schedule, dict):
                days = schedule.get("days") or []
                start = (schedule.get("start") or "").strip()
                end = (schedule.get("end") or "").strip()
                sched_summary = f"{','.join(days)} {start}-{end}"
            summary = f"{name} — {sched_summary} — roles:{','.join(roles)} — {voice_id}"
            self.presenters_list.addItem(QListWidgetItem(summary))
        self._log(f"[GET /presenters] {self.presenters_list.count()} item(s)")
        self._status("Presenters loaded", 1500)

    def clear_form(self) -> None:
        self.edit_name.clear()
        for cb in self.day_checks:
            cb.setChecked(False)
        self.time_start.setTime(QTime(9, 0))
        self.time_end.setTime(QTime(12, 0))
        self.blocks_list.clear()
        for cb in self.role_checks:
            cb.setChecked(False)
        if self.cmb_voice_id.count() > 0:
            self.cmb_voice_id.setCurrentIndex(0)

    def create_presenter(self) -> None:
        payload = self._build_payload()
        if payload is None:
            return
        body_preview = _compact_json(payload)
        self._log(f"[POST /presenters] body: {body_preview}")
        self._set_enabled(False)
        try:
            ok, status, text = self.api.create_presenter(payload)
            if ok and 200 <= status < 300:
                self._log(f"[POST /presenters] {status} ok")
                self._status("Presenter created", 2500)
                self.load_presenters()
                self.clear_form()
            else:
                snippet = (text or "")
                if len(snippet) > 600:
                    snippet = snippet[:600] + "…"
                self._log(f"[POST /presenters] {status} fail: {snippet}")
                QMessageBox.warning(self, "Create failed", f"HTTP {status}\n{snippet}")
        finally:
            self._set_enabled(True)

    def on_add_block(self) -> None:
        days = [cb.property("code") for cb in self.day_checks if cb.isChecked()]
        if not days:
            QMessageBox.warning(self, "Validation", "Select at least one day for the block.")
            return
        start = self.time_start.time()
        end = self.time_end.time()
        if start >= end:
            QMessageBox.warning(self, "Validation", "End time must be after start time.")
            return
        block = {"days": days, "start": start.toString("HH:mm"), "end": end.toString("HH:mm")}
        summary = f"{','.join(days)} {block['start']}-{block['end']}"
        item = QListWidgetItem(summary)
        item.setData(Qt.ItemDataRole.UserRole, block)
        self.blocks_list.addItem(item)

    def on_remove_block(self) -> None:
        rows = sorted({i.row() for i in self.blocks_list.selectedIndexes()}, reverse=True)
        for r in rows:
            self.blocks_list.takeItem(r)

    def on_clear_blocks(self) -> None:
        self.blocks_list.clear()

    # Internals
    def _build_payload(self) -> Optional[Dict[str, Any]]:
        name = self.edit_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "Name is required.")
            return None
        # Collect blocks from the list; if none, try to use current selection as one block
        blocks: List[Dict[str, Any]] = []
        for i in range(self.blocks_list.count()):
            it = self.blocks_list.item(i)
            b = it.data(Qt.ItemDataRole.UserRole) or {}
            if isinstance(b, dict):
                days = [d for d in (b.get("days") or []) if d]
                start = str(b.get("start") or "").strip()
                end = str(b.get("end") or "").strip()
                if days and start and end:
                    blocks.append({"days": days, "start": start, "end": end})
        if not blocks:
            days = [cb.property("code") for cb in self.day_checks if cb.isChecked()]
            start = self.time_start.time()
            end = self.time_end.time()
            if days and start < end:
                blocks.append({"days": days, "start": start.toString("HH:mm"), "end": end.toString("HH:mm")})
        if not blocks:
            QMessageBox.warning(self, "Validation", "Add at least one schedule block.")
            return None
        # Validate each block
        for b in blocks:
            if not b["days"]:
                QMessageBox.warning(self, "Validation", "A schedule block has no days selected.")
                return None
            try:
                t_start = QTime.fromString(b["start"], "HH:mm")
                t_end = QTime.fromString(b["end"], "HH:mm")
            except Exception:
                QMessageBox.warning(self, "Validation", "Invalid time in a schedule block.")
                return None
            if not t_start.isValid() or not t_end.isValid() or t_start >= t_end:
                QMessageBox.warning(self, "Validation", "Each block must have End after Start.")
                return None
        roles = [cb.property("code") for cb in self.role_checks if cb.isChecked()]
        if not roles:
            QMessageBox.warning(self, "Validation", "Select at least one role.")
            return None
        voice_model = VOICE_MODEL_DEFAULT
        voice_id = self.cmb_voice_id.currentText().strip()
        if not voice_id:
            QMessageBox.warning(self, "Validation", "Voice ID is required.")
            return None
        payload = {
            "name": name,
            "schedule": blocks,
            "roles": roles,
            "voice_model": voice_model,
            "voice_id": voice_id,
        }
        return payload

    def _coerce_presenters_list(self, data: Any) -> List[Dict[str, Any]]:
        if isinstance(data, dict):
            if "presenters" in data and isinstance(data["presenters"], list):
                return [p for p in data["presenters"] if isinstance(p, dict)]
            # Some APIs might return keyed dicts
            return [v for v in data.values() if isinstance(v, dict)]
        if isinstance(data, list):
            return [p for p in data if isinstance(p, dict)]
        return []

    def _set_enabled(self, enabled: bool) -> None:
        for w in [
            self.presenters_list,
            self.btn_reload,
            self.edit_name,
            *self.day_checks,
            self.time_start,
            self.time_end,
            self.btn_add_block,
            self.blocks_list,
            self.btn_remove_block,
            self.btn_clear_blocks,
            *self.role_checks,
            self.cmb_voice_id,
            self.btn_clear,
            self.btn_create,
        ]:
            w.setEnabled(enabled)

    def _log(self, msg: str) -> None:
        try:
            self._log_cb(msg)
        except Exception:
            pass

    def _status(self, msg: str, ms: int = 3000) -> None:
        try:
            self._status_cb(msg, ms)
        except Exception:
            pass


def _wrap(layout: QHBoxLayout) -> QWidget:
    c = QWidget()
    c.setLayout(layout)
    return c


def _compact_json(obj: Any) -> str:
    try:
        return __import__("json").dumps(obj, separators=(",", ":"), ensure_ascii=False)
    except Exception:
        return str(obj)
