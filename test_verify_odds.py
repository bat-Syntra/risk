"""
Test 2: Vérifier qu'on peut extraire les cotes sans screenshots
"""

import asyncio
from playwright.async_api import async_playwright

async def test_verify_odds():
    """
    Test l'extraction des cotes directement du DOM
    """
    
    print("🔍 Test 2: Extraction des cotes SANS screenshots\n")
    print("=" * 50)
    
    # URLs à tester
    test_urls = {
        'BET99': 'https://bet99.ca/en/sportsbook/basketball/usa/nba',
        'Coolbet': 'https://www.coolbet.com/en/sports/basketball/nba'
    }
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False  # Met False pour VOIR ce qui se passe!
        )
        
        for casino, url in test_urls.items():
            print(f"\n🎰 Test sur {casino}")
            print(f"   URL: {url}")
            
            page = await browser.new_page()
            
            try:
                print("   ⏳ Chargement de la page...")
                await page.goto(url, wait_until='networkidle', timeout=30000)
                
                # Cherche "Myles Turner" sur la page
                print("   🔍 Recherche de 'Myles Turner'...")
                
                # Méthode 1: Recherche directe
                turner_found = await page.locator("text=Myles Turner").count()
                
                if turner_found > 0:
                    print(f"   ✅ Trouvé {turner_found} fois 'Myles Turner'!")
                    
                    # Essaie d'extraire les cotes autour
                    elements = await page.locator("text=Myles Turner").all()
                    for i, elem in enumerate(elements[:2]):  # Max 2 pour pas spam
                        parent = await elem.evaluate("""
                            el => {
                                const parent = el.closest('[class*="bet"], [class*="odd"], [class*="market"]');
                                return parent ? parent.innerText : el.parentElement.innerText;
                            }
                        """)
                        print(f"   📊 Contexte {i+1}: {parent[:100]}...")
                        
                else:
                    print(f"   ⚠️ 'Myles Turner' pas trouvé sur la page d'accueil")
                    
                    # Essaie la recherche
                    search_selectors = [
                        'input[placeholder*="Search"]',
                        'input[type="search"]',
                        '.search-input',
                        '[class*="search"]'
                    ]
                    
                    search_found = False
                    for selector in search_selectors:
                        if await page.locator(selector).count() > 0:
                            print(f"   🔍 Barre de recherche trouvée!")
                            await page.fill(selector, "Myles Turner")
                            await page.press(selector, "Enter")
                            await page.wait_for_timeout(2000)
                            
                            # Revérifie
                            if await page.locator("text=Myles Turner").count() > 0:
                                print(f"   ✅ Trouvé après recherche!")
                                search_found = True
                            break
                    
                    if not search_found:
                        print(f"   ❌ Impossible de trouver même avec recherche")
                
                # Pause pour voir
                print(f"   ⏸️ Regarde le browser pendant 5 secondes...")
                await page.wait_for_timeout(5000)
                
            except Exception as e:
                print(f"   ❌ Erreur: {e}")
            
            finally:
                await page.close()
        
        await browser.close()
    
    print("\n" + "=" * 50)
    print("🎯 TEST 2 TERMINÉ!")
    print("\n📝 Observations:")
    print("   - Si 'Myles Turner' trouvé → On peut extraire sans IA ✅")
    print("   - Si pas trouvé → On aura besoin de navigation plus complexe")
    print("   - Si recherche marche → On peut utiliser ça comme fallback")

if __name__ == "__main__":
    print("🚀 Lancement du test d'extraction des cotes...\n")
    print("⚠️ Le browser va s'ouvrir en mode VISIBLE pour que tu voies!\n")
    asyncio.run(test_verify_odds())
