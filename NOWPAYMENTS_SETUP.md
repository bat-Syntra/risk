# Configuration NOWPayments - Paiements Crypto Automatisés

## Pourquoi NOWPayments?

✅ **150+ cryptos** supportées (BTC, ETH, USDT, SOL, TON, DOGE, etc.)  
✅ **API complète** avec webhooks pour automatisation  
✅ **Pas de KYC** requis pour commencer  
✅ **Frais bas** - 0.5% par transaction  
✅ **Paiements instantanés** via Lightning Network  
✅ **Conversion auto** en stablecoin ou fiat si besoin  

## Étape 1: Créer un Compte NOWPayments

1. Va sur https://nowpayments.io
2. Clique "Sign Up"
3. Crée un compte (email + password)
4. Vérifie ton email
5. Va dans Dashboard

## Étape 2: Obtenir les API Keys

1. Dans le Dashboard, va dans **Settings → API Keys**
2. Génère une nouvelle API Key
3. Copie:
   - `API Key` (pour faire des requêtes)
   - `IPN Secret` (pour vérifier les webhooks)

4. Ajoute dans `.env`:
```bash
# NOWPayments Configuration
NOWPAYMENTS_API_KEY=FR3N5NM-A9J4CVZ-GRFP0EZ-Y26SF5R
NOWPAYMENTS_IPN_SECRET=qNwqHASSdC4DGwWPZCNKFWo3YXCo5elv
NOWPAYMENTS_SANDBOX=False  # True pour tester, False pour production
```

## Étape 3: Configurer le Webhook (IPN)

Le webhook permet à NOWPayments de notifier ton bot quand un paiement est confirmé.

1. Dans NOWPayments Dashboard → **Settings → IPN**
2. IPN Callback URL: `https://ton-domaine.com/webhook/nowpayments`
3. Active IPN

**Note:** Tu dois avoir un domaine public. Si tu utilises localhost, utilise **ngrok** pour tester:
```bash
# Installer ngrok
brew install ngrok

# Exposer ton bot
ngrok http 8080

# URL webhook sera: https://xxxx.ngrok.io/webhook/nowpayments
```

## Étape 4: Code d'Intégration

### 4.1 Installer la librairie NOWPayments

```bash
source .venv/bin/activate
pip install nowpayments-api
```

Ou ajoute dans `requirements.txt`:
```
nowpayments-api
```

### 4.2 Créer le module de paiement

Crée `bot/nowpayments_handler.py`:

```python
import os
import hmac
import hashlib
from nowpayments import NOWPayments
from datetime import datetime, timedelta
from database import SessionLocal
from models.user import User, TierLevel

# Init NOWPayments
NOWPAYMENTS_API_KEY = os.getenv("NOWPAYMENTS_API_KEY")
NOWPAYMENTS_IPN_SECRET = os.getenv("NOWPAYMENTS_IPN_SECRET")
SANDBOX = os.getenv("NOWPAYMENTS_SANDBOX", "False") == "True"

nowpayments = NOWPayments(NOWPAYMENTS_API_KEY, sandbox=SANDBOX)

class NOWPaymentsManager:
    
    @staticmethod
    async def create_payment(telegram_id: int, price_cad: float, email: str = None):
        """
        Create a payment invoice for PREMIUM subscription
        
        Args:
            telegram_id: User's Telegram ID
            price_cad: Price in CAD
            email: Optional email for receipt
            
        Returns:
            Payment URL and invoice ID
        """
        try:
            # Convert CAD to USD (NOWPayments uses USD)
            # 200 CAD ≈ 145 USD (update with real rate or use API)
            price_usd = price_cad * 0.73
            
            # Create payment
            payment = nowpayments.create_payment(
                price_amount=price_usd,
                price_currency="usd",
                pay_currency="btc",  # Default, user can choose others
                order_id=f"premium_{telegram_id}_{int(datetime.now().timestamp())}",
                order_description=f"Risk0 Casino PREMIUM - 1 month",
                ipn_callback_url=os.getenv("NOWPAYMENTS_IPN_URL"),
                success_url="https://t.me/YourBotUsername",
                cancel_url="https://t.me/YourBotUsername"
            )
            
            return {
                "payment_url": payment["invoice_url"],
                "payment_id": payment["payment_id"],
                "order_id": payment["order_id"]
            }
            
        except Exception as e:
            print(f"Error creating NOWPayments invoice: {e}")
            return None
    
    @staticmethod
    def verify_ipn_signature(request_body: bytes, signature: str) -> bool:
        """
        Verify IPN webhook signature from NOWPayments
        
        Args:
            request_body: Raw request body
            signature: X-NOWPayments-Sig header
            
        Returns:
            True if signature is valid
        """
        expected_sig = hmac.new(
            NOWPAYMENTS_IPN_SECRET.encode(),
            request_body,
            hashlib.sha512
        ).hexdigest()
        
        return hmac.compare_digest(expected_sig, signature)
    
    @staticmethod
    async def handle_payment_confirmation(payment_data: dict):
        """
        Handle confirmed payment from IPN webhook
        
        Args:
            payment_data: Payment data from NOWPayments IPN
        """
        try:
            # Extract order_id: "premium_123456789_1234567890"
            order_id = payment_data.get("order_id", "")
            if not order_id.startswith("premium_"):
                return
            
            parts = order_id.split("_")
            telegram_id = int(parts[1])
            
            # Update user to PREMIUM
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.telegram_id == telegram_id).first()
                if user:
                    user.tier = TierLevel.PREMIUM
                    user.subscription_start = datetime.now()
                    user.subscription_end = datetime.now() + timedelta(days=30)
                    db.commit()
                    
                    # TODO: Send confirmation message to user
                    print(f"✅ User {telegram_id} upgraded to PREMIUM")
            finally:
                db.close()
                
        except Exception as e:
            print(f"Error handling payment confirmation: {e}")
```

### 4.3 Ajouter le webhook endpoint dans `main_new.py`

```python
from fastapi import Request, Header
from bot.nowpayments_handler import NOWPaymentsManager

@app.post("/webhook/nowpayments")
async def nowpayments_webhook(
    request: Request,
    x_nowpayments_sig: str = Header(None)
):
    """
    Receive payment confirmation from NOWPayments
    """
    body = await request.body()
    
    # Verify signature
    if not NOWPaymentsManager.verify_ipn_signature(body, x_nowpayments_sig):
        return {"status": "error", "message": "Invalid signature"}
    
    # Parse payment data
    import json
    payment_data = json.loads(body)
    
    # Check payment status
    if payment_data.get("payment_status") == "finished":
        await NOWPaymentsManager.handle_payment_confirmation(payment_data)
        return {"status": "success"}
    
    return {"status": "received"}
```

### 4.4 Mettre à jour `bot/handlers.py`

```python
from bot.nowpayments_handler import NOWPaymentsManager

@router.callback_query(F.data == "buy_premium")
async def callback_buy_premium(callback: types.CallbackQuery):
    """Handle PREMIUM tier purchase via NOWPayments"""
    await callback.answer()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if not user:
            await callback.answer("Please send /start", show_alert=True)
            return
        
        # Create payment invoice
        payment = await NOWPaymentsManager.create_payment(
            telegram_id=callback.from_user.id,
            price_cad=200
        )
        
        if not payment:
            await callback.answer("Error creating payment. Contact support.", show_alert=True)
            return
        
        lang = user.language or "en"
        
        if lang == "fr":
            payment_text = (
                f"💎 <b>PREMIUM - 200 CAD/mois</b>\n\n"
                f"💰 Clique sur le bouton ci-dessous pour payer avec crypto.\n\n"
                f"✅ Plus de 150 cryptos acceptées\n"
                f"⚡ Activation automatique après paiement\n"
                f"🔐 Paiement sécurisé et anonyme\n\n"
                f"📱 Ton ID: <code>{callback.from_user.id}</code>"
            )
            pay_text = "💳 Payer Maintenant"
            back_text = "◀️ Retour"
        else:
            payment_text = (
                f"💎 <b>PREMIUM - 200 CAD/month</b>\n\n"
                f"💰 Click the button below to pay with crypto.\n\n"
                f"✅ 150+ cryptos accepted\n"
                f"⚡ Auto-activation after payment\n"
                f"🔐 Secure and anonymous\n\n"
                f"📱 Your ID: <code>{callback.from_user.id}</code>"
            )
            pay_text = "💳 Pay Now"
            back_text = "◀️ Back"
        
        keyboard = [
            [InlineKeyboardButton(text=pay_text, url=payment["payment_url"])],
            [InlineKeyboardButton(text=back_text, callback_data="show_tiers")]
        ]
        
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        await BotMessageManager.send_or_edit(
            event=callback,
            text=payment_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )
    finally:
        db.close()
```

## Étape 5: Variables d'Environnement

Ajoute dans `.env`:

```bash
# NOWPayments
NOWPAYMENTS_API_KEY=your_api_key_here
NOWPAYMENTS_IPN_SECRET=your_ipn_secret_here
NOWPAYMENTS_IPN_URL=https://your-domain.com/webhook/nowpayments
NOWPAYMENTS_SANDBOX=False
```

## Étape 6: Test en Sandbox

1. Active le mode Sandbox: `NOWPAYMENTS_SANDBOX=True`
2. Utilise les API keys de sandbox depuis NOWPayments
3. Teste un paiement
4. Vérifie que le webhook arrive bien
5. Vérifie que l'utilisateur est upgradé à PREMIUM

## Avantages de l'Automatisation

✅ **Zéro intervention manuelle** - Tout est automatique  
✅ **Scalable** - Peut gérer 1000+ paiements/jour  
✅ **Instantané** - L'utilisateur est activé dès confirmation  
✅ **Tracking** - Historique complet des paiements dans NOWPayments  
✅ **Multi-crypto** - L'utilisateur choisit sa crypto préférée  

## Support et Documentation

- NOWPayments Docs: https://documenter.getpostman.com/view/7907941/S1a32n38
- NOWPayments API: https://nowpayments.io/api-documentation
- Support NOWPayments: support@nowpayments.io
- Telegram Support: @NOWPayments_bot

## Prix et Frais

- **Pas de frais fixes** - Seulement des frais par transaction
- **0.5%** par transaction (très compétitif)
- **Pas de setup fee**
- **Pas de frais mensuels**

## Alternative: Liens de Paiement Simples

Si tu ne veux pas coder l'API, NOWPayments permet aussi de créer des liens de paiement manuellement:

1. Dashboard → **Payment Links**
2. Créer un lien pour 200 CAD
3. Partager le lien aux utilisateurs
4. Check manuellement les paiements et upgrade via `/admin`

C'est moins automatisé mais plus simple pour commencer!
