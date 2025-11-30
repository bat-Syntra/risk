#!/usr/bin/env python3
"""
Script de debug pour voir TOUS les messages/photos reçus par le bot
"""
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

async def handle_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log tous les messages reçus"""
    chat_id = update.effective_chat.id if update.effective_chat else "UNKNOWN"
    user = update.effective_user
    username = user.username if user else "UNKNOWN"
    
    # Type de message
    msg_type = "TEXT"
    if update.message and update.message.photo:
        msg_type = "PHOTO"
    elif update.message and update.message.document:
        msg_type = "DOCUMENT"
    
    text = update.message.text if update.message and update.message.text else ""
    
    print("\n" + "="*60)
    print(f"📨 MESSAGE REÇU")
    print(f"Chat ID: {chat_id}")
    print(f"User: @{username} (ID: {user.id if user else 'N/A'})")
    print(f"Type: {msg_type}")
    if text:
        print(f"Texte: {text[:100]}")
    print("="*60 + "\n")

async def handle_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler spécifique pour les photos"""
    chat_id = update.effective_chat.id if update.effective_chat else "UNKNOWN"
    print("\n" + "🖼️ "*20)
    print(f"🖼️ PHOTO DÉTECTÉE dans chat_id={chat_id}")
    print("🖼️ "*20 + "\n")

def main():
    print("="*60)
    print("🔍 BOT DEBUG - Écoute TOUS les messages")
    print("="*60)
    print("Ce bot va logger TOUT ce qu'il reçoit.")
    print("Envoie une photo dans n'importe quel groupe où le bot est membre.")
    print("="*60 + "\n")
    
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Handler pour TOUTES les photos (n'importe quel chat)
    app.add_handler(MessageHandler(filters.PHOTO, handle_photos))
    
    # Handler pour TOUS les messages
    app.add_handler(MessageHandler(filters.ALL, handle_all_messages))
    
    print("✅ Bot démarré - en écoute...\n")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
