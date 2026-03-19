from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, 
                             QComboBox, QDateEdit, QPushButton, QDialogButtonBox, 
                             QMessageBox, QHBoxLayout, QLabel, QScrollArea, QFrame, 
                             QApplication, QTableWidget, QTableWidgetItem, QHeaderView,
                             QAbstractItemView, QCheckBox, QWidget, QSpinBox, QTextBrowser)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor
import uuid
from datetime import datetime

import sys
import os
import config
import updater

# Funções auxiliares
def format_currency(value):
    try: return f"{float(value):.2f}".replace(".", ",")
    except: return str(value)

def parse_float(text):
    if not text: return 0.0
    s = str(text).strip().replace('R$', '').replace(' ', '')
    if ',' in s: s = s.replace('.', '').replace(',', '.')
    else:
        if '.' in s:
            parts = s.split('.')
            if len(parts) == 2 and len(parts[1]) > 2: s = s.replace('.', '')
    try: return float(s)
    except ValueError: return 0.0

def parse_int(text):
    if not text: return 0
    try: return int(parse_float(text))
    except ValueError: return 0

class GenericEditDialog(QDialog):
    def __init__(self, parent=None, title="Editar", fields=None, data=None, current_user="Sistema"):
        super().__init__(parent)
        self.current_user = current_user
        self.setWindowTitle(title)
        self.data = data if data else {}
        self.inputs = {}
        self.setMinimumWidth(300)
        layout = QVBoxLayout()
        form = QFormLayout()
        if not fields: fields = [("Nome", "nome"), ("Descrição", "descricao")]
        for label, key in fields:
            if key == 'perfil':
                inp = QComboBox(); inp.addItems(["admin", "gerência", "usuário"])
                idx = inp.findText(str(self.data.get(key, '')))
                if idx >= 0: inp.setCurrentIndex(idx)
            else:
                inp = QLineEdit(); inp.setText(str(self.data.get(key, '')))
            self.inputs[key] = inp
            form.addRow(label + ":", inp)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        layout.addLayout(form); layout.addWidget(buttons)
        self.setLayout(layout)

    def get_data(self):
        result = {}
        for key, inp in self.inputs.items():
            result[key] = inp.currentText() if isinstance(inp, QComboBox) else inp.text()
        if not self.data.get('id'): result['usuario_cadastro'] = self.current_user
        else: result['usuario_alteracao'] = self.current_user
        return result

class ProductDialog(QDialog):
    def __init__(self, manager, current_user="Sistema", parent=None, product_data=None):
        super().__init__(parent)
        self.manager = manager; self.current_user = current_user; self.product_data = product_data
        self.setWindowTitle("Produto" if not product_data else "Editar Produto")
        self.setMinimumWidth(450)
        self.setup_ui()
        if product_data: self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(); form = QFormLayout()
        self.input_nome = QLineEdit()
        self.combo_cat = QComboBox(); self.load_categories()
        self.combo_un = QComboBox(); self.combo_un.addItems(["UN", "CX", "PC", "KG", "L", "MT"])
        self.input_valor = QLineEdit(placeholderText="Ex: 1500,50")
        self.input_ata = QLineEdit(placeholderText="Nº do Ata/Licitação")
        self.combo_status = QComboBox(); self.combo_status.addItem("Ativo", "true"); self.combo_status.addItem("Inativo", "false")
        self.layout_validade = QHBoxLayout()
        self.combo_val_tipo = QComboBox(); self.combo_val_tipo.addItems(["INDEFINIDA", "DEFINIDA"])
        self.date_validade = QDateEdit(); self.date_validade.setCalendarPopup(True); self.date_validade.setDate(QDate.currentDate()); self.date_validade.setDisabled(True)
        self.combo_val_tipo.currentTextChanged.connect(lambda t: self.date_validade.setEnabled(t == "DEFINIDA"))
        self.layout_validade.addWidget(self.combo_val_tipo); self.layout_validade.addWidget(self.date_validade)
        self.input_min = QLineEdit(placeholderText="Ex: 10")
        
        form.addRow("Nome:", self.input_nome); form.addRow("Categoria:", self.combo_cat)
        form.addRow("Unidade:", self.combo_un); form.addRow("Valor (R$):", self.input_valor)
        form.addRow("Ata/Licitação:", self.input_ata); form.addRow("Status:", self.combo_status)
        form.addRow("Validade:", self.layout_validade); form.addRow("Estoque Mínimo:", self.input_min)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_data); buttons.rejected.connect(self.reject)
        layout.addLayout(form); layout.addWidget(buttons); self.setLayout(layout)

    def load_categories(self):
        for c in self.manager.get_categories(): self.combo_cat.addItem(c['nome'], c['id'])

    def load_data(self):
        self.input_nome.setText(self.product_data.get('nome', ''))
        idx = self.combo_cat.findData(self.product_data.get('categoria'))
        if idx >= 0: self.combo_cat.setCurrentIndex(idx)
        idx_u = self.combo_un.findText(self.product_data.get('unidade_medida', ''))
        if idx_u >= 0: self.combo_un.setCurrentIndex(idx_u)
        try: self.input_valor.setText(f"{float(self.product_data.get('valor', 0)):.2f}".replace(".", ","))
        except: pass
        self.input_ata.setText(str(self.product_data.get('ata_licitacao', '')))
        idx_s = self.combo_status.findData(self.product_data.get('ativo', 'true'))
        if idx_s >= 0: self.combo_status.setCurrentIndex(idx_s)
        val_tipo = self.product_data.get('validade_tipo', 'INDEFINIDA')
        self.combo_val_tipo.setCurrentText(val_tipo)
        if val_tipo == 'DEFINIDA' and self.product_data.get('validade'):
            try:
                dt = datetime.strptime(self.product_data['validade'], "%d/%m/%Y")
                self.date_validade.setDate(QDate(dt.year, dt.month, dt.day))
            except: pass
        self.input_min.setText(str(self.product_data.get('estoque_minimo', 0)))

    def get_data(self):
        val_tipo = self.combo_val_tipo.currentText()
        val_data = self.date_validade.date().toString("dd/MM/yyyy") if val_tipo == "DEFINIDA" else "*"
        data = {
            "nome": self.input_nome.text(), "categoria": self.combo_cat.currentData(),
            "nome_categoria": self.combo_cat.currentText(), "unidade_medida": self.combo_un.currentText(),
            "valor": parse_float(self.input_valor.text()), "ata_licitacao": self.input_ata.text(),
            "ativo": self.combo_status.currentData(), "validade_tipo": val_tipo, "validade": val_data,
            "estoque_minimo": parse_int(self.input_min.text())
        }
        if self.product_data:
            data['id'] = self.product_data['id']; data['data_cadastro'] = self.product_data.get('data_cadastro')
            data['usuario_alteracao'] = self.current_user
        else:
            data['id'] = uuid.uuid4().hex[:8]; data['data_cadastro'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            data['usuario_cadastro'] = self.current_user
        return data

    def accept_data(self):
        if not self.input_nome.text(): QMessageBox.warning(self, "Erro", "O nome é obrigatório."); return
        self.accept()

class MovementDialog(QDialog):
    def __init__(self, manager, current_user="Sistema", parent=None, mov_data=None, user_obj=None):
        super().__init__(parent)
        self.manager = manager
        self.current_user = current_user
        self.mov_data = mov_data 
        self.user_obj = user_obj 
        self.selected_items = []
        
        if mov_data:
            self.setWindowTitle("Editar Movimentação Única")
            self.setMinimumWidth(450)
        else:
            self.setWindowTitle("Nova Movimentação em Lote")
            self.setMinimumSize(900, 600)
            
        self.setup_ui()
        if mov_data: self.load_single_data()

    def setup_ui(self):
        main_layout = QVBoxLayout()
        
        # 1. CABEÇALHO
        header_layout = QFormLayout()
        self.combo_tipo = QComboBox()
        self.combo_tipo.addItems(["ENTRADA", "SAÍDA", "TRANSFERÊNCIA"])
        self.combo_tipo.currentTextChanged.connect(self.update_visibility)
        
        self.combo_origem = QComboBox()
        self.combo_destino = QComboBox()
        for l in self.manager.get_locations():
            self.combo_origem.addItem(l['nome'], l['id'])
            self.combo_destino.addItem(l['nome'], l['id'])
            
        self.lbl_origem = QLabel("Local de Origem:")
        self.lbl_destino = QLabel("Local de Destino:")
        
        header_layout.addRow("Tipo de Movimentação:", self.combo_tipo)
        header_layout.addRow(self.lbl_origem, self.combo_origem)
        header_layout.addRow(self.lbl_destino, self.combo_destino)
        main_layout.addLayout(header_layout)
        
        # LÓGICA DE RESTRIÇÃO DE USUÁRIO
        # CORREÇÃO: Verifica se o perfil é 'usuário' (com acento)
        is_restricted = self.user_obj and self.user_obj.get('perfil') == 'usuário'
        
        if is_restricted:
            user_loc_id = self.user_obj.get('localizacao_id')
            idx_d = self.combo_destino.findData(user_loc_id)
            if idx_d >= 0:
                self.combo_destino.setCurrentIndex(idx_d)
                self.combo_destino.setEnabled(False)
            
            idx_o = self.combo_origem.findData(user_loc_id)
            if idx_o >= 0:
                self.combo_origem.setCurrentIndex(idx_o)
                self.combo_origem.setEnabled(False)
        
        # 2. ÁREA DE FILTROS
        if not self.mov_data:
            filter_group = QFrame()
            filter_group.setStyleSheet("QFrame { background-color: #F3F4F6; border-radius: 5px; padding: 5px; }")
            fl = QHBoxLayout()
            
            fl.addWidget(QLabel("Filtrar Categoria:"))
            self.combo_filter_cat = QComboBox()
            self.combo_filter_cat.addItem("Todas", None)
            for c in self.manager.get_categories(): self.combo_filter_cat.addItem(c['nome'], c['id'])
            fl.addWidget(self.combo_filter_cat)
            
            fl.addWidget(QLabel("Ata/Licitação:"))
            self.input_filter_ata = QLineEdit(placeholderText="Digite para filtrar...")
            fl.addWidget(self.input_filter_ata)
            
            btn_filter = QPushButton("Aplicar Filtros")
            btn_filter.clicked.connect(self.apply_filters)
            fl.addWidget(btn_filter)
            
            filter_group.setLayout(fl)
            main_layout.addWidget(filter_group)
            
        # 3. TABELA DE PRODUTOS
        if not self.mov_data:
            self.table_products = QTableWidget()
            self.table_products.setColumnCount(5)
            self.table_products.setHorizontalHeaderLabels(["Produto", "Categoria", "Ata/Licitação", "Sel.", "Quantidade"])
            self.table_products.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
            self.table_products.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self.table_products.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.table_products.verticalHeader().setDefaultSectionSize(40)
            
            self.load_product_table()
            main_layout.addWidget(self.table_products)
        else:
            edit_form = QFormLayout()
            self.lbl_prod_name = QLabel(str(self.mov_data.get('nome_produto', '-')))
            self.lbl_prod_name.setStyleSheet("font-weight: bold;")
            self.input_qtd_single = QLineEdit(placeholderText="Quantidade")
            edit_form.addRow("Produto:", self.lbl_prod_name)
            edit_form.addRow("Quantidade:", self.input_qtd_single)
            main_layout.addLayout(edit_form)
            
        # 4. MOTIVO E BOTÕES
        footer_layout = QVBoxLayout()
        footer_layout.addWidget(QLabel("Motivo:"))
        self.input_motivo = QLineEdit(placeholderText="Descrição ou motivo da movimentação")
        footer_layout.addWidget(self.input_motivo)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_data)
        buttons.rejected.connect(self.reject)
        footer_layout.addWidget(buttons)
        
        main_layout.addLayout(footer_layout)
        self.setLayout(main_layout)
        self.update_visibility("ENTRADA")

    def load_product_table(self):
        products = self.manager.get_products()
        self.table_products.setRowCount(len(products))
        
        for r, p in enumerate(products):
            nome_item = QTableWidgetItem(p.get('nome', ''))
            nome_item.setData(Qt.UserRole, p.get('id'))
            
            self.table_products.setItem(r, 0, nome_item)
            self.table_products.setItem(r, 1, QTableWidgetItem(p.get('nome_categoria', '-')))
            self.table_products.setItem(r, 2, QTableWidgetItem(str(p.get('ata_licitacao', '-'))))
            
            chk_widget = QWidget()
            chk_layout = QHBoxLayout(chk_widget)
            chk = QCheckBox()
            chk_layout.setAlignment(Qt.AlignCenter)
            chk_layout.setContentsMargins(0,0,0,0)
            chk_layout.addWidget(chk)
            self.table_products.setCellWidget(r, 3, chk_widget)
            
            qtd_widget = QWidget()
            qtd_layout = QHBoxLayout(qtd_widget)
            qtd_input = QLineEdit(placeholderText="0")
            qtd_input.setAlignment(Qt.AlignCenter)
            qtd_layout.addWidget(qtd_input)
            qtd_layout.setContentsMargins(4, 0, 4, 0)
            self.table_products.setCellWidget(r, 4, qtd_widget)

    def apply_filters(self):
        cat_id = self.combo_filter_cat.currentData()
        ata_text = self.input_filter_ata.text().lower()
        
        for r in range(self.table_products.rowCount()):
            cat_name = self.table_products.item(r, 1).text()
            ata_name = self.table_products.item(r, 2).text()
            
            match_cat = (cat_id is None)
            if cat_id:
                cat_obj = next((c for c in self.manager.get_categories() if c['id'] == cat_id), None)
                if cat_obj and cat_name == cat_obj['nome']: match_cat = True
                else: match_cat = False
                
            match_ata = (ata_text == "") or (ata_text in ata_name.lower())
            
            self.table_products.setRowHidden(r, not (match_cat and match_ata))

    def update_visibility(self, tipo):
        is_saida = (tipo == "SAÍDA")
        is_trans = (tipo == "TRANSFERÊNCIA")
        
        self.lbl_origem.setVisible(is_saida or is_trans)
        self.combo_origem.setVisible(is_saida or is_trans)
        self.lbl_destino.setVisible(not is_saida)
        self.combo_destino.setVisible(not is_saida)
        
        if tipo == "ENTRADA": self.lbl_destino.setText("Local de Destino:")
        elif tipo == "SAÍDA": self.lbl_origem.setText("Local de Origem:")
        elif tipo == "TRANSFERÊNCIA":
            self.lbl_origem.setText("Local de Origem:")
            self.lbl_destino.setText("Local de Destino:")

    def load_single_data(self):
        self.combo_tipo.setCurrentText(self.mov_data.get('tipo', 'ENTRADA'))
        self.input_motivo.setText(self.mov_data.get('motivo', ''))
        self.input_qtd_single.setText(str(self.mov_data.get('quantidade', 0)))
        
        if self.combo_origem.isEnabled():
            idx_o = self.combo_origem.findData(self.mov_data.get('localizacao_origem_id'))
            if idx_o >= 0: self.combo_origem.setCurrentIndex(idx_o)
        
        if self.combo_destino.isEnabled():
            idx_d = self.combo_destino.findData(self.mov_data.get('localizacao_destino_id'))
            if idx_d >= 0: self.combo_destino.setCurrentIndex(idx_d)
        
        self.update_visibility(self.combo_tipo.currentText())

    def accept_data(self):
        tipo = self.combo_tipo.currentText()
        motivo = self.input_motivo.text()
        
        common = {
            "tipo": tipo, "motivo": motivo, "usuario": self.current_user,
            "localizacao_origem_id": None, "nome_origem": None,
            "localizacao_destino_id": None, "nome_destino": None
        }
        
        if tipo in ["SAÍDA", "TRANSFERÊNCIA"]:
            common['localizacao_origem_id'] = self.combo_origem.currentData()
            common['nome_origem'] = self.combo_origem.currentText()
        if tipo in ["ENTRADA", "TRANSFERÊNCIA"]:
            common['localizacao_destino_id'] = self.combo_destino.currentData()
            common['nome_destino'] = self.combo_destino.currentText()
            
        if self.mov_data:
            qtd = parse_float(self.input_qtd_single.text())
            if qtd <= 0:
                QMessageBox.warning(self, "Erro", "Quantidade inválida."); return
            
            self.data = {
                **common,
                'produto_id': self.mov_data['produto_id'],
                'nome_produto': self.mov_data['nome_produto'],
                'quantidade': qtd,
                'id': self.mov_data['id'],
                'data_hora': self.mov_data['data_hora'],
                'is_batch': False
            }
            self.accept()
            return

        items = []
        for r in range(self.table_products.rowCount()):
            if self.table_products.isRowHidden(r): continue
            
            chk_widget = self.table_products.cellWidget(r, 3)
            qtd_widget = self.table_products.cellWidget(r, 4)
            
            chk = chk_widget.findChild(QCheckBox)
            qtd_edit = qtd_widget.findChild(QLineEdit)
            
            if chk and chk.isChecked():
                qtd = parse_float(qtd_edit.text())
                if qtd > 0:
                    pid = self.table_products.item(r, 0).data(Qt.UserRole)
                    pnome = self.table_products.item(r, 0).text()
                    items.append({
                        'produto_id': pid,
                        'nome_produto': pnome,
                        'quantidade': qtd
                    })
        
        if not items:
            QMessageBox.warning(self, "Aviso", "Selecione ao menos um produto e defina a quantidade.")
            return
            
        self.data = {**common, 'items': items, 'is_batch': True}
        self.accept()

class UserDialog(QDialog):
    def __init__(self, manager, current_user="Sistema", parent=None, user_data=None):
        super().__init__(parent)
        self.manager = manager; self.current_user = current_user; self.user_data = user_data
        self.setWindowTitle("Novo Usuário" if not user_data else "Editar Usuário")
        self.setMinimumWidth(400)
        self.setup_ui()
        if user_data: self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(); form = QFormLayout()
        self.input_nome = QLineEdit()
        self.input_email = QLineEdit()
        self.input_senha = QLineEdit(); self.input_senha.setEchoMode(QLineEdit.Password)
        self.combo_perfil = QComboBox(); self.combo_perfil.addItems(["admin", "gerência", "usuário"])
        self.combo_loc = QComboBox()
        for l in self.manager.get_locations(): self.combo_loc.addItem(l['nome'], l['id'])
        self.combo_ativo = QComboBox(); self.combo_ativo.addItem("Ativo", "true"); self.combo_ativo.addItem("Inativo", "false")
        form.addRow("Nome:", self.input_nome); form.addRow("Email:", self.input_email); form.addRow("Senha:", self.input_senha)
        form.addRow("Perfil:", self.combo_perfil); form.addRow("Localização:", self.combo_loc); form.addRow("Status:", self.combo_ativo)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addLayout(form); layout.addWidget(buttons); self.setLayout(layout)

    def load_data(self):
        self.input_nome.setText(self.user_data.get('nome', '')); self.input_email.setText(self.user_data.get('email', '')); self.input_senha.setText(self.user_data.get('senha', ''))
        idx = self.combo_perfil.findText(self.user_data.get('perfil', '')); 
        if idx >= 0: self.combo_perfil.setCurrentIndex(idx)
        idx_loc = self.combo_loc.findData(self.user_data.get('localizacao_id')); 
        if idx_loc >= 0: self.combo_loc.setCurrentIndex(idx_loc)
        idx_ativo = self.combo_ativo.findData(self.user_data.get('ativo', 'true')); 
        if idx_ativo >= 0: self.combo_ativo.setCurrentIndex(idx_ativo)

    def get_data(self):
        data = {
            "nome": self.input_nome.text(), "email": self.input_email.text(), "senha": self.input_senha.text(),
            "perfil": self.combo_perfil.currentText(), "localizacao_id": self.combo_loc.currentData(),
            "ativo": self.combo_ativo.currentData()
        }
        if self.user_data: data['usuario_alteracao'] = self.current_user
        else: data['usuario_cadastro'] = self.current_user
        return data

    def validate_and_accept(self):
        nome = self.input_nome.text().strip()
        email = self.input_email.text().strip()
        senha = self.input_senha.text().strip()
        perfil = self.combo_perfil.currentText()
        loc_id = self.combo_loc.currentData()

        if not nome or not email or not senha:
            QMessageBox.warning(self, "Validação", "Nome, Email e Senha são obrigatórios.")
            return
        
        if perfil == 'usuário' and not loc_id:
            QMessageBox.warning(self, "Validação", "O perfil 'usuário' requer uma Localização definida.")
            return
        
        self.accept()

# Substitua a classe AboutDialog existente em dialogs.py por esta:

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sobre o Sistema")
        self.setMinimumSize(500, 450)
        
        layout = QVBoxLayout()
        
        # Título
        title = QLabel("<h2>Controle de Estoque</h2><h3>Vigilância Socioassistencial</h3>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # --- Área de Texto Principal ---
        # Usando QTextBrowser para permitir rolagem e formatação HTML
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)
        self.text_browser.setFrameShape(QFrame.NoFrame) # Remove borda para ficar mais limpo
        
        # Conteúdo padrão (Sobre)
        self.about_content = f"""
            <b>Versão:</b> {config.VERSAO_ATUAL}<br>
            <b>Data da Versão:</b> 03/2026<br><br>
            <b>Descrição:</b><br>
            Sistema desenvolvido para gestão do estoque.<br><br>
            <b>Órgão Responsável:</b><br>
            Secretaria Municipal de Desenvolvimento e Assistência Social (SEDEAS)<br><br>
            <b>Chefe da Vigilância Socioassistencial:</b><br>
            Rafael Morcillo<br><br>
            <b>Desenvolvimento e Programação:</b><br>
            Nelson Carvalho<br>
            nelson77carvalho@gmail.com<br><br>
            <b>Colaboradores / Agradecimentos:</b><br>
            À toda equipe SEDEAS<br><br>
            <b>Ano:</b> 2026
        """
        self.text_browser.setHtml(self.about_content)
        layout.addWidget(self.text_browser)
        
        # --- Botões ---
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok)
        btn_box.accepted.connect(self.accept)
        
        # Layout horizontal para os botões de ação
        action_layout = QHBoxLayout()
        
        self.btn_notes = QPushButton("Notas de Lançamento")
        self.btn_notes.clicked.connect(self.toggle_notes)
        
        self.btn_update = QPushButton("Verificar Atualizações")
        self.btn_update.clicked.connect(self.check_update)
        
        # Adiciona botões ao layout da esquerda para direita
        action_layout.addWidget(self.btn_notes)
        action_layout.addWidget(self.btn_update)
        action_layout.addStretch() # Empurra o OK para a direita
        action_layout.addWidget(btn_box)
        
        layout.addLayout(action_layout)
        self.setLayout(layout)
        
        # Estado inicial (mostrando 'Sobre')
        self.showing_notes = False

    def toggle_notes(self):
        """Alterna entre mostrar 'Sobre' e 'Notas de Lançamento'."""
        if not self.showing_notes:
            # Buscar notas
            self.text_browser.setHtml("<i>Carregando notas do GitHub...</i>")
            version, notes = updater.get_latest_release_info()
            
            if version:
                # Formata o texto das notas
                formatted_notes = notes.replace('\n', '<br>')
                html_content = f"""
                    <h3>Versão {version}</h3>
                    <hr>
                    <div style='font-family: sans-serif; font-size: 12px;'>
                        {formatted_notes}
                    </div>
                """
                self.text_browser.setHtml(html_content)
                self.btn_notes.setText("Voltar ao Sobre")
            else:
                self.text_browser.setHtml(f"<font color='red'>Erro ao carregar notas:<br>{notes}</font>")
                self.btn_notes.setText("Tentar Novamente")
            
            self.showing_notes = True
        else:
            # Voltar para 'Sobre'
            self.text_browser.setHtml(self.about_content)
            self.btn_notes.setText("Notas de Lançamento")
            self.showing_notes = False

    def check_update(self):
        # Mantenha sua função check_update existente aqui exatamente como está
        import updater
        import time
        
        self.btn_update.setText("Verificando...")
        self.btn_update.setEnabled(False)
        try:
            has_update, version_or_msg, url = updater.check_for_updates()
            
            if has_update:
                msg = (f"<b>Nova versão encontrada!</b><br><br>"
                       f"<b>Repositório:</b> {version_or_msg}<br>"
                       f"<b>Local:</b> {config.VERSAO_ATUAL}<br><br>"
                       f"Deseja baixar e instalar?")
                       
                reply = QMessageBox.question(self, "Atualização Disponível", msg, QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    current_exe_path = updater.get_real_exe_path()
                    current_dir = os.path.dirname(current_exe_path)
                    new_exe = os.path.join(current_dir, "ControleEstoque_update.exe")
                    QMessageBox.information(self, "Download", "Baixando atualização...")
                    success, msg = updater.download_update(url, new_exe)
                    if success:
                        update_success, update_msg = updater.apply_update(new_exe, version_or_msg)
                        if update_success:
                            QMessageBox.information(self, "Sucesso", "O programa será fechado para atualizar.")
                            time.sleep(2)
                            sys.exit(0)
                        else: 
                            QMessageBox.critical(self, "Erro na Atualização", f"Falha ao iniciar script: {update_msg}")
                    else: 
                        QMessageBox.critical(self, "Erro no Download", str(msg))
            else:
                if version_or_msg: 
                    QMessageBox.critical(self, "Erro", str(version_or_msg))
                else:
                    msg = (f"Você já possui a versão mais recente.<br><br>"
                           f"<b>Versão Local:</b> {config.VERSAO_ATUAL}<br>")
                    QMessageBox.information(self, "Atualizado", msg)
                    
        except Exception as e: 
            QMessageBox.critical(self, "Erro Crítico", f"Erro inesperado: {e}")
        finally: 
            self.btn_update.setText("Verificar Atualizações")
            self.btn_update.setEnabled(True)