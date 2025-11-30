"""
Multi-language system for the bot
Supports French and English
"""
from typing import Dict, Any


class Language:
    """Language codes"""
    FR = "fr"
    EN = "en"


class Translations:
    """All bot translations"""
    
    TEXTS = {
        # === WELCOME ===
        "welcome_title": {
            "fr": "🎰 <b>Bienvenue sur ArbitrageBot Canada!</b>",
            "en": "🎰 <b>Welcome to ArbitrageBot Canada!</b>"
        },
        "welcome_desc": {
            "fr": "💰 Profite d'arbitrages garantis sur 18 casinos canadiens.",
            "en": "💰 Enjoy guaranteed arbitrage on 18 Canadian casinos."
        },
        
        # === MAIN MENU ===
        "main_menu_title": {
            "fr": "🏠 <b>MENU PRINCIPAL</b>",
            "en": "🏠 <b>MAIN MENU</b>"
        },
        "main_menu_desc": {
            "fr": "Que veux-tu faire?",
            "en": "What do you want to do?"
        },
        
        # === BUTTONS ===
        "btn_stats": {
            "fr": "📊 Mes Stats",
            "en": "📊 My Stats"
        },
        "btn_settings": {
            "fr": "⚙️ Paramètres",
            "en": "⚙️ Settings"
        },
        "btn_tiers": {
            "fr": "💎 Tiers Premium",
            "en": "💎 Premium Tiers"
        },
        "btn_referral": {
            "fr": "🎁 Parrainage",
            "en": "🎁 Referral"
        },
        "btn_guide": {
            "fr": "📖 Guide",
            "en": "📖 Guide"
        },
        "btn_casinos": {
            "fr": "🎰 Casinos",
            "en": "🎰 Casinos"
        },
        "btn_language": {
            "fr": "🌍 English",
            "en": "🌍 Français"
        },
        "btn_back": {
            "fr": "◀️ Menu",
            "en": "◀️ Menu"
        },
        "btn_calculator": {
            "fr": "🧮 Calculateur",
            "en": "🧮 Calculator"
        },
        "btn_risked": {
            "fr": "⚠️ Mode RISKED",
            "en": "⚠️ RISKED Mode"
        },
        "btn_copy": {
            "fr": "📋 Copier",
            "en": "📋 Copy"
        },
        
        # === CASINOS MENU ===
        "casinos_title": {
            "fr": "🎰 <b>CASINOS PARTENAIRES</b>",
            "en": "🎰 <b>PARTNER CASINOS</b>"
        },
        "casinos_desc": {
            "fr": "Clique sur un casino pour t'inscrire ou te connecter.",
            "en": "Click on a casino to register or login."
        },
        "casinos_footer": {
            "fr": "✅ Tous les casinos sont légaux au Canada/Québec",
            "en": "✅ All casinos are legal in Canada/Quebec"
        },
        
        # === STATS ===
        "stats_title": {
            "fr": "📊 <b>TES STATISTIQUES</b>",
            "en": "📊 <b>YOUR STATISTICS</b>"
        },
        "stats_tier": {
            "fr": "🎖️ Tier: <b>{tier}</b>",
            "en": "🎖️ Tier: <b>{tier}</b>"
        },
        "stats_profit": {
            "fr": "💰 <b>Profit Total: ${profit}</b>",
            "en": "💰 <b>Total Profit: ${profit}</b>"
        },
        "stats_bets": {
            "fr": "📈 Bets placés: {count}",
            "en": "📈 Bets placed: {count}"
        },
        
        # === SETTINGS ===
        "settings_title": {
            "fr": "⚙️ <b>PARAMÈTRES</b>",
            "en": "⚙️ <b>SETTINGS</b>"
        },
        "settings_bankroll": {
            "fr": "💰 Bankroll: <b>${amount}</b>",
            "en": "💰 Bankroll: <b>${amount}</b>"
        },
        "settings_risk": {
            "fr": "🎯 Risk: <b>{percent}%</b>",
            "en": "🎯 Risk: <b>{percent}%</b>"
        },
        "settings_notif": {
            "fr": "🔔 Notifications: <b>{status}</b>",
            "en": "🔔 Notifications: <b>{status}</b>"
        },
        "settings_lang": {
            "fr": "🌍 Langue: <b>Français</b>",
            "en": "🌍 Language: <b>English</b>"
        },
        
        # === ALERT ===
        "alert_title": {
            "fr": "🚨 <b>ARBITRAGE ALERT - {percent}%</b> 🚨",
            "en": "🚨 <b>ARBITRAGE ALERT - {percent}%</b> 🚨"
        },
        "bankroll": {
            "fr": "💰 <b>Bankroll: ${amount}</b>",
            "en": "💰 <b>Bankroll: ${amount}</b>"
        },
        "guaranteed_profit": {
            "fr": "✅ <b>Profit Garanti: ${profit}</b>",
            "en": "✅ <b>Guaranteed Profit: ${profit}</b>"
        },
        "stake": {
            "fr": "💵 Miser: <code>${amount}</code>",
            "en": "💵 Stake: <code>${amount}</code>"
        },
        "return": {
            "fr": "Retour: ${amount}",
            "en": "Return: ${amount}"
        },
        
        # === LANGUAGE CHANGE ===
        "lang_changed": {
            "fr": "✅ <b>Langue changée!</b>\n\nNouvelle langue: <b>Français</b>",
            "en": "✅ <b>Language changed!</b>\n\nNew language: <b>English</b>"
        },
        
        # === COMMON ===
        "enabled": {
            "fr": "Activées",
            "en": "Enabled"
        },
        "disabled": {
            "fr": "Désactivées",
            "en": "Disabled"
        },
    }
    
    @staticmethod
    def get(key: str, lang: str = "fr", **kwargs) -> str:
        """
        Get translation for a key
        
        Args:
            key: Translation key
            lang: Language code (fr or en)
            **kwargs: Variables for string formatting
            
        Returns:
            Translated and formatted string
            
        Example:
            Translations.get("welcome_title", lang="fr")
            Translations.get("alert_title", lang="en", percent=5.16)
        """
        text = Translations.TEXTS.get(key, {}).get(lang, key)
        
        # Format with variables if present
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, ValueError):
                pass  # Return unformatted if error
        
        return text
    
    @staticmethod
    def get_user_language(telegram_id: int, db) -> str:
        """
        Get user's language preference from database
        
        Args:
            telegram_id: User's Telegram ID
            db: Database session
            
        Returns:
            Language code (fr or en)
        """
        from models.user import User
        
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        return user.language if user and user.language else Language.EN
