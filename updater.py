# updater.py
import requests
import os
import subprocess
import sys
import json
import config
import zipfile
import time
import re
from itertools import zip_longest

def check_version_greater(new_version, old_version):
    """
    Compara versões de forma robusta.
    Limpa a string, remove texto e compara número a número.
    1.1.0 é maior que 1.0.1.
    """
    def parse(v):
        # 1. Garante que é string
        v_str = str(v)
        
        # 2. Remove o prefixo 'v' ou 'V'
        v_str = v_str.lstrip('vV')
        
        # 3. Remove qualquer coisa que não seja número ou ponto (ex: "Release 1.0.1" -> "1.0.1")
        v_str = re.sub(r'[^0-9.]', '', v_str)
        
        # 4. Divide em partes
        parts = v_str.split('.')
        
        # 5. Converte para inteiros
        return [int(p) for p in parts if p.isdigit()]

    try:
        v_new = parse(new_version)
        v_old = parse(old_version)
        
        # LOG DETALHADO NO CONSOLE
        print(f"[UPDATE] Comparando versões:")
        print(f"  -> Repositório (Bruta): '{new_version}' -> Parse: {v_new}")
        print(f"  -> Local (Config):      '{old_version}' -> Parse: {v_old}")
        
        # Compara preenchendo com zeros (ex: 1.1 vs 1.0.1 -> 1,1,0 vs 1,0,1)
        for n, o in zip_longest(v_new, v_old, fillvalue=0):
            if n > o: return True
            if n < o: return False
        
        # Se forem iguais
        return False
        
    except Exception as e:
        print(f"[UPDATE] Erro na comparação: {e}. Usando fallback de string.")
        # Fallback simples
        return str(new_version) > str(old_version)

def check_for_updates():
    """Verifica a última release no GitHub."""
    print("[UPDATE] Verificando atualizações no GitHub...")
    
    if not hasattr(config, 'GITHUB_REPO') or not config.GITHUB_REPO:
        return False, "GITHUB_REPO não configurado no config.py", None

    try:
        url = f"https://api.github.com/repos/{config.GITHUB_REPO}/releases/latest"
        headers = {"User-Agent": "ControleEstoque-Updater"}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            tag_name = data.get('tag_name', 'v0.0.0')
            latest_version = tag_name.replace('v', '')
            
            # A comparação agora é robusta
            if check_version_greater(latest_version, config.VERSAO_ATUAL):
                download_url = None
                for asset in data.get('assets', []):
                    name = asset['name'].lower()
                    if name.endswith('.zip') or name.endswith('.exe'):
                        download_url = asset['browser_download_url']
                        break
                
                if download_url:
                    return True, latest_version, download_url
                else:
                    return False, "Release encontrada, mas sem arquivo anexado.", None
            else:
                # Se caiu aqui, a versão local é maior ou igual à do repositório
                return False, None, None
        elif response.status_code == 404:
            return False, "Repositório ou Release não encontrado no GitHub.", None
        else:
            return False, f"Erro HTTP {response.status_code}", None

    except Exception as e:
        return False, f"Erro de conexão: {str(e)}", None

def download_update(url, dest_path):
    """Baixa o arquivo do GitHub."""
    try:
        print(f"[UPDATE] Baixando de: {url}")
        headers = {"User-Agent": "ControleEstoque-Updater"}
        response = requests.get(url, stream=True, timeout=300, headers=headers)
        
        if response.status_code != 200:
            return False, f"Erro ao baixar: HTTP {response.status_code}"

        temp_path = dest_path + ".tmp"
        
        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk: f.write(chunk)
        
        with open(temp_path, 'rb') as f:
            header = f.read(4)

        if header.startswith(b'PK'):  # ZIP
            print("[UPDATE] Arquivo ZIP detectado.")
            return extract_zip(temp_path, dest_path)
        elif header.startswith(b'MZ'):  # EXE
            print("[UPDATE] Arquivo EXE detectado.")
            if os.path.exists(dest_path):
                os.remove(dest_path)
            os.rename(temp_path, dest_path)
            return True, "Sucesso"
        else:
            os.remove(temp_path)
            return False, "Arquivo baixado não é ZIP nem EXE."

    except Exception as e:
        return False, f"Erro no download: {str(e)}"

def extract_zip(zip_path, dest_path):
    try:
        extract_dir = os.path.dirname(dest_path)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            exe_name = None
            for file in zip_ref.namelist():
                if file.lower().endswith('.exe'):
                    exe_name = file
                    break
            
            if exe_name:
                zip_ref.extract(exe_name, extract_dir)
                extracted_path = os.path.join(extract_dir, exe_name)
                if os.path.exists(dest_path):
                    os.remove(dest_path)
                os.rename(extracted_path, dest_path)
                os.remove(zip_path)
                return True, "Sucesso"
            else:
                os.remove(zip_path)
                return False, "Nenhum .exe encontrado dentro do ZIP."
    except Exception as e:
        return False, f"Erro ao extrair: {str(e)}"

def get_real_exe_path():
    """Retorna o caminho real do .exe em execução."""
    candidate = os.path.abspath(sys.argv[0])
    if candidate.lower().endswith('.exe') and os.path.isfile(candidate):
        return candidate
    return sys.executable

def apply_update(new_exe_path, version):
    """
    Aplica a atualização via script .bat.
    """
    current_exe = get_real_exe_path()
    current_dir = os.path.dirname(current_exe)
    batch_path = os.path.join(current_dir, "ATUALIZAR.bat")
    pid = os.getpid()
    
    # --- LÓGICA DE NOMENCLATURA ---
    exe_basename = os.path.basename(current_exe)
    name_no_ext = os.path.splitext(exe_basename)[0]
    clean_name = re.sub(r'_[vV]?\d+(\.\d+)*$', '', name_no_ext)
    
    final_exe_name = f"{clean_name}_{version}.exe"
    final_exe_path = os.path.join(current_dir, final_exe_name)

    bat_content = (
        "@echo off\n"
        "chcp 65001 >nul\n"
        "echo Aguardando o programa fechar completamente...\n"
        f":waitloop\n"
        f"tasklist /FI \"PID eq {pid}\" 2>nul | find \"{pid}\" >nul\n"
        "if not errorlevel 1 (\n"
        "    timeout /t 1 /nobreak >nul\n"
        "    goto waitloop\n"
        ")\n"
        "echo Programa fechado. Aguardando liberacao dos arquivos...\n"
        "timeout /t 3 /nobreak >nul\n"
        "echo Deletando executavel antigo...\n"
        f"del /F /Q \"{current_exe}\"\n"
        f"if exist \"{final_exe_path}\" del /F /Q \"{final_exe_path}\"\n"
        f"move /Y \"{new_exe_path}\" \"{final_exe_path}\"\n"
        "echo Reiniciando...\n"
        f"start \"\" \"{final_exe_path}\"\n"
        "(goto) 2>nul & del \"%~f0\"\n"
    )

    try:
        with open(batch_path, 'w', encoding='utf-8') as f:
            f.write(bat_content)
            f.flush()
            os.fsync(f.fileno())
        
        if not os.path.exists(batch_path):
            return False, "Falha critica: Arquivo .bat nao foi salvo."

        subprocess.Popen(f'cmd /c start "" /min "{batch_path}"', shell=True)
        
        return True, "Atualização iniciada"
    except Exception as e:
        return False, str(e)
    
# Adicionar ao final de updater.py

def get_latest_release_info():
    """Busca a tag e o corpo (notas) da última release no GitHub."""
    if not hasattr(config, 'GITHUB_REPO') or not config.GITHUB_REPO:
        return None, "Repositório não configurado."
    
    try:
        url = f"https://api.github.com/repos/{config.GITHUB_REPO}/releases/latest"
        headers = {"User-Agent": "ControleEstoque-Updater"}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            version = data.get('tag_name', 'Desconhecida')
            notes = data.get('body', 'Sem descrição disponível.')
            return version, notes
        else:
            return None, f"Erro ao buscar release (HTTP {response.status_code})"
            
    except Exception as e:
        return None, f"Erro de conexão: {str(e)}"