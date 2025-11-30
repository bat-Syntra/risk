"""
Script de test pour envoyer un call avec deep links
Usage: python test_deep_links.py <telegram_user_id>
"""
import asyncio
import sys
from aiogram import Bot
from config import BOT_TOKEN, ADMIN_CHAT_ID

# Simuler l'import de la fonction d'envoi
async def test_send_with_deep_links(user_id: int):
    bot = Bot(token=BOT_TOKEN)
    
    # Drop de test: Udinese vs Bologna - Team Total Corners
    test_drop = {
        'event_id': 'test_udinese_bologna_123',
        'event_id_api': None,  # Pas d'event_id API → va utiliser fallback
        'sport_key': 'soccer_italy_serie_a',  # Correct sport key
        'match': 'Udinese Calcio vs Bologna FC 1909',
        'league': 'Italy - Serie A',
        'market': 'Team Total Corners',
        'arb_percentage': 9.41,
        'outcomes': [
            {
                'casino': 'Betsson',
                'outcome': 'Udinese Calcio Over 3',
                'odds': -143
            },
            {
                'casino': 'Coolbet',
                'outcome': 'Udinese Calcio Under 3',
                'odds': 215
            }
        ],
        'drop_event_id': 999  # Fake ID pour test
    }
    
    # Import des modules nécessaires
    from core.tiers import TierLevel
    from main_new import send_alert_to_user
    
    try:
        # Envoyer l'alerte (sera en mode PREMIUM pour avoir les boutons)
        await send_alert_to_user(user_id, TierLevel.PREMIUM, test_drop)
        print(f"✅ Test call envoyé à {user_id}")
        print(f"⚠️ Note: event_id_api est None, donc les liens seront des fallbacks (homepage)")
        print(f"📝 Pour tester les VRAIS deep links, il faut un vrai event_id de The Odds API")
    except Exception as e:
        print(f"❌ Erreur: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_deep_links.py <telegram_user_id>")
        print(f"Ou utilise l'admin ID: {ADMIN_CHAT_ID}")
        sys.exit(1)
    
    user_id = int(sys.argv[1]) if len(sys.argv) > 1 else int(ADMIN_CHAT_ID)
    
    asyncio.run(test_send_with_deep_links(user_id))
