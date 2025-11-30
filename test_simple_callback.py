"""
Test ultra simple pour voir si les callbacks fonctionnent
"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from aiogram import Bot, Dispatcher, F, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_CHAT_ID = int(os.getenv('ADMIN_CHAT_ID', '0'))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Simple callback handler
@dp.callback_query(F.data == "test_simple")
async def test_simple_callback(callback: types.CallbackQuery):
    print("✅ SIMPLE CALLBACK WORKED!")
    await callback.answer("✅ ÇA MARCHE!", show_alert=True)

@dp.callback_query(F.data.startswith("test_"))
async def test_prefix_callback(callback: types.CallbackQuery):
    print(f"✅ PREFIX CALLBACK WORKED! Data: {callback.data}")
    await callback.answer(f"✅ Reçu: {callback.data}", show_alert=True)

async def send_test():
    """Send test message with buttons"""
    keyboard = [
        [InlineKeyboardButton(text="🔴 Test Simple", callback_data="test_simple")],
        [InlineKeyboardButton(text="🟡 Test Prefix", callback_data="test_prefix_123")],
        [InlineKeyboardButton(text="🟢 Test Middle", callback_data="midnew_bet_xyz")]
    ]
    
    await bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text="🧪 <b>TEST CALLBACKS SIMPLES</b>\n\nClique pour tester:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode=ParseMode.HTML
    )
    print("📤 Message test envoyé!")

async def main():
    print("🚀 Démarrage bot de test...")
    
    # Send test message
    await send_test()
    
    # Start polling
    print("👂 En attente des callbacks...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot arrêté")
