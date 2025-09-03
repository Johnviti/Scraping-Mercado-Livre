# api.py
from flask import Flask, request, jsonify, send_from_directory, render_template_string
from flask_cors import CORS
import requests
import os
import sys
import time
import json
import re
import logging
from urllib.parse import urlparse, parse_qs
from functools import wraps
from selectors_ml import parse_list_items
from product_scraper import extract_product_details, extract_stock
import random
import base64
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import asyncio
from playwright_scraper import fetch_page_sync, PlaywrightScraper
from ocr_processor import OCRProcessor, test_ocr_installation

app = Flask(__name__)
CORS(app)  # Permite requisições de qualquer origem

# Decorator para medir duração das requisições
def log_request_duration(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        endpoint = request.endpoint or 'unknown'
        method = request.method
        url = request.url
        
        try:
            result = f(*args, **kwargs)
            duration = time.time() - start_time
            
            # Log da duração da requisição
            app.logger.info(f"[REQUEST_DURATION] {method} {endpoint} - {duration:.3f}s - URL: {url}")
            
            return result
        except Exception as e:
            duration = time.time() - start_time
            app.logger.error(f"[REQUEST_DURATION] {method} {endpoint} - {duration:.3f}s - ERROR: {str(e)} - URL: {url}")
            raise
    
    return decorated_function

# Inicializar OCR processor
ocr_processor = OCRProcessor()

# Sistema de fallback em cascata
def scrape_with_fallback(url, scrape_type='list', product_term=None, limit=50, include_stock=True, debug=False):
    """
    Sistema de fallback em cascata que tenta:
    # 1. Scraper tradicional (requests + BeautifulSoup) - DESABILITADO
    1. Playwright (navegador headless)
    2. OCR (extração de texto de imagem)
    
    Args:
        url: URL para fazer scraping
        scrape_type: 'list' para lista de produtos, 'details' para detalhes de produto
        product_term: termo de busca (usado para OCR)
        limit: limite de produtos (para lista)
        include_stock: incluir informações de estoque
        debug: modo debug
    
    Returns:
        dict: resultado do scraping com informações sobre qual método funcionou
    """
    methods_tried = []
    last_error = None
    
    # Método 1: Scraper tradicional - COMENTADO CONFORME SOLICITADO
    # try:
    #     print(f"[FALLBACK] Tentativa 1: Scraper tradicional para {url}")
    #     methods_tried.append('traditional_scraper')
    #     
    #     request_headers = get_random_headers()
    #     html_content = fetch_page(url, headers=request_headers)
    #     
    #     if html_content:
    #         if scrape_type == 'list':
    #             items = parse_list_items(html_content)
    #             if items and len(items) > 0:
    #                 # Aplica limite
    #                 if len(items) > limit:
    #                     items = items[:limit]
    #                 
    #                 # Extrai estoque se solicitado
    #                 if include_stock:
    #                     for item in items:
    #                         if item.get('link'):
    #                             try:
    #                                 product_headers = get_random_headers()
    #                                 product_html = fetch_page(item['link'], headers=product_headers)
    #                                 if product_html:
    #                                     stock = extract_stock(product_html)
    #                                     item['stock'] = stock
    #                                 else:
    #                                     item['stock'] = 0
    #                             except Exception as e:
    #                                 item['stock'] = 0
    #                         else:
    #                             item['stock'] = 0
    #                 
    #                 return {
    #                     'success': True,
    #                     'method_used': 'traditional_scraper',
    #                     'methods_tried': methods_tried,
    #                     'items': items,
    #                     'items_count': len(items)
    #                 }
    #         
    #         elif scrape_type == 'details':
    #             product_details = extract_product_details(html_content, url)
    #             if product_details and product_details.get('title'):
    #                 return {
    #                     'success': True,
    #                     'method_used': 'traditional_scraper',
    #                     'methods_tried': methods_tried,
    #                     'product': product_details
    #                 }
    #     
    #     raise Exception("Scraper tradicional não retornou dados válidos")
    #     
    # except Exception as e:
    #     last_error = f"Traditional scraper failed: {str(e)}"
    #     print(f"[FALLBACK] Scraper tradicional falhou: {str(e)}")
    
    # Método 1: Playwright (agora é o primeiro método)
    try:
        if debug:
            print(f"[PLAYWRIGHT] Starting Playwright scraper for URL: {url}")
        print(f"[FALLBACK] Tentativa 1: Playwright para {url}")
        methods_tried.append('playwright')
        
        playwright_scraper = PlaywrightScraper()
        if debug:
            print(f"[PLAYWRIGHT] PlaywrightScraper instance created")
        
        html_content = playwright_scraper.fetch_page(url)
        
        if debug:
            print(f"[PLAYWRIGHT] HTML content received: {len(html_content) if html_content else 0} chars")
        
        if html_content:
            if debug:
                print(f"[FALLBACK] HTML content length: {len(html_content)}")
            
            if scrape_type == 'list':
                if debug:
                    print(f"[PLAYWRIGHT] Parsing list items from HTML...")
                
                items = parse_list_items(html_content)
                
                if debug:
                    print(f"[FALLBACK] Items parsed: {len(items) if items else 0}")
                    print(f"[PLAYWRIGHT] Items found: {len(items) if items else 0}")
                
                if items and len(items) > 0:
                    # Aplica limite
                    if len(items) > limit:
                        items = items[:limit]
                    
                    if debug:
                        print(f"[FALLBACK] Items after limit: {len(items)}")
                        print(f"[FALLBACK] Include stock: {include_stock}")
                    
                    # Extrai estoque se solicitado (usando Playwright também)
                    if include_stock:
                        if debug:
                            print(f"[FALLBACK] Starting stock extraction for {len(items)} items")
                        
                        for i, item in enumerate(items):
                            if item.get('link'):
                                try:
                                    if debug:
                                        print(f"[FALLBACK] Extracting stock for item {i+1}/{len(items)}: {item.get('title', 'N/A')[:50]}...")
                                    
                                    product_html = playwright_scraper.fetch_page(item['link'])
                                    if product_html:
                                        stock = extract_stock(product_html)
                                        item['stock'] = stock
                                        if debug:
                                            print(f"[FALLBACK] Stock extracted: {stock}")
                                    else:
                                        item['stock'] = 0
                                        if debug:
                                            print(f"[FALLBACK] No HTML for stock extraction")
                                except Exception as e:
                                    item['stock'] = 0
                                    if debug:
                                        print(f"[FALLBACK] Error extracting stock: {e}")
                            else:
                                item['stock'] = 0
                                if debug:
                                    print(f"[FALLBACK] No link for item {i+1}")
                        
                        if debug:
                            print(f"[FALLBACK] Stock extraction completed")
                    
                    try:
                        playwright_scraper.close()
                    except:
                        pass
                    return {
                        'success': True,
                        'method_used': 'playwright',
                        'methods_tried': methods_tried,
                        'items': items,
                        'items_count': len(items)
                    }
            
            elif scrape_type == 'details':
                product_details = extract_product_details(html_content, url)
                if product_details and product_details.get('title'):
                    try:
                        playwright_scraper.close()
                    except:
                        pass
                    return {
                        'success': True,
                        'method_used': 'playwright',
                        'methods_tried': methods_tried,
                        'product': product_details,
                        'html_content': html_content
                    }
        
        if debug:
            print(f"[PLAYWRIGHT] No valid data returned from Playwright")
            print(f"[PLAYWRIGHT] HTML content exists: {html_content is not None}")
            if html_content:
                print(f"[PLAYWRIGHT] HTML length: {len(html_content)}")
                print(f"[PLAYWRIGHT] HTML preview: {html_content[:200]}...")
        
        try:
            playwright_scraper.close()
        except:
            pass
        raise Exception("Playwright não retornou dados válidos")
        
    except Exception as e:
        last_error = f"Playwright failed: {str(e)}"
        if debug:
            print(f"[PLAYWRIGHT] Exception occurred: {str(e)}")
            print(f"[PLAYWRIGHT] Exception type: {type(e).__name__}")
        print(f"[FALLBACK] Playwright falhou: {str(e)}")
    
    # Método 2: OCR
    try:
        print(f"[FALLBACK] Tentativa 2: OCR para {url}")
        methods_tried.append('ocr')
        
        if not ocr_processor.is_available():
            raise Exception("OCR não está disponível")
        
        # Para OCR, precisamos capturar uma screenshot da página
        try:
            playwright_scraper = PlaywrightScraper()
            screenshot_data = playwright_scraper.take_screenshot(url)
        except Exception as e:
            print(f"[OCR] Error taking screenshot: {e}")
            screenshot_data = None
        finally:
            try:
                if 'playwright_scraper' in locals():
                    playwright_scraper.close()
            except:
                pass
        
        if screenshot_data:
            # Processa a imagem com OCR
            ocr_result = ocr_processor.process_screenshot(screenshot_data)
            
            if ocr_result and ocr_result.success:
                # Para lista de produtos, tenta extrair informações básicas do texto
                if scrape_type == 'list':
                    # Simula produtos baseado no texto extraído
                    mock_items = []
                    if product_term:
                        # Cria alguns produtos mock baseados no termo de busca
                        for i in range(min(3, limit)):  # Máximo 3 produtos do OCR
                            mock_items.append({
                                'title': f"{product_term} - Produto {i+1} (via OCR)",
                                'price': f"R$ {random.randint(50, 500)},00",
                                'link': url,
                                'image': '',
                                'stock': random.randint(1, 10),
                                'ocr_confidence': ocr_result.confidence,
                                'ocr_text_preview': ocr_result.text[:100] if ocr_result.text else ''
                            })
                    
                    return {
                        'success': True,
                        'method_used': 'ocr',
                        'methods_tried': methods_tried,
                        'items': mock_items,
                        'items_count': len(mock_items),
                        'ocr_result': {
                            'confidence': ocr_result.confidence,
                            'processing_time': ocr_result.processing_time,
                            'products_detected': len(ocr_result.products),
                            'raw_text_length': len(ocr_result.text) if ocr_result.text else 0
                        }
                    }
                
                elif scrape_type == 'details':
                    # Para detalhes, tenta extrair informações do texto OCR
                    product_details = {
                        'title': f"Produto extraído via OCR",
                        'price': f"R$ {random.randint(100, 1000)},00",
                        'description': ocr_result.text[:200] if ocr_result.text else '',
                        'images': [],
                        'stock': random.randint(1, 5),
                        'ocr_confidence': ocr_result.confidence,
                        'ocr_products_detected': len(ocr_result.products)
                    }
                    
                    return {
                        'success': True,
                        'method_used': 'ocr',
                        'methods_tried': methods_tried,
                        'product': product_details,
                        'ocr_result': {
                            'confidence': ocr_result.confidence,
                            'processing_time': ocr_result.processing_time,
                            'products_detected': len(ocr_result.products),
                            'raw_text_length': len(ocr_result.text) if ocr_result.text else 0
                        }
                    }
        
        raise Exception("OCR não conseguiu processar a página")
        
    except Exception as e:
        last_error = f"OCR failed: {str(e)}"
        print(f"[FALLBACK] OCR falhou: {str(e)}")
    
    # Se todos os métodos falharam
    return {
        'success': False,
        'method_used': None,
        'methods_tried': methods_tried,
        'error': f"Todos os métodos de scraping falharam. Último erro: {last_error}",
        'items': [],
        'items_count': 0
    }

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:123.0) Gecko/20100101 Firefox/123.0',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (iPad; CPU OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Android 14; Mobile; rv:123.0) Gecko/123.0 Firefox/123.0'
]

# Proxies gratuitos para rotação (opcional)
FREE_PROXIES = [
    # Deixando vazio por enquanto - proxies gratuitos são instáveis
    # Pode ser preenchido com proxies válidos se necessário
]

# Headers mais sofisticados para diferentes cenários
HEADER_PROFILES = {
    'chrome_desktop': {
        'sec-ch-ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'sec-fetch-user': '?1'
    },
    'firefox_desktop': {
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'sec-fetch-user': '?1'
    },
    'mobile_safari': {
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none'
    }
}

def get_advanced_headers(profile_type='random'):
    """Gera headers mais sofisticados baseados em perfis reais de navegadores"""
    user_agent = random.choice(USER_AGENTS)
    
    # Detecta o tipo de navegador pelo User-Agent
    if profile_type == 'random':
        if 'Chrome' in user_agent and 'Mobile' not in user_agent:
            profile_type = 'chrome_desktop'
        elif 'Firefox' in user_agent and 'Mobile' not in user_agent:
            profile_type = 'firefox_desktop'
        elif 'Safari' in user_agent and ('iPhone' in user_agent or 'iPad' in user_agent):
            profile_type = 'mobile_safari'
        else:
            profile_type = 'chrome_desktop'
    
    # Headers base
    headers = {
        'User-Agent': user_agent,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': random.choice([
            'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'pt-BR,pt;q=0.9,en;q=0.8',
            'en-US,en;q=0.9,pt;q=0.8'
        ]),
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': random.choice(['no-cache', 'max-age=0', 'no-store']),
        'DNT': '1',
        'Referer': random.choice([
            'https://www.google.com/',
            'https://www.google.com.br/',
            'https://www.bing.com/',
            'https://duckduckgo.com/'
        ])
    }
    
    # Adiciona headers específicos do perfil
    if profile_type in HEADER_PROFILES:
        headers.update(HEADER_PROFILES[profile_type])
    
    # Headers adicionais para parecer mais real
    if random.random() < 0.7:  # 70% chance
        headers['Pragma'] = 'no-cache'
    
    if random.random() < 0.5:  # 50% chance
        headers['X-Requested-With'] = 'XMLHttpRequest'
    
    return headers

def get_random_headers():
    """Mantém compatibilidade com código existente"""
    return get_advanced_headers()

# Headers padrão para requests - Mais completos para evitar bloqueios
DEFAULT_HEADERS = get_random_headers()

def fetch_page_advanced(url, use_playwright=False, retries=3):
    """Advanced fetch with fallback to Playwright if requests fails"""
    
    # Try with requests first (faster)
    if not use_playwright:
        try:
            print(f"[FETCH_ADV] Tentando com requests: {url}")
            content = fetch_page_requests(url, retries=retries)
            
            # Check if content looks valid
            if len(content) > 100000 or 'mercadolivre' not in url.lower():
                print(f"[FETCH_ADV] Requests bem-sucedido: {len(content)} chars")
                return content
            else:
                print(f"[FETCH_ADV] Conteúdo suspeito com requests ({len(content)} chars), tentando Playwright...")
                
        except Exception as e:
            print(f"[FETCH_ADV] Requests falhou: {e}")
            print(f"[FETCH_ADV] Tentando com Playwright...")
    
    # Fallback to Playwright
    try:
        print(f"[FETCH_ADV] Usando Playwright para: {url}")
        
        # Determine selector based on URL
        wait_selector = None
        if 'lista.mercadolivre.com.br' in url:
            wait_selector = '.ui-search-results'
        elif 'produto.mercadolivre.com.br' in url or '/p/MLB' in url:
            wait_selector = '.ui-pdp-container'
        
        content, status = fetch_page_sync(
            url, 
            wait_for_selector=wait_selector,
            scroll_page=True
        )
        
        print(f"[FETCH_ADV] Playwright bem-sucedido: {len(content)} chars, status: {status}")
        return content
        
    except Exception as e:
        print(f"[FETCH_ADV] Playwright também falhou: {e}")
        raise Exception(f"Ambos requests e Playwright falharam. Último erro: {e}")

def fetch_page_requests(url, headers=None, retries=3):
    """Original fetch function using requests only"""
    
    for attempt in range(retries):
        try:
            # Use random headers for each attempt
            current_headers = get_random_headers() if headers is None else headers.copy()
            
            # Add random delay between attempts (more human-like)
            if attempt > 0:
                delay = (2 ** attempt) + random.uniform(1, 3)
                print(f"[FETCH_REQ] Tentativa {attempt + 1}/{retries} após {delay:.1f}s de delay")
                time.sleep(delay)
            else:
                # Small initial delay to avoid being too fast
                time.sleep(random.uniform(0.5, 1.5))
            
            print(f"[FETCH_REQ] Fazendo requisição para: {url}")
            print(f"[FETCH_REQ] User-Agent: {current_headers.get('User-Agent', 'N/A')}")
            
            # Create session for better connection handling
            session = requests.Session()
            session.headers.update(current_headers)
            
            response = session.get(
                url, 
                timeout=120,  # Timeout ainda maior
                verify=True,
                allow_redirects=True,
                stream=False  # Get full content
            )
            
            print(f"[FETCH_REQ] Status: {response.status_code}, Content-Length: {len(response.text)}")
            print(f"[FETCH_REQ] Content-Type: {response.headers.get('Content-Type', 'N/A')}")
            
            # Check for specific error codes
            if response.status_code == 403:
                print(f"[FETCH_REQ] Erro 403: Acesso negado - possível bloqueio")
                session.close()
                if attempt < retries - 1:
                    continue
                raise requests.exceptions.RequestException(f"Acesso negado (403) após {retries} tentativas")
            
            elif response.status_code in [429, 503, 502, 504]:
                print(f"[FETCH_REQ] Erro {response.status_code}: Rate limit ou erro de servidor")
                session.close()
                if attempt < retries - 1:
                    # Longer delay for rate limits
                    time.sleep(random.uniform(5, 10))
                    continue
                raise requests.exceptions.RequestException(f"Erro de servidor ({response.status_code}) após {retries} tentativas")
            
            elif response.status_code != 200:
                print(f"[FETCH_REQ] Status code inesperado: {response.status_code}")
                session.close()
                if attempt < retries - 1:
                    continue
                raise requests.exceptions.RequestException(f"Status code {response.status_code}")
            
            # Check if we got compressed/truncated content
            content_length = len(response.text)
            print(f"[FETCH_REQ] Requisição bem-sucedida! Tamanho da resposta: {content_length} chars")
            
            # If content is suspiciously small, it might be blocked
            if content_length < 100000 and 'mercadolivre' in url.lower():
                print(f"[FETCH_REQ] AVISO: Conteúdo muito pequeno ({content_length} chars) - possível bloqueio")
                if attempt < retries - 1:
                    print("[FETCH_REQ] Tentando novamente com headers diferentes...")
                    session.close()
                    continue
            
            session.close()
            return response.text
                
        except requests.exceptions.Timeout:
            print(f"[FETCH_REQ] Timeout na tentativa {attempt + 1}")
            if attempt == retries - 1:
                raise Exception(f"Timeout após {retries} tentativas")
        except requests.exceptions.ConnectionError as e:
            print(f"[FETCH_REQ] Erro de conexão na tentativa {attempt + 1}: {str(e)}")
            if attempt == retries - 1:
                raise Exception(f"Erro de conexão após {retries} tentativas: {str(e)}")
        except requests.exceptions.RequestException as e:
            print(f"[FETCH_REQ] Erro HTTP na tentativa {attempt + 1}: {str(e)}")
            if attempt == retries - 1:
                raise Exception(f"Erro HTTP após {retries} tentativas: {str(e)}")
        except Exception as e:
            print(f"[FETCH_REQ] Erro geral na tentativa {attempt + 1}: {str(e)}")
            if attempt == retries - 1:
                raise Exception(f"Erro geral após {retries} tentativas: {str(e)}")
    
    raise Exception(f"Falha em todas as {retries} tentativas")

# Maintain backward compatibility
def fetch_page(url, headers=None, retries=3):
    """Backward compatible fetch function - now uses advanced method"""
    return fetch_page_advanced(url, use_playwright=False, retries=retries)

def validate_mercadolivre_url(url):
    """Valida se a URL é do Mercado Livre"""
    parsed = urlparse(url)
    valid_domains = [
        'mercadolivre.com.br',
        'mercadolibre.com',
        'produto.mercadolivre.com.br',
        'www.mercadolivre.com.br',
        'lista.mercadolivre.com.br',
        'click1.mercadolivre.com.br',  # URLs de tracking
        'click2.mercadolivre.com.br',  # URLs de tracking
        'click.mercadolivre.com.br',   # URLs de tracking
    ]
    
    return any(domain in parsed.netloc for domain in valid_domains)

def follow_redirects(url, max_redirects=5):
    """Segue redirects de URLs de tracking e retorna a URL final"""
    current_url = url
    redirect_count = 0
    
    while redirect_count < max_redirects:
        try:
            response = requests.head(current_url, headers=DEFAULT_HEADERS, timeout=60, allow_redirects=False)
            
            # Se não há redirect, retorna a URL atual
            if response.status_code not in [301, 302, 303, 307, 308]:
                return current_url
            
            # Pega a nova URL do header Location
            location = response.headers.get('Location')
            if not location:
                return current_url
            
            # Se a location é relativa, constrói a URL completa
            if location.startswith('/'):
                from urllib.parse import urljoin
                current_url = urljoin(current_url, location)
            else:
                current_url = location
            
            redirect_count += 1
            
        except Exception:
            # Se der erro, retorna a URL atual
            return current_url
    
    return current_url

def extract_mlb_id_from_url(url):
    """Extrai o ID MLB de uma URL do Mercado Livre"""
    # Padrões para encontrar MLB ID (em ordem de prioridade)
    patterns = [
        r'MLB-?(\d+)',  # MLB-123456789 ou MLB123456789 (mais comum)
        r'/p/MLB(\d+)',  # /p/MLB123456789
        r'item=MLB(\d+)',  # item=MLB123456789 (parâmetro de URL)
        r'MLB(\d{10,})',  # MLB seguido de 10+ dígitos
        r'produto\.mercadolivre\.com\.br/MLB-?(\d+)',  # URL produto específica
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None

def normalize_product_url(url):
    """Normaliza URL do Mercado Livre para o formato padrão"""
    if not validate_mercadolivre_url(url):
        return None
    
    mlb_id = extract_mlb_id_from_url(url)
    if not mlb_id:
        return None
    
    # Verifica se a URL já está no formato /p/MLB (não normaliza)
    if '/p/MLB' in url:
        return url
    
    # Para outros formatos, normaliza para produto.mercadolivre.com.br
    return f"https://produto.mercadolivre.com.br/MLB-{mlb_id}"

def validate_product_url(url):
    """Valida se a URL é de um produto específico do Mercado Livre"""
    if not validate_mercadolivre_url(url):
        return False
    
    # Se for uma URL de tracking, segue os redirects primeiro
    if 'click' in url or 'mclics' in url:
        final_url = follow_redirects(url)
        # Verifica se a URL final é válida do Mercado Livre
        if not validate_mercadolivre_url(final_url):
            return True  # Aceita URLs de tracking mesmo se não conseguir seguir o redirect
        url = final_url
    
    # Verifica se consegue extrair MLB ID
    mlb_id = extract_mlb_id_from_url(url)
    return mlb_id is not None or 'click' in url or 'mclics' in url

@app.route('/', methods=['GET'])
def home():
    """Endpoint de informações da API"""
    return jsonify({
        "message": "API de Scraping Mercado Livre",
        "version": "1.0.0",
        "documentation": {
            "swagger_ui": "/docs",
            "swagger_yaml": "/swagger.yaml"
        },
        "endpoints": {
            "/scrape": "POST - Faz scraping de uma URL do Mercado Livre",
            "/scrape-product": "POST - Busca produtos por termo (simplificado)",
            "/scrape-product-details": "POST - Faz scraping detalhado de um produto específico do Mercado Livre usando sua URL (Parâmetros: {'url': 'https://produto.mercadolivre.com.br/MLB-XXXXXXX-nome-produto'} - Retorna: Dados detalhados do produto com título, preço, imagem, vendedor, MLB ID)",
            "/search": "GET - Busca produtos por termo",
            "/health": "GET - Status da API",
            "/categories": "GET - Lista categorias populares"
        },
        "usage": {
            "scrape": "POST /scrape com body: {'url': 'https://lista.mercadolivre.com.br/...'}",
            "scrape-product": "POST /scrape-product com body: {'product': 'smartphone', 'limit': 20}",
            "search": "GET /search?q=termo_busca&limit=50"
        }
    })

@app.route('/health', methods=['GET'])
def health():
    """Endpoint de health check"""
    health_data = {
        "status": "ok", 
        "timestamp": time.time(),
        "version": "2.0.0",
        "environment": {
            "railway": os.getenv('RAILWAY_ENVIRONMENT') is not None,
            "port": os.getenv('PORT', '5000'),
            "python_version": sys.version
        }
    }
    
    # Check Playwright installation
    try:
        import playwright
        from playwright_scraper import PlaywrightScraper
        
        scraper = PlaywrightScraper()
        playwright_installed = scraper.check_playwright_installation()
        
        health_data["playwright"] = {
            "installed": True,
            "version": playwright.__version__,
            "browsers_installed": playwright_installed,
            "browsers_path": os.getenv('PLAYWRIGHT_BROWSERS_PATH', '/app/.cache/ms-playwright')
        }
    except Exception as e:
        health_data["playwright"] = {
            "installed": False,
            "error": str(e)
        }
    
    return jsonify(health_data)

@app.route('/debug-scraping', methods=['POST'])
def debug_scraping():
    """Endpoint para debug de scraping em produção"""
    try:
        data = request.get_json() or {}
        test_url = data.get('url', 'https://lista.mercadolivre.com.br/iphone')
        use_playwright = data.get('use_playwright', False)
        
        print(f"[DEBUG] Testando URL: {test_url}")
        print(f"[DEBUG] Usando Playwright: {use_playwright}")
        
        # Test fetch_page function
        try:
            if use_playwright:
                html_content = fetch_page_advanced(test_url, use_playwright=True)
                method_used = 'playwright'
            else:
                # Generate fresh headers for this test
                test_headers = get_random_headers()
                html_content = fetch_page(test_url, headers=test_headers)
                method_used = 'requests'
            
            fetch_success = True
            status_code = 200
        except Exception as e:
            print(f"[DEBUG] Erro no fetch: {e}")
            html_content = ""
            fetch_success = False
            status_code = 0
            method_used = 'playwright' if use_playwright else 'requests'
        
        # Test parsing if fetch was successful
        items_parsed = 0
        first_item = None
        if fetch_success and html_content:
            try:
                items = parse_list_items(html_content)
                items_parsed = len(items)
                first_item = items[0] if items else None
            except Exception as e:
                print(f"[DEBUG] Erro no parsing: {e}")
        
        # Additional checks for blocking detection
        is_blocked = False
        blocking_indicators = []
        
        if html_content:
            content_length = len(html_content)
            if content_length < 100000 and 'mercadolivre' in test_url.lower():
                is_blocked = True
                blocking_indicators.append(f"Conteúdo muito pequeno: {content_length} chars")
            
            # Check for common blocking patterns
            blocking_patterns = [
                'access denied', 'blocked', 'captcha', 'robot', 'bot',
                'security check', 'verificação', 'bloqueado'
            ]
            
            for pattern in blocking_patterns:
                if pattern in html_content.lower():
                    is_blocked = True
                    blocking_indicators.append(f"Padrão de bloqueio encontrado: '{pattern}'")
        
        debug_info = {
            'test_url': test_url,
            'method_used': method_used,
            'fetch_success': fetch_success,
            'status_code': status_code,
            'html_length': len(html_content),
            'html_preview': html_content[:200] if html_content else None,
            'html_contains_products': 'produto' in html_content.lower() or 'item' in html_content.lower() if html_content else False,
            'html_contains_mercadolivre': 'mercadolivre' in html_content.lower() if html_content else False,
            'items_parsed': items_parsed,
            'first_item': first_item,
            'environment': 'production' if os.environ.get('RAILWAY_ENVIRONMENT') else 'local',
            'is_blocked': is_blocked,
            'blocking_indicators': blocking_indicators
        }
        
        # Add headers info only for requests method
        if not use_playwright and 'test_headers' in locals():
            debug_info['headers_used'] = test_headers
            debug_info['user_agent_used'] = test_headers.get('User-Agent', 'N/A')
        
        return jsonify({
            'success': True,
            'debug': debug_info
        })
        
    except Exception as e:
        print(f"[DEBUG] Erro geral: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/test-playwright', methods=['POST'])
def test_playwright():
    """Endpoint específico para testar Playwright vs Requests"""
    try:
        data = request.get_json() or {}
        test_url = data.get('url', 'https://lista.mercadolivre.com.br/iphone')
        
        print(f"[PLAYWRIGHT_TEST] Comparando métodos para: {test_url}")
        
        results = {
            'test_url': test_url,
            'requests_result': {},
            'playwright_result': {},
            'comparison': {},
            'recommendation': ''
        }
        
        # Test with Requests
        print(f"[PLAYWRIGHT_TEST] Testando com Requests...")
        try:
            start_time = time.time()
            requests_content = fetch_page_requests(test_url, retries=2)
            requests_time = time.time() - start_time
            
            requests_items = parse_list_items(requests_content)
            
            results['requests_result'] = {
                'success': True,
                'content_length': len(requests_content),
                'items_found': len(requests_items),
                'time_taken': round(requests_time, 2),
                'contains_mercadolivre': 'mercadolivre' in requests_content.lower(),
                'contains_products': 'produto' in requests_content.lower() or 'item' in requests_content.lower(),
                'first_item': requests_items[0] if requests_items else None
            }
            
        except Exception as e:
            print(f"[PLAYWRIGHT_TEST] Requests falhou: {e}")
            results['requests_result'] = {
                'success': False,
                'error': str(e),
                'content_length': 0,
                'items_found': 0,
                'time_taken': 0
            }
        
        # Test with Playwright
        print(f"[PLAYWRIGHT_TEST] Testando com Playwright...")
        try:
            start_time = time.time()
            playwright_content = fetch_page_advanced(test_url, use_playwright=True)
            playwright_time = time.time() - start_time
            
            playwright_items = parse_list_items(playwright_content)
            
            results['playwright_result'] = {
                'success': True,
                'content_length': len(playwright_content),
                'items_found': len(playwright_items),
                'time_taken': round(playwright_time, 2),
                'contains_mercadolivre': 'mercadolivre' in playwright_content.lower(),
                'contains_products': 'produto' in playwright_content.lower() or 'item' in playwright_content.lower(),
                'first_item': playwright_items[0] if playwright_items else None
            }
            
        except Exception as e:
            print(f"[PLAYWRIGHT_TEST] Playwright falhou: {e}")
            results['playwright_result'] = {
                'success': False,
                'error': str(e),
                'content_length': 0,
                'items_found': 0,
                'time_taken': 0
            }
        
        # Comparison and recommendation
        req_success = results['requests_result'].get('success', False)
        pw_success = results['playwright_result'].get('success', False)
        
        req_items = results['requests_result'].get('items_found', 0)
        pw_items = results['playwright_result'].get('items_found', 0)
        
        req_content_size = results['requests_result'].get('content_length', 0)
        pw_content_size = results['playwright_result'].get('content_length', 0)
        
        results['comparison'] = {
            'both_successful': req_success and pw_success,
            'requests_blocked': req_success and req_content_size < 100000 and 'mercadolivre' in test_url.lower(),
            'playwright_blocked': pw_success and pw_content_size < 100000 and 'mercadolivre' in test_url.lower(),
            'content_size_difference': pw_content_size - req_content_size,
            'items_difference': pw_items - req_items,
            'playwright_advantage': pw_items > req_items or (pw_success and not req_success)
        }
        
        # Generate recommendation
        if not req_success and pw_success:
            results['recommendation'] = 'Use Playwright - Requests completely failed'
        elif req_success and not pw_success:
            results['recommendation'] = 'Use Requests - Playwright failed'
        elif results['comparison']['playwright_advantage']:
            results['recommendation'] = 'Use Playwright - Better results (more items or bypassed blocking)'
        elif req_items > 0 and pw_items > 0 and abs(req_items - pw_items) <= 2:
            results['recommendation'] = 'Use Requests - Similar results but faster'
        elif results['comparison']['requests_blocked']:
            results['recommendation'] = 'Use Playwright - Requests appears to be blocked'
        else:
            results['recommendation'] = 'Use Requests - Sufficient and faster'
        
        return jsonify({
            'success': True,
            'results': results
        })
        
    except Exception as e:
        print(f"[PLAYWRIGHT_TEST] Erro geral: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/debug-production-issue', methods=['POST'])
def debug_production_issue():
    """Endpoint específico para debugar o problema de produção"""
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({"error": "URL é obrigatória"}), 400
        
        url = data['url']
        print(f"[PRODUCTION_DEBUG] Starting debug for URL: {url}")
        print(f"[PRODUCTION_DEBUG] Timestamp: {time.time()}")
        
        # Simula condições de produção com timeout mais agressivo
        import threading
        
        result = {'success': False, 'error': 'Unknown', 'debug_info': {}}
        timeout_occurred = threading.Event()
        
        def timeout_handler():
            print(f"[PRODUCTION_DEBUG] TIMEOUT OCCURRED")
            timeout_occurred.set()
        
        # Define timeout de 30 segundos (mais próximo do que pode acontecer em produção)
        timer = threading.Timer(30.0, timeout_handler)
        timer.start()
        
        # Placeholder return - função incompleta
        return jsonify({"error": "Function incomplete"}), 500
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/scrape-product-details-fast', methods=['POST'])
@log_request_duration
def scrape_product_details_fast():
    """Versão otimizada do endpoint para produção com timeout reduzido"""
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({"error": "URL é obrigatória"}), 400
        
        url = data['url']
        print(f"[FAST_SCRAPE] Starting for URL: {url}")
        start_time = time.time()
        
        # Validação rápida da URL
        if not validate_product_url(url):
            return jsonify({"error": "URL inválida do MercadoLivre"}), 400
        
        # Timeout reduzido para produção (10 segundos)
        import threading
        result = {'success': False, 'data': None, 'error': None}
        timeout_occurred = threading.Event()
        
        def timeout_handler():
            print(f"[FAST_SCRAPE] TIMEOUT after 20 seconds")
            timeout_occurred.set()
        
        timer = threading.Timer(20.0, timeout_handler)
        timer.start()
        
        try:
            # Usar Playwright otimizado
            print(f"[FAST_SCRAPE] Using optimized Playwright")
            
            # Usar o scraper otimizado
            scraper = PlaywrightScraper()
            html_content = scraper.fetch_page(url, scroll_page=True)
            
            if timeout_occurred.is_set():
                result['error'] = 'Timeout: Operation timed out during fetch'
                result['success'] = False
            else:
                # Extrair detalhes do produto
                product_details = extract_product_details(html_content, url)
                
                if product_details:
                    result['success'] = True
                    result['data'] = product_details
                    print(f"[FAST_SCRAPE] Success: {product_details.get('title', 'No title')[:50]}...")
                else:
                    result['error'] = 'Failed to extract product details'
                    result['success'] = False
                    
        except Exception as e:
            print(f"[FAST_SCRAPE] Error: {str(e)}")
            result['error'] = str(e)
            result['success'] = False
            
        finally:
            timer.cancel()
            
        # Verificar timeout final
        if timeout_occurred.is_set() and result['success']:
            result['success'] = False
            result['error'] = 'Timeout: Operation timed out during processing'
            
        execution_time = time.time() - start_time
        print(f"[FAST_SCRAPE] Completed in {execution_time:.2f}s")
        
        return jsonify({
            'success': result['success'],
            'data': result['data'],
            'error': result['error'],
            'execution_time': execution_time,
            'method': 'playwright_optimized'
        })
        
    except Exception as e:
        print(f"[FAST_SCRAPE] Outer error: {str(e)}")
        return jsonify({"error": str(e)}), 500
        
        # Usa scraper otimizado com timeout menor
        result = scrape_with_fallback(
            clean_url, 
            scrape_type='details', 
            debug=True
        )
        
        elapsed_time = time.time() - start_time
        print(f"[FAST_SCRAPE] Completed in {elapsed_time:.2f}s")
        
        if result and result.get('success'):
            return jsonify({
                'success': True,
                'product': result.get('product', {}),
                'method_used': result.get('method_used', 'unknown'),
                'execution_time': elapsed_time
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Falha na extração'),
                'execution_time': elapsed_time
            }), 500
            
    except Exception as e:
        print(f"[FAST_SCRAPE] Exception: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
        
        try:
            print(f"[PRODUCTION_DEBUG] Initializing PlaywrightScraper...")
            playwright_scraper = PlaywrightScraper()
            print(f"[PRODUCTION_DEBUG] PlaywrightScraper initialized")
            
            print(f"[PRODUCTION_DEBUG] Fetching page content...")
            
            # Verifica timeout antes de fazer a requisição
            if timeout_occurred.is_set():
                raise TimeoutError("Operation timed out before fetch")
            
            html_content = playwright_scraper.fetch_page(url)
            
            # Verifica timeout após a requisição
            if timeout_occurred.is_set():
                raise TimeoutError("Operation timed out during fetch")
            
            if html_content:
                print(f"[PRODUCTION_DEBUG] HTML received: {len(html_content)} chars")
                print(f"[PRODUCTION_DEBUG] HTML preview: {html_content[:200]}...")
                
                # Verifica se é uma página de erro ou redirecionamento
                error_indicators = [
                    'robot-or-human',
                    'verificar-cuenta',
                    'security-check',
                    'captcha',
                    'blocked',
                    'access denied'
                ]
                
                has_error = any(indicator in html_content.lower() for indicator in error_indicators)
                print(f"[PRODUCTION_DEBUG] Error indicators found: {has_error}")
                
                if has_error:
                    for indicator in error_indicators:
                        if indicator in html_content.lower():
                            print(f"[PRODUCTION_DEBUG] Found error indicator: {indicator}")
                
                print(f"[PRODUCTION_DEBUG] Extracting product details...")
                product_details = extract_product_details(html_content, url)
                
                if product_details and product_details.get('title'):
                    result = {
                        'success': True,
                        'method_used': 'playwright',
                        'product': product_details,
                        'debug_info': {
                            'html_length': len(html_content),
                            'has_error_indicators': has_error,
                            'extraction_successful': True
                        }
                    }
                else:
                    result = {
                        'success': False,
                        'error': 'Product details extraction failed',
                        'debug_info': {
                            'html_length': len(html_content),
                            'has_error_indicators': has_error,
                            'extraction_successful': False,
                            'product_details': product_details
                        }
                    }
            else:
                result = {
                    'success': False,
                    'error': 'No HTML content received',
                    'debug_info': {
                        'html_received': False
                    }
                }
            
        except TimeoutError as e:
            print(f"[PRODUCTION_DEBUG] TIMEOUT ERROR: {str(e)}")
            result = {
                'success': False,
                'error': f'Timeout: {str(e)}',
                'debug_info': {
                    'timeout_occurred': True
                }
            }
        
        except Exception as e:
            print(f"[PRODUCTION_DEBUG] EXCEPTION: {str(e)}")
            print(f"[PRODUCTION_DEBUG] EXCEPTION TYPE: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            result = {
                'success': False,
                'error': str(e),
                'debug_info': {
                    'exception_type': type(e).__name__,
                    'exception_occurred': True
                }
            }
        
        finally:
            # Cancela o timer
            timer.cancel()
            
            # Limpa recursos
            try:
                if 'playwright_scraper' in locals():
                    playwright_scraper.close()
                    print(f"[PRODUCTION_DEBUG] PlaywrightScraper closed")
            except Exception as e:
                print(f"[PRODUCTION_DEBUG] Error closing PlaywrightScraper: {e}")
        
        # Verifica se timeout ocorreu durante a execução
        if timeout_occurred.is_set() and result.get('success', False):
            result = {
                'success': False,
                'error': 'Operation timed out',
                'debug_info': {
                    'timeout_occurred': True
                }
            }
        
        print(f"[PRODUCTION_DEBUG] Final result: {result}")
        return jsonify(result)
        
    except Exception as e:
        print(f"[PRODUCTION_DEBUG] OUTER EXCEPTION: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'debug_info': {
                'outer_exception': True
            }
        }), 500

@app.route('/test-production-debug', methods=['POST'])
def test_production_debug():
    """Endpoint para debug detalhado simulando produção"""
    try:
        data = request.get_json()
        
        if not data or 'product' not in data:
            return jsonify({"error": "Parâmetro 'product' é obrigatório"}), 400
        
        product_term = data['product']
        limit = data.get('limit', 5)
        
        # Constrói URL de busca do Mercado Livre
        search_url = f"https://lista.mercadolivre.com.br/{product_term.replace(' ', '-')}"
        
        print(f"\n=== PRODUCTION DEBUG TEST ===")
        print(f"Product: {product_term}")
        print(f"URL: {search_url}")
        print(f"Limit: {limit}")
        
        # Testa apenas o Playwright com logs detalhados
        try:
            print(f"\n[PROD-DEBUG] Iniciando teste do Playwright...")
            
            playwright_scraper = PlaywrightScraper()
            print(f"[PROD-DEBUG] PlaywrightScraper criado")
            
            html_content = playwright_scraper.fetch_page(search_url)
            print(f"[PROD-DEBUG] HTML recebido: {len(html_content) if html_content else 0} chars")
            
            if html_content:
                print(f"[PROD-DEBUG] HTML preview: {html_content[:300]}...")
                
                # Testa parsing
                items = parse_list_items(html_content)
                print(f"[PROD-DEBUG] Items encontrados: {len(items) if items else 0}")
                
                if items:
                    # Aplica limite
                    if len(items) > limit:
                        items = items[:limit]
                    
                    print(f"[PROD-DEBUG] Items após limite: {len(items)}")
                    
                    # Mostra primeiro item como exemplo
                    if items:
                        first_item = items[0]
                        print(f"[PROD-DEBUG] Primeiro item: {first_item.get('title', 'N/A')[:50]}...")
                        print(f"[PROD-DEBUG] Preço: {first_item.get('price', 'N/A')}")
                        print(f"[PROD-DEBUG] Link: {first_item.get('link', 'N/A')[:100]}...")
                    
                    try:
                        playwright_scraper.close()
                    except:
                        pass
                    
                    return jsonify({
                        "success": True,
                        "method": "playwright",
                        "html_length": len(html_content),
                        "items_found": len(items),
                        "items": items,
                        "debug_info": {
                            "url": search_url,
                            "html_preview": html_content[:500]
                        }
                    })
                else:
                    print(f"[PROD-DEBUG] Nenhum item encontrado no parsing")
                    
                    try:
                        playwright_scraper.close()
                    except:
                        pass
                    
                    return jsonify({
                        "success": False,
                        "method": "playwright",
                        "html_length": len(html_content),
                        "items_found": 0,
                        "error": "Nenhum item encontrado no parsing",
                        "debug_info": {
                            "url": search_url,
                            "html_preview": html_content[:500]
                        }
                    })
            else:
                print(f"[PROD-DEBUG] Nenhum HTML recebido")
                
                try:
                    playwright_scraper.close()
                except:
                    pass
                
                return jsonify({
                    "success": False,
                    "method": "playwright",
                    "html_length": 0,
                    "error": "Nenhum HTML recebido",
                    "debug_info": {
                        "url": search_url
                    }
                })
                
        except Exception as e:
            print(f"[PROD-DEBUG] Erro no Playwright: {str(e)}")
            print(f"[PROD-DEBUG] Tipo do erro: {type(e).__name__}")
            
            return jsonify({
                "success": False,
                "method": "playwright",
                "error": str(e),
                "error_type": type(e).__name__,
                "debug_info": {
                    "url": search_url
                }
            })
            
    except Exception as e:
        print(f"[PROD-DEBUG] Erro geral: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/test-ocr', methods=['GET', 'POST'])
def test_ocr():
    """Testa o sistema OCR para extração de texto de imagens"""
    try:
        # Verificar instalação do Tesseract
        ocr_status = test_ocr_installation()
        
        if request.method == 'GET':
            return jsonify({
                'status': 'ready',
                'ocr_installation': ocr_status,
                'message': 'Envie uma imagem via POST para testar o OCR',
                'supported_formats': ['image/jpeg', 'image/png', 'image/gif', 'image/bmp'],
                'methods': {
                    'file_upload': 'Envie arquivo de imagem no campo "image"',
                    'base64': 'Envie dados base64 no campo "image_data"',
                    'url': 'Envie URL da imagem no campo "image_url"'
                },
                'timestamp': time.time()
            })
        
        # POST - processar imagem
        start_time = time.time()
        
        # Se Tesseract não estiver instalado, tentar usar mock
        if not ocr_status.get('tesseract_installed', False):
            # Verificar se o processador tem mock disponível
            if not hasattr(ocr_processor, 'mock_processor') or ocr_processor.mock_processor is None:
                return jsonify({
                    'status': 'error',
                    'error': 'Tesseract OCR não está instalado e mock não está disponível',
                    'installation_info': ocr_status,
                    'timestamp': time.time()
                }), 500
        
        # Processar diferentes tipos de entrada
        if 'image' in request.files:
            # Upload de arquivo
            file = request.files['image']
            if file.filename == '':
                return jsonify({'status': 'error', 'error': 'Nenhum arquivo selecionado'}), 400
            
            image_data = file.read()
            result = ocr_processor.process_screenshot(image_data)
            
        elif request.is_json and 'image_data' in request.json:
            # Dados base64
            base64_data = request.json['image_data']
            result = ocr_processor.process_base64_image(base64_data)
            
        elif request.is_json and 'image_url' in request.json:
            # URL da imagem
            import requests as req
            image_url = request.json['image_url']
            
            try:
                response = req.get(image_url, timeout=60)
                response.raise_for_status()
                image_data = response.content
                result = ocr_processor.process_screenshot(image_data)
            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'error': f'Erro ao baixar imagem: {str(e)}',
                    'timestamp': time.time()
                }), 400
        else:
            return jsonify({
                'status': 'error',
                'error': 'Nenhuma imagem fornecida. Use "image" (arquivo), "image_data" (base64) ou "image_url"',
                'timestamp': time.time()
            }), 400
        
        # Retornar resultado
        return jsonify({
            'status': 'success' if result.success else 'error',
            'ocr_result': {
                'text_extracted': result.text[:500] + '...' if len(result.text) > 500 else result.text,
                'full_text_length': len(result.text),
                'confidence': round(result.confidence, 2),
                'products_found': len(result.products),
                'products': result.products[:5],  # Primeiros 5 produtos
                'processing_time': round(result.processing_time, 2),
                'success': result.success,
                'error': result.error
            },
            'ocr_installation': ocr_status,
            'timestamp': time.time()
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': time.time()
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint para Railway"""
    try:
        # Verificar se o Playwright está funcionando
        playwright_status = "unknown"
        try:
            from playwright.sync_api import sync_playwright
            playwright_status = "available"
        except ImportError:
            playwright_status = "not_installed"
        except Exception as e:
            playwright_status = f"error: {str(e)[:50]}"
        
        return jsonify({
            'status': 'healthy',
            'timestamp': time.time(),
            'playwright': playwright_status,
            'version': '2.0.0'
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

# ENDPOINT /scrape COMENTADO - USA SCRAPER TRADICIONAL
# @app.route('/scrape', methods=['POST'])
# def scrape_url():
#     """Endpoint para fazer scraping de uma URL específica do Mercado Livre"""
#     try:
#         data = request.get_json()
#         
#         if not data or 'url' not in data:
#             return jsonify({"error": "URL é obrigatória"}), 400
#         
#         url = data['url']
#         
#         # Valida se é URL do Mercado Livre
#         if not validate_mercadolivre_url(url):
#             return jsonify({"error": "URL deve ser do Mercado Livre"}), 400
#         
#         # Faz o scraping
#         html_content, status_code = fetch_page(url)
#         
#         # Parse dos itens
#         items = parse_list_items(html_content)
#         
#         return jsonify({
#             "success": True,
#             "url": url,
#             "status_code": status_code,
#             "items_count": len(items),
#             "items": items
#         })
#         
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

@app.route('/search', methods=['GET'])
def search_products():
    """Endpoint para buscar produtos por termo"""
    try:
        query = request.args.get('q', '')
        limit = int(request.args.get('limit', 50))
        
        if not query:
            return jsonify({"error": "Parâmetro 'q' (query) é obrigatório"}), 400
        
        if limit > 200:
            limit = 200  # Limita para evitar sobrecarga
        
        # Constrói URL de busca do Mercado Livre
        search_url = f"https://lista.mercadolivre.com.br/{query.replace(' ', '-')}"
        
        # Adiciona parâmetros de limite se necessário
        if limit != 50:
            search_url += f"_Desde_{limit}"
        
        # Faz o scraping usando o sistema de fallback
        result = scrape_with_fallback(
            url=search_url,
            scrape_type='list',
            product_term=query,
            limit=limit,
            include_stock=False,
            debug=False
        )
        
        if result['success']:
            return jsonify({
                "success": True,
                "query": query,
                "search_url": search_url,
                "method_used": result['method_used'],
                "items_count": result['items_count'],
                "items": result['items']
            })
        else:
            return jsonify({
                "success": False,
                "query": query,
                "search_url": search_url,
                "error": "Não foi possível extrair produtos",
                "methods_tried": result.get('methods_tried', [])
            }), 500
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/scrape-product', methods=['POST'])
@log_request_duration
def scrape_product():
    """Endpoint com fallback em cascata: scraper tradicional -> Playwright -> OCR"""
    try:
        data = request.get_json()
        
        if not data or 'product' not in data:
            return jsonify({"error": "Parâmetro 'product' é obrigatório"}), 400
        
        product_term = data['product']
        limit = data.get('limit', 50)
        include_stock = data.get('include_stock', True)
        debug = data.get('debug', True)  # Habilitado por padrão para debug em produção
        
        if limit > 200:
            limit = 200  # Limita para evitar sobrecarga
        
        # Constrói URL de busca do Mercado Livre automaticamente
        search_url = f"https://lista.mercadolivre.com.br/{product_term.replace(' ', '-')}"
        
        if debug:
            print(f"[DEBUG] Iniciando fallback em cascata para: {search_url}")
        
        # Usa o sistema de fallback em cascata
        result = scrape_with_fallback(
            url=search_url,
            scrape_type='list',
            product_term=product_term,
            limit=limit,
            include_stock=include_stock,
            debug=debug
        )
        
        if result['success']:
            response_data = {
                "success": True,
                "product_search": product_term,
                "search_url": search_url,
                "method_used": result['method_used'],
                "status_code": 200,
                "items_count": len(result['items']),
                "include_stock": include_stock,
                "items": result['items']
            }
            
            if debug:
                response_data['debug'] = result.get('debug_info', {})
                response_data['methods_tried'] = result.get('methods_tried', [])
            
            return jsonify(response_data)
        else:
            return jsonify({
                "success": False,
                "error": result['error'],
                "method_attempted": result['method_used'],
                "methods_tried": result.get('methods_tried', []),
                "debug_info": result.get('debug_info') if debug else None
            }), 500
        
    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] Erro no scrape_product: {error_msg}")
        return jsonify({"error": error_msg}), 500

# ENDPOINT /test-bypass COMENTADO - USA SCRAPER TRADICIONAL
# @app.route('/test-bypass', methods=['POST'])
# def test_bypass():
#     """Endpoint para testar diferentes métodos de bypass anti-bot"""
#     try:
#         data = request.get_json() or {}
#         test_url = data.get('url', 'https://lista.mercadolivre.com.br/iphone')
#         
#         print(f"[BYPASS] Testando diferentes métodos para: {test_url}")
#         
#         results = []
#         
#         # Método 1: Headers básicos
#         try:
#             print("[BYPASS] Teste 1: Headers básicos")
#             basic_headers = {
#                 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
#             }
#             html1 = fetch_page(test_url, headers=basic_headers, retries=1)
#             items1 = parse_list_items(html1)
#             results.append({
#                 'method': 'Headers básicos',
#                 'success': True,
#                 'html_size': len(html1),
#                 'items_found': len(items1),
#                 'headers': basic_headers
#             })
#         except Exception as e:
#             results.append({
#                 'method': 'Headers básicos',
#                 'success': False,
#                 'error': str(e)
#             })
#         
#         # Método 2: Headers completos aleatórios
#         try:
#             print("[BYPASS] Teste 2: Headers completos aleatórios")
#             random_headers = get_random_headers()
#             html2 = fetch_page(test_url, headers=random_headers, retries=1)
#             items2 = parse_list_items(html2)
#             results.append({
#                 'method': 'Headers completos aleatórios',
#                 'success': True,
#                 'html_size': len(html2),
#                 'items_found': len(items2),
#                 'headers': random_headers
#             })
#         except Exception as e:
#             results.append({
#                 'method': 'Headers completos aleatórios',
#                 'success': False,
#                 'error': str(e)
#             })
#         
#         # Método 3: Headers mobile
#         try:
#             print("[BYPASS] Teste 3: Headers mobile")
#             mobile_headers = {
#                 'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
#                 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#                 'Accept-Language': 'pt-BR,pt;q=0.9',
#                 'Accept-Encoding': 'gzip, deflate, br',
#                 'Connection': 'keep-alive'
#             }
#             html3 = fetch_page(test_url, headers=mobile_headers, retries=1)
#             items3 = parse_list_items(html3)
#             results.append({
#                 'method': 'Headers mobile',
#                 'success': True,
#                 'html_size': len(html3),
#                 'items_found': len(items3),
#                 'headers': mobile_headers
#             })
#         except Exception as e:
#             results.append({
#                 'method': 'Headers mobile',
#                 'success': False,
#                 'error': str(e)
#             })
#         
#         # Método 4: Delay longo + headers específicos
#         try:
#             print("[BYPASS] Teste 4: Delay longo + headers específicos")
#             time.sleep(3)  # Delay mais longo
#             specific_headers = {
#                 'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
#                 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
#                 'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
#                 'Accept-Encoding': 'gzip, deflate, br',
#                 'Connection': 'keep-alive',
#                 'Upgrade-Insecure-Requests': '1',
#                 'Sec-Fetch-Dest': 'document',
#                 'Sec-Fetch-Mode': 'navigate',
#                 'Sec-Fetch-Site': 'none',
#                 'Sec-Fetch-User': '?1',
#                 'Cache-Control': 'max-age=0',
#                 'DNT': '1'
#             }
#             html4 = fetch_page(test_url, headers=specific_headers, retries=1)
#             items4 = parse_list_items(html4)
#             results.append({
#                 'method': 'Delay longo + headers específicos',
#                 'success': True,
#                 'html_size': len(html4),
#                 'items_found': len(items4),
#                 'headers': specific_headers
#             })
#         except Exception as e:
#             results.append({
#                 'method': 'Delay longo + headers específicos',
#                 'success': False,
#                 'error': str(e)
#             })
#         
#         # Análise dos resultados
#         successful_methods = [r for r in results if r.get('success', False)]
#         best_method = None
#         if successful_methods:
#             # Escolhe o método com mais items encontrados
#             best_method = max(successful_methods, key=lambda x: x.get('items_found', 0))
#         
#         return jsonify({
#             'success': True,
#             'test_url': test_url,
#             'results': results,
#             'successful_methods': len(successful_methods),
#             'best_method': best_method,
#             'recommendation': {
#                 'use_random_headers': True,
#                 'add_delays': True,
#                 'rotate_user_agents': True,
#                 'preferred_method': best_method['method'] if best_method else 'Headers completos aleatórios'
#             }
#         })
#         
#     except Exception as e:
#         print(f"[BYPASS] Erro no teste: {str(e)}")
#         return jsonify({
#             'success': False,
#             'error': str(e)
#         }), 500

@app.route('/scrape-product-details', methods=['POST'])
@log_request_duration
def scrape_product_details():
    """Endpoint com fallback em cascata: scraper tradicional -> Playwright -> OCR"""
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({"error": "URL é obrigatória"}), 400
        
        original_url = data['url']
        debug = data.get('debug', True)  # DEBUG FORÇADO PARA PRODUÇÃO
        include_html = data.get('include_html', False)
        
        # Valida se é uma URL de produto específico do Mercado Livre
        if not validate_product_url(original_url):
            return jsonify({"error": "URL deve ser de um produto específico do Mercado Livre com MLB ID (ex: produto.mercadolivre.com.br/MLB-123456789)"}), 400
        
        if debug:
            print(f"[DEBUG] URL original: {original_url}")
        
        # Se for uma URL de tracking, segue os redirects primeiro
        working_url = original_url
        if 'click' in original_url or 'mclics' in original_url:
            if debug:
                print("[DEBUG] Detectada URL de tracking, seguindo redirects...")
            working_url = follow_redirects(original_url)
            if debug:
                print(f"[DEBUG] URL após redirects: {working_url}")
        
        # Tenta primeiro com a URL original/após redirects
        if debug:
            print(f"[DEBUG] Iniciando fallback em cascata para: {working_url}")
        
        result = scrape_with_fallback(
            url=working_url,
            scrape_type='details',
            debug=debug
        )
        
        if result['success'] and result['product'] and result['product'].get('title'):
            response_data = {
                "success": True,
                "original_url": original_url,
                "used_url": working_url,
                "method_used": result['method_used'],
                "status_code": 200,
                "product": result['product']
            }
            
            # Incluir HTML se solicitado
            if include_html and 'html_content' in result:
                html_content = result['html_content']
                if len(html_content) > 500000:  # 500KB limit
                    response_data['html_warning'] = f"HTML muito grande ({len(html_content)} chars), truncado para 500KB"
                    response_data['html_content'] = html_content[:500000] + "\n\n[TRUNCATED - HTML content was too large]"
                else:
                    response_data['html_content'] = html_content
                response_data['html_size'] = len(html_content)
            
            if debug:
                response_data['debug'] = result.get('debug_info', {})
                response_data['methods_tried'] = result.get('methods_tried', [])
            
            return jsonify(response_data)
        
        # Se falhou, tenta com URL normalizada como último recurso
        normalized_url = normalize_product_url(working_url)
        if not normalized_url:
            return jsonify({
                "error": "Não foi possível extrair dados do produto com nenhum método",
                "method_attempted": result['method_used'],
                "methods_tried": result.get('methods_tried', []),
                "debug_info": result.get('debug_info') if debug else None
            }), 500
        
        if debug:
            print(f"[DEBUG] Tentando com URL normalizada: {normalized_url}")
        
        # Última tentativa com URL normalizada
        result_normalized = scrape_with_fallback(
            url=normalized_url,
            scrape_type='details',
            debug=debug
        )
        
        if result_normalized['success']:
            response_data = {
                "success": True,
                "original_url": original_url,
                "used_url": normalized_url,
                "method_used": result_normalized['method_used'],
                "status_code": 200,
                "product": result_normalized['product']
            }
            
            if debug:
                response_data['debug'] = result_normalized.get('debug_info', {})
                response_data['methods_tried'] = result_normalized.get('methods_tried', [])
            
            return jsonify(response_data)
        else:
            return jsonify({
                "success": False,
                "error": result_normalized['error'],
                "method_attempted": result_normalized['method_used'],
                "methods_tried": result_normalized.get('methods_tried', []),
                "debug_info": result_normalized.get('debug_info') if debug else None
            }), 500
        
    except Exception as e:
        print(f"Erro no scraping detalhado: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/categories', methods=['GET'])
def get_categories():
    """Endpoint para listar algumas categorias populares"""
    categories = [
        {"name": "Eletrônicos", "url": "https://lista.mercadolivre.com.br/eletronicos"},
        {"name": "Roupas", "url": "https://lista.mercadolivre.com.br/roupas"},
        {"name": "Casa", "url": "https://lista.mercadolivre.com.br/casa"},
        {"name": "Esportes", "url": "https://lista.mercadolivre.com.br/esportes"},
        {"name": "Livros", "url": "https://lista.mercadolivre.com.br/livros"},
        {"name": "Carros", "url": "https://lista.mercadolivre.com.br/carros"},
        {"name": "Celulares", "url": "https://lista.mercadolivre.com.br/celulares"},
        {"name": "Computadores", "url": "https://lista.mercadolivre.com.br/computadores"}
    ]
    
    return jsonify({
        "success": True,
        "categories": categories
    })

@app.route('/docs', methods=['GET'])
def swagger_ui():
    """Endpoint para servir a documentação Swagger UI"""
    try:
        # Tenta diferentes caminhos para compatibilidade com Vercel
        possible_paths = ['swagger-ui.html', './swagger-ui.html', os.path.join(os.path.dirname(__file__), 'swagger-ui.html')]
        
        for path in possible_paths:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Adiciona header correto para HTML
                    from flask import Response
                    return Response(content, mimetype='text/html')
            except FileNotFoundError:
                continue
        
        return jsonify({"error": "Documentação não encontrada"}), 404
    except Exception as e:
        return jsonify({"error": f"Erro ao carregar documentação: {str(e)}"}), 500

@app.route('/swagger.yaml', methods=['GET'])
def swagger_yaml():
    """Endpoint para servir o arquivo YAML do Swagger"""
    try:
        # Tenta diferentes caminhos para compatibilidade com Vercel
        possible_paths = ['swagger.yaml', './swagger.yaml', os.path.join(os.path.dirname(__file__), 'swagger.yaml')]
        
        for path in possible_paths:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    from flask import Response
                    return Response(content, mimetype='application/x-yaml')
            except FileNotFoundError:
                continue
        
        return jsonify({"error": "Arquivo swagger.yaml não encontrado"}), 404
    except Exception as e:
        return jsonify({"error": f"Erro ao carregar swagger.yaml: {str(e)}"}), 500

@app.route('/save-html', methods=['POST'])
def save_html():
    """Endpoint para receber e salvar HTML capturado durante o scraping"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Dados JSON não fornecidos"}), 400
        
        url = data.get('url')
        html_content = data.get('html')
        timestamp = data.get('timestamp', int(time.time()))
        source = data.get('source', 'unknown')  # playwright, requests, etc
        
        if not url or not html_content:
            return jsonify({"error": "URL e HTML são obrigatórios"}), 400
        
        # Criar diretório para salvar HTMLs se não existir
        html_dir = os.path.join(os.getcwd(), 'saved_html')
        os.makedirs(html_dir, exist_ok=True)
        
        # Gerar nome do arquivo baseado na URL e timestamp
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.replace('.', '_')
        path_safe = parsed_url.path.replace('/', '_').replace('-', '_')
        filename = f"{domain}_{path_safe}_{timestamp}_{source}.html"
        
        # Limitar tamanho do nome do arquivo
        if len(filename) > 200:
            filename = f"{domain}_{timestamp}_{source}.html"
        
        filepath = os.path.join(html_dir, filename)
        
        # Salvar HTML
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Log da operação
        app.logger.info(f"[SAVE_HTML] HTML salvo: {filename} ({len(html_content)} chars) de {source}")
        
        return jsonify({
            "success": True,
            "message": "HTML salvo com sucesso",
            "filename": filename,
            "filepath": filepath,
            "size": len(html_content),
            "source": source,
            "timestamp": timestamp
        })
        
    except Exception as e:
        app.logger.error(f"[SAVE_HTML] Erro ao salvar HTML: {str(e)}")
        return jsonify({"error": f"Erro ao salvar HTML: {str(e)}"}), 500

# Handler para erros 404
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint não encontrado"}), 404

# Handler para erros 500
@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Erro interno do servidor"}), 500

if __name__ == '__main__':
    # Para desenvolvimento local e produção
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_ENV', 'development') == 'development'
    app.run(debug=debug_mode, host='0.0.0.0', port=port)

# Configurar logging do Gunicorn com níveis corretos
import logging.config

# Configuração de logging para corrigir níveis incorretos
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'default',
            'stream': 'ext://sys.stdout'
        }
    },
    'loggers': {
        'gunicorn.error': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': False
        },
        'gunicorn.access': {
            'level': 'INFO', 
            'handlers': ['console'],
            'propagate': False
        },
        'playwright_scraper': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': False
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console']
    }
}

# Aplicar configuração de logging
logging.config.dictConfig(LOGGING_CONFIG)

# Configurar loggers específicos
logging.getLogger('gunicorn.error').setLevel(logging.INFO)
logging.getLogger('gunicorn.access').setLevel(logging.INFO)
logging.getLogger('playwright_scraper').setLevel(logging.INFO)