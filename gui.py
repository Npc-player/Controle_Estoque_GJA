import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QLineEdit, 
                             QTabWidget, QFrame, QSpacerItem, QSizePolicy, 
                             QStyle)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPixmap, QIcon

from config import resource_path
import backend
import dialogs
# Importa as abas do novo arquivo widgets.py
from abas import (DashboardTab, ProductsTab, StockTab, MovementsTab, 
                     DeletedTab, AdminTab, ReportsTab)

STYLESHEET = """
QMainWindow { background-color: #F3F4F6; }
QWidget { font-family: 'Segoe UI', sans-serif; font-size: 14px; color: #333; }
QTabWidget::pane { border: 1px solid #E5E7EB; background: transparent; border-radius: 5px; top: -1px; }
QTabBar::tab { background: #E5E7EB; color: #6B7280; padding: 10px 20px; margin-right: 4px; border-top-left-radius: 6px; border-top-right-radius: 6px; min-width: 130px; }
QTabBar::tab:selected { background: #DBEAFE; color: #1E40AF; font-weight: bold; border-bottom: 2px solid #2563EB; }
QPushButton { background-color: #2563EB; color: white; border-radius: 5px; padding: 8px 16px; font-weight: bold; }
QPushButton:hover { background-color: #1D4ED8; }
QPushButton:disabled { background-color: #9CA3AF; }
QPushButton#deleteBtn { background-color: #EF4444; }
QPushButton#editBtn   { background-color: #F59E0B; }
QLineEdit { padding: 8px; border: 1px solid #D1D5DB; border-radius: 5px; background: white; }
QTableWidget { background-color: transparent; border: none; gridline-color: #D1D5DB; }
QHeaderView::section { background-color: rgba(255, 255, 255, 200); padding: 8px; border: none; border-bottom: 1px solid #E5E7EB; font-weight: bold; }
QFrame#header { background-color: white; border-bottom: 1px solid #E5E7EB; }
QLabel#statusOffline { color: #EF4444; font-weight: bold; }
QLabel#statusOnline  { color: #10B981; font-weight: bold; }
QLabel#statusSaving  { color: #F59E0B; font-weight: bold; }
QLabel#statusSyncing { color: #6366F1; font-weight: bold; }
"""

class AsyncDataLoader(QThread):
    finished = pyqtSignal(bool)
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
    def run(self):
        self.finished.emit(self.manager.fetch_data())

class LoginWindow(QWidget):
    def __init__(self, manager, on_success_callback):
        super().__init__()
        self.manager = manager
        self.on_success = on_success_callback
        self.setWindowTitle("Login")
        self.setFixedSize(400, 300)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        title = QLabel("Controle de Estoque")
        title.setFont(QFont('Segoe UI', 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        self.email_input = QLineEdit(placeholderText="Email")
        self.senha_input = QLineEdit(placeholderText="Senha")
        self.senha_input.setEchoMode(QLineEdit.Password)
        self.senha_input.returnPressed.connect(self._handle_login)
        btn = QPushButton("Entrar")
        btn.clicked.connect(self._handle_login)
        btn.setFixedHeight(40)
        layout.addWidget(title)
        layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        layout.addWidget(self.email_input)
        layout.addWidget(self.senha_input)
        layout.addWidget(btn)
        layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        self.setLayout(layout)

    def _handle_login(self):
        user = self.manager.check_login(self.email_input.text(), self.senha_input.text())
        if user:
            self.on_success(user)
        else:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Erro", "Usuário ou senha inválidos.")

class MainWindow(QMainWindow):
    def __init__(self, user, manager, skip_initial_sync=False):
        super().__init__()
        self.user = user
        self.manager = manager
        self._loader = None
        self.setWindowTitle(f"Controle de Estoque — {user.get('nome', 'Usuário')}")
        self.resize(1100, 700)
        self._setup_ui()
        self._refresh_all_tabs()
        
        # Timer existente (verifica status visual a cada 2s)
        self.sync_timer = QTimer()
        self.sync_timer.timeout.connect(self._update_sync_status)
        self.sync_timer.start(2000)
        
        # --- NOVA FUNCIONALIDADE: Atualização automática a cada 5 minutos ---
        # 5 minutos = 300000 milissegundos
        self.auto_refresh_timer = QTimer(self)
        self.auto_refresh_timer.timeout.connect(self.refresh_data)
        self.auto_refresh_timer.start(300000) 
        # --------------------------------------------------------------------
        
        if not skip_initial_sync:
            self.refresh_data()

    def _update_sync_status(self):
        if hasattr(self.manager, 'get_sync_status'):
            status = self.manager.get_sync_status()
            if status['queue_size'] > 0:
                self.lbl_status.setText(f"⏳ Sincronizando... ({status['queue_size']} na fila)")
                self.lbl_status.setStyleSheet("color: #6366F1; font-weight: bold;")

    def _setup_ui(self):
        self.setWindowIcon(QIcon(resource_path('ctrlestoque.ico')))
        central = QWidget()
        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        header = QFrame(objectName="header")
        header.setFixedHeight(70)
        hl = QHBoxLayout()
        self.lbl_logo = QLabel()
        pixmap = QPixmap(resource_path("cab.png"))
        if not pixmap.isNull():
            self.lbl_logo.setPixmap(pixmap.scaledToHeight(50, Qt.SmoothTransformation))
        self.lbl_logo.setAlignment(Qt.AlignCenter)
        self.lbl_user = QLabel(f"Usuário: {self.user.get('nome','N/A')} ({self.user.get('perfil','-')})")
        self.lbl_status = QLabel("⏳ Sincronizando...", objectName="statusSyncing")
        self.lbl_status.setStyleSheet("color: #6366F1; font-weight: bold;")
        btn_refresh = QPushButton("↻ Atualizar")
        btn_refresh.setFixedWidth(110)
        btn_refresh.clicked.connect(self.refresh_data)
        btn_about = QPushButton()
        icon_info = self.style().standardIcon(QStyle.SP_MessageBoxInformation)
        btn_about.setIcon(icon_info)
        btn_about.setFixedSize(40, 40)
        btn_about.setToolTip("Sobre o Sistema")
        btn_about.clicked.connect(self._show_about)
        btn_logout = QPushButton("Sair")
        btn_logout.setFixedWidth(80)
        btn_logout.clicked.connect(self.close)
        hl.addWidget(self.lbl_user)
        hl.addStretch()
        hl.addWidget(self.lbl_logo)
        hl.addStretch()
        right_widgets = QVBoxLayout()
        rw_h = QHBoxLayout()
        rw_h.addWidget(self.lbl_status)
        rw_h.addWidget(btn_refresh)
        rw_h.addWidget(btn_about)
        rw_h.addWidget(btn_logout)
        right_widgets.addLayout(rw_h)
        right_widgets.addStretch()
        hl.addLayout(right_widgets)
        header.setLayout(hl)
        self.tabs = QTabWidget()
        perfil = self.user.get('perfil', 'usuario')
        
        # Visão Geral: Admin e Gerência
        if perfil in ['admin', 'gerência']:
            self.tabs.addTab(DashboardTab(self.manager), "Visão Geral")
            
        # Abas Padrão
        self.tabs.addTab(ProductsTab(self.manager, self.user, self), "Produtos")
        self.tabs.addTab(StockTab(self.manager, self.user), "Estoque Atual")
        self.tabs.addTab(MovementsTab(self.manager, self.user, self), "Movimentações")
        
        # Exclusões: Admin e Gerência
        if perfil in ['admin', 'gerência']:
            self.tabs.addTab(DeletedTab(self.manager), "Exclusões")
            
        # Cadastros: Apenas Admin
        if perfil == 'admin':
            self.tabs.addTab(AdminTab(self.manager, self.user), "Cadastros")
            
        # Relatórios: Admin e Gerência (ALTERAÇÃO REALIZADA AQUI)
        if perfil in ['admin', 'gerência']:
            self.tabs.addTab(ReportsTab(self.manager, self.user), "Relatórios")
            
        self.tabs.currentChanged.connect(self._on_tab_changed)
        root.addWidget(header)
        root.addWidget(self.tabs)
        central.setLayout(root)
        self.setCentralWidget(central)

    def _show_about(self):
        dlg = dialogs.AboutDialog(self)
        dlg.exec_()

    def refresh_data(self):
        # Se já existe um carregamento em andamento, ignora a nova solicitação
        if self._loader and self._loader.isRunning():
            return

        self._set_status("⏳ Sincronizando...", "#6366F1")
        self._loader = AsyncDataLoader(self.manager)
        self._loader.finished.connect(self._on_sync_done)
        self._loader.start()

    def _on_sync_done(self, success):
        self._update_status_and_tabs(success and self.manager.is_online)

    def _update_status_and_tabs(self, online: bool):
        if online:
            self._set_status("🟢 Online", "#10B981")
        else:
            self._set_status("🔴 Offline (Cache)", "#EF4444")
        self._refresh_all_tabs()

    def _set_status(self, text, color):
        self.lbl_status.setText(text)
        self.lbl_status.setStyleSheet(f"color: {color}; font-weight: bold;")

    def set_saving_status(self, saving: bool):
        if saving:
            self._set_status("💾 Salvando...", "#F59E0B")
        else:
            color = "#10B981" if self.manager.is_online else "#EF4444"
            label = "🟢 Online" if self.manager.is_online else "🔴 Offline (Cache)"
            self._set_status(label, color)

    def _refresh_all_tabs(self):
        current = self.tabs.currentIndex()
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if i == current:
                if hasattr(tab, 'load_table'):
                    tab.load_table()
            else:
                tab._needs_refresh = True

    def _on_tab_changed(self, index):
        tab = self.tabs.widget(index)
        if getattr(tab, '_needs_refresh', False):
            tab._needs_refresh = False
            if hasattr(tab, 'load_table'):
                tab.load_table()

    def mark_tabs_dirty(self):
        current = self.tabs.currentIndex()
        for i in range(self.tabs.count()):
            if i != current:
                self.tabs.widget(i)._needs_refresh = True