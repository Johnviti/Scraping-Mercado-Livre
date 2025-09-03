# product_scraper.py
# Funções para fazer scraping detalhado de produtos específicos do Mercado Livre

import re
import json
from typing import Dict, Optional

def extract_mlb_id(url: str) -> str:
    """Extrai o ID MLB da URL do produto"""
    mlb_match = re.search(r'MLB-?(\d+)', url)
    if mlb_match:
        return f"MLB{mlb_match.group(1)}"
    else:
        # Se não encontrar um ID MLB válido, gera um placeholder
        import random
        return f"MLB{random.randint(1000000000, 9999999999)}"

def extract_title(html: str) -> str:
    """Extrai o título do produto"""
    patterns = [
        r'<h1[^>]*class="[^"]*ui-pdp-title[^"]*"[^>]*>([^<]+)</h1>',
        r'<meta[^>]*property="og:title"[^>]*content="([^"]+)"',
        r'<title>([^<]+)</title>'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match and match.group(1).strip():
            return match.group(1).strip()
    
    return 'Produto sem título'

def extract_price(html: str) -> Dict[str, float]:
    """Extrai preço e preço promocional do produto"""
    price = 0.0
    promo_price = 0.0
    
    # Tenta extrair preço promocional primeiro
    promo_pattern = r'<span[^>]*class="[^"]*andes-money-amount[^"]*ui-pdp-price__part[^"]*"[^>]*>[\s\S]*?<span[^>]*class="[^"]*andes-money-amount__fraction[^"]*"[^>]*>([\d.,]+)</span>[\s\S]*?<span[^>]*class="[^"]*andes-money-amount__cents[^"]*"[^>]*>([\d.,]+)</span>'
    promo_match = re.search(promo_pattern, html)
    
    # Tenta extrair preço original (para cálculo de promoção)
    original_pattern = r'<span[^>]*class="[^"]*andes-money-amount__fraction[^"]*"[^>]*data-testid="original-price"[^>]*>([\d.,]+)</span>'
    original_match = re.search(original_pattern, html)
    
    if original_match and original_match.group(1):
        promo_price = float(original_match.group(1).replace('.', '').replace(',', '.'))
    
    if promo_match and promo_match.group(1) and promo_match.group(2):
        whole_part = float(promo_match.group(1).replace('.', '').replace(',', '.'))
        cents_part = float(promo_match.group(2))
        price = whole_part + (cents_part / 100)
        
        # Se temos ambos os preços e são iguais, reseta promo para 0
        if promo_price > 0 and abs(promo_price - price) < 0.01:
            promo_price = 0.0
    else:
        # Fallback para extração de preço regular
        price_patterns = [
            r'<span data-testid="price-part"[\s\S]*?<span[^>]*class="[^"]*andes-money-amount__fraction[^"]*"[^>]*>([\d.]+)</span>[\s\S]*?<span[^>]*class="[^"]*andes-money-amount__cents[^"]*"[^>]*>([\d]+)</span>',
            r'"price":(\d+(?:\.\d+)?)',
            r'<span[^>]*class="[^"]*price-tag-fraction[^"]*"[^>]*>([\d.,]+)</span>'
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, html)
            if match:
                if len(match.groups()) == 2:  # Tem parte inteira e centavos
                    whole_part = float(match.group(1).replace('.', '').replace(',', '.'))
                    cents_part = float(match.group(2))
                    price = whole_part + (cents_part / 100)
                else:  # Só um valor
                    price = float(match.group(1).replace('.', '').replace(',', '.'))
                break
    
    return {
        'price': price,
        'promo_price': promo_price if promo_price != price else 0.0
    }

def extract_image_url(html: str) -> str:
    """Extrai URL da imagem principal do produto"""
    patterns = [
        r'<img[^>]*data-zoom="([^"]+)"',
        r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"',
        r'<img[^>]*class="[^"]*ui-pdp-image[^"]*"[^>]*src="([^"]+)"'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match and match.group(1):
            return match.group(1)
    
    return ''

def extract_seller_name(html: str, url: str) -> str:
    """Extrai nome do vendedor"""
    patterns = [
        r'"seller_name":"([^"]+)"',
        r'<h3[^>]*class="[^"]*store-header__title[^"]*"[^>]*>([^<]+)</h3>',
        r'<a[^>]*class="[^"]*store-info__name[^"]*"[^>]*>([^<]+)</a>',
        r'"seller":\s*{\s*"@type":\s*"Organization",\s*"name":\s*"([^"]+)"',
        r'<a[^>]*href="[^"]*\/loja\/([^"\/]+)"',
        r'<span[^>]*class="[^"]*store-info__name[^"]*"[^>]*>([^<]+)</span>',
        r'seller:\s*{\s*id:\s*\d+,\s*name:\s*"([^"]+)"',
        r'<p[^>]*class="[^"]*official-store-info__title[^"]*"[^>]*>([^<]+)</p>'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match and match.group(1).strip():
            return match.group(1).strip()
    
    # Se não encontrou, tenta extrair da URL
    url_match = re.search(r'mercadolivre\.com\.br\/loja\/([^\/\?]+)', url)
    if url_match and url_match.group(1):
        seller_name = url_match.group(1).replace('-', ' ')
        # Capitaliza cada palavra
        return ' '.join(word.capitalize() for word in seller_name.split())
    
    return 'Vendedor ML'

def extract_stock(html: str) -> int:
    """Extrai a quantidade de estoque disponível do produto"""
    stock = 0
    
    # Tentativa de extrair o estoque da nova estrutura HTML
    availability_pattern = r'<span[^>]*class="[^"]*ui-pdp-buybox__quantity__available[^"]*"[^>]*>\(\+(\d+) disponíveis\)</span>'
    availability_match = re.search(availability_pattern, html)
    if availability_match and availability_match.group(1):
        stock = int(availability_match.group(1))
        print(f"Found stock from availability span: {availability_match.group(1)}, adjusted to: {stock}")
        return stock
    
    # Fallback caso não encontre o estoque diretamente no HTML
    stock_pattern = r'"available_quantity":(\d+)'
    stock_match = re.search(stock_pattern, html)
    if stock_match and stock_match.group(1):
        stock = int(stock_match.group(1))
        print(f"Found stock from available_quantity: {stock}")
        return stock
    
    return stock

def extract_product_details(html: str, url: str) -> Dict:
    """Extrai todos os detalhes do produto"""
    print(f"[PRODUCT_SCRAPER] Iniciando extração de detalhes para URL: {url}")
    print(f"[PRODUCT_SCRAPER] HTML length: {len(html) if html else 0}")
    
    if not html:
        print(f"[PRODUCT_SCRAPER] ERROR: HTML está vazio ou None")
        return {}
    
    # Verifica se o HTML contém elementos esperados
    checks = {
        'title_element': 'ui-pdp-title' in html,
        'price_element': 'andes-money-amount' in html,
        'mercadolivre_content': 'mercadolivre' in html.lower(),
        'body_content': '<body' in html
    }
    
    print(f"[PRODUCT_SCRAPER] HTML content checks: {checks}")
    
    try:
        mlb_id = extract_mlb_id(url)
        print(f"[PRODUCT_SCRAPER] MLB ID extracted: {mlb_id}")
        
        title = extract_title(html)
        print(f"[PRODUCT_SCRAPER] Title extracted: '{title}'")
        
        price_data = extract_price(html)
        print(f"[PRODUCT_SCRAPER] Price data extracted: {price_data}")
        
        image_url = extract_image_url(html)
        print(f"[PRODUCT_SCRAPER] Image URL extracted: {image_url[:100] if image_url else 'None'}...")
        
        seller_name = extract_seller_name(html, url)
        print(f"[PRODUCT_SCRAPER] Seller name extracted: '{seller_name}'")
        
        stock = extract_stock(html)
        print(f"[PRODUCT_SCRAPER] Stock extracted: {stock}")
        
        result = {
            'mlb_id': mlb_id,
            'title': title,
            'price': price_data['price'],
            'promo_price': price_data['promo_price'],
            'image_url': image_url,
            'seller_name': seller_name,
            'stock': stock,
            'url': url
        }
        
        print(f"[PRODUCT_SCRAPER] Final result: {result}")
        
        # Verifica se os dados são válidos
        is_valid = title and title != 'Produto sem título' and len(title) > 5
        print(f"[PRODUCT_SCRAPER] Data is valid: {is_valid}")
        
        return result
        
    except Exception as e:
        print(f"[PRODUCT_SCRAPER] ERROR during extraction: {str(e)}")
        print(f"[PRODUCT_SCRAPER] ERROR type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return {}