import sys
from typing import Optional

from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox
from dialogs.hmac_key_dialog import HMACKeyDialog
from main_window import MainWindow


def request_hmac_key(parent=None) -> Optional[str]:
    dlg = HMACKeyDialog(parent)
    result = dlg.exec()
    if result == QDialog.DialogCode.Accepted:
        return dlg.get_key()
    return None


def main() -> int:
    app = QApplication(sys.argv)
    hmac_key = request_hmac_key()

    if not hmac_key:
        QMessageBox.information(None, "Exiting", "An HMAC key is required. The application will close.")
        return 0

    # Show the main dashboard window; Settings can be opened later from the menu
    win = MainWindow(hmac_key=hmac_key)
    win.show()

    # Optionally log debug info (avoid logging secrets in production)
    print("[DEBUG] HMAC key captured (do not log secrets in production):", hmac_key)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
