# test_api.py
# Script para testar a API localmente

import requests
import json

# URL base da API (mude para sua URL da Vercel após deploy)
BASE_URL = "http://localhost:5000"

def test_health():
    """Testa o endpoint de health check"""
    print("\n=== Testando Health Check ===")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Erro: {e}")

def test_home():
    """Testa o endpoint home"""
    print("\n=== Testando Home ===")
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    except Exception as e:
        print(f"Erro: {e}")

def test_search(query="smartphone", limit=5):
    """Testa o endpoint de busca"""
    print(f"\n=== Testando Busca: {query} ===")
    try:
        response = requests.get(f"{BASE_URL}/search", params={"q": query, "limit": limit})
        print(f"Status: {response.status_code}")
        data = response.json()
        
        if data.get("success"):
            print(f"Query: {data['query']}")
            print(f"Items encontrados: {data['items_count']}")
            print(f"URL de busca: {data['search_url']}")
            
            # Mostra os primeiros 3 itens
            for i, item in enumerate(data['items'][:3]):
                print(f"\nItem {i+1}:")
                print(f"  Título: {item.get('title', 'N/A')}")
                print(f"  Preço: {item.get('price', 'N/A')}")
                print(f"  Link: {item.get('link', 'N/A')[:80]}...")
        else:
            print(f"Erro: {data.get('error')}")
            
    except Exception as e:
        print(f"Erro: {e}")

def test_scrape(url="https://lista.mercadolivre.com.br/eletronicos"):
    """Testa o endpoint de scraping"""
    print(f"\n=== Testando Scrape: {url} ===")
    try:
        response = requests.post(
            f"{BASE_URL}/scrape",
            json={"url": url},
            headers={"Content-Type": "application/json"}
        )
        print(f"Status: {response.status_code}")
        data = response.json()
        
        if data.get("success"):
            print(f"URL: {data['url']}")
            print(f"Items encontrados: {data['items_count']}")
            print(f"Status HTTP: {data['status_code']}")
            
            # Mostra os primeiros 3 itens
            for i, item in enumerate(data['items'][:3]):
                print(f"\nItem {i+1}:")
                print(f"  Título: {item.get('title', 'N/A')}")
                print(f"  Preço: {item.get('price', 'N/A')}")
                print(f"  Patrocinado: {item.get('sponsored', False)}")
        else:
            print(f"Erro: {data.get('error')}")
            
    except Exception as e:
        print(f"Erro: {e}")

def test_categories():
    """Testa o endpoint de categorias"""
    print("\n=== Testando Categorias ===")
    try:
        response = requests.get(f"{BASE_URL}/categories")
        print(f"Status: {response.status_code}")
        data = response.json()
        
        if data.get("success"):
            print(f"Categorias disponíveis: {len(data['categories'])}")
            for cat in data['categories'][:5]:
                print(f"  - {cat['name']}: {cat['url']}")
        else:
            print(f"Erro: {data.get('error')}")
            
    except Exception as e:
        print(f"Erro: {e}")

def main():
    """Executa todos os testes"""
    print("🧪 Testando API de Scraping Mercado Livre")
    print(f"Base URL: {BASE_URL}")
    
    # Testa todos os endpoints
    test_health()
    test_home()
    test_categories()
    test_search("notebook", 3)
    test_scrape("https://lista.mercadolivre.com.br/casaco")
    
    print("\n✅ Testes concluídos!")
    print("\n💡 Dicas:")
    print("- Mude BASE_URL para sua URL da Vercel após deploy")
    print("- Use este script para testar novos endpoints")
    print("- Monitore os logs para identificar possíveis bloqueios")

if __name__ == "__main__":
    main()