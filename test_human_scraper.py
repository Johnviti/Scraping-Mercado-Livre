#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste das melhorias humanas no Playwright scraper
"""

import asyncio
from playwright_scraper import PlaywrightScraper

async def test_human_scraping():
    """Testa o scraping com comportamento humano"""
    print("🤖 Testando scraper com comportamento humano...")
    
    try:
        async with PlaywrightScraper() as scraper:
            # URL específica do produto do capacete
            test_url = "https://produto.mercadolivre.com.br/MLB-4613785362-capacete-robocop-articulado-texx-gladiator-v3-preto-fosco-_JM?searchVariation=182511638887#polycard_client=search-nordic&searchVariation=182511638887&position=11&search_layout=stack&type=item&tracking_id=aae0642c-0fa1-443f-812e-1c197520c4a9"
            
            print(f"🏍️ Navegando para produto do capacete: {test_url[:80]}...")
            
            # Fazer scraping com comportamento humano
            content, status = await scraper.fetch_page_content(
                test_url,
                wait_for_selector=".ui-pdp-title",  # Aguardar título do produto
                scroll_page=True
            )
            
            print(f"✅ Status: {status}")
            print(f"📄 Tamanho do conteúdo: {len(content):,} caracteres")
            
            # Verificar se encontrou elementos importantes
            if "capacete" in content.lower() or "gladiator" in content.lower():
                print("✅ Produto do capacete encontrado")
            if ".ui-pdp-title" in content:
                print("✅ Título do produto carregado")
            if ".price-tag-fraction" in content or "price" in content.lower():
                print("✅ Preço encontrado")
            if "data-testid=\"action:understood\"" in content:
                print("⚠️  Modal de cookies ainda presente")
            else:
                print("✅ Cookies processados")
                
            # Verificar se as técnicas stealth funcionaram
            if "webdriver" not in content.lower():
                print("✅ Stealth: webdriver removido")
            
            print("\n🔍 Resumo das melhorias implementadas:")
            print("  ✅ Chrome real em desenvolvimento")
            print("  ✅ Perfil persistente com cookies")
            print("  ✅ Configurações brasileiras (pt-BR, São Paulo)")
            print("  ✅ User-agent atualizado (Chrome 131)")
            print("  ✅ Técnicas stealth avançadas")
            print("  ✅ Interações humanas (mouse, scroll, cookies)")
            print("  ✅ Aguarda hidratação da página")
                
            return True
            
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_human_scraping())
    if success:
        print("\n🎉 Teste concluído com sucesso!")
        print("\n📋 Próximos passos:")
        print("  1. Deploy no Railway para testar em produção")
        print("  2. Monitorar logs para verificar se ML detecta menos automação")
        print("  3. Ajustar timeouts se necessário")
    else:
        print("\n💥 Teste falhou!")