"""
Fix pour que les alertes Middle et Good EV soient envoyées correctement
Le problème est que l'enrichment API peut échouer silencieusement
"""

def add_logging_to_handlers():
    """Ajoute du logging détaillé aux handlers Middle et Good EV"""
    
    # Dans handle_positive_ev, ligne ~1559
    changes_good_ev = """
    try:
        msg_sent = await bot.send_message(
            chat_id=user.telegram_id,
            text=message,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode=ParseMode.HTML
        )
        sent_count += 1
        logger.info(f"✅ Good EV sent to {user.telegram_id}")
    except Exception as e:
        logger.error(f"❌ Failed to send Good Odds to user {user.telegram_id}: {e}")
        # Afficher plus de détails sur l'erreur
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
    """
    
    # Dans handle_middle, ligne ~1776
    changes_middle = """
    try:
        msg_sent = await bot.send_message(
            chat_id=user.telegram_id,
            text=message,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode=ParseMode.HTML
        )
        sent_count += 1
        logger.info(f"✅ Middle sent to {user.telegram_id}")
    except Exception as e:
        logger.error(f"❌ Failed to send Middle to user {user.telegram_id}: {e}")
        # Afficher plus de détails sur l'erreur
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
    """
    
    print("Changements à faire:")
    print("1. Ajouter logging détaillé dans handle_positive_ev")
    print("2. Ajouter logging détaillé dans handle_middle")
    print("3. Vérifier que l'enrichment API ne casse pas la structure")

if __name__ == "__main__":
    add_logging_to_handlers()
