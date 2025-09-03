#!/usr/bin/env python3
"""
Script para diagnosticar e corrigir problemas do Playwright em produção
"""

import os
import sys
import subprocess
import glob
import shutil

def diagnose_playwright():
    """Diagnostica problemas do Playwright"""
    print("[PLAYWRIGHT_FIX] Iniciando diagnóstico...")
    
    # Verificar se o Playwright está instalado
    try:
        import playwright
        print(f"[PLAYWRIGHT_FIX] ✓ Playwright instalado: {playwright.__version__}")
    except ImportError:
        print("[PLAYWRIGHT_FIX] ✗ Playwright não instalado")
        return False
    
    # Verificar variáveis de ambiente
    browsers_path = os.getenv('PLAYWRIGHT_BROWSERS_PATH', '/app/.cache/ms-playwright')
    print(f"[PLAYWRIGHT_FIX] Browsers path: {browsers_path}")
    
    # Verificar se o diretório existe
    if os.path.exists(browsers_path):
        print(f"[PLAYWRIGHT_FIX] ✓ Diretório browsers existe")
        
        # Listar conteúdo
        try:
            contents = os.listdir(browsers_path)
            print(f"[PLAYWRIGHT_FIX] Conteúdo: {contents}")
            
            # Procurar por chromium
            chromium_dirs = glob.glob(os.path.join(browsers_path, 'chromium-*'))
            if chromium_dirs:
                print(f"[PLAYWRIGHT_FIX] ✓ Chromium encontrado: {chromium_dirs}")
                
                # Verificar executável
                for chromium_dir in chromium_dirs:
                    executable_path = os.path.join(chromium_dir, 'chrome-linux', 'chrome')
                    if os.path.exists(executable_path):
                        print(f"[PLAYWRIGHT_FIX] ✓ Executável encontrado: {executable_path}")
                        return True
                    else:
                        print(f"[PLAYWRIGHT_FIX] ✗ Executável não encontrado: {executable_path}")
            else:
                print("[PLAYWRIGHT_FIX] ✗ Chromium não encontrado")
        except Exception as e:
            print(f"[PLAYWRIGHT_FIX] Erro ao listar diretório: {e}")
    else:
        print(f"[PLAYWRIGHT_FIX] ✗ Diretório browsers não existe: {browsers_path}")
    
    return False

def fix_playwright():
    """Tenta corrigir problemas do Playwright"""
    print("[PLAYWRIGHT_FIX] Tentando corrigir problemas...")
    
    # Criar diretório se não existir
    browsers_path = os.getenv('PLAYWRIGHT_BROWSERS_PATH', '/app/.cache/ms-playwright')
    os.makedirs(browsers_path, exist_ok=True)
    
    # Configurar variáveis de ambiente
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = browsers_path
    os.environ['PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS'] = 'true'
    
    # Tentar reinstalar browsers
    try:
        print("[PLAYWRIGHT_FIX] Reinstalando Chromium...")
        
        # Limpar cache antigo
        if os.path.exists(browsers_path):
            shutil.rmtree(browsers_path, ignore_errors=True)
            os.makedirs(browsers_path, exist_ok=True)
        
        # Instalar novamente
        result = subprocess.run([
            sys.executable, "-m", "playwright", "install", "chromium"
        ], capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0:
            print("[PLAYWRIGHT_FIX] ✓ Chromium reinstalado com sucesso")
            return True
        else:
            print(f"[PLAYWRIGHT_FIX] ✗ Erro na reinstalação: {result.stderr}")
            
            # Tentar com --force
            print("[PLAYWRIGHT_FIX] Tentando com --force...")
            result2 = subprocess.run([
                sys.executable, "-m", "playwright", "install", "--force", "chromium"
            ], capture_output=True, text=True, timeout=600)
            
            if result2.returncode == 0:
                print("[PLAYWRIGHT_FIX] ✓ Chromium instalado com --force")
                return True
            else:
                print(f"[PLAYWRIGHT_FIX] ✗ Falha total: {result2.stderr}")
                
    except Exception as e:
        print(f"[PLAYWRIGHT_FIX] Erro inesperado: {e}")
    
    return False

def test_playwright():
    """Testa se o Playwright está funcionando"""
    try:
        print("[PLAYWRIGHT_FIX] Testando Playwright...")
        
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto('https://httpbin.org/get')
            content = page.content()
            browser.close()
            
            if 'httpbin' in content:
                print("[PLAYWRIGHT_FIX] ✓ Playwright funcionando corretamente")
                return True
            else:
                print("[PLAYWRIGHT_FIX] ✗ Playwright não retornou conteúdo esperado")
                
    except Exception as e:
        print(f"[PLAYWRIGHT_FIX] ✗ Erro no teste: {e}")
    
    return False

if __name__ == "__main__":
    print("[PLAYWRIGHT_FIX] Iniciando correção do Playwright...")
    
    # Diagnóstico inicial
    if diagnose_playwright():
        print("[PLAYWRIGHT_FIX] Playwright parece estar funcionando")
        if test_playwright():
            print("[PLAYWRIGHT_FIX] ✓ Tudo funcionando perfeitamente!")
            sys.exit(0)
    
    # Tentar corrigir
    if fix_playwright():
        print("[PLAYWRIGHT_FIX] Correção aplicada, testando...")
        if test_playwright():
            print("[PLAYWRIGHT_FIX] ✓ Problema corrigido com sucesso!")
            sys.exit(0)
        else:
            print("[PLAYWRIGHT_FIX] ✗ Correção não resolveu o problema")
    
    print("[PLAYWRIGHT_FIX] ✗ Não foi possível corrigir o Playwright")
    sys.exit(1)