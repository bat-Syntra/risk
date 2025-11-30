"""
Odds Verifier Handler - Intégration du Smart Casino Navigator dans le bot
"""

import re
import asyncio
from typing import Dict, Any, Optional
from aiogram import types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from utils.smart_casino_navigator import SmartCasinoNavigator
from utils.bot_manager import BotMessageManager
from database import SessionLocal
from models import User

class OddsVerifier:
    """
    Gère la vérification des cotes et les liens directs
    """
    
    def __init__(self, odds_api_key: str = None):
        self.navigator = SmartCasinoNavigator(odds_api_key)
        # Cache pour stocker les données d'arbitrage
        self.arbitrage_cache = {}
    
    def parse_arbitrage_message(self, text: str) -> Dict[str, Any]:
        """
        Parse le message d'alerte arbitrage pour extraire toutes les infos
        """
        data = {}
        
        # Extract teams
        teams_match = re.search(r'🏟️\s*([^vs]+)\s+vs\s+(.+?)(?:\n|$)', text)
        if teams_match:
            data['away_team'] = teams_match.group(1).strip()
            data['home_team'] = teams_match.group(2).strip()
        
        # Extract sport and market
        sport_match = re.search(r'🏀\s*(\w+)\s*-\s*([^:]+):\s*([^/]+)/([^/\n]+)', text)
        if sport_match:
            data['sport'] = sport_match.group(1).strip()
            data['market_type'] = sport_match.group(2).strip()
            
            # Parse player and over/under
            over_under = sport_match.group(3).strip() + '/' + sport_match.group(4).strip()
            
            # Extract player name and line
            player_match = re.search(r'([A-Za-z\s]+)\s+(Over|Under)\s+([\d.]+)', over_under)
            if player_match:
                data['player'] = player_match.group(1).strip()
                data['line'] = float(player_match.group(3))
        
        # Extract date/time
        time_match = re.search(r'🕐\s*([^-]+)\s*-\s*([^(\n]+)', text)
        if time_match:
            data['game_date'] = time_match.group(1).strip()
            data['game_time'] = time_match.group(2).strip()
        
        # Extract bets info
        bet1_match = re.search(r'\[([^\]]+)\]\s*([^O\n]+)Over\s+([\d.]+).*?\(([\+\-]\d+)\)', text)
        if bet1_match:
            data['bet1'] = {
                'casino': bet1_match.group(1).strip(),
                'player': bet1_match.group(2).strip(),
                'type': 'Over',
                'line': float(bet1_match.group(3)),
                'odds': bet1_match.group(4)
            }
        
        bet2_match = re.search(r'\[([^\]]+)\]\s*([^U\n]+)Under\s+([\d.]+).*?\(([\+\-]\d+)\)', text)
        if bet2_match:
            data['bet2'] = {
                'casino': bet2_match.group(1).strip(),
                'player': bet2_match.group(2).strip(),
                'type': 'Under',
                'line': float(bet2_match.group(3)),
                'odds': bet2_match.group(4)
            }
        
        # Extract stakes
        stake1_match = re.search(r'💵 Miser:\s*\$([\d.]+)', text)
        if stake1_match:
            if 'bet1' in data:
                data['bet1']['stake'] = float(stake1_match.group(1))
        
        # Find second stake
        stakes = re.findall(r'💵 Miser:\s*\$([\d.]+)', text)
        if len(stakes) >= 2 and 'bet2' in data:
            data['bet2']['stake'] = float(stakes[1])
        
        # Extract profit
        profit_match = re.search(r'Profit Garanti:\s*\$([\d.]+)', text)
        if profit_match:
            data['profit'] = float(profit_match.group(1))
        
        return data
    
    async def create_arbitrage_message(
        self,
        arbitrage_data: Dict[str, Any],
        user_id: int
    ) -> tuple[str, InlineKeyboardMarkup]:
        """
        Crée le message avec les boutons pour les liens directs
        """
        
        # Génère un ID unique pour cet arbitrage
        arb_id = f"{user_id}_{arbitrage_data['bet1']['casino']}_{arbitrage_data['bet2']['casino']}_{arbitrage_data['player']}"
        
        # Stocke dans le cache
        self.arbitrage_cache[arb_id] = arbitrage_data
        
        # Trouve les liens directs (instantané, 0 coût)
        async with SmartCasinoNavigator() as nav:
            links = await nav.find_bet_links(arbitrage_data)
        
        # Stocke les liens
        self.arbitrage_cache[arb_id]['links'] = links
        
        # Crée le message
        message = self._format_arbitrage_message(arbitrage_data)
        
        # Crée les boutons
        keyboard = []
        
        # Boutons des casinos avec liens directs
        casino_buttons = []
        
        if links.get('bet1_link'):
            btn1_text = f"💯 {arbitrage_data['bet1']['casino']}"
            btn1 = InlineKeyboardButton(
                text=btn1_text,
                url=links['bet1_link']
            )
            casino_buttons.append(btn1)
        
        if links.get('bet2_link'):
            btn2_text = f"❄️ {arbitrage_data['bet2']['casino']}"
            btn2 = InlineKeyboardButton(
                text=btn2_text,
                url=links['bet2_link']
            )
            casino_buttons.append(btn2)
        
        if casino_buttons:
            keyboard.append(casino_buttons)
        
        # Bouton "I BET"
        keyboard.append([
            InlineKeyboardButton(
                text=f"💰 I BET (${arbitrage_data.get('profit', 0):.2f} profit)",
                callback_data=f"ibet_{arb_id}"
            )
        ])
        
        # Autres boutons
        keyboard.extend([
            [InlineKeyboardButton(text="📊 Custom Calculator", callback_data=f"calc_{arb_id}")],
            [InlineKeyboardButton(text="💰 Change CASHH", callback_data=f"cashh_{arb_id}")],
            [InlineKeyboardButton(text="✅ Verify Odds", callback_data=f"verify_{arb_id}")]
        ])
        
        return message, InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    def _format_arbitrage_message(self, data: Dict[str, Any]) -> str:
        """
        Formate le message d'arbitrage
        """
        
        bet1 = data['bet1']
        bet2 = data['bet2']
        
        message = f"""🚨 ALERTE ARBITRAGE - {data.get('profit_percent', 5.0):.2f}% 🚨

🏟️ {data.get('away_team', '')} vs {data.get('home_team', '')}
🏀 {data.get('sport', 'NBA')} - {data.get('market_type', 'Player Assists')} : {data.get('player', '')} Over {bet1.get('line', 2.5)}/Under {bet2.get('line', 2.5)}
🕐 {data.get('game_date', '')}- {data.get('game_time', '')}

💰 CASHH: ${data.get('total_stake', 750):.1f}
✅ Profit Garanti: ${data.get('profit', 39.88):.2f} (ROI: {data.get('roi', 5.32):.2f}%)

💯 [{bet1['casino']}] {bet1.get('player', data.get('player', ''))} Over {bet1['line']}
💵 Miser: ${bet1.get('stake', 0):.2f} ({bet1['odds']}) → Retour: ${bet1.get('return', 0):.2f}

❄️ [{bet2['casino']}] {bet2.get('player', data.get('player', ''))} Under {bet2['line']}
💵 Miser: ${bet2.get('stake', 0):.2f} ({bet2['odds']}) → Retour: ${bet2.get('return', 0):.2f}

⚠️ Odds can change - always verify before betting!"""
        
        return message
    
    async def handle_verify_callback(
        self,
        callback: types.CallbackQuery,
        arb_id: str
    ):
        """
        Gère le callback quand l'utilisateur clique sur "Verify Odds"
        """
        
        # Récupère les données du cache
        arb_data = self.arbitrage_cache.get(arb_id)
        if not arb_data:
            await callback.answer("❌ Arbitrage data expired", show_alert=True)
            return
        
        await callback.answer("🔍 Vérification en cours...")
        
        # Message de loading
        await BotMessageManager.send_or_edit(
            event=callback,
            text="🔄 Vérification des cotes sur les 2 casinos...\n⏱️ Environ 5-7 secondes",
            parse_mode='HTML'
        )
        
        links = arb_data.get('links', {})
        bet1 = arb_data['bet1']
        bet2 = arb_data['bet2']
        
        # Vérifie les cotes
        async with SmartCasinoNavigator() as nav:
            result = await nav.verify_odds_smart(
                bet1_link=links.get('bet1_link'),
                bet2_link=links.get('bet2_link'),
                player=arb_data.get('player'),
                line=bet1.get('line', 2.5),
                expected_odds1=bet1['odds'],
                expected_odds2=bet2['odds']
            )
        
        # Formate le résultat
        message = self._format_verification_result(arb_data, result)
        
        # Crée les boutons
        keyboard = []
        
        if result['still_valid']:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"🌐 {bet1['casino']} ✅",
                    url=links.get('bet1_link')
                ),
                InlineKeyboardButton(
                    text=f"🌐 {bet2['casino']} ✅",
                    url=links.get('bet2_link')
                )
            ])
            keyboard.append([
                InlineKeyboardButton(
                    text="💰 PLACE BETS NOW",
                    callback_data=f"ibet_{arb_id}"
                )
            ])
        else:
            keyboard.append([
                InlineKeyboardButton(
                    text="🔄 Revérifier",
                    callback_data=f"verify_{arb_id}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton(
                text="◀️ Retour",
                callback_data=f"back_{arb_id}"
            )
        ])
        
        await BotMessageManager.send_or_edit(
            event=callback,
            text=message,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode='HTML'
        )
    
    def _format_verification_result(
        self,
        arb_data: Dict[str, Any],
        result: Dict[str, Any]
    ) -> str:
        """
        Formate le résultat de la vérification
        """
        
        bet1 = arb_data['bet1']
        bet2 = arb_data['bet2']
        
        # Status icons
        bet1_icon = "✅" if result['bet1']['match'] else "⚠️"
        bet2_icon = "✅" if result['bet2']['match'] else "⚠️"
        
        if result['still_valid']:
            status = "✅ <b>ARBITRAGE TOUJOURS VALIDE!</b>"
        else:
            status = "⚠️ <b>COTES ONT CHANGÉ</b>"
        
        message = f"""📊 <b>RÉSULTATS DE VÉRIFICATION</b>

{status}

<b>{bet1['casino']}:</b> {bet1_icon}
• Cotes attendues: {bet1['odds']}
• Cotes actuelles: {result['bet1'].get('current_odds', 'N/A')}

<b>{bet2['casino']}:</b> {bet2_icon}
• Cotes attendues: {bet2['odds']}
• Cotes actuelles: {result['bet2'].get('current_odds', 'N/A')}

"""
        
        if result['still_valid']:
            message += "✅ Les cotes sont toujours bonnes! Place tes bets maintenant! 🚀"
        else:
            message += "⚠️ Les cotes ont trop changé. L'arbitrage n'est plus optimal."
        
        return message


# Intégration dans les handlers existants
async def send_arbitrage_alert(
    bot,
    user_id: int,
    arbitrage_text: str
):
    """
    Envoie une alerte d'arbitrage avec liens directs
    """
    
    verifier = OddsVerifier()
    
    # Parse le message
    arb_data = verifier.parse_arbitrage_message(arbitrage_text)
    
    # Crée le message avec boutons
    message, keyboard = await verifier.create_arbitrage_message(arb_data, user_id)
    
    # Envoie
    await bot.send_message(
        chat_id=user_id,
        text=message,
        reply_markup=keyboard,
        parse_mode='HTML'
    )
