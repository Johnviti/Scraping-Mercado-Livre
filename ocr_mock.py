#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mock do sistema OCR para demonstração quando Tesseract não está disponível
"""

import io
import time
import base64
from typing import Dict, List, Optional
from PIL import Image
from dataclasses import dataclass

@dataclass
class MockOCRResult:
    """Resultado simulado da extração OCR"""
    text: str
    confidence: float
    products: List[Dict]
    processing_time: float
    success: bool
    error: Optional[str] = None

class MockOCRProcessor:
    """Processador OCR simulado para demonstração"""
    
    def __init__(self):
        # Texto simulado que seria extraído de uma página do Mercado Livre
        self.mock_text = """
        Tênis Nike Air Max 270
        R$ 299,90
        12x R$ 24,99 sem juros
        Frete grátis
        
        Tênis Adidas Ultraboost 22
        R$ 449,90
        10x R$ 44,99
        
        Tênis Vans Old Skool
        R$ 189,90
        6x R$ 31,65
        
        Tênis Converse All Star
        R$ 159,90
        5x R$ 31,98
        
        Tênis Puma RS-X
        R$ 329,90
        8x R$ 41,24
        """
        
        self.mock_products = [
            {
                'title': 'Tênis Nike Air Max 270',
                'price': '299,90',
                'raw_text': 'Tênis Nike Air Max 270 R$ 299,90',
                'extracted_via': 'ocr_mock'
            },
            {
                'title': 'Tênis Adidas Ultraboost 22',
                'price': '449,90',
                'raw_text': 'Tênis Adidas Ultraboost 22 R$ 449,90',
                'extracted_via': 'ocr_mock'
            },
            {
                'title': 'Tênis Vans Old Skool',
                'price': '189,90',
                'raw_text': 'Tênis Vans Old Skool R$ 189,90',
                'extracted_via': 'ocr_mock'
            },
            {
                'title': 'Tênis Converse All Star',
                'price': '159,90',
                'raw_text': 'Tênis Converse All Star R$ 159,90',
                'extracted_via': 'ocr_mock'
            },
            {
                'title': 'Tênis Puma RS-X',
                'price': '329,90',
                'raw_text': 'Tênis Puma RS-X R$ 329,90',
                'extracted_via': 'ocr_mock'
            }
        ]
    
    def process_screenshot(self, image_data: bytes) -> MockOCRResult:
        """Simula o processamento de screenshot"""
        start_time = time.time()
        
        try:
            # Verificar se é uma imagem válida
            image = Image.open(io.BytesIO(image_data))
            
            # Simular tempo de processamento
            time.sleep(0.5)
            
            processing_time = time.time() - start_time
            
            return MockOCRResult(
                text=self.mock_text.strip(),
                confidence=85.5,  # Confiança simulada
                products=self.mock_products,
                processing_time=processing_time,
                success=True
            )
            
        except Exception as e:
            return MockOCRResult(
                text="",
                confidence=0.0,
                products=[],
                processing_time=time.time() - start_time,
                success=False,
                error=f"Erro ao processar imagem: {str(e)}"
            )
    
    def process_base64_image(self, base64_data: str) -> MockOCRResult:
        """Simula o processamento de imagem em base64"""
        try:
            # Remover prefixo data:image se presente
            if 'base64,' in base64_data:
                base64_data = base64_data.split('base64,')[1]
            
            # Decodificar base64
            image_data = base64.b64decode(base64_data)
            
            return self.process_screenshot(image_data)
            
        except Exception as e:
            return MockOCRResult(
                text="",
                confidence=0.0,
                products=[],
                processing_time=0.0,
                success=False,
                error=f"Erro ao processar imagem base64: {str(e)}"
            )

def test_mock_ocr_installation():
    """Testa a instalação simulada do OCR"""
    return {
        'tesseract_installed': False,
        'mock_mode': True,
        'version': 'Mock OCR v1.0',
        'test_successful': True,
        'message': 'Usando modo simulado - Tesseract não instalado'
    }

if __name__ == "__main__":
    # Teste básico
    processor = MockOCRProcessor()
    result = test_mock_ocr_installation()
    print("Teste de instalação OCR Mock:")
    print(result)
    
    # Criar uma imagem de teste
    test_image = Image.new('RGB', (800, 600), color='white')
    img_bytes = io.BytesIO()
    test_image.save(img_bytes, format='PNG')
    img_bytes = img_bytes.getvalue()
    
    # Testar processamento
    ocr_result = processor.process_screenshot(img_bytes)
    print("\nResultado do teste OCR:")
    print(f"Sucesso: {ocr_result.success}")
    print(f"Produtos encontrados: {len(ocr_result.products)}")
    print(f"Tempo de processamento: {ocr_result.processing_time:.2f}s")