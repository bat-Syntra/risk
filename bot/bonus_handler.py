"""
Bonus Marketing System - Handler for /bonus command and marketing automation
"""
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from database import DATABASE_URL, SessionLocal
from models.user import User, TierLevel
import logging
import os

logger = logging.getLogger(__name__)
router = Router()


class BonusManager:
    """Manage bonus eligibility and activation"""
    
    @staticmethod
    def check_eligibility(telegram_id: int) -> dict:
        """
        Check if user is eligible for $50 bonus
        Eligible if: started < 2 days ago AND never had bonus before
        """
        db = SessionLocal()
        try:
            # Get user's creation date and tier
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                return {
                    'eligible': False,
                    'reason': 'user_not_found',
                    'message_fr': "❌ Utilisateur non trouvé. Utilise /start d'abord.",
                    'message_en': "❌ User not found. Use /start first."
                }
            
            # CRITICAL: Bonus is ONLY for FREE users, not PREMIUM/LIFETIME
            if user.tier != TierLevel.FREE:
                return {
                    'eligible': False,
                    'reason': 'not_free_user',
                    'message_fr': "❌ Le bonus est réservé aux membres GRATUIT uniquement.",
                    'message_en': "❌ Bonus is for FREE members only."
                }
            
            # Check bonus_tracking table
            result = db.execute(text("""
                SELECT * FROM bonus_tracking 
                WHERE telegram_id = :tid
            """), {'tid': telegram_id}).first()
            
            # If no record, create one with user's creation date
            if not result:
                # Calculate if eligible (< 2 days since creation)
                days_since_start = (datetime.now() - user.created_at).total_seconds() / 86400
                is_eligible = days_since_start < 2
                
                db.execute(text("""
                    INSERT INTO bonus_tracking 
                    (telegram_id, started_at, bonus_eligible, ever_had_bonus)
                    VALUES (:tid, :started, :eligible, 0)
                """), {
                    'tid': telegram_id,
                    'started': user.created_at,
                    'eligible': is_eligible
                })
                db.commit()
                
                if is_eligible:
                    return {
                        'eligible': True,
                        'days_left': 2 - days_since_start,
                        'new_user': True
                    }
                else:
                    return {
                        'eligible': False,
                        'reason': 'too_late',
                        'days_since_start': days_since_start
                    }
            
            # User has record, check status
            # IMPORTANT: Check if bonus is activated FIRST before checking ever_had_bonus
            if result.bonus_activated_at:
                # Parse datetime strings from SQLite
                expires_at = result.bonus_expires_at
                if isinstance(expires_at, str):
                    expires_at = datetime.fromisoformat(expires_at)
                
                if datetime.now() < expires_at:
                    # Bonus active and not expired - show remaining time
                    time_left = expires_at - datetime.now()
                    return {
                        'eligible': True,
                        'activated': True,
                        'time_left': time_left,
                        'expires_at': expires_at
                    }
                else:
                    # Bonus expired
                    return {
                        'eligible': False,
                        'reason': 'expired',
                        'message_fr': "❌ Ton bonus a expiré.",
                        'message_en': "❌ Your bonus has expired."
                    }
            
            if result.bonus_redeemed:
                return {
                    'eligible': False,
                    'reason': 'already_redeemed',
                    'message_fr': "✅ Tu as déjà utilisé ton bonus!",
                    'message_en': "✅ You already used your bonus!"
                }
            
            if result.ever_had_bonus:
                return {
                    'eligible': False,
                    'reason': 'already_used',
                    'message_fr': "❌ Tu as déjà bénéficié d'un bonus dans le passé.",
                    'message_en': "❌ You already benefited from a bonus in the past."
                }
            
            # Check if eligible (< 2 days since start)
            if result.bonus_eligible:
                return {
                    'eligible': True,
                    'activated': False,
                    'new_user': False
                }
            else:
                return {
                    'eligible': False,
                    'reason': 'not_eligible',
                    'message_fr': "❌ Tu n'es plus éligible au bonus (> 2 jours depuis inscription).",
                    'message_en': "❌ You're no longer eligible for the bonus (> 2 days since signup)."
                }
                
        finally:
            db.close()
    
    @staticmethod
    def activate_bonus(telegram_id: int) -> bool:
        """Activate bonus for user - sets expiry to 7 days from now"""
        db = SessionLocal()
        try:
            now = datetime.now()
            expires_at = now + timedelta(days=7)
            
            db.execute(text("""
                UPDATE bonus_tracking 
                SET bonus_activated_at = :now,
                    bonus_expires_at = :expires,
                    ever_had_bonus = 1,
                    updated_at = :now
                WHERE telegram_id = :tid
            """), {
                'tid': telegram_id,
                'now': now,
                'expires': expires_at
            })
            db.commit()
            
            logger.info(f"✅ Bonus activated for user {telegram_id}, expires at {expires_at}")
            return True
        except Exception as e:
            logger.error(f"Error activating bonus for {telegram_id}: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    @staticmethod
    def redeem_bonus(telegram_id: int) -> bool:
        """Mark bonus as redeemed when user purchases"""
        db = SessionLocal()
        try:
            now = datetime.now()
            db.execute(text("""
                UPDATE bonus_tracking 
                SET bonus_redeemed = 1,
                    bonus_redeemed_at = :now,
                    updated_at = :now
                WHERE telegram_id = :tid
            """), {
                'tid': telegram_id,
                'now': now
            })
            db.commit()
            
            logger.info(f"✅ Bonus redeemed for user {telegram_id}")
            return True
        except Exception as e:
            logger.error(f"Error redeeming bonus for {telegram_id}: {e}")
            db.rollback()
            return False
        finally:
            db.close()


@router.message(Command("bonus"))
async def handle_bonus_command(message: types.Message):
    """Handle /bonus command - check and activate bonus eligibility"""
    user_id = message.from_user.id
    
    # Get user language
    db = SessionLocal()
    user = db.query(User).filter(User.telegram_id == user_id).first()
    lang = user.language if user else 'en'
    db.close()
    
    # Check eligibility
    eligibility = BonusManager.check_eligibility(user_id)
    
    if not eligibility['eligible']:
        # Not eligible - show reason
        reason = eligibility.get('reason', 'unknown')
        
        if reason in ['user_not_found', 'already_used', 'already_redeemed', 'expired', 'not_eligible']:
            await message.answer(
                eligibility.get('message_fr' if lang == 'fr' else 'message_en', 
                              "❌ Non éligible au bonus." if lang == 'fr' else "❌ Not eligible for bonus."),
                parse_mode=ParseMode.HTML
            )
        else:
            text = (
                "❌ <b>BONUS NON DISPONIBLE</b>\n\n"
                "Tu n'es pas éligible au bonus de $50.\n\n"
                "Le bonus est réservé aux nouveaux membres (< 2 jours)."
                if lang == 'fr' else
                "❌ <b>BONUS NOT AVAILABLE</b>\n\n"
                "You're not eligible for the $50 bonus.\n\n"
                "Bonus is reserved for new members (< 2 days)."
            )
            await message.answer(text, parse_mode=ParseMode.HTML)
        return
    
    # Eligible! Check if already activated
    if eligibility.get('activated'):
        # Bonus already activated - show remaining time
        time_left = eligibility.get('time_left')
        total_hours = int(time_left.total_seconds() // 3600)
        days_left = total_hours // 24
        hours_left = total_hours % 24
        
        # Format time display
        if days_left > 0:
            time_display = f"{days_left} jour{'s' if days_left > 1 else ''} {hours_left}h" if lang == 'fr' else f"{days_left} day{'s' if days_left > 1 else ''} {hours_left}h"
        else:
            time_display = f"{hours_left}h" if lang == 'fr' else f"{hours_left}h"
        
        text = (
            f"🎁 <b>BONUS ACTIF!</b>\n\n"
            f"Ton rabais de $50 est actif!\n\n"
            f"⏰ Expire dans: <b>{time_display}</b>\n\n"
            f"<s>$200</s> <b>$150 CAD/mois</b>\n"
            f"(Premier mois seulement)\n\n"
            f"Clique sur 'Acheter ALPHA' pour profiter du bonus!"
            if lang == 'fr' else
            f"🎁 <b>BONUS ACTIVE!</b>\n\n"
            f"Your $50 discount is active!\n\n"
            f"⏰ Expires in: <b>{time_display}</b>\n\n"
            f"<s>$200</s> <b>$150 CAD/month</b>\n"
            f"(First month only)\n\n"
            f"Click 'Buy ALPHA' to use your bonus!"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🚀 Acheter ALPHA ($150)" if lang == 'fr' else "🚀 Buy ALPHA ($150)",
                callback_data="upgrade_premium"
            )],
            [InlineKeyboardButton(
                text="📱 Menu Principal" if lang == 'fr' else "📱 Main Menu",
                callback_data="main_menu"
            )]
        ])
        
        await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    else:
        # Eligible but not yet activated - activate now!
        BonusManager.activate_bonus(user_id)
        
        # Send notification to admin
        try:
            admin_id = int(os.getenv("ADMIN_ID", "8213628656"))
            db = SessionLocal()
            user_obj = db.query(User).filter(User.telegram_id == user_id).first()
            db.close()
            
            username = f"@{user_obj.username}" if user_obj and user_obj.username else f"User {user_id}"
            admin_text = (
                f"🎁 <b>NOUVEAU BONUS ACTIVÉ!</b>\n\n"
                f"👤 Utilisateur: {username}\n"
                f"🆔 ID: {user_id}\n"
                f"⏰ Expire dans: <b>7 jours</b>\n\n"
                f"Le user peut maintenant acheter ALPHA à $150 au lieu de $200!"
            )
            await message.bot.send_message(admin_id, admin_text, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Error sending admin notification: {e}")
        
        text = (
            "🎉 <b>FÉLICITATIONS!</b>\n\n"
            "✅ Ton bonus de $50 est maintenant ACTIVÉ!\n\n"
            "⏰ <b>Expire dans: 7 jours</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💰 <b>TARIF SPÉCIAL:</b>\n"
            "<s>$200</s> <b>$150 CAD/mois</b> 🎁\n"
            "(Premier mois seulement)\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🚀 <b>CE QUE TU DÉVEROUILLES:</b>\n\n"
            "✅ Calls arbitrage illimités\n"
            "✅ Middle Bets + Good Odds\n"
            "✅ Parlays optimisés (Beta)\n"
            "✅ Mode RISKED (profits 2-3x)\n"
            "✅ Dashboard statistiques\n"
            "✅ Last Call (24h history)\n"
            "✅ Support VIP prioritaire\n"
            "✅ Referral 20% à vie\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚠️ <b>ATTENTION:</b>\n"
            "Le bonus expire dans 7 jours!\n\n"
            "Profite-en maintenant pour économiser $50! 💰"
            if lang == 'fr' else
            "🎉 <b>CONGRATULATIONS!</b>\n\n"
            "✅ Your $50 bonus is now ACTIVATED!\n\n"
            "⏰ <b>Expires in: 7 days</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💰 <b>SPECIAL PRICE:</b>\n"
            "<s>$200</s> <b>$150 CAD/month</b> 🎁\n"
            "(First month only)\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🚀 <b>WHAT YOU UNLOCK:</b>\n\n"
            "✅ Unlimited arbitrage calls\n"
            "✅ Middle Bets + Good Odds\n"
            "✅ Optimized Parlays (Beta)\n"
            "✅ RISKED mode (2-3x profits)\n"
            "✅ Statistics dashboard\n"
            "✅ Last Call (24h history)\n"
            "✅ VIP priority support\n"
            "✅ 20% referral for life\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚠️ <b>WARNING:</b>\n"
            "Bonus expires in 7 days!\n\n"
            "Take advantage now to save $50! 💰"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🚀 Acheter ALPHA ($150)" if lang == 'fr' else "🚀 Buy ALPHA ($150)",
                callback_data="upgrade_premium"
            )],
            [InlineKeyboardButton(
                text="💬 Questions?" if lang == 'fr' else "💬 Questions?",
                callback_data="contact_support"
            )],
            [InlineKeyboardButton(
                text="📱 Menu Principal" if lang == 'fr' else "📱 Main Menu",
                callback_data="main_menu"
            )]
        ])
        
        await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


@router.callback_query(F.data == "bonus_unsubscribe")
async def handle_bonus_unsubscribe(callback: types.CallbackQuery):
    """Handle unsubscribe from bonus marketing campaign"""
    await callback.answer()
    
    user_id = callback.from_user.id
    
    # Get user language
    db = SessionLocal()
    user = db.query(User).filter(User.telegram_id == user_id).first()
    lang = user.language if user else 'en'
    
    # Expire the bonus immediately to stop campaign
    try:
        db.execute(text("""
            UPDATE bonus_tracking
            SET bonus_expires_at = datetime('now'),
                updated_at = datetime('now')
            WHERE telegram_id = :tid
        """), {'tid': user_id})
        db.commit()
        
        text = (
            "✅ <b>Désabonné</b>\n\n"
            "Tu ne recevras plus de messages marketing sur le bonus.\n\n"
            "Tu peux toujours utiliser /bonus pour vérifier ton éligibilité."
            if lang == 'fr' else
            "✅ <b>Unsubscribed</b>\n\n"
            "You won't receive any more marketing messages about the bonus.\n\n"
            "You can still use /bonus to check your eligibility."
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="📱 Menu Principal" if lang == 'fr' else "📱 Main Menu",
                callback_data="main_menu"
            )]
        ])
        
        await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error unsubscribing {user_id} from bonus campaign: {e}")
        await callback.answer("Error. Please contact support.", show_alert=True)
    finally:
        db.close()
