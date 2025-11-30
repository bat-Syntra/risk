"""
Language Change Handlers
Toggle between French and English
"""
from aiogram import Router, F, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode

from core.languages import Translations, Language
from bot.commands_setup import set_user_commands
from database import SessionLocal
from models.user import User

router = Router()


@router.callback_query(F.data == "change_language")
async def show_language_menu(callback: types.CallbackQuery):
    """
    Show language selection menu
    """
    await callback.answer()
    user = callback.from_user
    db = SessionLocal()
    
    try:
        db_user = db.query(User).filter(User.telegram_id == user.id).first()
        
        if not db_user:
            await callback.answer("Error: User not found")
            return
        
        current_lang = db_user.language or 'en'
        
        # Show menu in both languages
        text = (
            "🌐 <b>CHOOSE YOUR LANGUAGE</b>\n"
            "🌐 <b>CHOISIS TA LANGUE</b>\n\n"
            f"Current / Actuel: <b>{'English 🇬🇧' if current_lang == 'en' else 'Français 🇫🇷'}</b>"
        )
        
        keyboard = [
            [InlineKeyboardButton(
                text="🇬🇧 English",
                callback_data="set_lang_en"
            )],
            [InlineKeyboardButton(
                text="🇫🇷 Français",
                callback_data="set_lang_fr"
            )],
            [InlineKeyboardButton(
                text="◀️ Back / Retour",
                callback_data="settings"
            )]
        ]
        
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        await callback.message.edit_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        
    finally:
        db.close()


@router.callback_query(F.data.startswith("set_lang_"))
async def set_language(callback: types.CallbackQuery):
    """
    Set user language to EN or FR
    """
    await callback.answer()
    user = callback.from_user
    db = SessionLocal()
    
    try:
        db_user = db.query(User).filter(User.telegram_id == user.id).first()
        
        if not db_user:
            await callback.answer("Error: User not found")
            return
        
        # Get selected language
        new_lang = "en" if callback.data == "set_lang_en" else "fr"
        db_user.language = new_lang
        db.commit()
        
        # Update per-chat commands to the new language
        try:
            await set_user_commands(callback.bot, callback.message.chat.id, new_lang)
        except Exception:
            pass

        # Show confirmation
        if new_lang == 'en':
            await callback.answer("✅ Language set to English", show_alert=True)
        else:
            await callback.answer("✅ Langue changée en Français", show_alert=True)
        
        # Return to settings
        from bot.handlers import callback_settings
        await callback_settings(callback)
        
    finally:
        db.close()
