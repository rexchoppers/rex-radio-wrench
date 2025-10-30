from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox

class HMACKeyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Enter HMAC Key")
        self.setModal(True)
        self._key: Optional[str] = None

        self.label = QLabel("Please enter your HMAC key to continue:")
        self.edit = QLineEdit()
        self.edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit.setPlaceholderText("HMAC key…")
        self.edit.returnPressed.connect(self.accept)

        self.btn_ok = QPushButton("OK")
        self.btn_cancel = QPushButton("Cancel")

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_ok)

        root = QVBoxLayout(self)
        root.addWidget(self.label)
        root.addWidget(self.edit)
        root.addLayout(btn_row)

        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

        self.resize(420, self.sizeHint().height())
        self.edit.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    def validate_key(self, key: str) -> bool:
        if not key.strip():
            return False
        return True

    def accept(self) -> None:  # type: ignore[override]
        key = self.edit.text()
        if not self.validate_key(key):
            QMessageBox.warning(self, "Invalid key", "Please provide a valid HMAC key.")
            return
        self._key = key
        super().accept()

    def get_key(self) -> Optional[str]:
        return self._key
