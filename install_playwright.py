#!/usr/bin/env python3
"""
Script para instalar browsers do Playwright no Railway
Este script deve ser executado após a instalação das dependências
"""

import subprocess
import sys
import os
import shutil

def setup_playwright_environment():
    """Configura o ambiente para o Playwright"""
    try:
        # Criar diretório cache se não existir
        cache_dir = os.getenv('PLAYWRIGHT_BROWSERS_PATH', '/app/.cache/ms-playwright')
        os.makedirs(cache_dir, exist_ok=True)
        print(f"[PLAYWRIGHT_INSTALL] Cache dir: {cache_dir}")
        
        # Configurar variáveis de ambiente
        os.environ['PLAYWRIGHT_BROWSERS_PATH'] = cache_dir
        os.environ['PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS'] = 'true'
        
        return True
    except Exception as e:
        print(f"[PLAYWRIGHT_INSTALL] Erro ao configurar ambiente: {e}")
        return False

def install_playwright_browsers():
    """Instala os browsers necessários para o Playwright"""
    try:
        print("[PLAYWRIGHT_INSTALL] Iniciando instalação dos browsers...")
        
        # Configurar ambiente primeiro
        if not setup_playwright_environment():
            return False
        
        # Instalar apenas o Chromium (mais leve)
        print("[PLAYWRIGHT_INSTALL] Instalando Chromium...")
        result = subprocess.run([
            sys.executable, "-m", "playwright", "install", "chromium", "--with-deps"
        ], capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0:
            print("[PLAYWRIGHT_INSTALL] Chromium instalado com sucesso!")
            if result.stdout:
                print(result.stdout)
        else:
            print(f"[PLAYWRIGHT_INSTALL] Erro na instalação: {result.stderr}")
            # Tentar sem --with-deps
            print("[PLAYWRIGHT_INSTALL] Tentando instalação sem dependências...")
            result2 = subprocess.run([
                sys.executable, "-m", "playwright", "install", "chromium"
            ], capture_output=True, text=True, timeout=600)
            
            if result2.returncode != 0:
                print(f"[PLAYWRIGHT_INSTALL] Falha total: {result2.stderr}")
                return False
            
        return True
        
    except subprocess.TimeoutExpired:
        print("[PLAYWRIGHT_INSTALL] Timeout na instalação dos browsers")
        return False
    except Exception as e:
        print(f"[PLAYWRIGHT_INSTALL] Erro inesperado: {e}")
        return False

def check_playwright_installation():
    """Verifica se o Playwright está funcionando"""
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto('https://example.com')
            title = page.title()
            browser.close()
            
        print(f"[PLAYWRIGHT_CHECK] Teste bem-sucedido! Título: {title}")
        return True
        
    except Exception as e:
        print(f"[PLAYWRIGHT_CHECK] Erro no teste: {e}")
        return False

if __name__ == "__main__":
    print("[PLAYWRIGHT_INSTALL] Configurando Playwright para produção...")
    
    # Verificar se estamos no Railway
    is_railway = os.getenv('RAILWAY_ENVIRONMENT') is not None
    
    if is_railway:
        print("[PLAYWRIGHT_INSTALL] Detectado ambiente Railway")
    
    # Instalar browsers
    if install_playwright_browsers():
        print("[PLAYWRIGHT_INSTALL] Instalação concluída!")
        
        # Testar instalação
        if check_playwright_installation():
            print("[PLAYWRIGHT_INSTALL] Playwright está funcionando corretamente!")
            sys.exit(0)
        else:
            print("[PLAYWRIGHT_INSTALL] Playwright instalado mas com problemas")
            sys.exit(1)
    else:
        print("[PLAYWRIGHT_INSTALL] Falha na instalação")
        sys.exit(1)