"""
Verify Odds Handler - Real-time odds verification for alerts
Handles: verify_arb_, verify_middle_, verify_goodev_
"""
import json
from datetime import datetime, timedelta
from aiogram import Router, types, F
from aiogram.enums import ParseMode
from database import SessionLocal
from sqlalchemy import text

router = Router()

# Rate limiting: 1 verification per 5 minutes per user
rate_limits = {}

@router.callback_query(F.data.startswith("verify_arb_"))
@router.callback_query(F.data.startswith("verify_middle_"))
@router.callback_query(F.data.startswith("verify_goodev_"))
async def handle_verify_odds(callback: types.CallbackQuery):
    """Verify odds for arbitrage/middle/good_ev alerts"""
    
    user_id = callback.from_user.id
    
    # Rate limiting: 5 minutes
    rate_limit_key = f"verify_{user_id}"
    now = datetime.now()
    
    if rate_limit_key in rate_limits:
        last_check = rate_limits[rate_limit_key]
        time_since = (now - last_check).total_seconds()
        
        if time_since < 300:  # 5 minutes
            remaining = int(300 - time_since)
            minutes = remaining // 60
            seconds = remaining % 60
            await callback.answer(
                f"⏱️ Attendez {minutes}m {seconds}s avant de vérifier à nouveau",
                show_alert=True
            )
            return
    
    # Update rate limit
    rate_limits[rate_limit_key] = now
    
    await callback.answer("🔍 Vérification en cours...")
    
    # Parse callback data
    callback_data = callback.data
    
    if callback_data.startswith("verify_arb_"):
        drop_event_id = int(callback_data.replace("verify_arb_", ""))
        alert_type = "arbitrage"
    elif callback_data.startswith("verify_middle_"):
        event_id = callback_data.replace("verify_middle_", "")
        alert_type = "middle"
        drop_event_id = None  # Will query by event_id
    else:  # verify_goodev_
        event_id = callback_data.replace("verify_goodev_", "")
        alert_type = "good_ev"
        drop_event_id = None
    
    # Get drop from database
    db = SessionLocal()
    try:
        if drop_event_id:
            drop = db.execute(text("""
                SELECT * FROM drop_events WHERE id = :id
            """), {'id': drop_event_id}).fetchone()
        else:
            drop = db.execute(text("""
                SELECT * FROM drop_events WHERE event_id = :eid
            """), {'eid': event_id}).fetchone()
        
        if not drop:
            await callback.message.answer("❌ Alert not found in database")
            return
        
        # Parse payload
        payload = json.loads(drop.payload) if isinstance(drop.payload, str) else drop.payload or {}
        
        # Import verifier
        try:
            from utils.odds_verifier import OddsVerifier
            verifier = OddsVerifier()
        except:
            await callback.message.answer("❌ Service de vérification temporairement indisponible")
            return
        
        # Format outcomes for verification
        verification_legs = []
        
        if alert_type == "arbitrage":
            # Arbitrage has multiple outcomes
            outcomes = payload.get('outcomes', [])
            for outcome in outcomes:
                verification_legs.append({
                    'match': drop.match or payload.get('match', ''),
                    'sport': drop.league or 'Unknown',
                    'market': payload.get('market', 'Unknown'),
                    'odds': outcome.get('decimal_odds', outcome.get('odds_decimal', 2.0)),
                    'american_odds': outcome.get('odds', 100),
                    'bookmaker': outcome.get('book', outcome.get('bookmaker', 'Unknown')),
                    'time': payload.get('formatted_time', payload.get('commence_time', 'Unknown'))
                })
        
        elif alert_type == "middle":
            # Middle has 2 sides
            side_a = payload.get('side_a', {})
            side_b = payload.get('side_b', {})
            
            # Use the actual market type for player prop detection
            market_type = payload.get('market', f"{side_a.get('team', '')} {side_a.get('line', '')}")
            
            verification_legs.append({
                'match': f"{payload.get('team1', '')} vs {payload.get('team2', '')}",
                'sport': payload.get('league', 'Unknown'),
                'market': market_type,  # Ex: "Player Receiving Yards"
                'selection': f"{side_a.get('selection', '')} {side_a.get('line', '')}",  # Ex: "Over 31.5"
                'odds': side_a.get('decimal_odds', 2.0),
                'american_odds': side_a.get('odds', 100),
                'bookmaker': side_a.get('bookmaker', 'Unknown'),
                'time': payload.get('formatted_time', payload.get('commence_time', 'Unknown'))
            })
            
            verification_legs.append({
                'match': f"{payload.get('team1', '')} vs {payload.get('team2', '')}",
                'sport': payload.get('league', 'Unknown'),
                'market': market_type,  # Ex: "Player Receiving Yards"
                'selection': f"{side_b.get('selection', '')} {side_b.get('line', '')}",  # Ex: "Under 32.5"
                'odds': side_b.get('decimal_odds', 2.0),
                'american_odds': side_b.get('odds', 100),
                'bookmaker': side_b.get('bookmaker', 'Unknown'),
                'time': payload.get('formatted_time', payload.get('commence_time', 'Unknown'))
            })
        
        else:  # good_ev
            # Good EV has 1 outcome
            verification_legs.append({
                'match': drop.match or payload.get('match', ''),
                'sport': payload.get('league', 'Unknown'),
                'market': payload.get('market', 'Unknown'),
                'odds': payload.get('decimal_odds', 2.0),
                'american_odds': payload.get('odds', 100),
                'bookmaker': payload.get('bookmaker', 'Unknown'),
                'time': payload.get('formatted_time', payload.get('commence_time', 'Unknown'))
            })
        
        # Verify odds
        verification = await verifier.verify_parlay_odds(verification_legs)
        
        # Build verification section to APPEND to original message
        verification_section = f"\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        verification_section += f"🔍 <b>VÉRIFICATION</b> ({now.strftime('%H:%M')})\n"
        verification_section += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # Debug
        print(f"📊 Verification details: {verification['details']}")
        print(f"📊 Total legs: {len(verification_legs)}")
        
        # Count player props
        player_props = sum(1 for d in verification['details'] if d.get('note') == 'Player props not available via API')
        print(f"📊 Player props detected: {player_props}")
        
        if player_props == len(verification_legs):
            # All are player props
            verification_section += "⚠️ <b>Player props détectés</b>\n"
            verification_section += "La vérification automatique n'est pas disponible pour les paris sur joueurs.\n\n"
            verification_section += "💡 <b>Action:</b> Vérifiez manuellement sur les sites des bookmakers avant de placer.\n"
        elif player_props > 0:
            # Some player props
            verification_section += f"⚠️ <b>{player_props} player prop(s) non vérifiable(s)</b>\n\n"
            for i, detail in enumerate(verification['details'], 1):
                if detail.get('note') == 'Player props not available via API':
                    bookmaker = detail['leg'].get('bookmaker', 'Unknown')
                    verification_section += f"• {bookmaker}: Vérification manuelle nécessaire\n"
            verification_section += "\n"
        
        # Show verified legs
        content_added = False
        if verification['verified_legs'] > 0:
            verification_section += f"✅ <b>{verification['verified_legs']} cotes vérifiées</b>\n"
            content_added = True
        if verification['legs_better'] > 0:
            verification_section += f"📈 <b>{verification['legs_better']} améliorée(s)</b>\n"
            content_added = True
        if verification['legs_worse'] > 0:
            verification_section += f"📉 <b>{verification['legs_worse']} détériorée(s)</b>\n"
            content_added = True
        
        # Si aucun contenu ajouté, afficher un message par défaut
        if not content_added and player_props == 0:
            # Detect specific market types
            all_markets = [d['leg'].get('market', '') for d in verification['details']]
            market_text = ' '.join(all_markets).upper()
            
            specific_markets = []
            if 'CORNER' in market_text:
                specific_markets.append('Corners')
            if 'CARD' in market_text or 'YELLOW' in market_text or 'RED' in market_text:
                specific_markets.append('Cards')
            if 'BOOKING' in market_text:
                specific_markets.append('Bookings')
            if 'SHOT' in market_text:
                specific_markets.append('Shots')
            if 'FOUL' in market_text:
                specific_markets.append('Fouls')
            
            # Get bookmakers
            bookmakers = list(set([d['leg'].get('bookmaker', 'bookmaker') for d in verification['details']]))
            bookmakers_text = ' et '.join(bookmakers) if len(bookmakers) <= 2 else f"{bookmakers[0]}, {bookmakers[1]}, etc."
            
            if specific_markets:
                markets_text = ', '.join(specific_markets)
                verification_section += f"⚠️ <b>{markets_text} non disponibles pour vérification automatique</b>\n\n"
                verification_section += f"💡 <b>Action:</b> Vérifiez manuellement sur {bookmakers_text}\n"
                verification_section += f"<i>(Marchés spécifiques non supportés par API)</i>\n"
            else:
                verification_section += "⚠️ Vérification automatique non disponible pour ce type de pari.\n\n"
                verification_section += f"💡 <b>Action:</b> Vérifiez manuellement sur {bookmakers_text}\n"
        
        # Add to original message
        original_text = callback.message.text or callback.message.caption or ""
        new_text = original_text + verification_section
        
        # Edit original message to add verification
        try:
            await callback.message.edit_text(
                new_text,
                parse_mode=ParseMode.HTML,
                reply_markup=callback.message.reply_markup
            )
        except Exception as e:
            # If edit fails (message too long), send as new message
            print(f"Could not edit message: {e}")
            await callback.message.answer(
                verification_section,
                parse_mode=ParseMode.HTML
            )
        
    except Exception as e:
        print(f"Error verifying odds: {e}")
        await callback.message.answer(
            f"❌ Erreur lors de la vérification: {str(e)}"
        )
    finally:
        db.close()
