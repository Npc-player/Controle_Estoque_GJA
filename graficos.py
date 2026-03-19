import matplotlib
matplotlib.use('Qt5Agg') 
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QSizePolicy
from PyQt5.QtCore import Qt

class ChartCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        # Fundo transparente
        self.fig.patch.set_alpha(0.0)
        self.axes = self.fig.add_subplot(111)
        super(ChartCanvas, self).__init__(self.fig)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.updateGeometry()

class ChartsWidget(QWidget):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # --- Filtros ---
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("<b>Filtrar Por Produto:</b>"))
        
        self.combo_product = QComboBox()
        self.combo_product.addItem("Todos os Produtos", None)
        self.combo_product.currentIndexChanged.connect(self.update_charts)
        
        filter_layout.addWidget(self.combo_product)
        filter_layout.addStretch()
        
        # --- Área dos Gráficos ---
        charts_layout = QHBoxLayout()
        
        # REMOVIDO: Espaçador à esquerda (para não centralizar horizontalmente)
        
        # Gráfico 1: Barras Horizontais
        self.canvas_bar = ChartCanvas(self, width=5, height=4, dpi=100)
        charts_layout.addWidget(self.canvas_bar)
        
        # Gráfico 2: Pizza
        self.canvas_pie = ChartCanvas(self, width=4, height=4, dpi=100)
        charts_layout.addWidget(self.canvas_pie)
        
        # REMOVIDO: Espaçador à direita
        
        layout.addLayout(filter_layout)
        layout.addLayout(charts_layout)
        
        self.setMinimumHeight(350)
        self.setLayout(layout)
        
    def load_data(self):
        current_data = self.combo_product.currentData()
        self.combo_product.blockSignals(True)
        self.combo_product.clear()
        self.combo_product.addItem("Todos os Produtos", None)
        
        for p in self.manager.get_products():
            self.combo_product.addItem(p['nome'], p['id'])
            
        if current_data:
            idx = self.combo_product.findData(current_data)
            if idx >= 0: self.combo_product.setCurrentIndex(idx)
                
        self.combo_product.blockSignals(False)
        self.update_charts()
        
    def update_charts(self):
        try:
            selected_id = self.combo_product.currentData()
            stock_data = self.manager.get_stock()
            
            loc_data = {}
            for item in stock_data:
                loc = item.get('nome_localizacao', 'Sem Local')
                qty = float(item.get('quantidade', 0))
                if selected_id and item.get('produto_id') != selected_id:
                    continue
                if loc in loc_data:
                    loc_data[loc] += qty
                else:
                    loc_data[loc] = qty
                    
            labels = list(loc_data.keys())
            values = list(loc_data.values())
            
            # --- Atualizar Gráfico de Barras ---
            ax_bar = self.canvas_bar.axes
            ax_bar.clear()
            ax_bar.set_facecolor('none')
            
            if values:
                sorted_pairs = sorted(zip(values, labels))
                values_sorted = [x[0] for x in sorted_pairs]
                labels_sorted = [x[1] for x in sorted_pairs]
                
                ax_bar.barh(labels_sorted, values_sorted, color='#2563EB')
                ax_bar.set_title('Estoque por Localização', fontsize=10, fontweight='bold')
                ax_bar.set_xlabel('Quantidade')
                ax_bar.grid(True, linestyle='--', alpha=0.3)
                self.canvas_bar.fig.subplots_adjust(left=0.35, bottom=0.15, right=0.95, top=0.90)
            else:
                ax_bar.text(0.5, 0.5, "Sem dados", ha='center', transform=ax_bar.transAxes)
                
            self.canvas_bar.draw()
            
            # --- Atualizar Gráfico de Pizza ---
            ax_pie = self.canvas_pie.axes
            ax_pie.clear()
            ax_pie.set_facecolor('none')
            
            if values:
                explode = [0.05 if v == max(values) else 0 for v in values]
                ax_pie.pie(values, labels=labels, autopct='%1.1f%%', startangle=90, 
                           explode=explode, pctdistance=0.85)
                ax_pie.set_title('Distribuição por Local', fontsize=10, fontweight='bold')
                
                # Ajuste de margem para não cortar o título
                self.canvas_pie.fig.subplots_adjust(top=0.85, bottom=0.1, left=0.1, right=0.9)
            else:
                ax_pie.text(0.5, 0.5, "Sem dados", ha='center', transform=ax_pie.transAxes)
                
            self.canvas_pie.draw()
            
        except Exception as e:
            print(f"Erro ao gerar gráficos: {e}")