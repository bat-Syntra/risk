"""
Send all 7 marketing campaign messages to admin for preview
"""
import asyncio
import os
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8213628656"))


async def send_preview():
    """Send all 7 campaign messages to admin"""
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    # French messages (7 days)
    messages_fr = [
        # Day 1
        (
            "🎁 <b>RAPPEL: Ton bonus de $50 est actif!</b>\n\n"
            f"⏰ Expire dans <b>7 jours</b>\n\n"
            "Ne laisse pas passer cette occasion!\n\n"
            "<s>$200</s> <b>$150 CAD/mois</b>\n"
            "Premier mois seulement 💰\n\n"
            "Clique ci-dessous pour upgrader maintenant! 👇"
        ),
        # Day 2
        (
            "💡 <b>Tu savais que...</b>\n\n"
            "Les membres ALPHA font en moyenne $3,500-7,000/mois?\n\n"
            f"⏰ Ton bonus expire dans <b>6 jours</b>\n\n"
            "Économise $50 sur ton premier mois:\n"
            "<s>$200</s> <b>$150 CAD</b>\n\n"
            "C'est un retour de 20x sur investissement! 🚀"
        ),
        # Day 3
        (
            "🔥 <b>PLUS QUE QUELQUES JOURS!</b>\n\n"
            f"⏰ Ton bonus expire dans <b>5 jours</b>\n\n"
            "Ce que tu manques en restant GRATUIT:\n"
            "• Calls illimités (vs 5/jour)\n"
            "• Parlays optimisés (Beta)\n"
            "• Middle Bets + Good Odds\n"
            "• $200-300/jour en profit potentiel\n\n"
            "Économise $50 maintenant! 💰"
        ),
        # Day 4
        (
            "⚠️ <b>ATTENTION!</b>\n\n"
            f"Ton bonus de $50 expire dans <b>4 jours</b>!\n\n"
            "Chaque jour que tu attends = $100-300 de profit manqué\n\n"
            "<s>$200</s> <b>$150 CAD/mois</b>\n\n"
            "Ne laisse pas cette opportunité s'envoler! ⏰"
        ),
        # Day 5
        (
            "🎯 <b>DERNIÈRE CHANCE!</b>\n\n"
            f"⏰ <b>Expire dans 3 jours</b>\n\n"
            "Le rabais de $50 sur ALPHA\n"
            "ne sera plus disponible après!\n\n"
            "Rejoins les membres qui font\n"
            "$3,500-7,000/mois 💰\n\n"
            "Clique maintenant! 👇"
        ),
        # Day 6
        (
            "⏰ <b>URGENT - EXPIRE DEMAIN!</b>\n\n"
            f"Il te reste <b>2 jours</b>\n"
            "pour profiter de ton bonus de $50!\n\n"
            "<s>$200</s> <b>$150 CAD/mois</b>\n\n"
            "Après demain, tu paies plein prix.\n\n"
            "Ne manque pas cette chance! 🚨"
        ),
        # Day 7 (last day)
        (
            "🚨 <b>DERNIÈRES HEURES!</b>\n\n"
            f"⏰ Ton bonus expire dans <b>1 jour</b>!\n\n"
            "C'est ta DERNIÈRE CHANCE\n"
            "d'économiser $50 sur ALPHA!\n\n"
            "Après aujourd'hui = plein prix ($200/mois)\n\n"
            "AGIS MAINTENANT! ⚡"
        )
    ]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Acheter ALPHA ($150)", callback_data="upgrade_premium")],
        [InlineKeyboardButton(text="❌ Ne plus recevoir", callback_data="bonus_unsubscribe")]
    ])
    
    try:
        # Send intro message
        await bot.send_message(
            ADMIN_ID,
            "📧 <b>PREVIEW - 7 Messages Marketing Bonus</b>\n\n"
            "Voici les 7 messages que les users avec bonus actif vont recevoir (1 par jour pendant 7 jours):\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━",
            parse_mode=ParseMode.HTML
        )
        
        # Wait a bit
        await asyncio.sleep(1)
        
        # Send each message
        for day, message in enumerate(messages_fr, 1):
            header = f"📅 <b>JOUR {day}/7</b>\n\n"
            full_message = header + message
            
            await bot.send_message(
                ADMIN_ID,
                full_message,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
            
            # Wait between messages
            await asyncio.sleep(2)
        
        # Send summary
        await bot.send_message(
            ADMIN_ID,
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "✅ <b>FIN DES PREVIEWS</b>\n\n"
            "Ces messages sont envoyés automatiquement:\n"
            "• 1 message par jour pendant 7 jours\n"
            "• Seulement aux users avec bonus actif\n"
            "• S'arrête automatiquement si:\n"
            "  - User achète ALPHA\n"
            "  - Bonus expire\n"
            "  - User clique 'Ne plus recevoir'\n\n"
            "📊 Pour voir les stats:\n"
            "<code>SELECT * FROM bonus_tracking WHERE campaign_messages_sent > 0;</code>",
            parse_mode=ParseMode.HTML
        )
        
        print(f"✅ Preview sent to admin {ADMIN_ID}")
        
    except Exception as e:
        print(f"❌ Error sending preview: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(send_preview())
