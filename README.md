# API de Scraping Mercado Livre

API Flask para fazer scraping de produtos do Mercado Livre

## 📋 Estrutura do Projeto

```
docker-curso/
├── api.py              # API Flask principal
├── selectors_ml.py     # Funções de parsing HTML
├── vercel.json         # Configuração Vercel
├── requirements.txt    # Dependências Python
├── README.md          # Este arquivo
├── debug_requests_ml.py    # Script de debug (requests)
├── debug_selenium_ml.py    # Script de debug (selenium)
└── diagnostico_ml/    # Pasta de diagnósticos
```

## 🔧 Endpoints da API

### GET `/`
Informações gerais da API

**Resposta:**
```json
{
  "message": "API de Scraping Mercado Livre",
  "version": "1.0.0",
  "endpoints": {...}
}
```

### GET `/health`
Health check da API

**Resposta:**
```json
{
  "status": "ok",
  "timestamp": 1703123456.789
}
```

### POST `/scrape`
Faz scraping de uma URL específica do Mercado Livre

**Body:**
```json
{
  "url": "https://lista.mercadolivre.com.br/casaco"
}
```

**Resposta:**
```json
{
  "success": true,
  "url": "https://lista.mercadolivre.com.br/casaco",
  "status_code": 200,
  "items_count": 50,
  "items": [
    {
      "title": "Casaco Feminino Inverno",
      "price": "89,90",
      "previous_price": "120,00",
      "discount": "25% OFF",
      "brand": "Marca X",
      "seller": "Loja Y",
      "rating": "4.5",
      "reviews_total": "(123)",
      "shipping": "Frete grátis",
      "sponsored": false,
      "link": "https://produto.mercadolivre.com.br/...",
      "is_tracking_link": false,
      "image": "https://http2.mlstatic.com/..."
    }
  ]
}
```

### GET `/search?q=termo&limit=50`
Busca produtos por termo

**Parâmetros:**
- `q` (obrigatório): Termo de busca
- `limit` (opcional): Limite de resultados (padrão: 50, máximo: 200)

**Exemplo:**
```
GET /search?q=notebook&limit=20
```

**Resposta:**
```json
{
  "success": true,
  "query": "notebook",
  "search_url": "https://lista.mercadolivre.com.br/notebook",
  "status_code": 200,
  "items_count": 20,
  "items": [...]
}
```

### GET `/categories`
Lista categorias populares

**Resposta:**
```json
{
  "success": true,
  "categories": [
    {
      "name": "Eletrônicos",
      "url": "https://lista.mercadolivre.com.br/eletronicos"
    }
  ]
}
```
## 🛠️ Desenvolvimento

### Estrutura de Arquivos

- `api.py`: API Flask principal com todos os endpoints
- `selectors_ml.py`: Funções de parsing HTML do Mercado Livre
- `vercel.json`: Configuração para deploy na Vercel
- `requirements.txt`: Dependências Python

### Adicionando Novos Endpoints

```python
@app.route('/novo-endpoint', methods=['GET'])
def novo_endpoint():
    try:
        # Sua lógica aqui
        return jsonify({"success": True, "data": "..."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

## 📝 Logs e Debugging

Para debug local, use os scripts existentes:
- `debug_requests_ml.py`: Testa scraping com requests
- `debug_selenium_ml.py`: Testa scraping com selenium
