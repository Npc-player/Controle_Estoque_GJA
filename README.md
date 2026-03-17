📦 Controle de Estoque - Vigilância Socioassistencial
Sistema desktop completo para gestão de estoque, desenvolvido em Python com PyQt5 e integração com Supabase. Projetado para atender às necessidades de controle de materiais da Secretaria Municipal de Desenvolvimento e Assistência Social (SEDEAS).

PythonLicenseStatus

📖 Visão Geral
Este sistema oferece uma solução robusta para o gerenciamento de entradas, saídas e transferências de produtos, com controle de usuários por níveis de acesso e geração de relatórios gráficos e documentais.

Principais Funcionalidades
Dashboard Interativo: Visualização gráfica de estoque por localização.
Gestão de Produtos: Cadastro com controle de validade, ata/licitação e estoque mínimo.
Movimentações: Entrada, Saída e Transferência entre locais com estorno automático.
Controle de Acesso:
Admin: Acesso total e cadastro de usuários/locais.
Gerência: Acesso a relatórios e exclusões.
Usuário: Restrito ao seu local de trabalho.
Relatórios: Exportação para PDF e Excel com filtros avançados.
Atualização Automática: Sistema verifica e instala atualizações via GitHub Releases.
🛠️ Tecnologias Utilizadas
Frontend: Python 3, PyQt5.
Backend/Database: Supabase (PostgreSQL).
Gráficos: Matplotlib.
Exportação: Pandas, OpenPyXL, ReportLab.
Deploy: PyInstaller (para geração do executável).
⚙️ Instalação e Configuração
Pré-requisitos
Python 3.9 ou superior instalado.
Uma conta no Supabase com as tabelas criadas.
Passo a Passo
Clone o repositório:
git clone https://github.com/Npc-player/Controle_Estoque_GJA.gitcd Controle_Estoque_GJA
Crie um ambiente virtual (Recomendado):
python -m venv venv# Windowsvenv\Scripts\activate# Linux/Macsource venv/bin/activate
Instale as dependências:
pip install -r requirements.txt
Configure as credenciais:Crie um arquivo config.py ou edite o existente com suas chaves do Supabase:
SUPABASE_URL = "sua_url_do_supabase"SUPABASE_KEY = "sua_chave_anon_publica"GITHUB_REPO = "seu_usuario/seu_repositorio"VERSAO_ATUAL = "1.0.0"
Execute o sistema:
python main.py
🗃️ Estrutura do Banco de Dados
O sistema espera as seguintes tabelas no Supabase:

usuarios: Dados de login e perfil.
produtos: Cadastro de materiais.
categorias: Classificação dos produtos.
localizacoes: Locais físicos de armazenamento.
estoque: Saldo atual (atualizado via triggers).
movimentacoes: Histórico de entradas/saídas.
excluidos: Auditoria de registros removidos.
🚀 Gerando o Executável (Deploy)
Para distribuir o sistema como um executável .exe, utilize o PyInstaller:

pyinstaller --noconsole --onefile --icon=ctrlestoque.ico --add-data "cab.png;." --add-data "fundo.png;." --add-data "rod.png;." main.py
Nota: O comando --add-data pode variar dependendo do sistema operacional.

📄 Licença
Este projeto está sob a licença MIT. Veja o arquivo LICENSE para mais detalhes.

✒️ Autores
Desenvolvimento: Nelson Carvalho - nelson77carvalho@gmail.com
