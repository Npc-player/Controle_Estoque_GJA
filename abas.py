# widgets.py
import sys
import uuid
import os
from datetime import datetime
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox, 
                             QComboBox, QFrame, QSpacerItem, QSizePolicy, QDialog, 
                             QFormLayout, QDialogButtonBox, QHeaderView, 
                             QAbstractItemView, QDateEdit, QTabWidget, QFileDialog)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor, QPainter, QPixmap

from config import resource_path
import backend
import dialogs
import graficos

# --- Importações para Exportação ---
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

# --- Funções Auxiliares ---
def show_error_box(parent, title, message):
    msg_box = QMessageBox(parent)
    msg_box.setIcon(QMessageBox.Critical)
    msg_box.setWindowTitle(title)
    msg_box.setText(str(message))
    msg_box.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
    msg_box.exec_()

# --- Classes Auxiliares ---
class DateTableWidgetItem(QTableWidgetItem):
    def __init__(self, text, sort_key):
        super().__init__(text)
        self.sort_key = sort_key
    def __lt__(self, other):
        if not isinstance(other, DateTableWidgetItem):
            return super().__lt__(other)
        return self.sort_key < other.sort_key

# --- Classe Base ---
class BaseTab(QWidget):
    def __init__(self, manager, main_window=None):
        super().__init__()
        self.manager = manager
        self.main_window = main_window
        self._needs_refresh = False
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.bg_pixmap = QPixmap(resource_path("fundo.png"))

    def _create_table(self):
        t = QTableWidget()
        t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        t.setSortingEnabled(True)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.setSelectionBehavior(QAbstractItemView.SelectRows)
        t.setSelectionMode(QAbstractItemView.SingleSelection)
        return t

    def _set_btns(self, enabled, *btns):
        for b in btns:
            if b: b.setEnabled(enabled)

    def _notify_saving(self, saving):
        if self.main_window:
            self.main_window.set_saving_status(saving)

    def _after_write(self):
        if self.main_window:
            self.main_window.mark_tabs_dirty()
            
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setOpacity(1.0)
        if not self.bg_pixmap.isNull():
            painter.drawPixmap(self.rect(), self.bg_pixmap)
        super().paintEvent(event)

# --- Abas Específicas ---

class DashboardTab(BaseTab):
    def __init__(self, manager):
        super().__init__(manager)
        self.layout.addWidget(QLabel("<h2>Painel de Controle</h2>"))
        self.stats = QLabel("Carregando...")
        self.stats.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.stats)
        self.layout.addStretch(1)
        try:
            chart_container = QFrame()
            chart_container.setStyleSheet("background-color: transparent; border: none;")
            chart_layout = QVBoxLayout()
            self.charts_widget = graficos.ChartsWidget(manager)
            chart_layout.addWidget(self.charts_widget)
            chart_container.setLayout(chart_layout)
            self.layout.addWidget(chart_container)
        except Exception as e:
            print(f"Erro ao carregar gráficos: {e}")
        self.layout.addStretch(2)

    def load_table(self):
        total_prod = len(self.manager.get_products())
        total_stock = int(sum(float(i.get('quantidade') or 0) for i in self.manager.get_stock()))
        self.stats.setText(f"<ul><li><b>Produtos ativos:</b> {total_prod}</li><li><b>Itens em estoque:</b> {total_stock}</li></ul>")
        if hasattr(self, 'charts_widget'):
            self.charts_widget.load_data()

class ProductsTab(BaseTab):
    def __init__(self, manager, user, main_window):
        super().__init__(manager, main_window)
        self.user = user
        self.btn_add = self.btn_edit = self.btn_del = None
        self._setup_ui()

    def _setup_ui(self):
        hl = QHBoxLayout()
        hl.addWidget(QLabel("<h3>Lista de Produtos</h3>"))
        self.btn_inactive = QPushButton("Mostrar Inativos")
        self.btn_inactive.setCheckable(True)
        self.btn_inactive.clicked.connect(self._toggle_inactive)
        if self.user.get('perfil') == 'admin':
            self.btn_add = QPushButton("Novo Produto")
            self.btn_edit = QPushButton("Editar Selecionado", objectName="editBtn")
            self.btn_del = QPushButton("Excluir Selecionado", objectName="deleteBtn")
            self.btn_add.clicked.connect(self._add)
            self.btn_edit.clicked.connect(self._edit)
            self.btn_del.clicked.connect(self._delete)
            hl.addWidget(self.btn_add)
            hl.addWidget(self.btn_edit)
            hl.addWidget(self.btn_del)
        hl.addStretch()
        hl.addWidget(self.btn_inactive)
        self.layout.addLayout(hl)
        self.table = self._create_table()
        # ALTERAÇÃO: Tabela ocupa toda a largura
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.layout.addWidget(self.table)

    def _toggle_inactive(self):
        self.btn_inactive.setText("Mostrar Ativos" if self.btn_inactive.isChecked() else "Mostrar Inativos")
        self.load_table()

    def _add(self):
        dlg = dialogs.ProductDialog(self.manager, self.user.get('nome'), self)
        if dlg.exec_() == QDialog.Accepted:
            self._write(self.manager.send_upsert, 'produtos', dlg.get_data())

    def _edit(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows: return
        pid = self.table.item(rows[0].row(), 0).data(Qt.UserRole)
        data = self.manager.get_product_by_id(pid)
        if data:
            dlg = dialogs.ProductDialog(self.manager, self.user.get('nome'), self, data)
            if dlg.exec_() == QDialog.Accepted:
                self._write(self.manager.send_upsert, 'produtos', dlg.get_data())

    def _delete(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows: return
        pid = self.table.item(rows[0].row(), 0).data(Qt.UserRole)
        if QMessageBox.question(self, "Excluir", "Confirmar exclusão?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self._write(self.manager.delete_row, 'produtos', pid)

    def _write(self, fn, *args):
        self._set_btns(False, self.btn_add, self.btn_edit, self.btn_del)
        self._notify_saving(True)
        ok, msg = fn(*args)
        self._set_btns(True, self.btn_add, self.btn_edit, self.btn_del)
        self._notify_saving(False)
        if ok:
            self.load_table()
            self._after_write()
        else:
            show_error_box(self, "Erro", str(msg))

    def load_table(self):
        self.table.setUpdatesEnabled(False)
        self.table.setSortingEnabled(False)
        data = self.manager.get_products()
        self.table.setRowCount(len(data))
        self.table.setColumnCount(12)
        self.table.setHorizontalHeaderLabels(["Nome", "Categoria", "Unidade", "Valor", "Ata/Licitação", "Validade", "Status", "Est. Mínimo", "Cadastro (Data)", "Cadastro (Usuário)", "Alteração (Data)", "Alteração (Usuário)"])
        for r, item in enumerate(data):
            n = QTableWidgetItem(item.get('nome', ''))
            n.setData(Qt.UserRole, item.get('id'))
            self.table.setItem(r, 0, n)
            self.table.setItem(r, 1, QTableWidgetItem(item.get('nome_categoria', '')))
            self.table.setItem(r, 2, QTableWidgetItem(item.get('unidade_medida', '')))
            try:
                val = float(item.get('valor', 0))
                val_str = f"{val:.2f}".replace(".", ",")
            except:
                val_str = str(item.get('valor', '-'))
            self.table.setItem(r, 3, QTableWidgetItem(val_str))
            self.table.setItem(r, 4, QTableWidgetItem(str(item.get('ata_licitacao', '-'))))
            vt = item.get('validade_tipo', 'INDEFINIDA')
            self.table.setItem(r, 5, QTableWidgetItem(item.get('validade') if vt == 'DEFINIDA' else "Indefinida"))
            self.table.setItem(r, 6, QTableWidgetItem("Ativo" if str(item.get('ativo')).lower() == 'true' else "Inativo"))
            self.table.setItem(r, 7, QTableWidgetItem(str(item.get('estoque_minimo', 0))))
            self.table.setItem(r, 8, QTableWidgetItem(str(item.get('data_cadastro', '-'))))
            self.table.setItem(r, 9, QTableWidgetItem(str(item.get('usuario_cadastro', '-'))))
            self.table.setItem(r, 10, QTableWidgetItem(str(item.get('data_alteracao', '-'))))
            self.table.setItem(r, 11, QTableWidgetItem(str(item.get('usuario_alteracao', '-'))))
        self.table.setSortingEnabled(True)
        self.table.setUpdatesEnabled(True)
        # Ajuste automático de largura das colunas para visualização, respeitando o stretch
        self.table.resizeColumnsToContents()

class StockTab(BaseTab):
    def __init__(self, manager, user):
        super().__init__(manager)
        self.user = user
        self._setup_ui()

    def _setup_ui(self):
        self.layout.addWidget(QLabel("<h3>Estoque por Local</h3>"))
        filter_widget = QWidget()
        filter_layout = QHBoxLayout()
        filter_layout.setContentsMargins(0, 0, 0, 0)
        self.filter_container = filter_widget
        
        filter_layout.addWidget(QLabel("Categoria:"))
        self.combo_categoria = QComboBox()
        self.combo_categoria.setMinimumWidth(150)
        self.combo_categoria.currentIndexChanged.connect(self._on_categoria_changed)
        filter_layout.addWidget(self.combo_categoria)
        
        filter_layout.addWidget(QLabel("Produto:"))
        self.combo_produto = QComboBox()
        self.combo_produto.setMinimumWidth(200)
        self.combo_produto.currentIndexChanged.connect(self._on_produto_changed)
        filter_layout.addWidget(self.combo_produto)
        
        btn_limpar = QPushButton("Limpar Filtros")
        btn_limpar.clicked.connect(self._reset_filters)
        filter_layout.addWidget(btn_limpar)
        filter_layout.addStretch()
        filter_widget.setLayout(filter_layout)
        self.layout.addWidget(filter_widget)
        
        if self.user.get('perfil') == 'usuário':
            self.filter_container.hide()
        
        self.table = self._create_table()
        self.layout.addWidget(self.table)

    def _on_categoria_changed(self):
        self._update_product_combo()
        self.load_table()

    def _on_produto_changed(self):
        self.load_table()

    def _reset_filters(self):
        self.combo_categoria.blockSignals(True)
        self.combo_categoria.setCurrentIndex(0)
        self.combo_categoria.blockSignals(False)
        self._update_product_combo()
        self.load_table()

    def _update_product_combo(self):
        current_cat_id = self.combo_categoria.currentData()
        self.combo_produto.blockSignals(True)
        self.combo_produto.clear()
        self.combo_produto.addItem("Todos", None)
        for p in self.manager.get_products():
            if current_cat_id and p.get('categoria') != current_cat_id:
                continue
            self.combo_produto.addItem(p['nome'], p['id'])
        self.combo_produto.blockSignals(False)

    def load_table(self):
        data = self.manager.get_stock(user=self.user)
        if self.user.get('perfil') != 'usuário':
            self._refresh_combos_data()
            selected_cat_id = self.combo_categoria.currentData()
            selected_prod_id = self.combo_produto.currentData()
            products = self.manager.get_products()
            prod_map = {p['id']: p for p in products}
            filtered_data = []
            for item in data:
                prod_id = item.get('produto_id')
                if selected_prod_id:
                    if prod_id != selected_prod_id: continue
                elif selected_cat_id:
                    prod_info = prod_map.get(prod_id)
                    if not prod_info or prod_info.get('categoria') != selected_cat_id: continue
                filtered_data.append(item)
            data = filtered_data
            
        self.table.setUpdatesEnabled(False)
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(data))
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Produto", "Localização", "Qtd", "Status"])
        for r, item in enumerate(data):
            self.table.setItem(r, 0, QTableWidgetItem(item.get('nome_produto', '')))
            self.table.setItem(r, 1, QTableWidgetItem(item.get('nome_localizacao', '')))
            try:
                qtd = float(item.get('quantidade') or 0)
            except:
                qtd = 0.0
            self.table.setItem(r, 2, QTableWidgetItem(str(int(qtd))))
            si = QTableWidgetItem("Baixo" if qtd < 10 else "OK")
            if qtd < 10:
                si.setBackground(QColor("#FEE2E2"))
            self.table.setItem(r, 3, si)
        self.table.setSortingEnabled(True)
        self.table.setUpdatesEnabled(True)

    def _refresh_combos_data(self):
        current_cat = self.combo_categoria.currentData()
        current_prod = self.combo_produto.currentData()
        self.combo_categoria.blockSignals(True)
        self.combo_categoria.clear()
        self.combo_categoria.addItem("Todas", None)
        for c in self.manager.get_categories():
            self.combo_categoria.addItem(c['nome'], c['id'])
        idx = self.combo_categoria.findData(current_cat)
        if idx >= 0:
            self.combo_categoria.setCurrentIndex(idx)
        else:
            self.combo_categoria.setCurrentIndex(0)
        self.combo_categoria.blockSignals(False)
        
        self.combo_produto.blockSignals(True)
        selected_cat_id = self.combo_categoria.currentData()
        self.combo_produto.clear()
        self.combo_produto.addItem("Todos", None)
        for p in self.manager.get_products():
            if selected_cat_id and p.get('categoria') != selected_cat_id:
                continue
            self.combo_produto.addItem(p['nome'], p['id'])
        idx_p = self.combo_produto.findData(current_prod)
        if idx_p >= 0:
            self.combo_produto.setCurrentIndex(idx_p)
        else:
            self.combo_produto.setCurrentIndex(0)
        self.combo_produto.blockSignals(False)

class MovementsTab(BaseTab):
    def __init__(self, manager, user, main_window):
        super().__init__(manager, main_window)
        self.user = user
        self.btn_new = self.btn_edit = self.btn_del = None
        self._setup_ui()

    def _setup_ui(self):
        hl = QHBoxLayout()
        hl.addWidget(QLabel("<h3>Histórico de Movimentações</h3>"))
        self.btn_new = QPushButton("Nova Movimentação")
        self.btn_new.clicked.connect(self._new)
        hl.addWidget(self.btn_new)
        if self.user.get('perfil') == 'admin':
            self.btn_edit = QPushButton("Editar Selecionado", objectName="editBtn")
            self.btn_edit.clicked.connect(self._edit)
            hl.addWidget(self.btn_edit)
            self.btn_del = QPushButton("Excluir Selecionado", objectName="deleteBtn")
            self.btn_del.clicked.connect(self._delete)
            hl.addWidget(self.btn_del)
        dw = QWidget()
        dl = QHBoxLayout()
        dl.setContentsMargins(0, 0, 0, 0)
        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDate(QDate.currentDate().addMonths(-1))
        self.date_end = QDateEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setDate(QDate.currentDate())
        btn_f = QPushButton("Filtrar")
        btn_f.clicked.connect(self._apply_filter)
        btn_r = QPushButton("Resetar")
        btn_r.clicked.connect(self._reset_filter)
        for w in [QLabel("De:"), self.date_start, QLabel("Até:"), self.date_end, btn_f, btn_r]:
            dl.addWidget(w)
        dw.setLayout(dl)
        hl.addStretch()
        hl.addWidget(dw)
        self.layout.addLayout(hl)
        self.table = self._create_table()
        # ALTERAÇÃO: Tabela ocupa toda a largura
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.layout.addWidget(self.table)

    def _new(self):
        if not self.manager.is_online:
            QMessageBox.warning(self, "Offline", "Movimentações exigem conexão.")
            return
        dlg = dialogs.MovementDialog(self.manager, self.user.get('nome'), self, user_obj=self.user)
        if dlg.exec_() == QDialog.Accepted:
            data = dlg.data
            if data.get('is_batch'):
                self._process_batch(data)
            else:
                self._write(self.manager.process_movement, data)

    def _process_batch(self, batch_data):
        items = batch_data['items']
        self._set_btns(False, self.btn_new, self.btn_edit, self.btn_del)
        self._notify_saving(True)
        success_count = 0
        error_msg = None
        
        base = {
            "tipo": batch_data['tipo'],
            "motivo": batch_data['motivo'],
            "usuario": batch_data['usuario'],
            "localizacao_origem_id": batch_data.get('localizacao_origem_id'),
            "nome_origem": batch_data.get('nome_origem'),
            "localizacao_destino_id": batch_data.get('localizacao_destino_id'),
            "nome_destino": batch_data.get('nome_destino'),
            "data_hora": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        }

        for item in items:
            payload = {**base, **item, "id": uuid.uuid4().hex[:8]}
            ok, msg = self.manager.process_movement(payload)
            if ok:
                success_count += 1
            else:
                error_msg = f"Erro em '{item['nome_produto']}': {msg}"
                break
        
        self._set_btns(True, self.btn_new, self.btn_edit, self.btn_del)
        self._notify_saving(False)
        if error_msg:
            show_error_box(self, "Erro no Lote", error_msg)
        else:
            QMessageBox.information(self, "Sucesso", f"{success_count} movimentações processadas!")
        self.load_table()
        self._after_write()

    def _edit(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.warning(self, "Aviso", "Selecione uma movimentação.")
            return
        mov_id = self.table.item(rows[0].row(), 0).data(Qt.UserRole)
        old_mov = next((m for m in self.manager.get_movements() if m['id'] == mov_id), None)
        if old_mov:
            dlg = dialogs.MovementDialog(self.manager, self.user.get('nome'), self, mov_data=old_mov, user_obj=self.user)
            if dlg.exec_() == QDialog.Accepted:
                self._write(self.manager.edit_movement, old_mov, dlg.data)

    def _delete(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows: return
        mov_id = self.table.item(rows[0].row(), 0).data(Qt.UserRole)
        mov_data = next((m for m in self.manager.get_movements() if m['id'] == mov_id), None)
        if mov_data:
            if QMessageBox.question(self, "Excluir", "Confirma exclusão?\nO saldo de estoque será estornado automaticamente.", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                self._write(self.manager.delete_movement, mov_data)

    def _write(self, fn, *args):
        self._set_btns(False, self.btn_new, self.btn_edit, self.btn_del)
        self._notify_saving(True)
        ok, msg = fn(*args)
        self._set_btns(True, self.btn_new, self.btn_edit, self.btn_del)
        self._notify_saving(False)
        if ok:
            QMessageBox.information(self, "Sucesso", str(msg))
            self.load_table()
            self._after_write()
        else:
            show_error_box(self, "Erro", str(msg))

    def _apply_filter(self):
        self.load_table()

    def _reset_filter(self):
        self.date_start.setDate(QDate.currentDate().addMonths(-1))
        self.date_end.setDate(QDate.currentDate())
        self.load_table()

    def load_table(self):
        self.table.setUpdatesEnabled(False)
        self.table.setSortingEnabled(False)
        all_data = self.manager.get_movements(user=self.user)
        
        def get_date_obj(ds):
            if not ds: return datetime.min
            try: return datetime.strptime(ds.split('.')[0], "%Y-%m-%d %H:%M:%S").date()
            except:
                try: return datetime.strptime(ds, "%d/%m/%Y %H:%M:%S").date()
                except: return datetime.min
        
        d_start = self.date_start.date().toPyDate()
        d_end = self.date_end.date().toPyDate()
        data = []
        for item in all_data:
            item_date = get_date_obj(item.get('data_hora'))
            if d_start <= item_date <= d_end:
                data.append(item)
        
        def parse_date(ds):
            try: return datetime.strptime(ds.split('.')[0], "%Y-%m-%d %H:%M:%S")
            except:
                try: return datetime.strptime(ds, "%d/%m/%Y %H:%M:%S")
                except: return datetime.min
        data.sort(key=lambda x: parse_date(x.get('data_hora', '')), reverse=True)

        self.table.setRowCount(len(data))
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["Data", "Tipo", "Produto", "Origem", "Destino", "Qtd", "Motivo", "Usuário"])
        red_color = QColor("#FFE4E1")
        for r, item in enumerate(data):
            ds = str(item.get('data_hora', ''))
            dt_obj = parse_date(ds)
            df = dt_obj.strftime("%d/%m/%Y %H:%M") if dt_obj != datetime.min else ds
            di = DateTableWidgetItem(df, dt_obj)
            di.setData(Qt.UserRole, item.get('id'))
            i_tipo = QTableWidgetItem(item.get('tipo', ''))
            i_prod = QTableWidgetItem(item.get('nome_produto', ''))
            i_orig = QTableWidgetItem(item.get('nome_origem', '-'))
            i_dest = QTableWidgetItem(item.get('nome_destino', '-'))
            try: qty = int(float(item.get('quantidade', 0)))
            except: qty = 0
            i_qtd = QTableWidgetItem(str(qty))
            motivo = str(item.get('motivo', '-'))
            i_motivo = QTableWidgetItem(motivo)
            i_motivo.setToolTip(motivo)
            i_user = QTableWidgetItem(item.get('usuario', '-'))
            if "ESTORNO" in motivo.upper():
                for i in [di, i_tipo, i_prod, i_orig, i_dest, i_qtd, i_motivo, i_user]:
                    i.setBackground(red_color)
            self.table.setItem(r, 0, di)
            self.table.setItem(r, 1, i_tipo)
            self.table.setItem(r, 2, i_prod)
            self.table.setItem(r, 3, i_orig)
            self.table.setItem(r, 4, i_dest)
            self.table.setItem(r, 5, i_qtd)
            self.table.setItem(r, 6, i_motivo)
            self.table.setItem(r, 7, i_user)
        self.table.setSortingEnabled(True)
        self.table.setUpdatesEnabled(True)
        self.table.resizeColumnsToContents()

class DeletedTab(BaseTab):
    def __init__(self, manager):
        super().__init__(manager)
        self.layout.addWidget(QLabel("<h3>Registros Excluídos</h3>"))
        self.table = self._create_table()
        self.layout.addWidget(self.table)

    def load_table(self):
        self.table.setUpdatesEnabled(False)
        self.table.setSortingEnabled(False)
        data = self.manager.get_deleted()
        def parse_date(ds):
            try: return datetime.strptime(ds.split('.')[0], "%Y-%m-%d %H:%M:%S")
            except:
                try: return datetime.strptime(ds, "%d/%m/%Y %H:%M:%S")
                except: return datetime.min
        data.sort(key=lambda x: parse_date(x.get('data_hora', '')), reverse=True)
        self.table.setRowCount(len(data))
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["Data", "Tipo", "Produto", "Origem", "Destino", "Qtd", "Motivo", "Usuário"])
        for r, item in enumerate(data):
            ds = str(item.get('data_hora', ''))
            dt_obj = parse_date(ds)
            df = dt_obj.strftime("%d/%m/%Y %H:%M") if dt_obj != datetime.min else ds
            di = DateTableWidgetItem(df, dt_obj)
            self.table.setItem(r, 0, di)
            self.table.setItem(r, 1, QTableWidgetItem(item.get('tipo', '')))
            self.table.setItem(r, 2, QTableWidgetItem(item.get('nome_produto', '')))
            self.table.setItem(r, 3, QTableWidgetItem(item.get('nome_origem', '-')))
            self.table.setItem(r, 4, QTableWidgetItem(item.get('nome_destino', '-')))
            try: qty = int(float(item.get('quantidade', 0)))
            except: qty = 0
            self.table.setItem(r, 5, QTableWidgetItem(str(qty)))
            mo = str(item.get('motivo', '-'))
            mi = QTableWidgetItem(mo)
            mi.setToolTip(mo)
            self.table.setItem(r, 6, mi)
            self.table.setItem(r, 7, QTableWidgetItem(str(item.get('usuario', '-'))))
        self.table.setSortingEnabled(True)
        self.table.setUpdatesEnabled(True)

class AdminTab(BaseTab):
    def __init__(self, manager, user):
        super().__init__(manager)
        self.current_user = user.get('nome')
        self.layout.addWidget(QLabel("<h3>Cadastros Auxiliares</h3>"))
        self.combo_user_location = None
        tc = QTabWidget()
        tc.addTab(self._crud('categorias', ["Nome","Descrição"], [('Nome','nome'),('Descrição','descricao')]), "Categorias")
        tc.addTab(self._crud('localizacoes', ["Nome","Descrição"], [('Nome','nome'),('Descrição','descricao')], on_save_callback=self.refresh_user_location_combo), "Localizações")
        # ALTERAÇÃO: Adicionado colunas Localização e Status na lista de cabeçalhos
        tc.addTab(self._crud('usuarios', ["Nome","Email","Perfil","Localização","Status"], [('Nome','nome'),('Email','email'),('Senha','senha'),('Perfil','perfil')], is_user=True), "Usuários")
        self.layout.addWidget(tc)

    def refresh_user_location_combo(self):
        if self.combo_user_location:
            current_data = self.combo_user_location.currentData()
            self.combo_user_location.clear()
            for l in self.manager.get_locations():
                self.combo_user_location.addItem(l['nome'], l['id'])
            if current_data:
                idx = self.combo_user_location.findData(current_data)
                if idx >= 0:
                    self.combo_user_location.setCurrentIndex(idx)

    def _crud(self, entity_key, headers, edit_fields, is_user=False, on_save_callback=None):
        w = QWidget()
        lay = QVBoxLayout()
        if not is_user:
            frm = QFormLayout()
            inp = {}
            inp['nome'] = QLineEdit()
            frm.addRow("Nome:", inp['nome'])
            inp['descricao'] = QLineEdit()
            frm.addRow("Descrição:", inp['descricao'])
            lay.addLayout(frm)
        else:
            inp = {}
            
        bl = QHBoxLayout()
        bs = QPushButton("Salvar Novo")
        be = QPushButton("Editar Selecionado", objectName="editBtn")
        bd = QPushButton("Excluir Selecionado", objectName="deleteBtn")
        bl.addWidget(bs)
        bl.addWidget(be)
        bl.addWidget(bd)
        
        table = self._create_table()
        display_headers = headers[:]
        if not is_user:
            display_headers.extend(["Cadastro (Usuário)", "Alteração (Data)", "Alteração (Usuário)"])
        else:
            display_headers.extend(["Alteração (Data)", "Alteração (Usuário)"])
        table.setColumnCount(len(display_headers))
        table.setHorizontalHeaderLabels(display_headers)

        def set_busy(b):
            bs.setEnabled(not b)
            be.setEnabled(not b)
            bd.setEnabled(not b)

        def do_write(fn, *args):
            set_busy(True)
            ok, msg = fn(*args)
            set_busy(False)
            if ok:
                if not is_user and 'nome' in inp:
                    inp['nome'].clear()
                    inp['descricao'].clear()
                load()
                if on_save_callback:
                    on_save_callback()
            else:
                QMessageBox.critical(w, "Erro", str(msg))

        def save():
            if is_user:
                dlg = dialogs.UserDialog(self.manager, self.current_user, w)
                if dlg.exec_() == QDialog.Accepted:
                    data = dlg.get_data()
                    if not data['nome']: return
                    data['id'] = uuid.uuid4().hex[:8]
                    data['data_cadastro'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    do_write(self.manager.send_upsert, entity_key, data)
            else:
                if not inp['nome'].text(): return
                d = {"id": uuid.uuid4().hex[:8], "nome": inp['nome'].text(), "ativo": "true"}
                d['descricao'] = inp['descricao'].text()
                d['usuario_cadastro'] = self.current_user
                do_write(self.manager.send_upsert, entity_key, d)

        def edit():
            rows = table.selectionModel().selectedRows()
            if not rows: return
            iid = table.item(rows[0].row(), 0).data(Qt.UserRole)
            cur = None
            for it in self.manager.data.get(entity_key, []):
                if it.get('id') == iid or (is_user and it.get('email') == iid):
                    cur = it
                    break
            if cur:
                if is_user:
                    dlg = dialogs.UserDialog(self.manager, self.current_user, w, cur)
                    if dlg.exec_() == QDialog.Accepted:
                        new_data = cur.copy()
                        new_data.update(dlg.get_data())
                        do_write(self.manager.send_upsert, entity_key, new_data)
                else:
                    dlg = dialogs.GenericEditDialog(w, f"Editar {entity_key.capitalize()}", edit_fields, cur, self.current_user)
                    if dlg.exec_() == QDialog.Accepted:
                        cur.update(dlg.get_data())
                        do_write(self.manager.send_upsert, entity_key, cur)

        def delete():
            rows = table.selectionModel().selectedRows()
            if not rows: return
            iid = table.item(rows[0].row(), 0).data(Qt.UserRole)
            if QMessageBox.question(w, "Excluir", "Confirma exclusão?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                do_write(self.manager.delete_row, entity_key, iid)

        def load():
            table.setUpdatesEnabled(False)
            table.setSortingEnabled(False)
            data = self.manager.data.get(entity_key, [])
            table.setRowCount(len(data))
            for r, item in enumerate(data):
                ident = item.get('id', item.get('email'))
                ni = QTableWidgetItem(item.get('nome', ''))
                ni.setData(Qt.UserRole, ident)
                table.setItem(r, 0, ni)
                col_idx = 1
                if is_user:
                    table.setItem(r, 1, QTableWidgetItem(item.get('email', '')))
                    table.setItem(r, 2, QTableWidgetItem(item.get('perfil', '')))
                    
                    # ALTERAÇÃO: Lógica para exibir Localização e Status
                    # Coluna Localização (índice 3)
                    loc_id = item.get('localizacao_id')
                    loc_name = "-"
                    if loc_id:
                        loc_obj = next((l for l in self.manager.get_locations() if l['id'] == loc_id), None)
                        if loc_obj: loc_name = loc_obj.get('nome', '-')
                    table.setItem(r, 3, QTableWidgetItem(loc_name))
                    
                    # Coluna Status (índice 4)
                    status_val = "Ativo" if str(item.get('ativo')).lower() == 'true' else "Inativo"
                    table.setItem(r, 4, QTableWidgetItem(status_val))
                    
                    # Próxima coluna (índice 5)
                    col_idx = 5
                else:
                    table.setItem(r, 1, QTableWidgetItem(item.get('descricao', '')))
                    col_idx = 2
                if not is_user:
                    table.setItem(r, col_idx, QTableWidgetItem(str(item.get('usuario_cadastro', '-'))))
                    col_idx += 1
                table.setItem(r, col_idx, QTableWidgetItem(str(item.get('data_alteracao', '-'))))
                col_idx += 1
                table.setItem(r, col_idx, QTableWidgetItem(str(item.get('usuario_alteracao', '-'))))
            table.setSortingEnabled(True)
            table.setUpdatesEnabled(True)

        bs.clicked.connect(save)
        be.clicked.connect(edit)
        bd.clicked.connect(delete)
        load()
        if not is_user:
            lay.addStretch()
        lay.addLayout(bl)
        lay.addWidget(table)
        w.setLayout(lay)
        return w

class ReportsTab(BaseTab):
    def __init__(self, manager, user):
        super().__init__(manager)
        self.user = user
        self.current_headers = []
        self.current_data = []
        self._setup_ui()

    def _setup_ui(self):
        self.layout.addWidget(QLabel("<h2>Relatórios Gerenciais</h2>"))
        
        filter_frame = QFrame()
        filter_frame.setStyleSheet("QFrame { background-color: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 5px; padding: 10px; }")
        fl = QVBoxLayout(filter_frame)
        
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("<b>Tipo de Relatório:</b>"))
        self.combo_type = QComboBox()
        self.combo_type.addItems([
            "Produtos por Ata/Licitação", 
            "Produtos por Categoria", 
            "Produtos por Status", 
            "Estoque por Localização",
            "Movimentações por Data", 
            "Movimentações por Local"
        ])
        self.combo_type.currentIndexChanged.connect(self._update_filter_visibility)
        row1.addWidget(self.combo_type)
        row1.addStretch()
        fl.addLayout(row1)

        self.dynamic_filter_widget = QWidget()
        self.dyn_layout = QHBoxLayout(self.dynamic_filter_widget)
        self.dyn_layout.setContentsMargins(0, 0, 0, 0)
        
        self.input_ata = QLineEdit(placeholderText="Digite a Ata/Licitação")
        self.combo_cat = QComboBox()
        self.combo_loc = QComboBox()
        self.combo_status = QComboBox()
        self.combo_status.addItems(["Ativo", "Inativo"])
        
        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDate(QDate.currentDate().addMonths(-1))
        self.date_start.setEnabled(True)
        
        self.date_end = QDateEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setDate(QDate.currentDate())
        self.date_end.setEnabled(True)
        
        self.dyn_layout.addWidget(QLabel("Filtro:"))
        self.dyn_layout.addWidget(self.input_ata)
        self.dyn_layout.addWidget(self.combo_cat)
        self.dyn_layout.addWidget(self.combo_loc)
        self.dyn_layout.addWidget(self.combo_status)
        self.dyn_layout.addWidget(QLabel("De:"))
        self.dyn_layout.addWidget(self.date_start)
        self.dyn_layout.addWidget(QLabel("Até:"))
        self.dyn_layout.addWidget(self.date_end)
        self.dyn_layout.addStretch()
        
        fl.addWidget(self.dynamic_filter_widget)
        
        btn_row = QHBoxLayout()
        
        # Botão Gerar Relatório (Azul Padrão)
        btn_generate = QPushButton("Gerar Relatório")
        btn_generate.setFixedWidth(170) # Aumentado de 150 para 170
        btn_generate.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; border-radius: 5px; padding: 8px;")
        btn_generate.clicked.connect(self.generate_report)
        
        # Botão Exportar PDF (Vermelho)
        self.btn_pdf = QPushButton("Exportar para PDF")
        self.btn_pdf.setFixedWidth(170)
        self.btn_pdf.setStyleSheet("background-color: #DC2626; color: white; font-weight: bold; border-radius: 5px; padding: 8px;")
        self.btn_pdf.clicked.connect(self._export_pdf)
        
        # Botão Exportar Excel (Verde)
        self.btn_excel = QPushButton("Exportar para Excel")
        self.btn_excel.setFixedWidth(170)
        self.btn_excel.setStyleSheet("background-color: #16A34A; color: white; font-weight: bold; border-radius: 5px; padding: 8px;")
        self.btn_excel.clicked.connect(self._export_excel)
        
        btn_row.addWidget(btn_generate)
        btn_row.addWidget(self.btn_pdf)
        btn_row.addWidget(self.btn_excel)
        btn_row.addStretch()
        
        fl.addLayout(btn_row)
        
        self.layout.addWidget(filter_frame)
        self.table = self._create_table()
        self.layout.addWidget(self.table)
        
        self._load_combo_data()
        self._update_filter_visibility()

    def _load_combo_data(self):
        self.combo_cat.blockSignals(True)
        self.combo_cat.clear()
        self.combo_cat.addItem("Todas", None)
        for c in self.manager.get_categories():
            self.combo_cat.addItem(c['nome'], c['id'])
        self.combo_cat.blockSignals(False)
        
        self.combo_loc.blockSignals(True)
        self.combo_loc.clear()
        self.combo_loc.addItem("Todas", None)
        for l in self.manager.get_locations():
            self.combo_loc.addItem(l['nome'], l['id'])
        self.combo_loc.blockSignals(False)

    def _update_filter_visibility(self):
        # Esconde todos os filtros dinâmicos primeiro
        self.input_ata.hide()
        self.combo_cat.hide()
        self.combo_loc.hide()
        self.combo_status.hide()
        
        # Mostra os campos de data (sempre visíveis)
        self.date_start.show()
        self.date_end.show()
        
        idx = self.combo_type.currentIndex()
        
        # Exibe o filtro específico de cada relatório
        if idx == 0: 
            self.input_ata.show() # Produtos por Ata
        elif idx == 1: 
            self.combo_cat.show() # Produtos por Categoria
        elif idx == 2: 
            self.combo_status.show() # Produtos por Status
        elif idx == 3: 
            self.combo_loc.show() # Estoque por Localização
        elif idx == 5: 
            self.combo_loc.show() # Movimentações por Local (ADICIONADO)

    def generate_report(self):
        idx = self.combo_type.currentIndex()
        if idx == 0: self._report_by_ata()
        elif idx == 1: self._report_by_category()
        elif idx == 2: self._report_by_status()
        elif idx == 3: self._report_stock_by_location()
        elif idx == 4: self._report_movements_by_date()
        elif idx == 5: self._report_movements_by_location()

    def _populate_table(self, data, headers):
        self.current_headers = headers
        self.current_data = data
        
        self.table.setUpdatesEnabled(False)
        
        # --- CORREÇÃO: Desativar ordenação antes de preencher ---
        self.table.setSortingEnabled(False)
        
        self.table.clear()
        self.table.setRowCount(len(data))
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        
        for r, row_data in enumerate(data):
            for c, val in enumerate(row_data):
                self.table.setItem(r, c, QTableWidgetItem(str(val)))
        
        # --- CORREÇÃO: Reativar ordenação após preencher ---
        self.table.setSortingEnabled(True)
        
        self.table.setUpdatesEnabled(True)
        self.table.resizeColumnsToContents()

    def _get_date_filter(self):
        return self.date_start.date().toPyDate(), self.date_end.date().toPyDate()

    def _filter_by_date(self, date_str, start, end):
        if not date_str: return False
        try:
            dt = datetime.strptime(date_str.split('.')[0], "%Y-%m-%d %H:%M:%S").date()
        except:
            try:
                dt = datetime.strptime(date_str, "%d/%m/%Y %H:%M:%S").date()
            except:
                try:
                    dt = datetime.strptime(date_str, "%d/%m/%Y").date()
                except:
                    return False
        return start <= dt <= end

    def _report_by_ata(self):
        text = self.input_ata.text().lower()
        d_start, d_end = self._get_date_filter()
        products = self.manager.get_products()
        result = []
        for p in products:
            if text and text not in str(p.get('ata_licitacao', '')).lower():
                continue
            if not self._filter_by_date(p.get('data_cadastro'), d_start, d_end):
                continue
            
            val = p.get('valor', 0)
            try: val_fmt = f"{float(val):.2f}".replace(".", ",")
            except: val_fmt = str(val)
            result.append([
                p.get('nome', '-'),
                p.get('ata_licitacao', '-'),
                p.get('nome_categoria', '-'),
                val_fmt,
                "Ativo" if str(p.get('ativo')).lower() == 'true' else "Inativo"
            ])
        self._populate_table(result, ["Produto", "Ata/Licitação", "Categoria", "Valor", "Status"])

    def _report_by_category(self):
        cat_id = self.combo_cat.currentData()
        d_start, d_end = self._get_date_filter()
        products = self.manager.get_products()
        result = []
        for p in products:
            if cat_id and p.get('categoria') != cat_id:
                continue
            if not self._filter_by_date(p.get('data_cadastro'), d_start, d_end):
                continue
            
            val = p.get('valor', 0)
            try: val_fmt = f"{float(val):.2f}".replace(".", ",")
            except: val_fmt = str(val)
            result.append([
                p.get('nome', '-'),
                p.get('nome_categoria', '-'),
                p.get('unidade_medida', '-'),
                val_fmt,
                p.get('estoque_minimo', 0)
            ])
        self._populate_table(result, ["Produto", "Categoria", "Unidade", "Valor", "Est. Mínimo"])

    def _report_by_status(self):
        status_sel = self.combo_status.currentText()
        d_start, d_end = self._get_date_filter()
        products = self.manager.get_products()
        result = []
        for p in products:
            p_status = "Ativo" if str(p.get('ativo')).lower() == 'true' else "Inativo"
            if p_status != status_sel:
                continue
            if not self._filter_by_date(p.get('data_cadastro'), d_start, d_end):
                continue
            
            val = p.get('valor', 0)
            try: val_fmt = f"{float(val):.2f}".replace(".", ",")
            except: val_fmt = str(val)
            result.append([
                p.get('nome', '-'),
                p.get('nome_categoria', '-'),
                val_fmt,
                p_status
            ])
        self._populate_table(result, ["Produto", "Categoria", "Valor", "Status"])

    def _report_stock_by_location(self):
        loc_id = self.combo_loc.currentData()
        d_start, d_end = self._get_date_filter()
        stock = self.manager.get_stock()
        result = []
        for s in stock:
            if loc_id and s.get('localizacao_id') != loc_id:
                continue
            result.append([
                s.get('nome_produto', '-'),
                s.get('nome_localizacao', '-'),
                s.get('quantidade', 0)
            ])
        self._populate_table(result, ["Produto", "Localização", "Quantidade"])

    def _report_movements_by_date(self):
        d_start, d_end = self._get_date_filter()
        moves = self.manager.get_movements()
        result = []
        
        for m in moves:
            ds = m.get('data_hora', '')
            if self._filter_by_date(ds, d_start, d_end):
                result.append([
                    ds,
                    m.get('tipo', '-'),
                    m.get('nome_produto', '-'),
                    m.get('nome_origem', '-'),
                    m.get('nome_destino', '-'),
                    m.get('quantidade', 0),
                    m.get('usuario', '-')
                ])
        self._populate_table(result, ["Data/Hora", "Tipo", "Produto", "Origem", "Destino", "Qtd", "Usuário"])

    def _report_movements_by_location(self):
        loc_id = self.combo_loc.currentData()
        d_start, d_end = self._get_date_filter()
        moves = self.manager.get_movements()
        result = []
        
        for m in moves:
            if loc_id:
                if m.get('localizacao_origem_id') != loc_id and m.get('localizacao_destino_id') != loc_id:
                    continue
            
            ds = m.get('data_hora', '')
            if self._filter_by_date(ds, d_start, d_end):
                result.append([
                    ds,
                    m.get('tipo', '-'),
                    m.get('nome_produto', '-'),
                    m.get('nome_origem', '-'),
                    m.get('nome_destino', '-'),
                    m.get('quantidade', 0),
                    m.get('usuario', '-')
                ])
        self._populate_table(result, ["Data/Hora", "Tipo", "Produto", "Origem", "Destino", "Qtd", "Usuário"])

    def _export_excel(self):
        if not HAS_PANDAS:
            QMessageBox.warning(self, "Erro", "Biblioteca 'pandas' não instalada.\nInstale com: pip install pandas openpyxl")
            return
            
        if not self.current_data:
            QMessageBox.warning(self, "Aviso", "Gere um relatório primeiro para exportar.")
            return

        # --- ALTERAÇÃO: Define o nome padrão baseado no tipo de relatório ---
        nome_relatorio = self.combo_type.currentText()
        default_filename = f"{nome_relatorio}.xlsx"
        
        filename, _ = QFileDialog.getSaveFileName(self, "Salvar Excel", default_filename, "Excel Files (*.xlsx)")
        
        if filename:
            try:
                df = pd.DataFrame(self.current_data, columns=self.current_headers)
                df.to_excel(filename, index=False, engine='openpyxl')
                QMessageBox.information(self, "Sucesso", "Relatório exportado para Excel com sucesso!")
            except Exception as e:
                show_error_box(self, "Erro ao Exportar", str(e))

    def _export_pdf(self):
        if not HAS_REPORTLAB:
            QMessageBox.warning(self, "Erro", "Biblioteca 'reportlab' não instalada.\nInstale com: pip install reportlab")
            return
            
        if not self.current_data:
            QMessageBox.warning(self, "Aviso", "Gere um relatório primeiro para exportar.")
            return

        # Define o nome padrão baseado no tipo de relatório selecionado
        nome_relatorio = self.combo_type.currentText()
        default_filename = f"{nome_relatorio}.pdf"
        
        filename, _ = QFileDialog.getSaveFileName(self, "Salvar PDF", default_filename, "PDF Files (*.pdf)")
        if not filename: return

        try:
            doc = SimpleDocTemplate(filename, pagesize=A4,
                                    rightMargin=1*cm, leftMargin=1*cm,
                                    topMargin=3*cm, bottomMargin=2.5*cm)

            elements = []
            
            styles = getSampleStyleSheet()
            
            header_img = resource_path("cab.png")
            bg_img = resource_path("fundo.png")
            footer_img = resource_path("rod.png")

            def add_background(canvas, doc):
                canvas.saveState()
                width, height = A4
                
                if os.path.exists(bg_img):
                    canvas.drawImage(bg_img, 0, 0, width=width, height=height, mask='auto')
                
                if os.path.exists(header_img):
                    img_w = width - 2*cm 
                    canvas.drawImage(header_img, 1*cm, height - 2.5*cm, width=img_w, height=2*cm, mask='auto', preserveAspectRatio=True)
                
                if os.path.exists(footer_img):
                    x_pos = 0.0*cm
                    canvas.drawImage(footer_img, x_pos, 0.5*cm, width=18*cm, height=1.5*cm, mask='auto', preserveAspectRatio=True)
                
                canvas.restoreState()

            title = self.combo_type.currentText()
            elements.append(Spacer(1, 1*cm))
            elements.append(Paragraph(f"<b>{title}</b>", styles['Title']))
            elements.append(Spacer(1, 0.5*cm))

            available_width = A4[0] - 2*cm
            
            fixed_widths = {
                "Qtd": 1.5*cm,
                "Quantidade": 1.5*cm,
                "Status": 2.0*cm,
                "Tipo": 2.0*cm,
                "Unidade": 1.5*cm,
                "Valor": 2.5*cm,
                "Est. Mínimo": 2.0*cm,
                "Data/Hora": 3.5*cm,
                "Usuário": 3.0*cm
            }
            
            col_widths = []
            flexible_cols_count = 0
            used_width = 0
            
            for h in self.current_headers:
                if h in fixed_widths:
                    col_widths.append(fixed_widths[h])
                    used_width += fixed_widths[h]
                else:
                    col_widths.append(None)
                    flexible_cols_count += 1
            
            remaining_width = available_width - used_width
            
            if flexible_cols_count > 0 and remaining_width > 0:
                flexible_width = remaining_width / flexible_cols_count
                final_widths = []
                for w in col_widths:
                    if w is None:
                        final_widths.append(flexible_width)
                    else:
                        final_widths.append(w)
                col_widths = final_widths
            else:
                col_widths = [available_width / len(self.current_headers)] * len(self.current_headers)

            table_data = [self.current_headers] + self.current_data
            t = Table(table_data, colWidths=col_widths, repeatRows=1)
            
            idx = self.combo_type.currentIndex()
            is_movement_report = idx in [4, 5]

            style_list = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563EB')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]

            if is_movement_report:
                style_list.append(('FONTSIZE', (0, 0), (-1, 0), 7))
                style_list.append(('FONTSIZE', (0, 1), (-1, -1), 6))
            
            t.setStyle(TableStyle(style_list))
            
            elements.append(t)
            
            doc.build(elements, onFirstPage=add_background, onLaterPages=add_background)
            QMessageBox.information(self, "Sucesso", "Relatório exportado para PDF com sucesso!")
            
        except Exception as e:
            show_error_box(self, "Erro ao Exportar", str(e))

    def load_table(self):
        self._load_combo_data()
        self.table.setRowCount(0)