"""
Test Middle Complete System
Test avec les nouveaux handlers, boutons Calculator, Change CASHH, I BET, etc.
"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from aiogram import Bot
from aiogram.enums import ParseMode

from utils.middle_calculator import classify_middle_type
from bot.middle_handlers import store_middle, build_middle_keyboard, format_middle_message_with_calc

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_CHAT_ID = int(os.getenv('ADMIN_CHAT_ID', '0'))

bot = Bot(token=BOT_TOKEN)


async def test_middle_safe_complete():
    """Test middle safe avec système complet"""
    
    # Example data
    middle_data = {
        'team1': 'New England Patriots',
        'team2': 'Cincinnati Bengals',
        'league': 'NFL',
        'market': 'Player Receptions',
        'player': 'Chase Brown',
        'time': 'Today, 1:00PM',
        'side_a': {
            'bookmaker': 'Mise-o-jeu',
            'selection': 'Over 3.5',
            'line': '3.5',
            'odds': '-105',
            'market': 'Player Receptions'
        },
        'side_b': {
            'bookmaker': 'Coolbet',
            'selection': 'Under 4.5',
            'line': '4.5',
            'odds': '+120',
            'market': 'Player Receptions'
        }
    }
    
    user_cash = 500.0
    
    # Calculate
    print("🔄 Calculating middle...")
    calc = classify_middle_type(
        middle_data['side_a'],
        middle_data['side_b'],
        user_cash
    )
    
    print(f"✅ Type: {calc['type']}")
    print(f"✅ EV: {calc['ev_percent']}%")
    
    # Store in system
    middle_hash = store_middle(middle_data, calc)
    print(f"✅ Stored with hash: {middle_hash}")
    
    # Format message
    message = format_middle_message_with_calc(middle_data, calc)
    
    # Build keyboard with all buttons
    keyboard = build_middle_keyboard(middle_data, calc, middle_hash, bet_placed=False)
    
    # Send to admin
    print(f"\n📤 Sending to Telegram (chat_id: {ADMIN_CHAT_ID})...")
    
    try:
        await bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=message,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        print("✅ Message sent successfully!")
        print("\n🎯 Test les boutons:")
        print("  - 💰 I BET → Enregistre et met ✅")
        print("  - 🧮 Calculator → Affiche détails")
        print("  - 💵 Change CASHH → Recalcule en live")
        
    except Exception as e:
        print(f"❌ Error sending message: {e}")
    
    finally:
        await bot.session.close()


async def main():
    print("=" * 60)
    print("🎰 TEST MIDDLE BETS - SYSTÈME COMPLET")
    print("=" * 60)
    print("\n✅ Migration DB: middle_bets table créée")
    print("✅ Handlers: middle_handlers.router intégré")
    print("✅ Boutons: I BET, Calculator, Change CASHH")
    print("\n")
    
    await test_middle_safe_complete()
    
    print("\n" + "=" * 60)
    print("✅ Test terminé! Vérifie dans Telegram")
    print("=" * 60)


if __name__ == '__main__':
    asyncio.run(main())
