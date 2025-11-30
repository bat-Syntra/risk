import os
import hmac
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, Dict

import aiohttp
from dotenv import load_dotenv

from database import SessionLocal
from models.user import User, TierLevel as ModelTierLevel

load_dotenv()

NOWPAYMENTS_API_KEY = os.getenv("NOWPAYMENTS_API_KEY", "")
NOWPAYMENTS_IPN_SECRET = os.getenv("NOWPAYMENTS_IPN_SECRET", "")
NOWPAYMENTS_IPN_URL = os.getenv("NOWPAYMENTS_IPN_URL", "")
NOWPAYMENTS_SANDBOX = os.getenv("NOWPAYMENTS_SANDBOX", "False").lower() == "true"

API_BASE = "https://api.nowpayments.io"
if NOWPAYMENTS_SANDBOX:
    API_BASE = "https://api-sandbox.nowpayments.io"

# Simple in-memory mapping in case you want to correlate later
PAYMENT_MAP: Dict[str, int] = {}


class NOWPaymentsManager:
    @staticmethod
    async def create_invoice(telegram_id: int, amount_cad: float, success_url: Optional[str] = None,
                              cancel_url: Optional[str] = None) -> Optional[dict]:
        """
        Create a NOWPayments invoice for the given Telegram user.
        Returns dict with invoice_url, id, and order_id.
        """
        if not NOWPAYMENTS_API_KEY:
            return None
        headers = {
            "x-api-key": NOWPAYMENTS_API_KEY,
            "Content-Type": "application/json",
        }
        order_id = f"premium_{telegram_id}_{int(datetime.now().timestamp())}"
        payload = {
            "price_amount": float(amount_cad),
            "price_currency": "cad",
            "order_id": order_id,
            "order_description": "Risk0 Casino PREMIUM - 1 month",
        }
        if success_url:
            payload["success_url"] = success_url
        if cancel_url:
            payload["cancel_url"] = cancel_url
        if NOWPAYMENTS_IPN_URL:
            payload["ipn_callback_url"] = NOWPAYMENTS_IPN_URL
        url = f"{API_BASE}/v1/invoice"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, data=json.dumps(payload)) as resp:
                    if resp.status in (200, 201):
                        data = await resp.json()
                        # {'id': '...', 'invoice_url': '...', 'order_id': '...'}
                        invoice_id = data.get("id") or data.get("invoice_id")
                        inv_order_id = data.get("order_id") or order_id
                        if invoice_id:
                            PAYMENT_MAP[str(invoice_id)] = telegram_id
                        return {
                            "invoice_url": data.get("invoice_url"),
                            "invoice_id": invoice_id,
                            "order_id": inv_order_id,
                        }
                    else:
                        try:
                            err = await resp.text()
                        except Exception:
                            err = str(resp.status)
                        print(f"NOWPayments invoice error: {resp.status} -> {err}")
                        return None
        except Exception as e:
            print(f"NOWPayments create_invoice exception: {e}")
            return None

    @staticmethod
    def verify_ipn_signature(raw_body: bytes, signature: str) -> bool:
        if not NOWPAYMENTS_IPN_SECRET:
            return False
        calc = hmac.new(NOWPAYMENTS_IPN_SECRET.encode(), raw_body, hashlib.sha512).hexdigest()
        return hmac.compare_digest(calc, signature or "")

    @staticmethod
    def activate_premium(telegram_id: int) -> bool:
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                return False
            user.tier = ModelTierLevel.PREMIUM
            user.subscription_start = datetime.now()
            user.subscription_end = datetime.now() + timedelta(days=30)
            db.commit()
            
            # 🔔 Notify admin of new PREMIUM member
            import asyncio
            import os
            from aiogram import Bot
            
            admin_id = os.getenv("ADMIN_CHAT_ID")
            if admin_id:
                try:
                    bot_token = os.getenv("BOT_TOKEN")
                    bot = Bot(token=bot_token)
                    
                    username = user.username or "N/A"
                    message = (
                        "🎉 <b>NOUVEAU MEMBRE ALPHA!</b>\n\n"
                        f"👤 User: @{username}\n"
                        f"🆔 ID: <code>{telegram_id}</code>\n"
                        f"📅 Expire: {user.subscription_end.strftime('%Y-%m-%d')}\n\n"
                        f"💰 Paiement reçu via NOWPayments ✅\n"
                        f"🔥 Membre activé automatiquement!"
                    )
                    
                    # Run async in sync context
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(bot.send_message(int(admin_id), message, parse_mode="HTML"))
                    loop.run_until_complete(bot.session.close())
                    loop.close()
                except Exception as e:
                    print(f"Error notifying admin: {e}")
            
            return True
        finally:
            db.close()
