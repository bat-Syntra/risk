"""
Web API endpoints for bet confirmations
Syncs with Telegram confirmation system
"""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from sqlalchemy import and_

from database import SessionLocal
from models.bet import UserBet, DailyStats
from models.user import User

router = APIRouter(prefix="/api/confirmations", tags=["confirmations"])


class BetConfirmation(BaseModel):
    id: int
    bet_type: str  # 'arbitrage', 'middle', 'good_ev'
    match_name: str
    sport: Optional[str]
    total_stake: float
    expected_profit: float
    bet_date: Optional[str]
    
    # Casino details
    casino1_name: Optional[str]
    casino2_name: Optional[str]
    casino1_odds: Optional[str]
    casino2_odds: Optional[str]
    casino1_outcome: Optional[str]
    casino2_outcome: Optional[str]
    casino1_profit: Optional[float]
    casino2_profit: Optional[float]
    jackpot_profit: Optional[float]  # For middles
    
    # For good_ev
    potential_payout: Optional[float]


class ConfirmationAnswer(BaseModel):
    answer: str  # 'casino1', 'casino2', 'jackpot', 'won', 'lost', 'push', 'not_started'
    match_date: Optional[str] = None  # If answer is 'not_started' and user provides date


class PendingConfirmationsResponse(BaseModel):
    pending_count: int
    confirmations: List[BetConfirmation]


def _to_float(v):
    try:
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            s = v.strip().replace('%', '')
            if s.startswith('+'):
                s = s[1:]
            return float(s)
        return 0.0
    except Exception:
        return 0.0


def _odds_multiplier(odds):
    o = _to_float(odds)
    if 1.01 <= o <= 20:  # Decimal odds
        return o
    if o > 0:  # American positive
        return 1.0 + (o / 100.0)
    if o < 0:  # American negative
        return 1.0 + (100.0 / abs(o))
    return 0.0


@router.get("/{telegram_id}", response_model=PendingConfirmationsResponse)
async def get_pending_confirmations(telegram_id: int):
    """Get all pending confirmations for a user"""
    db = SessionLocal()
    try:
        today = date.today()
        
        # Get pending bets that are ready for confirmation
        pending_bets = db.query(UserBet).filter(
            and_(
                UserBet.user_id == telegram_id,
                UserBet.status == 'pending'
            )
        ).all()
        
        # Filter to only "ready" bets
        ready_bets = []
        for bet in pending_bets:
            if bet.match_date and bet.match_date < today:
                ready_bets.append(bet)
            elif bet.match_date is None and bet.bet_date and bet.bet_date < today:
                ready_bets.append(bet)
        
        confirmations = []
        for bet in ready_bets:
            conf = _build_confirmation(bet)
            confirmations.append(conf)
        
        return PendingConfirmationsResponse(
            pending_count=len(confirmations),
            confirmations=confirmations
        )
    finally:
        db.close()


def _build_confirmation(bet: UserBet) -> BetConfirmation:
    """Build confirmation object with all details from bet"""
    casino1_name = "Casino A"
    casino2_name = "Casino B"
    casino1_odds = None
    casino2_odds = None
    casino1_outcome = None
    casino2_outcome = None
    casino1_profit = 0.0
    casino2_profit = 0.0
    jackpot_profit = bet.expected_profit or 0.0
    potential_payout = 0.0
    
    if bet.drop_event and bet.drop_event.payload:
        try:
            drop_data = bet.drop_event.payload
            outcomes = drop_data.get('outcomes', [])
            
            # Get stakes from payload first, calculate optimal as fallback
            stake1_from_payload = outcomes[0].get('stake') if len(outcomes) >= 1 else None
            stake2_from_payload = outcomes[1].get('stake') if len(outcomes) >= 2 else None
            
            if stake1_from_payload and stake2_from_payload:
                # Use real stakes from payload
                stake1 = _to_float(stake1_from_payload)
                stake2 = _to_float(stake2_from_payload)
            else:
                # Calculate optimal stakes as fallback
                odds1_raw = outcomes[0].get('odds') if len(outcomes) >= 1 else None
                odds2_raw = outcomes[1].get('odds') if len(outcomes) >= 2 else None
                
                if odds1_raw and odds2_raw:
                    m1 = _odds_multiplier(str(odds1_raw))
                    m2 = _odds_multiplier(str(odds2_raw))
                    if m1 > 0 and m2 > 0:
                        # Calculate optimal stakes (equal payout formula)
                        P = bet.total_stake / (1/m1 + 1/m2)
                        stake1 = P / m1
                        stake2 = P / m2
                    else:
                        stake1 = stake2 = bet.total_stake / 2
                else:
                    stake1 = stake2 = bet.total_stake / 2
            
            if len(outcomes) >= 1:
                o1 = outcomes[0]
                casino1_name = o1.get('casino', 'Casino A')
                casino1_odds = str(o1.get('odds', ''))
                casino1_outcome = o1.get('outcome', '')
                
                # Use calculated stake for arbitrage, or from payload
                stake1_final = _to_float(o1.get('stake', o1.get('bet_amount', o1.get('wager', stake1))))
                payout1 = _to_float(o1.get('payout', o1.get('return', 0)))
                
                if payout1 == 0 and casino1_odds:
                    m1 = _odds_multiplier(casino1_odds)
                    payout1 = stake1_final * m1 if m1 > 0 else 0
                
                potential_payout = payout1  # For good_ev
            
            if len(outcomes) >= 2:
                o2 = outcomes[1]
                casino2_name = o2.get('casino', 'Casino B')
                casino2_odds = str(o2.get('odds', ''))
                casino2_outcome = o2.get('outcome', '')
                
                # Use calculated stake for arbitrage, or from payload
                stake2_final = _to_float(o2.get('stake', o2.get('bet_amount', o2.get('wager', stake2))))
                payout2 = _to_float(o2.get('payout', o2.get('return', 0)))
                
                if payout2 == 0 and casino2_odds:
                    m2 = _odds_multiplier(casino2_odds)
                    payout2 = stake2_final * m2 if m2 > 0 else 0
                
                # Calculate profits based on bet type
                if bet.bet_type == 'arbitrage':
                    # Arbitrage with optimal stakes:
                    # Both payouts are equal, so profit is guaranteed
                    casino1_profit = payout1 - bet.total_stake
                    casino2_profit = payout2 - bet.total_stake
                    # Should be equal (or very close)
                    jackpot_profit = min(casino1_profit, casino2_profit)
                    
                elif bet.bet_type == 'middle':
                    # Middle: different scenarios
                    # If only casino1 wins: you lose stake2
                    casino1_profit = payout1 - bet.total_stake
                    # If only casino2 wins: you lose stake1
                    casino2_profit = payout2 - bet.total_stake
                    # If both win (JACKPOT): you get both payouts!
                    jackpot_profit = (payout1 + payout2) - bet.total_stake
                    
                else:
                    # Good EV: simple profit calculation
                    casino1_profit = payout1 - stake1_final
                    casino2_profit = 0
                    jackpot_profit = casino1_profit
            
            # For middles, try to get proper profits from side_a/side_b
            if bet.bet_type == 'middle':
                side_a = drop_data.get('side_a', {})
                side_b = drop_data.get('side_b', {})
                if side_a and side_b:
                    try:
                        from utils.middle_calculator import classify_middle_type
                        cls = classify_middle_type(side_a, side_b, bet.total_stake)
                        casino1_name = side_a.get('casino', casino1_name)
                        casino2_name = side_b.get('casino', casino2_name)
                        casino1_profit = cls.get('profit_scenario_1', casino1_profit)
                        casino2_profit = cls.get('profit_scenario_3', casino2_profit)
                    except Exception:
                        pass
                        
        except Exception as e:
            pass
    
    return BetConfirmation(
        id=bet.id,
        bet_type=bet.bet_type,
        match_name=bet.match_name or "Match",
        sport=bet.sport,
        total_stake=bet.total_stake,
        expected_profit=bet.expected_profit or 0.0,
        bet_date=bet.bet_date.isoformat() if bet.bet_date else None,
        casino1_name=casino1_name,
        casino2_name=casino2_name,
        casino1_odds=casino1_odds,
        casino2_odds=casino2_odds,
        casino1_outcome=casino1_outcome,
        casino2_outcome=casino2_outcome,
        casino1_profit=casino1_profit,
        casino2_profit=casino2_profit,
        jackpot_profit=jackpot_profit,
        potential_payout=potential_payout
    )


@router.post("/{bet_id}/answer")
async def submit_confirmation_answer(bet_id: int, answer: ConfirmationAnswer):
    """Submit answer for a confirmation"""
    db = SessionLocal()
    try:
        bet = db.query(UserBet).filter(UserBet.id == bet_id).first()
        
        if not bet:
            raise HTTPException(status_code=404, detail="Bet not found")
        
        if bet.status != 'pending':
            raise HTTPException(status_code=400, detail="Bet already confirmed")
        
        # Handle "not started" case
        if answer.answer == 'not_started':
            if answer.match_date:
                from datetime import datetime
                bet.match_date = datetime.fromisoformat(answer.match_date).date()
                db.commit()
                return {"status": "postponed", "message": "Match date saved. Will ask again after the match."}
            else:
                return {"status": "postponed", "message": "Will ask again tomorrow."}
        
        # Handle "mistake" case - delete the bet
        if answer.answer == 'mistake':
            db.delete(bet)
            db.commit()
            return {"status": "deleted", "message": "Bet removed - marked as misclick"}
        
        # Calculate actual profit based on answer
        actual_profit = 0.0
        
        if bet.bet_type == 'arbitrage':
            if answer.answer == 'casino1':
                conf = _build_confirmation(bet)
                actual_profit = conf.casino1_profit or bet.expected_profit
            elif answer.answer == 'casino2':
                conf = _build_confirmation(bet)
                actual_profit = conf.casino2_profit or bet.expected_profit
            elif answer.answer == 'lost':
                actual_profit = -bet.total_stake
            else:
                actual_profit = bet.expected_profit
            
            bet.actual_profit = actual_profit
            bet.status = 'won' if actual_profit >= 0 else 'lost'
        
        elif bet.bet_type == 'middle':
            conf = _build_confirmation(bet)
            if answer.answer == 'jackpot':
                actual_profit = bet.expected_profit  # Jackpot profit
            elif answer.answer == 'casino1':
                actual_profit = conf.casino1_profit
            elif answer.answer == 'casino2':
                actual_profit = conf.casino2_profit
            elif answer.answer == 'lost':
                actual_profit = -bet.total_stake
            
            bet.actual_profit = actual_profit
            bet.status = 'won' if actual_profit >= 0 else 'lost'
        
        elif bet.bet_type == 'good_ev':
            if answer.answer == 'won':
                conf = _build_confirmation(bet)
                actual_profit = conf.potential_payout - bet.total_stake if conf.potential_payout else bet.expected_profit
            elif answer.answer == 'lost':
                actual_profit = -bet.total_stake
            elif answer.answer == 'push':
                actual_profit = 0.0
            
            bet.actual_profit = actual_profit
            bet.status = 'won' if actual_profit > 0 else ('push' if actual_profit == 0 and answer.answer == 'push' else 'lost')
        
        # Update daily stats
        bet_date = bet.bet_date
        daily_stat = db.query(DailyStats).filter(
            DailyStats.user_id == bet.user_id,
            DailyStats.date == bet_date
        ).first()
        
        if daily_stat:
            daily_stat.total_profit -= bet.expected_profit
            daily_stat.total_profit += bet.actual_profit
            daily_stat.confirmed = True
        
        db.commit()
        
        # Reset user notification for Telegram
        try:
            from bot.pending_confirmations import reset_user_notification
            reset_user_notification(bet.user_id)
        except:
            pass
        
        return {
            "status": "confirmed",
            "bet_id": bet.id,
            "actual_profit": bet.actual_profit,
            "bet_status": bet.status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
