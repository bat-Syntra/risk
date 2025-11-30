"""
Test manuel pour vérifier l'accessibilité des sites
"""

import asyncio
from playwright.async_api import async_playwright
import aiohttp

async def test_casino_accessibility():
    """
    Vérifie si les casinos sont accessibles
    """
    
    casinos = {
        'Sports Interaction': 'https://www.sportsinteraction.com',
        'iBet': 'https://www.ibet.com',
        'BET99': 'https://bet99.ca',
        'Coolbet': 'https://www.coolbet.com',
        'Betway': 'https://betway.ca'
    }
    
    print("🔍 TEST D'ACCESSIBILITÉ DES CASINOS")
    print("=" * 50)
    
    # Test avec aiohttp (rapide)
    print("\n1️⃣ Test HTTP rapide:")
    print("-" * 30)
    
    async with aiohttp.ClientSession() as session:
        for name, url in casinos.items():
            try:
                async with session.head(url, timeout=5, allow_redirects=True) as response:
                    if response.status < 400:
                        print(f"✅ {name}: Accessible ({response.status})")
                    else:
                        print(f"❌ {name}: Erreur {response.status}")
            except Exception as e:
                print(f"❌ {name}: {str(e)[:50]}")
    
    # Test avec Playwright (plus complet)
    print("\n2️⃣ Test avec browser headless:")
    print("-" * 30)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        for name, url in casinos.items():
            page = await browser.new_page()
            try:
                response = await page.goto(url, wait_until='domcontentloaded', timeout=10000)
                if response and response.ok:
                    title = await page.title()
                    print(f"✅ {name}: {title[:30]}")
                    
                    # Cherche NCAAB
                    ncaab_found = await page.locator("text=/NCAA|NCAAB|College/i").count() > 0
                    if ncaab_found:
                        print(f"   → NCAAB trouvé sur la page")
                else:
                    print(f"❌ {name}: Page non chargée")
            except Exception as e:
                print(f"❌ {name}: {str(e)[:50]}")
            finally:
                await page.close()
        
        await browser.close()
    
    print("\n" + "=" * 50)
    print("💡 RECOMMANDATIONS:")
    print("-" * 30)
    print("1. Si ❌ → Le site bloque peut-être l'automatisation")
    print("2. Si ✅ mais pas de NCAAB → Match pas encore listé")
    print("3. Essaie manuellement dans ton browser pour vérifier")

async def find_auburn_manually():
    """
    Ouvre les casinos pour que tu puisses chercher manuellement
    """
    
    print("\n3️⃣ RECHERCHE MANUELLE")
    print("=" * 50)
    print("Je vais ouvrir un browser VISIBLE")
    print("Tu pourras chercher Auburn vs St. John's manuellement")
    print("-" * 50)
    
    async with async_playwright() as p:
        # Browser VISIBLE
        browser = await p.chromium.launch(headless=False)
        
        # Sports Interaction
        page1 = await browser.new_page()
        await page1.goto('https://www.sportsinteraction.com/betting/basketball/usa/ncaa')
        print("\n📍 Sports Interaction ouvert")
        print("   → Cherche 'Auburn' sur la page")
        print("   → Si tu trouves, copie l'URL!")
        
        # iBet
        page2 = await browser.new_page()
        await page2.goto('https://www.ibet.com')
        print("\n📍 iBet ouvert")
        print("   → Navigate vers Basketball > NCAAB")
        print("   → Cherche 'Auburn vs St. John's'")
        
        print("\n⏸️ Browser restera ouvert 60 secondes...")
        print("   Copie les URLs des matchs si tu les trouves!")
        
        await asyncio.sleep(60)
        
        # Capture les URLs finales
        si_url = page1.url
        ibet_url = page2.url
        
        print("\n" + "=" * 50)
        print("URLs finales:")
        print(f"Sports Interaction: {si_url}")
        print(f"iBet: {ibet_url}")
        
        await browser.close()

if __name__ == "__main__":
    print("🚀 Tests de diagnostic\n")
    
    # Test 1: Accessibilité
    asyncio.run(test_casino_accessibility())
    
    # Test 2: Recherche manuelle
    response = input("\n❓ Veux-tu ouvrir les browsers pour chercher manuellement? (y/n): ")
    if response.lower() == 'y':
        asyncio.run(find_auburn_manually())
