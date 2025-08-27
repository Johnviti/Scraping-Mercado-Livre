# api.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import sys
import time
import json
from urllib.parse import urlparse, parse_qs
from selectors_ml import parse_list_items

app = Flask(__name__)
CORS(app)  # Permite requisições de qualquer origem

# Headers padrão para requests
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}

def fetch_page(url, headers=None):
    """Faz requisição HTTP e retorna o conteúdo da página"""
    if headers is None:
        headers = DEFAULT_HEADERS
    
    try:
        response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
        response.raise_for_status()
        return response.text, response.status_code
    except Exception as e:
        raise Exception(f"Erro ao buscar página: {str(e)}")

def validate_mercadolivre_url(url):
    """Valida se a URL é do Mercado Livre"""
    parsed = urlparse(url)
    return 'mercadolivre.com.br' in parsed.netloc or 'mercadolibre.com' in parsed.netloc

@app.route('/', methods=['GET'])
def home():
    """Endpoint de informações da API"""
    return jsonify({
        "message": "API de Scraping Mercado Livre",
        "version": "1.0.0",
        "endpoints": {
            "/scrape": "POST - Faz scraping de uma URL do Mercado Livre",
            "/search": "GET - Busca produtos por termo",
            "/health": "GET - Status da API"
        },
        "usage": {
            "scrape": "POST /scrape com body: {'url': 'https://lista.mercadolivre.com.br/...'}",
            "search": "GET /search?q=termo_busca&limit=50"
        }
    })

@app.route('/health', methods=['GET'])
def health():
    """Endpoint de health check"""
    return jsonify({"status": "ok", "timestamp": time.time()})

@app.route('/scrape', methods=['POST'])
def scrape_url():
    """Endpoint para fazer scraping de uma URL específica do Mercado Livre"""
    try:
        data = request.get_json()
        
        if not data or 'url' not in data:
            return jsonify({"error": "URL é obrigatória"}), 400
        
        url = data['url']
        
        # Valida se é URL do Mercado Livre
        if not validate_mercadolivre_url(url):
            return jsonify({"error": "URL deve ser do Mercado Livre"}), 400
        
        # Faz o scraping
        html_content, status_code = fetch_page(url)
        
        # Parse dos itens
        items = parse_list_items(html_content)
        
        return jsonify({
            "success": True,
            "url": url,
            "status_code": status_code,
            "items_count": len(items),
            "items": items
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
        
        # Faz o scraping
        html_content, status_code = fetch_page(search_url)
        
        # Parse dos itens
        items = parse_list_items(html_content)
        
        # Aplica limite aos resultados
        if len(items) > limit:
            items = items[:limit]
        
        return jsonify({
            "success": True,
            "query": query,
            "search_url": search_url,
            "status_code": status_code,
            "items_count": len(items),
            "items": items
        })
        
    except Exception as e:
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

# Handler para erros 404
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint não encontrado"}), 404

# Handler para erros 500
@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Erro interno do servidor"}), 500

if __name__ == '__main__':
    # Para desenvolvimento local
    app.run(debug=True, host='0.0.0.0', port=5000)