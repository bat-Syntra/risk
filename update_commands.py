#!/usr/bin/env python3
"""
Force update bot commands with Telegram
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aiogram import Bot
from bot.commands_setup import setup_bot_commands, setup_menu_button

async def force_update_commands():
    """Force update all bot commands"""
    
    # Use the actual bot token
    bot_token = "7999609044:AAFS0m1ZzPW9mxmmxtb5iDrUTjMVgyPFxhs"
    
    # Create bot instance
    bot = Bot(token=bot_token)
    
    try:
        print("🔄 Forcing bot commands update...")
        
        # Clear existing commands first
        await bot.delete_my_commands()
        print("✅ Cleared old commands")
        
        # Set new commands
        await setup_bot_commands(bot)
        print("✅ Set new commands")
        
        # Setup menu button
        await setup_menu_button(bot)
        print("✅ Updated menu button")
        
        print("\n🎉 Commands updated successfully!")
        print("\nAvailable commands:")
        print("  /menu - Menu")
        print("  /confirmations - Confirmations en attente")
        print("  /parlay_settings - Préférences parlays")
        print("  /parlays - Voir parlays disponibles") 
        print("  /report_odds - Signaler changement cotes")
        
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(force_update_commands())
