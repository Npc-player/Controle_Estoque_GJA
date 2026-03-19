# config.py
import sys
import os

SUPABASE_URL = "https://SUA_URL.supabase.co"
SUPABASE_KEY = "SUA_CHAVE" 
TIMEOUT_REQUISICAO = 60


# --- CONFIGURAÇÃO DO GITHUB ---
VERSAO_ATUAL = "1.1.1"
GITHUB_REPO = "Npc-player/Controle_Estoque_GJA" 

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)