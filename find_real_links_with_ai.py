"""
Trouve les VRAIS liens directs avec Claude Vision
Cette fois on utilise vraiment l'IA!
"""

import os
import re
import asyncio
import base64
from typing import Dict, Any
from playwright.async_api import async_playwright
import anthropic

class AIBetFinder:
    """
    Utilise Claude Vision pour naviguer et trouver les vrais liens
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY requis pour utiliser l'IA!")
        self.client = anthropic.Anthropic(api_key=self.api_key)
    
    async def find_exact_bet_link(
        self,
        casino: str,
        sport: str,
        team1: str,
        team2: str,
        bet_team: str,
        market: str = "Moneyline"
    ) -> Dict[str, Any]:
        """
        Utilise Claude pour naviguer et trouver le lien exact
        """
        
        # URLs de départ pour chaque casino
        start_urls = {
            'Betway': 'https://betway.com/en-ca/sports',
            'bet105': 'https://www.bet105.com/sports',
            'BET99': 'https://bet99.ca/en/sportsbook',
            'Coolbet': 'https://www.coolbet.com/en/sports'
        }
        
        start_url = start_urls.get(casino, f'https://{casino.lower()}.com')
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            print(f"🔍 Recherche sur {casino}...")
            print(f"   Sport: {sport}")
            print(f"   Match: {team1} vs {team2}")
            print(f"   Bet: {bet_team} {market}")
            
            try:
                # Étape 1: Page d'accueil
                await page.goto(start_url, wait_until='networkidle')
                await page.wait_for_timeout(2000)
                
                # Screenshot pour Claude
                screenshot = await page.screenshot()
                
                # Demande à Claude de naviguer
                navigation_result = await self._ask_claude_to_navigate(
                    screenshot,
                    f"Find the {sport} section and navigate to {team1} vs {team2}"
                )
                
                # Si Claude trouve une action à faire
                if navigation_result.get('action'):
                    action = navigation_result['action']
                    
                    if action['type'] == 'click':
                        # Click sur l'élément suggéré
                        try:
                            await page.click(action['selector'])
                            await page.wait_for_timeout(2000)
                        except:
                            # Essaie avec le texte
                            await page.click(f"text={action.get('text', sport)}")
                            await page.wait_for_timeout(2000)
                    
                    elif action['type'] == 'search':
                        # Utilise la recherche
                        search_input = page.locator('input[type="search"], input[placeholder*="Search"]').first
                        await search_input.fill(f"{team1} {team2}")
                        await search_input.press('Enter')
                        await page.wait_for_timeout(3000)
                
                # Étape 2: Cherche le match spécifique
                screenshot2 = await page.screenshot()
                
                match_result = await self._ask_claude_to_find_bet(
                    screenshot2,
                    team1, team2, bet_team, market
                )
                
                if match_result.get('found'):
                    # Si trouvé, on a le lien!
                    if match_result.get('click_needed'):
                        # Click pour aller sur la page du match
                        try:
                            selector = match_result.get('selector')
                            if selector:
                                await page.click(selector)
                            else:
                                await page.click(f"text={bet_team}")
                            await page.wait_for_timeout(2000)
                        except:
                            pass
                    
                    # L'URL actuelle est le lien direct!
                    final_url = page.url
                    
                    # Vérifie si on a un event ID
                    event_id_match = re.search(r'/event/(\d+)', final_url)
                    if event_id_match:
                        event_id = event_id_match.group(1)
                        print(f"   ✅ Event ID trouvé: {event_id}")
                    
                    await browser.close()
                    
                    return {
                        'success': True,
                        'url': final_url,
                        'event_id': event_id if event_id_match else None,
                        'odds': match_result.get('odds'),
                        'method': 'ai_navigation',
                        'cost': 0.006  # ~2 screenshots
                    }
                
                # Pas trouvé
                await browser.close()
                return {
                    'success': False,
                    'url': page.url,
                    'error': 'Match not found',
                    'cost': 0.006
                }
                
            except Exception as e:
                await browser.close()
                return {
                    'success': False,
                    'error': str(e),
                    'cost': 0.003
                }
    
    async def _ask_claude_to_navigate(self, screenshot: bytes, instruction: str) -> Dict:
        """
        Demande à Claude comment naviguer
        """
        
        img_b64 = base64.b64encode(screenshot).decode()
        
        prompt = f"""
        Look at this sports betting website screenshot.
        
        Task: {instruction}
        
        Tell me what to do:
        - If you see the match/sport, tell me where to click
        - If you need to search, tell me to use search
        - Be specific with selectors or text to click
        
        Return JSON only:
        {{
            "found": true/false,
            "action": {{
                "type": "click|search|none",
                "selector": "CSS selector if click",
                "text": "text to click or search"
            }}
        }}
        """
        
        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": img_b64
                        }
                    },
                    {"type": "text", "text": prompt}
                ]
            }]
        )
        
        try:
            import json
            text = response.content[0].text
            # Clean up response
            if "```" in text:
                text = text.split("```")[1].replace("json", "").strip()
            return json.loads(text)
        except:
            return {"found": False, "action": None}
    
    async def _ask_claude_to_find_bet(
        self,
        screenshot: bytes,
        team1: str,
        team2: str,
        bet_team: str,
        market: str
    ) -> Dict:
        """
        Demande à Claude de trouver le bet spécifique
        """
        
        img_b64 = base64.b64encode(screenshot).decode()
        
        prompt = f"""
        Look at this sports betting page.
        
        Find this specific bet:
        - Match: {team1} vs {team2}
        - Bet on: {bet_team} {market}
        
        Can you see:
        1. The match?
        2. The {market} option for {bet_team}?
        3. What are the odds?
        
        Return JSON:
        {{
            "found": true/false,
            "odds": "odds if visible (e.g., +120)",
            "click_needed": true/false,
            "selector": "selector to click if needed"
        }}
        """
        
        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=200,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": img_b64
                        }
                    },
                    {"type": "text", "text": prompt}
                ]
            }]
        )
        
        try:
            import json
            text = response.content[0].text
            if "```" in text:
                text = text.split("```")[1].replace("json", "").strip()
            return json.loads(text)
        except:
            return {"found": False}


async def main():
    """
    Test avec ton arbitrage
    """
    
    # Check API key
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ ERREUR: ANTHROPIC_API_KEY non configurée!")
        print("\n💡 Pour configurer:")
        print("   export ANTHROPIC_API_KEY='sk-ant-...'")
        print("\n   Ou ajoute dans .env:")
        print("   ANTHROPIC_API_KEY=sk-ant-...")
        return
    
    finder = AIBetFinder(api_key)
    
    print("🤖 Recherche avec Claude Vision...\n")
    print("=" * 50)
    
    # Test Betway
    result = await finder.find_exact_bet_link(
        casino='Betway',
        sport='NCAAB',
        team1='Oral Roberts',
        team2='Rice',
        bet_team='Rice',
        market='Moneyline'
    )
    
    print("\n" + "=" * 50)
    print("📊 RÉSULTAT:\n")
    
    if result['success']:
        print(f"✅ VRAI lien trouvé!")
        print(f"   URL: {result['url']}")
        if result.get('event_id'):
            print(f"   Event ID: {result['event_id']}")
        if result.get('odds'):
            print(f"   Cotes actuelles: {result['odds']}")
        print(f"   Coût: ${result['cost']:.3f}")
    else:
        print(f"❌ Pas trouvé")
        print(f"   Erreur: {result.get('error')}")
        print(f"   Coût: ${result['cost']:.3f}")
    
    print("\n💡 C'est ça un VRAI lien direct!")
    print("   Pointe exactement sur le match/bet")
    print("   Avec l'event ID qu'on peut pas deviner")

if __name__ == "__main__":
    asyncio.run(main())
