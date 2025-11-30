"""
Force commands update handler - backdoor to update commands
"""
import logging
from aiogram import Router, types
from aiogram.filters import Command
from bot.commands_setup import setup_bot_commands, setup_menu_button

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("force_update_commands"))
async def force_update_commands(message: types.Message):
    """Hidden command to force update all bot commands"""
    
    # Only allow admin
    if message.from_user.id != 8213628656:
        return
    
    try:
        await message.answer("🔄 Mise à jour des commandes...")
        
        bot = message.bot
        
        # Clear and set new commands
        await bot.delete_my_commands()
        await setup_bot_commands(bot)
        await setup_menu_button(bot)
        
        await message.answer(
            "✅ Commandes mises à jour!\n\n"
            "Disponibles:\n"
            "/menu\n"
            "/confirmations\n"
            "/parlay_settings\n"
            "/parlays\n"
            "/report_odds\n\n"
            "Ferme et rouvre Telegram pour voir les changements."
        )
        
    except Exception as e:
        logger.error(f"Error updating commands: {e}")
        await message.answer(f"❌ Erreur: {e}")
