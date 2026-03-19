import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QThread, pyqtSignal
from backend import DataManager
from gui import LoginWindow, MainWindow, STYLESHEET

import sys
import os


class SyncThread(QThread):
    finished_sync = pyqtSignal(bool)
    def __init__(self, manager):
        super().__init__()
        self.manager = manager

    def run(self):
        self.finished_sync.emit(self.manager.fetch_data())

class App:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setStyleSheet(STYLESHEET)
        self.manager = DataManager()
        self.login_window = None
        self.main_window = None

    def run(self):
        self.show_login()
        # Faz a primeira sincronização em background
        self.sync = SyncThread(self.manager)
        self.sync.finished_sync.connect(lambda s: print(f"[SYNC] Dados carregados: {s}"))
        self.sync.start()
        return self.app.exec_()

    def show_login(self):
        self.login_window = LoginWindow(self.manager, self._on_login_success)
        self.login_window.show()

    def _on_login_success(self, user):
        self.main_window = MainWindow(user, self.manager)
        self.main_window.show()
        self.login_window.close()

if __name__ == "__main__":
    app = App()
    sys.exit(app.run())