#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para testar o endpoint OCR
"""

import requests
import base64
import io
from PIL import Image, ImageDraw, ImageFont
import json

def create_test_image():
    """Cria uma imagem de teste com texto simulando uma página do Mercado Livre"""
    # Criar imagem
    img = Image.new('RGB', (800, 600), color='white')
    draw = ImageDraw.Draw(img)
    
    # Tentar usar uma fonte padrão
    try:
        font = ImageFont.truetype("arial.ttf", 20)
        font_small = ImageFont.truetype("arial.ttf", 16)
    except:
        font = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Adicionar texto simulando produtos
    y_pos = 50
    products = [
        "Tênis Nike Air Max 270",
        "R$ 299,90",
        "12x R$ 24,99 sem juros",
        "",
        "Tênis Adidas Ultraboost 22",
        "R$ 449,90",
        "10x R$ 44,99",
        "",
        "Tênis Vans Old Skool",
        "R$ 189,90",
        "6x R$ 31,65"
    ]
    
    for text in products:
        if text:
            if "R$" in text:
                draw.text((50, y_pos), text, fill='red', font=font)
            else:
                draw.text((50, y_pos), text, fill='black', font=font)
        y_pos += 30
    
    return img

def image_to_base64(image):
    """Converte imagem PIL para base64"""
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return img_str

def test_ocr_endpoint():
    """Testa o endpoint OCR"""
    print("Criando imagem de teste...")
    test_image = create_test_image()
    
    print("Convertendo para base64...")
    base64_data = image_to_base64(test_image)
    
    print("Enviando para endpoint OCR...")
    url = "http://localhost:5000/test-ocr"
    
    payload = {
        "image_data": base64_data
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("\n=== RESULTADO DO TESTE OCR ===")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            if result.get('status') == 'success':
                ocr_result = result.get('ocr_result', {})
                print(f"\n✅ OCR executado com sucesso!")
                print(f"📝 Texto extraído: {len(ocr_result.get('text_extracted', ''))} caracteres")
                print(f"🎯 Confiança: {ocr_result.get('confidence', 0)}%")
                print(f"🛍️ Produtos encontrados: {ocr_result.get('products_found', 0)}")
                print(f"⏱️ Tempo de processamento: {ocr_result.get('processing_time', 0)}s")
                
                products = ocr_result.get('products', [])
                if products:
                    print("\n📦 Produtos detectados:")
                    for i, product in enumerate(products[:3], 1):
                        print(f"  {i}. {product.get('title', 'N/A')} - R$ {product.get('price', 'N/A')}")
            else:
                print(f"❌ Erro no OCR: {result.get('error', 'Erro desconhecido')}")
        else:
            print(f"❌ Erro HTTP: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Erro na requisição: {str(e)}")

if __name__ == "__main__":
    test_ocr_endpoint()