"""
Casino Menu Handlers
Shows all 18 partner casinos with referral links
"""
from aiogram import Router, F, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode

from core.casinos import CASINOS
from core.languages import Translations
from database import SessionLocal
from models.user import User

router = Router()


@router.callback_query(F.data == "show_casinos")
async def show_casinos_menu(callback: types.CallbackQuery):
    """
    Display menu with all 18 casinos and referral links
    """
    user = callback.from_user
    db = SessionLocal()
    
    try:
        # Get user language
        db_user = db.query(User).filter(User.telegram_id == user.id).first()
        lang = db_user.language if db_user else "fr"
        
        # Build message
        message = Translations.get('casinos_title', lang) + "\n\n"
        message += Translations.get('casinos_desc', lang) + "\n\n"
        
        # List all casinos with emojis
        for casino_key, casino_info in CASINOS.items():
            logo = casino_info['logo']
            name = casino_info['name']
            message += f"{logo} {name}\n"
        
        message += "\n" + Translations.get('casinos_footer', lang)
        
        # Build keyboard - 2 casinos per row
        keyboard = []
        casino_items = list(CASINOS.items())
        
        for i in range(0, len(casino_items), 2):
            row = []
            for j in range(2):
                if i + j < len(casino_items):
                    casino_key, casino_info = casino_items[i + j]
                    row.append(InlineKeyboardButton(
                        text=f"{casino_info['logo']} {casino_info['name']}",
                        url=casino_info['referral_link']
                    ))
            keyboard.append(row)
        
        # Back button
        keyboard.append([
            InlineKeyboardButton(
                text=Translations.get('btn_back', lang),
                callback_data="main_menu"
            )
        ])
        
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        await callback.message.edit_text(
            text=message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
        
        await callback.answer()
        
    finally:
        db.close()
