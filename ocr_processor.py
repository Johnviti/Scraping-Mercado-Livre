#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo OCR para extração de texto de imagens
Usa Tesseract OCR para processar screenshots e extrair informações de produtos
"""

import io
import re
import base64
from typing import Dict, List, Optional, Tuple
from PIL import Image, ImageEnhance, ImageFilter
try:
    import pytesseract
    # Verificar se o executável do Tesseract está disponível
    try:
        pytesseract.get_tesseract_version()
        TESSERACT_AVAILABLE = True
    except Exception:
        TESSERACT_AVAILABLE = False
except ImportError:
    TESSERACT_AVAILABLE = False
    pytesseract = None

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None
    np = None

from dataclasses import dataclass

@dataclass
class OCRResult:
    """Resultado da extração OCR"""
    text: str
    confidence: float
    products: List[Dict]
    processing_time: float
    success: bool
    error: Optional[str] = None

class OCRProcessor:
    """Processador OCR para extração de texto de imagens"""
    
    def __init__(self):
        self.tesseract_available = TESSERACT_AVAILABLE
        self.mock_processor = None
        
        if not self.tesseract_available:
            # Importar mock processor se Tesseract não estiver disponível
            try:
                from ocr_mock import MockOCRProcessor
                self.mock_processor = MockOCRProcessor()
                print("Mock OCR carregado com sucesso")
            except ImportError as e:
                print(f"Erro ao importar mock OCR: {e}")
                self.mock_processor = None
            except Exception as e:
                print(f"Erro ao inicializar mock OCR: {e}")
                self.mock_processor = None
        
        self.tesseract_config = {
            'lang': 'por+eng',  # Português e Inglês
            'oem': 1,  # LSTM OCR Engine Mode
            'psm': 6,  # Uniform block of text
        }
        
        # Padrões regex para identificar produtos
        self.price_patterns = [
            r'R\$\s*([\d.,]+)',
            r'([\d.,]+)\s*reais?',
            r'Por\s+R\$\s*([\d.,]+)',
            r'([\d.,]+)\s*R\$'
        ]
        
        self.product_indicators = [
            'tênis', 'sapato', 'bota', 'sandália', 'chinelo',
            'nike', 'adidas', 'puma', 'vans', 'converse',
            'masculino', 'feminino', 'unissex',
            'tamanho', 'tam', 'número', 'cor',
            'frete', 'grátis', 'entrega', 'parcela'
        ]
    
    def is_available(self) -> bool:
        """Verifica se o OCR está disponível (Tesseract ou Mock)"""
        return self.tesseract_available or self.mock_processor is not None
    
    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """Pré-processa a imagem para melhorar a qualidade do OCR"""
        try:
            # Converter para RGB se necessário
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Aumentar contraste
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)
            
            # Aumentar nitidez
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.2)
            
            # Aplicar filtro para reduzir ruído
            image = image.filter(ImageFilter.MedianFilter(size=3))
            
            return image
            
        except Exception as e:
            print(f"Erro no pré-processamento: {e}")
            return image
    
    def extract_text_from_image(self, image: Image.Image) -> Tuple[str, float]:
        """Extrai texto da imagem usando Tesseract"""
        try:
            # Pré-processar imagem
            processed_image = self.preprocess_image(image)
            
            # Configurar Tesseract
            custom_config = f"--oem {self.tesseract_config['oem']} --psm {self.tesseract_config['psm']} -l {self.tesseract_config['lang']}"
            
            # Extrair texto
            text = pytesseract.image_to_string(processed_image, config=custom_config)
            
            # Obter dados de confiança
            data = pytesseract.image_to_data(processed_image, config=custom_config, output_type=pytesseract.Output.DICT)
            
            # Calcular confiança média
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            return text.strip(), avg_confidence
            
        except Exception as e:
            print(f"Erro na extração de texto: {e}")
            return "", 0.0
    
    def extract_prices(self, text: str) -> List[str]:
        """Extrai preços do texto"""
        prices = []
        
        for pattern in self.price_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Limpar e formatar preço
                price = re.sub(r'[^\d.,]', '', match)
                if price and ',' in price:
                    prices.append(price)
        
        return list(set(prices))  # Remover duplicatas
    
    def identify_products(self, text: str) -> List[Dict]:
        """Identifica produtos no texto extraído"""
        products = []
        lines = text.split('\n')
        
        current_product = {}
        
        for line in lines:
            line = line.strip().lower()
            if not line:
                continue
            
            # Verificar se a linha contém indicadores de produto
            is_product_line = any(indicator in line for indicator in self.product_indicators)
            
            if is_product_line:
                # Extrair preços da linha
                prices = self.extract_prices(line)
                
                if prices:
                    current_product = {
                        'title': line[:100],  # Primeiros 100 caracteres como título
                        'price': prices[0],
                        'raw_text': line,
                        'extracted_via': 'ocr'
                    }
                    products.append(current_product)
        
        return products
    
    def process_screenshot(self, image_data: bytes) -> OCRResult:
        """Processa screenshot e extrai informações de produtos"""
        import time
        start_time = time.time()
        
        # Se Tesseract não estiver disponível, usar mock
        if not self.tesseract_available and self.mock_processor:
            mock_result = self.mock_processor.process_screenshot(image_data)
            return OCRResult(
                text=mock_result.text,
                confidence=mock_result.confidence,
                products=mock_result.products,
                processing_time=mock_result.processing_time,
                success=mock_result.success,
                error=mock_result.error
            )
        
        if not self.tesseract_available:
            return OCRResult(
                text="",
                confidence=0.0,
                products=[],
                processing_time=time.time() - start_time,
                success=False,
                error="Tesseract não está disponível e mock não foi carregado"
            )
        
        try:
            # Carregar imagem
            image = Image.open(io.BytesIO(image_data))
            
            # Extrair texto
            text, confidence = self.extract_text_from_image(image)
            
            if not text:
                return OCRResult(
                    text="",
                    confidence=0.0,
                    products=[],
                    processing_time=time.time() - start_time,
                    success=False,
                    error="Nenhum texto extraído da imagem"
                )
            
            # Identificar produtos
            products = self.identify_products(text)
            
            return OCRResult(
                text=text,
                confidence=confidence,
                products=products,
                processing_time=time.time() - start_time,
                success=True
            )
            
        except Exception as e:
            return OCRResult(
                text="",
                confidence=0.0,
                products=[],
                processing_time=time.time() - start_time,
                success=False,
                error=str(e)
            )
    
    def process_base64_image(self, base64_data: str) -> OCRResult:
        """Processa imagem em base64"""
        # Se Tesseract não estiver disponível, usar mock
        if not self.tesseract_available and self.mock_processor:
            mock_result = self.mock_processor.process_base64_image(base64_data)
            return OCRResult(
                text=mock_result.text,
                confidence=mock_result.confidence,
                products=mock_result.products,
                processing_time=mock_result.processing_time,
                success=mock_result.success,
                error=mock_result.error
            )
        
        try:
            # Remover prefixo data:image se presente
            if 'base64,' in base64_data:
                base64_data = base64_data.split('base64,')[1]
            
            # Decodificar base64
            image_data = base64.b64decode(base64_data)
            
            return self.process_screenshot(image_data)
            
        except Exception as e:
            import time
            return OCRResult(
                text="",
                confidence=0.0,
                products=[],
                processing_time=0.0,
                success=False,
                error=f"Erro ao processar imagem base64: {str(e)}"
            )

def test_ocr_installation():
    """Testa se o Tesseract está instalado e funcionando"""
    if not TESSERACT_AVAILABLE:
        return {
            'tesseract_installed': False,
            'pytesseract_available': False,
            'error': 'pytesseract não está instalado. Execute: pip install pytesseract',
            'test_successful': False
        }
    
    try:
        # Criar uma imagem de teste simples
        test_image = Image.new('RGB', (200, 50), color='white')
        
        # Tentar extrair texto (deve retornar string vazia, mas sem erro)
        text = pytesseract.image_to_string(test_image)
        
        return {
            'tesseract_installed': True,
            'pytesseract_available': True,
            'version': pytesseract.get_tesseract_version(),
            'test_successful': True
        }
        
    except pytesseract.TesseractNotFoundError:
        return {
            'tesseract_installed': False,
            'pytesseract_available': True,
            'error': 'Tesseract executável não encontrado. No Windows, baixe de: https://github.com/UB-Mannheim/tesseract/wiki',
            'test_successful': False
        }
    except Exception as e:
        return {
            'tesseract_installed': False,
            'pytesseract_available': True,
            'error': str(e),
            'test_successful': False
        }

if __name__ == "__main__":
    # Teste básico
    result = test_ocr_installation()
    print("Teste de instalação OCR:")
    print(result)