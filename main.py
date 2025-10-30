import sys
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QMessageBox,
)


class HMACKeyDialog(QDialog):
    """
    Simple modal dialog to request an HMAC key from the user on application start.

    - The key is masked (password-like) by default.
    - Basic validation ensures the field is not empty.
    - Optionally, you can extend `validate_key` to enforce length/format.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Enter HMAC Key")
        self.setModal(True)
        self._key: Optional[str] = None

        # Widgets
        self.label = QLabel("Please enter your HMAC key to continue:")
        self.edit = QLineEdit()
        self.edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit.setPlaceholderText("HMAC key…")
        self.edit.returnPressed.connect(self.accept)

        self.btn_ok = QPushButton("OK")
        self.btn_cancel = QPushButton("Cancel")

        # Layout
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_ok)

        root = QVBoxLayout(self)
        root.addWidget(self.label)
        root.addWidget(self.edit)
        root.addLayout(btn_row)

        # Signals
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

        # UX niceties
        self.resize(420, self.sizeHint().height())
        self.edit.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    def validate_key(self, key: str) -> bool:
        """Return True if key looks acceptable. Adjust rules as needed."""
        if not key.strip():
            return False
        # Example: uncomment to enforce hex-only and a minimum length
        # import re
        # return bool(re.fullmatch(r"[0-9a-fA-F]{32,}", key))
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


def request_hmac_key(parent=None) -> Optional[str]:
    dlg = HMACKeyDialog(parent)
    result = dlg.exec()
    if result == QDialog.DialogCode.Accepted:
        return dlg.get_key()
    return None


def main() -> int:
    app = QApplication(sys.argv)

    # 1) Ask for the HMAC key right away (on application load)
    hmac_key = request_hmac_key()

    if not hmac_key:
        # User canceled or provided invalid key repeatedly.
        # You can decide to exit or allow limited functionality.
        QMessageBox.information(None, "Exiting", "An HMAC key is required. The application will close.")
        return 0

    # 2) At this point you can initialize your API client with `hmac_key`.
    #    For now we just demonstrate that we have it.
    #    Replace the following placeholder with your API initialization logic.
    QMessageBox.information(None, "HMAC Key Received", "The HMAC key has been captured and will be used to authorize API calls.")

    # Example placeholder: print to stdout (avoid logging secrets in production!)
    print("[DEBUG] HMAC key captured (do not log secrets in production):", hmac_key)

    # If you have a main window or further UI, you would launch it here.
    # For now, we just quit after capturing the key.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
