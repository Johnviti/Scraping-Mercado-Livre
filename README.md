# API de Scraping Mercado Livre

API Flask para fazer scraping de produtos do Mercado Livre, pronta para deploy na Vercel.

## 🚀 Deploy na Vercel

### Pré-requisitos
- Conta na [Vercel](https://vercel.com)
- [Vercel CLI](https://vercel.com/cli) instalado (opcional)

### Opção 1: Deploy via GitHub (Recomendado)

1. **Faça push do código para um repositório GitHub**
2. **Conecte o repositório na Vercel:**
   - Acesse [vercel.com](https://vercel.com)
   - Clique em "New Project"
   - Importe seu repositório GitHub
   - A Vercel detectará automaticamente que é um projeto Python
   - Clique em "Deploy"

### Opção 2: Deploy via Vercel CLI

```bash
# Instale a Vercel CLI
npm i -g vercel

# Faça login
vercel login

# Deploy do projeto
vercel

# Para deploy em produção
vercel --prod
```

### Opção 3: Deploy via Drag & Drop

1. Acesse [vercel.com/new](https://vercel.com/new)
2. Arraste a pasta do projeto para a área de upload
3. Aguarde o deploy automático

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

## 🧪 Testando Localmente

```bash
# Instale as dependências
pip install -r requirements.txt

# Execute a API
python api.py

# A API estará disponível em http://localhost:5000
```

### Exemplos de Teste

```bash
# Health check
curl http://localhost:5000/health

# Buscar produtos
curl "http://localhost:5000/search?q=smartphone&limit=10"

# Scraping de URL específica
curl -X POST http://localhost:5000/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://lista.mercadolivre.com.br/eletronicos"}'
```

## 🔒 Considerações de Segurança

- A API valida se as URLs são do Mercado Livre
- Limite máximo de 200 itens por requisição
- Timeout de 30 segundos para requisições HTTP
- CORS habilitado para todas as origens

## ⚠️ Limitações

- **Rate Limiting:** O Mercado Livre pode bloquear muitas requisições
- **Anti-bot:** Algumas páginas podem retornar captcha
- **Selenium:** Não incluído na API por limitações da Vercel
- **Timeout:** Máximo de 30 segundos por função na Vercel

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

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request

## 📄 Licença

Este projeto é para fins educacionais. Respeite os termos de uso do Mercado Livre.