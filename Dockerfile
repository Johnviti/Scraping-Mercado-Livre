# Dockerfile para Railway
FROM python:3.11-slim

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Adicionar repositório do Google Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome-keyring.gpg \
    && sh -c 'echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list'

# Instalar Google Chrome e dependências
RUN apt-get update && apt-get install -y \
    google-chrome-stable \
    fonts-ipafont-gothic \
    fonts-wqy-zenhei \
    fonts-thai-tlwg \
    fonts-freefont-ttf \
    libxss1 \
    tesseract-ocr \
    tesseract-ocr-por \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Definir diretório de trabalho
WORKDIR /app

# Copiar arquivos de dependências
COPY requirements-railway.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements-railway.txt

# Copiar código da aplicação
COPY . .

# Instalar browsers do Playwright
RUN python install_playwright.py

# Definir variáveis de ambiente
ENV PLAYWRIGHT_BROWSERS_PATH=/app/.cache/ms-playwright
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=false
ENV PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=true
ENV NODE_ENV=production
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Expor porta
EXPOSE 8080

# Comando de inicialização
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} --workers 1 --timeout 300 --worker-class sync --max-requests 100 --max-requests-jitter 10 api:app"]