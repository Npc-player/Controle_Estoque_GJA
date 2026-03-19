# backend.py
import supabase
import uuid
from datetime import datetime
import threading
import config

class DataManager:
    def __init__(self):
        # Conexão com Supabase
        self.supabase = supabase.create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        self.is_online = True
        self.data = {}
        self._db_lock = threading.Lock()
        print("[BACKEND] Conectado ao Supabase.")

    # --- Funções Auxiliares ---
    def _clean_value(self, value):
        if not isinstance(value, str):
            return value
        s = value.strip()
        if ',' in s:
            s = s.replace('.', '').replace(',', '.')
        else:
            if '.' in s:
                parts = s.split('.')
                if len(parts) == 2 and len(parts[1]) <= 2:
                    pass
                else:
                    s = s.replace('.', '')
        try:
            return float(s)
        except ValueError:
            return value

    # --- Cache e Leitura ---
    def fetch_data(self):
        try:
            self.data['usuarios'] = self._fetch_table('usuarios')
            self.data['produtos'] = self._fetch_table('produtos')
            self.data['categorias'] = self._fetch_table('categorias')
            self.data['localizacoes'] = self._fetch_table('localizacoes')
            self.data['estoque'] = self._fetch_table('estoque')
            self.data['movimentacoes'] = self._fetch_table('movimentacoes')
            self.data['excluidos'] = self._fetch_table('excluidos')
            return True
        except Exception as e:
            print(f"[BACKEND] Erro ao buscar dados: {e}")
            return False

    def _fetch_table(self, table_name):
        response = self.supabase.table(table_name).select("*").execute()
        return response.data if response.data else []

    def _refresh_memory(self, *tables):
        for t in tables:
            self.data[t] = self._fetch_table(t)

    # --- Escrita ---
    def send_upsert(self, entity_key, row_data):
        try:
            if not row_data.get('id'):
                row_data['id'] = uuid.uuid4().hex[:8]
            
            row_data['data_alteracao'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            
            float_fields = ['valor', 'quantidade']
            for field in float_fields:
                if field in row_data and row_data[field] is not None:
                    val = row_data[field]
                    if isinstance(val, str):
                        val = self._clean_value(val)
                    try:
                        row_data[field] = float(val)
                    except:
                        pass

            int_fields = ['estoque_minimo']
            for field in int_fields:
                if field in row_data and row_data[field] is not None:
                    val = row_data[field]
                    if isinstance(val, str):
                        val = self._clean_value(val)
                    try:
                        row_data[field] = int(float(val))
                    except:
                        pass
            
            self.supabase.table(entity_key).upsert(row_data).execute()
            self._refresh_memory(entity_key)
            return True, "Salvo com sucesso."
        except Exception as e:
            return False, str(e)

    def delete_row(self, entity_key, row_id):
        try:
            self.supabase.table(entity_key).delete().eq('id', row_id).execute()
            self._refresh_memory(entity_key)
            return True, "Excluído com sucesso."
        except Exception as e:
            return False, str(e)

    # --- Movimentações e Estoque ---
    def process_movement(self, mov_data):
        if not mov_data.get('id'):
            mov_data['id'] = uuid.uuid4().hex[:8]
        if not mov_data.get('data_hora'):
            mov_data['data_hora'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        try:
            qtd = float(self._clean_value(mov_data['quantidade']))
        except:
            qtd = 0.0

        try:
            self.supabase.rpc('processar_movimentacao', {
                'p_tipo': mov_data['tipo'],
                'p_produto_id': mov_data['produto_id'],
                'p_nome_produto': mov_data.get('nome_produto'),
                'p_quantidade': qtd,
                'p_motivo': mov_data.get('motivo'),
                'p_usuario': mov_data.get('usuario'),
                'p_localizacao_origem_id': mov_data.get('localizacao_origem_id'),
                'p_localizacao_destino_id': mov_data.get('localizacao_destino_id'),
                'p_nome_origem': mov_data.get('nome_origem'),
                'p_nome_destino': mov_data.get('nome_destino'),
                'p_id': mov_data['id'],
                'p_data_hora': mov_data['data_hora']
            }).execute()

            self._refresh_memory('movimentacoes', 'estoque')
            return True, "Movimentação processada."

        except Exception as e:
            if "Estoque insuficiente" in str(e):
                return False, "Erro: Estoque insuficiente."
            return False, str(e)

    def edit_movement(self, old_mov, new_mov):
        try:
            qtd_old = float(self._clean_value(old_mov['quantidade']))
            
            estorno_params = {
                'p_produto_id': old_mov['produto_id'],
                'p_quantidade': qtd_old,
                'p_nome_produto': old_mov.get('nome_produto'),
                'p_motivo': 'ESTORNO EDICAO',
                'p_usuario': old_mov.get('usuario')
            }

            if old_mov['tipo'] == 'ENTRADA':
                estorno_params['p_tipo'] = 'SAÍDA'
                estorno_params['p_localizacao_origem_id'] = old_mov.get('localizacao_destino_id')
                estorno_params['p_nome_origem'] = old_mov.get('nome_destino')
                estorno_params['p_localizacao_destino_id'] = None
                estorno_params['p_nome_destino'] = None
            
            elif old_mov['tipo'] == 'SAÍDA':
                estorno_params['p_tipo'] = 'ENTRADA'
                estorno_params['p_localizacao_destino_id'] = old_mov.get('localizacao_origem_id')
                estorno_params['p_nome_destino'] = old_mov.get('nome_origem')
                estorno_params['p_localizacao_origem_id'] = None
                estorno_params['p_nome_origem'] = None
            
            elif old_mov['tipo'] == 'TRANSFERÊNCIA':
                estorno_params['p_tipo'] = 'TRANSFERÊNCIA'
                estorno_params['p_localizacao_origem_id'] = old_mov.get('localizacao_destino_id')
                estorno_params['p_nome_origem'] = old_mov.get('nome_destino')
                estorno_params['p_localizacao_destino_id'] = old_mov.get('localizacao_origem_id')
                estorno_params['p_nome_destino'] = old_mov.get('nome_origem')

            self.supabase.rpc('processar_movimentacao', estorno_params).execute()
            self.supabase.table('movimentacoes').delete().eq('id', old_mov['id']).execute()
            return self.process_movement(new_mov)

        except Exception as e:
            return False, str(e)

    def delete_movement(self, mov_data):
        try:
            qtd_mov = float(self._clean_value(mov_data['quantidade']))
            
            estorno_params = {
                'p_produto_id': mov_data['produto_id'],
                'p_quantidade': qtd_mov,
                'p_nome_produto': mov_data.get('nome_produto'),
                'p_motivo': 'ESTORNO EXCLUSAO',
                'p_usuario': mov_data.get('usuario')
            }

            if mov_data['tipo'] == 'ENTRADA':
                estorno_params['p_tipo'] = 'SAÍDA'
                estorno_params['p_localizacao_origem_id'] = mov_data.get('localizacao_destino_id')
                estorno_params['p_nome_origem'] = mov_data.get('nome_destino')
                estorno_params['p_localizacao_destino_id'] = None
                estorno_params['p_nome_destino'] = None
            
            elif mov_data['tipo'] == 'SAÍDA':
                estorno_params['p_tipo'] = 'ENTRADA'
                estorno_params['p_localizacao_destino_id'] = mov_data.get('localizacao_origem_id')
                estorno_params['p_nome_destino'] = mov_data.get('nome_origem')
                estorno_params['p_localizacao_origem_id'] = None
                estorno_params['p_nome_origem'] = None
            
            elif mov_data['tipo'] == 'TRANSFERÊNCIA':
                estorno_params['p_tipo'] = 'TRANSFERÊNCIA'
                estorno_params['p_localizacao_origem_id'] = mov_data.get('localizacao_destino_id')
                estorno_params['p_nome_origem'] = mov_data.get('nome_destino')
                estorno_params['p_localizacao_destino_id'] = mov_data.get('localizacao_origem_id')
                estorno_params['p_nome_destino'] = mov_data.get('nome_origem')

            self.supabase.rpc('processar_movimentacao', estorno_params).execute()

            self.supabase.table('excluidos').insert(mov_data).execute()
            self.supabase.table('movimentacoes').delete().eq('id', mov_data['id']).execute()

            self._refresh_memory('movimentacoes', 'estoque', 'excluidos')
            return True, "Movimentação excluída e estoque estornado."
        except Exception as e:
            return False, str(e)

    # --- Getters e Status ---
    def get_sync_status(self): 
        return {'queue_size': 0, 'active_tasks': 0}

    def get_product_by_id(self, pid): 
        return next((p for p in self.get_products() if p['id'] == pid), None)

    def get_location_by_id(self, lid): 
        return next((l for l in self.get_locations() if l['id'] == lid), None)

    def check_login(self, email, senha):
        for u in self.data.get('usuarios', []):
            if str(u.get('email', '')).strip().lower() == email.strip().lower() and str(u.get('senha', '')).strip() == senha.strip():
                return u
        return None

    def get_products(self): return self.data.get('produtos', [])
    
    # --- FILTRAGEM POR LOCALIZAÇÃO ---
    def get_stock(self, user=None):
        data = self.data.get('estoque', [])
        # CORREÇÃO: Verifica se o perfil é 'usuário' (com acento)
        if user and user.get('perfil') == 'usuário' and user.get('localizacao_id'):
            lid = user.get('localizacao_id')
            return [item for item in data if item.get('localizacao_id') == lid]
        return data

    def get_locations(self): return self.data.get('localizacoes', [])
    def get_categories(self): return self.data.get('categorias', [])
    
    def get_movements(self, user=None):
        data = self.data.get('movimentacoes', [])
        # CORREÇÃO: Verifica se o perfil é 'usuário' (com acento)
        if user and user.get('perfil') == 'usuário' and user.get('localizacao_id'):
            lid = user.get('localizacao_id')
            return [item for item in data if item.get('localizacao_origem_id') == lid or item.get('localizacao_destino_id') == lid]
        return data

    def get_users(self): return self.data.get('usuarios', [])
    def get_deleted(self): return self.data.get('excluidos', [])