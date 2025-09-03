# playwright_scraper.py
import asyncio
import random
import time
import os
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PlaywrightScraper:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
        
    async def __aenter__(self):
        """Context manager entry"""
        await self.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        try:
            await self._close_async()
        except Exception as e:
            logger.error(f"Error in __aexit__: {e}")
        
    def check_playwright_installation(self):
        """Verifica se o Playwright está instalado corretamente"""
        try:
            import playwright
            # Usar o caminho padrão do Playwright no Windows
            if os.name == 'nt':  # Windows
                default_path = os.path.expanduser('~/AppData/Local/ms-playwright')
            else:  # Linux/Mac
                default_path = os.path.expanduser('~/.cache/ms-playwright')
            browsers_path = os.getenv('PLAYWRIGHT_BROWSERS_PATH', default_path)
            chromium_path = os.path.join(browsers_path, 'chromium-*')
            
            # Verificar se existe algum diretório do chromium
            import glob
            chromium_dirs = glob.glob(chromium_path)
            
            if not chromium_dirs:
                logger.error(f"Chromium não encontrado em {browsers_path}")
                return False
                
            logger.info(f"Chromium encontrado: {chromium_dirs[0]}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao verificar instalação do Playwright: {e}")
            return False
        
    async def start(self):
        """Initialize Playwright browser with human-like settings"""
        try:
            # Verificar instalação primeiro
            if not self.check_playwright_installation():
                raise Exception("Playwright não está instalado corretamente")
                
            self.playwright = await async_playwright().start()
            
            # Detectar se estamos em produção (Railway) ou desenvolvimento
            is_production = os.getenv('RAILWAY_ENVIRONMENT') is not None
            
            if is_production:
                # Produção: usar Chromium headless otimizado
                self.browser = await self.playwright.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-accelerated-2d-canvas',
                        '--no-first-run',
                        '--no-zygote',
                        '--disable-gpu',
                        '--disable-web-security',
                        '--disable-features=VizDisplayCompositor',
                        '--disable-background-timer-throttling',
                        '--disable-backgrounding-occluded-windows',
                        '--disable-renderer-backgrounding',
                        '--disable-field-trial-config',
                        '--disable-ipc-flooding-protection',
                        # Stealth args para evitar detecção
                        '--disable-blink-features=AutomationControlled',
                        '--exclude-switches=enable-automation',
                        '--disable-extensions-except',
                        '--disable-plugins-discovery',
                        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
                    ]
                )
            else:
                # Desenvolvimento: tentar usar Chrome real se disponível
                try:
                    self.browser = await self.playwright.chromium.launch(
                        channel='chrome',  # Usar Chrome real instalado
                        headless=False,    # Visível para debug
                        args=[
                            '--disable-blink-features=AutomationControlled',
                            '--exclude-switches=enable-automation',
                            '--disable-extensions-except',
                            '--disable-plugins-discovery',
                            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
                        ]
                    )
                    logger.info("Usando Chrome real para desenvolvimento")
                except Exception as e:
                    logger.warning(f"Chrome real não disponível, usando Chromium: {e}")
                    # Fallback para Chromium
                    self.browser = await self.playwright.chromium.launch(
                        headless=True,
                        args=[
                            '--disable-blink-features=AutomationControlled',
                            '--exclude-switches=enable-automation',
                            '--disable-extensions-except',
                            '--disable-plugins-discovery',
                            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
                        ]
                    )
            
            # Create context with realistic Brazilian settings
            context_options = {
                'viewport': {'width': 1366, 'height': 768},  # Resolução mais comum no Brasil
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'locale': 'pt-BR',
                'timezone_id': 'America/Sao_Paulo',
                'permissions': ['geolocation', 'notifications'],
                'geolocation': {'latitude': -23.5505, 'longitude': -46.6333},  # São Paulo coordinates
                'extra_http_headers': {
                    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Accept-Encoding': 'gzip, deflate, br, zstd',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'Cache-Control': 'max-age=0',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Sec-Ch-Ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                    'Sec-Ch-Ua-Mobile': '?0',
                    'Sec-Ch-Ua-Platform': '"Windows"',
                    'Upgrade-Insecure-Requests': '1'
                },
                'java_script_enabled': True,
                'bypass_csp': True,
                'ignore_https_errors': True
            }
            
            # Tentar usar perfil persistente em desenvolvimento
            if not is_production:
                try:
                    user_data_dir = os.path.join(os.getcwd(), 'browser_profile')
                    os.makedirs(user_data_dir, exist_ok=True)
                    
                    # Usar launchPersistentContext para perfil persistente
                    await self.browser.close()  # Fechar browser anterior
                    self.context = await self.playwright.chromium.launch_persistent_context(
                        user_data_dir,
                        channel='chrome' if not is_production else None,
                        headless=False if not is_production else True,
                        args=[
                            '--disable-blink-features=AutomationControlled',
                            '--exclude-switches=enable-automation',
                            '--disable-extensions-except',
                            '--disable-plugins-discovery'
                        ],
                        **context_options
                    )
                    self.browser = None  # Context gerencia o browser
                    logger.info("Usando perfil persistente para desenvolvimento")
                except Exception as e:
                    logger.warning(f"Perfil persistente não disponível: {e}")
                    self.context = await self.browser.new_context(**context_options)
            else:
                self.context = await self.browser.new_context(**context_options)
            
            # Add advanced stealth techniques
            await self.context.add_init_script("""
                // Remove webdriver property
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                // Mock realistic plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => {
                        return [
                            {
                                0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
                                description: "Portable Document Format",
                                filename: "internal-pdf-viewer",
                                length: 1,
                                name: "Chrome PDF Plugin"
                            },
                            {
                                0: {type: "application/pdf", suffixes: "pdf", description: "Portable Document Format"},
                                description: "Portable Document Format",
                                filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                                length: 1,
                                name: "Chrome PDF Viewer"
                            }
                        ];
                    },
                });
                
                // Mock realistic languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['pt-BR', 'pt', 'en-US', 'en'],
                });
                
                // Mock hardware concurrency
                Object.defineProperty(navigator, 'hardwareConcurrency', {
                    get: () => 8,
                });
                
                // Mock device memory
                Object.defineProperty(navigator, 'deviceMemory', {
                    get: () => 8,
                });
                
                // Mock WebGL vendor and renderer
                const getParameter = WebGLRenderingContext.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) {
                        return 'Intel Inc.';
                    }
                    if (parameter === 37446) {
                        return 'Intel(R) HD Graphics 620';
                    }
                    return getParameter(parameter);
                };
                
                // Mock permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                
                // Remove automation indicators
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
                
                // Mock chrome runtime
                if (!window.chrome) {
                    window.chrome = {};
                }
                if (!window.chrome.runtime) {
                    window.chrome.runtime = {
                        onConnect: undefined,
                        onMessage: undefined
                    };
                }
                
                // Mock realistic screen properties
                Object.defineProperty(screen, 'availWidth', {
                    get: () => 1366,
                });
                Object.defineProperty(screen, 'availHeight', {
                    get: () => 728,
                });
                Object.defineProperty(screen, 'width', {
                    get: () => 1366,
                });
                Object.defineProperty(screen, 'height', {
                    get: () => 768,
                });
            """)
            
            self.page = await self.context.new_page()
            
            # Set realistic timeouts
            self.page.set_default_timeout(120000)  # 120 seconds
            self.page.set_default_navigation_timeout(120000)
            
            logger.info("Playwright browser initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Playwright: {e}")
            raise
            
    async def close(self):
        """Close browser and cleanup"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
            logger.info("Playwright browser closed successfully")
        except Exception as e:
            logger.error(f"Error closing Playwright: {e}")
            
    async def fetch_page_content(self, url, wait_for_selector=None, scroll_page=True):
        """Fetch page content using Playwright with human-like behavior"""
        try:
            if not self.page:
                raise Exception("Page not initialized")
                
            logger.info(f"Navigating to: {url}")
            
            # Navigate to page
            response = await self.page.goto(
                url, 
                wait_until='domcontentloaded',
                timeout=120000
            )
            
            if not response:
                raise Exception("Failed to get response from page")
                
            logger.info(f"Page loaded with status: {response.status}")
            
            # Random delay to simulate human behavior
            await asyncio.sleep(random.uniform(1, 3))
            
            # Accept cookies and perform initial interactions
            await self.accept_cookies_and_interact()
            
            # Wait for page hydration - important for SPAs like ML
            await asyncio.sleep(random.uniform(2, 4))
            
            # Wait for specific selector if provided (PDP elements)
            if wait_for_selector:
                try:
                    await self.page.wait_for_selector(wait_for_selector, timeout=30000)
                    logger.info(f"Found selector: {wait_for_selector}")
                except Exception as e:
                    logger.warning(f"Selector not found: {wait_for_selector} - {e}")
            
            # Wait for common ML selectors to ensure page is fully loaded
            ml_selectors = [
                '.ui-pdp-title',  # Product title
                '.price-tag-fraction',  # Price
                '.ui-pdp-gallery',  # Image gallery
                '.ui-pdp-description'  # Description
            ]
            
            for selector in ml_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=5000)
                    logger.info(f"ML element loaded: {selector}")
                    break
                except Exception:
                    continue
            
            # Scroll page to trigger lazy loading
            if scroll_page:
                await self.simulate_human_scrolling()
            
            # Final wait for any dynamic content
            await asyncio.sleep(random.uniform(1, 2))
            
            # Get page content with null check
            if self.page:
                content = await self.page.content()
                logger.info(f"Page content retrieved: {len(content)} characters")
                return content, response.status
            else:
                raise Exception("Page became None during execution")
            
        except Exception as e:
            logger.error(f"Error fetching page content: {e}")
            raise
            
    async def simulate_human_scrolling(self):
        """Simulate realistic human scrolling behavior"""
        try:
            # Get page dimensions
            page_height = await self.page.evaluate('document.body.scrollHeight')
            viewport_height = await self.page.evaluate('window.innerHeight')
            
            # Detectar se estamos em produção para otimizar
            is_production = os.getenv('RAILWAY_ENVIRONMENT') is not None
            
            if is_production:
                # Produção: scroll rápido mas ainda humano
                scroll_positions = [viewport_height // 2, page_height // 2, page_height - viewport_height]
                for position in scroll_positions:
                    if position > 0 and position < page_height:
                        await self.page.evaluate(f'window.scrollTo({{top: {position}, behavior: "smooth"}})')
                        await asyncio.sleep(random.uniform(0.5, 1.0))
            else:
                # Desenvolvimento: scroll mais humano
                current_position = 0
                scroll_step = viewport_height // 3
                
                while current_position < page_height - viewport_height:
                    # Movimento de mouse aleatório
                    await self.page.mouse.move(
                        random.randint(100, 1200),
                        random.randint(100, 600)
                    )
                    
                    # Scroll suave
                    scroll_amount = random.randint(scroll_step - 50, scroll_step + 50)
                    current_position += scroll_amount
                    
                    await self.page.evaluate(f'window.scrollTo({{top: {current_position}, behavior: "smooth"}})')
                    await asyncio.sleep(random.uniform(0.8, 2.0))
                    
                    # Pausa ocasional como humano
                    if random.random() < 0.3:
                        await asyncio.sleep(random.uniform(1.0, 3.0))
            
            # Scroll de volta ao topo
            await self.page.evaluate('window.scrollTo({top: 0, behavior: "smooth"})')
            await asyncio.sleep(0.5)
            
            logger.info("Human-like scrolling completed")
            
        except Exception as e:
            logger.warning(f"Error during scrolling: {e}")
    
    async def accept_cookies_and_interact(self):
        """Accept cookies and perform human-like interactions"""
        try:
            # Lista de seletores comuns para aceitar cookies
            cookie_selectors = [
                'button[data-testid="action:understood"]',  # ML específico
                'button:has-text("Aceitar")',
                'button:has-text("Entendi")',
                'button:has-text("OK")',
                'button:has-text("Concordo")',
                '[data-testid="cookie-consent-accept"]',
                '.cookie-accept',
                '#cookie-accept',
                'button[aria-label*="aceitar"]',
                'button[aria-label*="Aceitar"]'
            ]
            
            # Tentar encontrar e clicar no botão de aceitar cookies
            for selector in cookie_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=3000)
                    if element:
                        # Movimento de mouse humano antes do clique
                        box = await element.bounding_box()
                        if box:
                            await self.page.mouse.move(
                                box['x'] + box['width'] / 2,
                                box['y'] + box['height'] / 2
                            )
                            await asyncio.sleep(random.uniform(0.2, 0.5))
                            
                        await element.click()
                        logger.info(f"Clicked cookie consent button: {selector}")
                        await asyncio.sleep(random.uniform(1, 2))
                        break
                except Exception:
                    continue
            
            # Simular movimento de mouse aleatório
            for _ in range(random.randint(2, 4)):
                await self.page.mouse.move(
                    random.randint(100, 1200),
                    random.randint(100, 600)
                )
                await asyncio.sleep(random.uniform(0.1, 0.3))
                
        except Exception as e:
            logger.warning(f"Error during cookie acceptance: {e}")

    async def take_screenshot_async(self, url, full_page=True):
        """Take a screenshot of a page"""
        try:
            logger.info(f"Taking screenshot of: {url}")
            
            # Navigate to page
            response = await self.page.goto(
                url, 
                wait_until='domcontentloaded',
                timeout=120000
            )
            
            if not response:
                raise Exception("Failed to get response from page")
                
            logger.info(f"Page loaded with status: {response.status}")
            
            # Wait for content to load (reduced for speed)
            await asyncio.sleep(random.uniform(1, 2))
            
            # Take screenshot
            screenshot_bytes = await self.page.screenshot(
                full_page=full_page,
                type='png'
            )
            
            logger.info(f"Screenshot taken: {len(screenshot_bytes)} bytes")
            
            return screenshot_bytes
            
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            raise

    def take_screenshot(self, url, full_page=True):
        """Synchronous wrapper for taking screenshots"""
        try:
            # Check if we're already in an event loop
            try:
                loop = asyncio.get_running_loop()
                # If we're in a running loop, create a task instead
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self._take_screenshot_with_context(url, full_page))
                    return future.result(timeout=60)
            except RuntimeError:
                # No running loop, safe to use asyncio.run
                return asyncio.run(self._take_screenshot_with_context(url, full_page))
        except Exception as e:
            logger.error(f"Error in sync screenshot wrapper: {e}")
            raise
    
    async def _take_screenshot_with_context(self, url, full_page=True):
        """Helper method to take screenshot with proper context management"""
        async with PlaywrightScraper() as scraper:
            return await scraper.take_screenshot_async(url, full_page)

    def fetch_page(self, url, wait_for_selector=None, scroll_page=True):
        """Synchronous wrapper for fetching page content"""
        try:
            # Check if we're already in an event loop
            try:
                loop = asyncio.get_running_loop()
                # If we're in a running loop, create a task instead
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self._fetch_page_with_context(url, wait_for_selector, scroll_page))
                    content, status = future.result(timeout=60)
                    return content
            except RuntimeError:
                # No running loop, safe to use asyncio.run
                content, status = asyncio.run(self._fetch_page_with_context(url, wait_for_selector, scroll_page))
                return content
        except Exception as e:
            logger.error(f"Error in sync fetch wrapper: {e}")
            raise
    
    async def _fetch_page_with_context(self, url, wait_for_selector=None, scroll_page=True):
        """Helper method to fetch page with proper context management"""
        async with PlaywrightScraper() as scraper:
            content, status = await scraper.fetch_page_content(url, wait_for_selector, scroll_page)
            
            # Get page content with timeout to prevent hanging
            import asyncio
            try:
                # Add timeout to prevent the method from hanging
                await asyncio.wait_for(asyncio.sleep(0.1), timeout=1)
                logger.info(f"Page content processing completed: {len(content)} characters")
                return content, status
            except asyncio.TimeoutError:
                logger.error("Timeout during page content processing")
                return content, status
    
    def close(self):
        """Synchronous wrapper for closing browser"""
        try:
            # Check if we're already in an event loop
            try:
                loop = asyncio.get_running_loop()
                # If we're in a running loop, create a task instead
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self._close_async())
                    future.result(timeout=15)  # Increased timeout
            except RuntimeError:
                # No running loop, safe to use asyncio.run
                asyncio.run(self._close_async())
        except Exception as e:
            logger.error(f"Error in sync close wrapper: {e}")
            # Force cleanup if normal close fails
            try:
                if hasattr(self, 'browser') and self.browser:
                    # Force close without waiting
                    pass
            except:
                pass
    
    async def _close_async(self):
        """Async method to close browser and cleanup resources"""
        # Set a shorter timeout for cleanup operations
        import asyncio
        
        async def close_with_timeout(coro, timeout=10):
            try:
                await asyncio.wait_for(coro, timeout=timeout)
            except asyncio.TimeoutError:
                logger.warning(f"Timeout during cleanup operation")
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
        
        try:
            if hasattr(self, 'page') and self.page:
                await close_with_timeout(self.page.close())
                self.page = None
                logger.info("Page closed")
        except Exception as e:
            logger.error(f"Error closing page: {e}")
        
        try:
            if hasattr(self, 'context') and self.context:
                await close_with_timeout(self.context.close())
                self.context = None
                logger.info("Context closed")
        except Exception as e:
            logger.error(f"Error closing context: {e}")
        
        try:
            if hasattr(self, 'browser') and self.browser:
                await close_with_timeout(self.browser.close())
                self.browser = None
                logger.info("Browser closed")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")
        
        try:
            if hasattr(self, 'playwright') and self.playwright:
                await close_with_timeout(self.playwright.stop())
                self.playwright = None
                logger.info("Playwright stopped")
        except Exception as e:
            logger.error(f"Error stopping playwright: {e}")

    async def click_element(self, selector, timeout=15000):
        """Click an element with human-like behavior"""
        try:
            # Wait for element to be visible
            await self.page.wait_for_selector(selector, state='visible', timeout=timeout)
            
            # Move mouse to element
            await self.page.hover(selector)
            await asyncio.sleep(random.uniform(0.1, 0.3))
            
            # Click element
            await self.page.click(selector)
            
            # Wait after click
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            logger.info(f"Clicked element: {selector}")
            
        except Exception as e:
            logger.error(f"Error clicking element {selector}: {e}")
            raise
            
    async def type_text(self, selector, text, delay=100):
        """Type text with human-like delays"""
        try:
            await self.page.wait_for_selector(selector, state='visible')
            await self.page.click(selector)
            await self.page.fill(selector, '')
            await self.page.type(selector, text, delay=delay)
            
            logger.info(f"Typed text into {selector}: {text}")
            
        except Exception as e:
            logger.error(f"Error typing text into {selector}: {e}")
            raise

# Async wrapper functions for easy integration
async def fetch_with_playwright(url, wait_for_selector=None, scroll_page=True):
    """Fetch page content using Playwright - standalone function"""
    async with PlaywrightScraper() as scraper:
        return await scraper.fetch_page_content(url, wait_for_selector, scroll_page)

def fetch_page_sync(url, wait_for_selector=None, scroll_page=True):
    """Synchronous wrapper for Playwright scraping"""
    try:
        # Check if we're already in an event loop
        try:
            loop = asyncio.get_running_loop()
            # If we're in a running loop, create a task instead
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, fetch_with_playwright(url, wait_for_selector, scroll_page))
                return future.result(timeout=60)
        except RuntimeError:
            # No running loop, safe to use asyncio.run
            return asyncio.run(fetch_with_playwright(url, wait_for_selector, scroll_page))
    except Exception as e:
        logger.error(f"Error in sync wrapper: {e}")
        raise

# Test function
async def test_scraper():
    """Test the Playwright scraper"""
    test_url = "https://lista.mercadolivre.com.br/iphone"
    
    try:
        async with PlaywrightScraper() as scraper:
            content, status = await scraper.fetch_page_content(
                test_url, 
                wait_for_selector='.ui-search-results',
                scroll_page=True
            )
            
            print(f"Status: {status}")
            print(f"Content length: {len(content)}")
            print(f"Contains 'mercadolivre': {'mercadolivre' in content.lower()}")
            print(f"Contains 'produto': {'produto' in content.lower()}")
            
            # Parse with BeautifulSoup to check for products
            soup = BeautifulSoup(content, 'html.parser')
            products = soup.find_all('div', class_='ui-search-result__wrapper')
            print(f"Products found: {len(products)}")
            
            return content, status
            
    except Exception as e:
        print(f"Test failed: {e}")
        raise

if __name__ == "__main__":
    # Run test
    asyncio.run(test_scraper())