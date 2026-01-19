"""
Web Dashboard API Endpoints
These endpoints are called by the web dashboard (risk0-web)
"""
import json
import asyncio
import re
import base64
from datetime import datetime, timedelta, date
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Query, Request
from pydantic import BaseModel
from typing import Optional, List, Set
from sqlalchemy import func, and_, extract, case
from database import SessionLocal
from models.user import User, TierLevel
from models.drop_event import DropEvent
from models.bet import UserBet
from models.referral import Referral, ReferralSettings
from core.referrals import ReferralManager

router = APIRouter(prefix="/api/web", tags=["web"])

# WebSocket connections manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"🔌 WebSocket connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"🔌 WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Send message to all connected clients"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        
        # Clean up disconnected
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

# Function to notify all connected clients of a new call
async def notify_new_call(call_data: dict):
    """Call this when a new drop is received to notify web clients instantly"""
    await manager.broadcast({
        "type": "new_call",
        "data": call_data
    })

# Function to notify all connected clients of new confirmations
async def notify_new_confirmation(user_id: int, count: int):
    """Call this when a bet needs confirmation to notify web clients instantly"""
    await manager.broadcast({
        "type": "new_confirmation",
        "user_id": user_id,
        "count": count
    })

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, wait for messages
            data = await websocket.receive_text()
            # Echo back or handle commands
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


class BetRequest(BaseModel):
    userId: int
    dropEventId: Optional[int] = None
    betType: str
    matchName: str
    sport: Optional[str] = ""
    totalStake: float
    expectedProfit: float


@router.get("/calls")
async def get_live_calls(type: str = "all", limit: int = 50):
    """Get live calls from the last 24 hours"""
    db = SessionLocal()
    try:
        query = db.query(DropEvent).filter(
            DropEvent.received_at > datetime.now() - timedelta(hours=24)
        )
        
        if type and type != "all":
            query = query.filter(DropEvent.bet_type == type)
        
        calls = query.order_by(DropEvent.received_at.desc()).limit(limit).all()
        
        # Count by type
        counts = {
            "arbitrage": db.query(DropEvent).filter(
                DropEvent.received_at > datetime.now() - timedelta(hours=24),
                DropEvent.bet_type == "arbitrage"
            ).count(),
            "middle": db.query(DropEvent).filter(
                DropEvent.received_at > datetime.now() - timedelta(hours=24),
                DropEvent.bet_type == "middle"
            ).count(),
            "good_ev": db.query(DropEvent).filter(
                DropEvent.received_at > datetime.now() - timedelta(hours=24),
                DropEvent.bet_type == "good_ev"
            ).count(),
        }
        
        result = []
        for call in calls:
            payload = {}
            if call.payload:
                if isinstance(call.payload, str):
                    try:
                        payload = json.loads(call.payload)
                    except:
                        payload = {}
                else:
                    payload = call.payload
            
            # Extract player name from payload
            player = payload.get("player")
            if not player:
                # Try to extract from selection like "Lauri Markkanen Over 7.5"
                sel = payload.get("selection", "")
                # Common pattern: "Player Name Over/Under X.X"
                match = re.match(r'^(.+?)\s+(?:Over|Under)\s+[\d.]+', sel, re.IGNORECASE)
                if match:
                    player = match.group(1).strip()
                # Also try from outcomes
                if not player and payload.get("outcomes"):
                    outcome = payload["outcomes"][0].get("outcome", "")
                    match = re.match(r'^(.+?)\s+(?:Over|Under)\s+[\d.]+', outcome, re.IGNORECASE)
                    if match:
                        player = match.group(1).strip()
            
            # Get match time from DB column first, then payload (try multiple fields)
            match_time = None
            if hasattr(call, 'match_time') and call.match_time:
                match_time = call.match_time.isoformat()
            elif payload.get("formatted_time"):
                match_time = payload.get("formatted_time")
            elif payload.get("commence_time"):
                match_time = payload.get("commence_time")
            elif payload.get("game_time"):
                match_time = payload.get("game_time")
            elif payload.get("event_time"):
                match_time = payload.get("event_time")
            # Also check nested in outcomes
            elif payload.get("outcomes") and len(payload.get("outcomes", [])) > 0:
                first_outcome = payload["outcomes"][0]
                if first_outcome.get("commence_time"):
                    match_time = first_outcome.get("commence_time")
            
            result.append({
                "id": call.id,
                "eventId": call.event_id,
                "receivedAt": call.received_at.isoformat() if call.received_at else (call.created_at.isoformat() if hasattr(call, 'created_at') and call.created_at else None),
                "betType": call.bet_type,
                "arbPercentage": call.arb_percentage,
                "match": call.match,
                "league": call.league,
                "market": call.market,
                "matchTime": match_time,
                "player": player,  # Player name for player props
                "payload": payload,
            })
        
        return {
            "calls": result,
            "counts": {
                "arbitrage": counts["arbitrage"],
                "middle": counts["middle"],
                "goodOdds": counts["good_ev"],
                "total": counts["arbitrage"] + counts["middle"] + counts["good_ev"],
            }
        }
    finally:
        db.close()


@router.get("/user/{telegram_id}")
async def get_user(telegram_id: int):
    """Get user info and stats"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get today's stats from UserBet table (recent bets)
        today = datetime.now().date()
        today_bets = db.query(UserBet).filter(
            UserBet.user_id == telegram_id,
            UserBet.bet_date == today
        ).all()
        
        today_count = len(today_bets)
        today_profit = sum(b.expected_profit or 0 for b in today_bets)
        
        # Calculate ALL-TIME stats from UserBet table (same as Telegram!)
        # This ensures stats are always in sync
        total_bets = db.query(func.count(UserBet.id)).filter(
            UserBet.user_id == telegram_id
        ).scalar() or 0
        
        total_profit = db.query(
            func.sum(case((UserBet.actual_profit != None, UserBet.actual_profit), else_=UserBet.expected_profit))
        ).filter(
            UserBet.user_id == telegram_id
        ).scalar() or 0
        
        # Calculate by bet type
        arb_bets = db.query(func.count(UserBet.id)).filter(
            UserBet.user_id == telegram_id,
            UserBet.bet_type == 'arbitrage'
        ).scalar() or 0
        arb_profit = db.query(
            func.sum(case((UserBet.actual_profit != None, UserBet.actual_profit), else_=UserBet.expected_profit))
        ).filter(
            UserBet.user_id == telegram_id,
            UserBet.bet_type == 'arbitrage'
        ).scalar() or 0
        
        mid_bets = db.query(func.count(UserBet.id)).filter(
            UserBet.user_id == telegram_id,
            UserBet.bet_type == 'middle'
        ).scalar() or 0
        mid_profit = db.query(
            func.sum(case((UserBet.actual_profit != None, UserBet.actual_profit), else_=UserBet.expected_profit))
        ).filter(
            UserBet.user_id == telegram_id,
            UserBet.bet_type == 'middle'
        ).scalar() or 0
        
        ev_bets = db.query(func.count(UserBet.id)).filter(
            UserBet.user_id == telegram_id,
            UserBet.bet_type == 'good_ev'
        ).scalar() or 0
        ev_profit = db.query(
            func.sum(case((UserBet.actual_profit != None, UserBet.actual_profit), else_=UserBet.expected_profit))
        ).filter(
            UserBet.user_id == telegram_id,
            UserBet.bet_type == 'good_ev'
        ).scalar() or 0
        
        # Calculate win rate
        win_rate = 0
        if total_bets > 0 and total_profit > 0:
            win_rate = 100.0  # Arb trading is usually 100% win rate
        
        return {
            "user": {
                "telegramId": user.telegram_id,
                "username": user.username,
                "firstName": user.first_name,
                "role": user.role,
                "tier": user.tier.value if user.tier else "free",
                "defaultBankroll": user.default_bankroll or 400,
                "subscriptionEnd": user.subscription_end.isoformat() if user.subscription_end else None,
                "freeAccess": user.free_access,
                "settings": {
                    "minArbPercent": user.min_arb_percent,
                    "maxArbPercent": user.max_arb_percent,
                    "enableGoodOdds": user.enable_good_odds,
                    "enableMiddle": user.enable_middle,
                }
            },
            "stats": {
                "totalBets": total_bets,
                "totalProfit": total_profit,
                "totalLoss": 0,
                "netProfit": total_profit,
                "arbitrageBets": arb_bets,
                "arbitrageProfit": arb_profit,
                "goodEvBets": ev_bets,
                "goodEvProfit": ev_profit,
                "middleBets": mid_bets,
                "middleProfit": mid_profit,
                "todayBets": today_count,
                "todayProfit": today_profit,
                "winRate": win_rate,
            }
        }
    finally:
        db.close()


@router.post("/bets")
async def record_bet(bet: BetRequest):
    """Record a bet when user clicks 'I BET'"""
    db = SessionLocal()
    try:
        # Verify user exists
        user = db.query(User).filter(User.telegram_id == bet.userId).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if bet already exists (prevent duplicates)
        existing = db.query(UserBet).filter(
            UserBet.user_id == bet.userId,
            UserBet.drop_event_id == bet.dropEventId
        ).first()
        if existing:
            return {"success": True, "betId": existing.id, "message": "Bet already exists"}
        
        # Create bet record
        today = datetime.now().date()
        
        user_bet = UserBet(
            user_id=bet.userId,
            drop_event_id=bet.dropEventId,
            event_hash=f"{bet.matchName}-{datetime.now().timestamp()}",
            bet_type=bet.betType,
            bet_date=today,
            match_name=bet.matchName,
            sport=bet.sport,
            total_stake=bet.totalStake,
            expected_profit=bet.expectedProfit,
            status="pending"
        )
        db.add(user_bet)
        
        # Update user stats
        user.total_bets = (user.total_bets or 0) + 1
        user.total_profit = (user.total_profit or 0) + bet.expectedProfit
        
        if bet.betType == "arbitrage":
            user.arbitrage_bets = (user.arbitrage_bets or 0) + 1
            user.arbitrage_profit = (user.arbitrage_profit or 0) + bet.expectedProfit
        elif bet.betType == "good_ev":
            user.good_ev_bets = (user.good_ev_bets or 0) + 1
            user.good_ev_profit = (user.good_ev_profit or 0) + bet.expectedProfit
        elif bet.betType == "middle":
            user.middle_bets = (user.middle_bets or 0) + 1
            user.middle_profit = (user.middle_profit or 0) + bet.expectedProfit
        
        db.commit()
        
        return {
            "success": True,
            "betId": user_bet.id,
            "message": "Bet recorded successfully"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/bets")
async def get_user_bets(user_id: int):
    """Get all bets for a user (to show which are already betted)"""
    db = SessionLocal()
    try:
        bets = db.query(UserBet).filter(
            UserBet.user_id == user_id,
            UserBet.bet_date >= datetime.now().date() - timedelta(days=7)  # Last 7 days
        ).order_by(UserBet.created_at.desc()).all()
        
        return {
            "bets": [
                {
                    "id": bet.id,
                    "dropEventId": bet.drop_event_id,
                    "betType": bet.bet_type,
                    "matchName": bet.match_name,
                    "sport": bet.sport,
                    "totalStake": bet.total_stake,
                    "expectedProfit": bet.expected_profit,
                    "status": bet.status,
                    "betDate": bet.bet_date.isoformat() if bet.bet_date else None,
                }
                for bet in bets
            ]
        }
    finally:
        db.close()


# ========================================
# CONFIRM BET RESULT (from Web)
# ========================================

@router.post("/bets/{bet_id}/confirm")
async def confirm_bet_result(bet_id: int, outcome: str, user_id: int):
    """
    Confirm bet result from web dashboard.
    
    Args:
        bet_id: ID of the bet to confirm
        outcome: Result type:
            - 'jackpot': Middle bet - both sides won
            - 'casino1': Side A won (arbitrage profit for middle, or arb)
            - 'casino2': Side B won (arbitrage profit for middle, or arb)
            - 'won': Generic win (for arb/good_ev)
            - 'lost': Lost (human error)
        user_id: User's telegram ID (for verification)
    """
    db = SessionLocal()
    try:
        bet = db.query(UserBet).filter(UserBet.id == bet_id).first()
        
        if not bet:
            raise HTTPException(status_code=404, detail="Bet not found")
        
        if bet.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        if bet.status != 'pending':
            raise HTTPException(status_code=400, detail=f"Bet already confirmed as {bet.status}")
        
        # Calculate profit based on bet type and outcome
        if bet.bet_type == 'middle':
            # Calculate profits from drop_event
            jackpot_profit = 0.0
            casino1_profit = 0.0
            casino2_profit = 0.0
            
            if bet.drop_event and bet.drop_event.payload:
                try:
                    drop_data = bet.drop_event.payload
                    side_a = drop_data.get('side_a', {})
                    side_b = drop_data.get('side_b', {})
                    
                    if side_a and side_b and 'odds' in side_a and 'odds' in side_b:
                        from utils.middle_calculator import classify_middle_type
                        cls = classify_middle_type(side_a, side_b, bet.total_stake)
                        casino1_profit = cls['profit_scenario_1']
                        casino2_profit = cls['profit_scenario_3']
                        jackpot_profit = cls['profit_scenario_2']
                except Exception as e:
                    logger.warning(f"Could not calculate middle profits: {e}")
            
            if outcome == 'jackpot':
                bet.actual_profit = jackpot_profit if jackpot_profit else bet.expected_profit
                bet.status = 'won'
            elif outcome == 'casino1':
                bet.actual_profit = casino1_profit
                bet.status = 'won'
            elif outcome == 'casino2':
                bet.actual_profit = casino2_profit
                bet.status = 'won'
            else:  # lost
                bet.actual_profit = -bet.total_stake
                bet.status = 'lost'
        
        elif bet.bet_type == 'arbitrage':
            if outcome in ['casino1', 'casino2', 'won']:
                bet.actual_profit = bet.expected_profit  # Guaranteed profit
                bet.status = 'won'
            else:  # lost
                bet.actual_profit = -bet.total_stake
                bet.status = 'lost'
        
        else:  # good_ev
            if outcome == 'won':
                # Calculate win from odds
                if bet.drop_event and bet.drop_event.payload:
                    outcomes = bet.drop_event.payload.get('outcomes', [])
                    if outcomes:
                        payout = outcomes[0].get('payout', bet.total_stake * 2)
                        bet.actual_profit = payout - bet.total_stake
                    else:
                        bet.actual_profit = bet.expected_profit
                else:
                    bet.actual_profit = bet.expected_profit
                bet.status = 'won'
            else:  # lost
                bet.actual_profit = -bet.total_stake
                bet.status = 'lost'
        
        # Update DailyStats
        from models.bet import DailyStats
        daily_stat = db.query(DailyStats).filter(
            DailyStats.user_id == bet.user_id,
            DailyStats.date == bet.bet_date
        ).first()
        
        if daily_stat:
            daily_stat.total_profit -= bet.expected_profit or 0
            daily_stat.total_profit += bet.actual_profit
            daily_stat.confirmed = True
        
        db.commit()
        
        return {
            "success": True,
            "bet": {
                "id": bet.id,
                "status": bet.status,
                "actualProfit": bet.actual_profit,
                "expectedProfit": bet.expected_profit
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error confirming bet: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/user/{telegram_id}/pending-confirmations")
async def get_pending_confirmations(telegram_id: int):
    """Get all bets pending confirmation for a user"""
    db = SessionLocal()
    try:
        from datetime import date
        today = date.today()
        
        bets = db.query(UserBet).filter(
            UserBet.user_id == telegram_id,
            UserBet.status == 'pending'
        ).order_by(UserBet.bet_date.desc()).all()
        
        # Filter to ready bets (match date passed or no date + bet date passed)
        ready_bets = []
        for bet in bets:
            if bet.match_date and bet.match_date < today:
                ready_bets.append(bet)
            elif bet.match_date is None and bet.bet_date and bet.bet_date < today:
                ready_bets.append(bet)
        
        result = []
        for bet in ready_bets:
            # Get side info from drop_event
            side_a = {}
            side_b = {}
            jackpot_profit = 0
            casino1_profit = 0
            casino2_profit = 0
            
            if bet.drop_event and bet.drop_event.payload:
                drop_data = bet.drop_event.payload
                side_a = drop_data.get('side_a', {})
                side_b = drop_data.get('side_b', {})
                
                if bet.bet_type == 'middle' and side_a and side_b:
                    try:
                        from utils.middle_calculator import classify_middle_type
                        cls = classify_middle_type(side_a, side_b, bet.total_stake)
                        casino1_profit = cls['profit_scenario_1']
                        casino2_profit = cls['profit_scenario_3']
                        jackpot_profit = cls['profit_scenario_2']
                    except:
                        pass
            
            result.append({
                "id": bet.id,
                "betType": bet.bet_type,
                "matchName": bet.match_name,
                "sport": bet.sport,
                "betDate": bet.bet_date.isoformat() if bet.bet_date else None,
                "matchDate": bet.match_date.isoformat() if bet.match_date else None,
                "totalStake": bet.total_stake,
                "expectedProfit": bet.expected_profit,
                "sideA": {
                    "bookmaker": side_a.get('bookmaker', side_a.get('casino', '')),
                    "selection": side_a.get('selection', ''),
                    "odds": side_a.get('odds', ''),
                    "line": side_a.get('line', '')
                },
                "sideB": {
                    "bookmaker": side_b.get('bookmaker', side_b.get('casino', '')),
                    "selection": side_b.get('selection', ''),
                    "odds": side_b.get('odds', ''),
                    "line": side_b.get('line', '')
                },
                "profits": {
                    "jackpot": jackpot_profit,
                    "casino1": casino1_profit,
                    "casino2": casino2_profit,
                    "guaranteed": bet.expected_profit
                }
            })
        
        return {
            "pendingCount": len(ready_bets),
            "bets": result
        }
        
    finally:
        db.close()


# ========================================
# RECENT BETS (for My Stats page)
# ========================================

@router.get("/user/{telegram_id}/recent-bets")
async def get_recent_bets(telegram_id: int, limit: int = 20):
    """Get recent bets for a user (for My Stats page)"""
    db = SessionLocal()
    try:
        bets = db.query(UserBet).filter(
            UserBet.user_id == telegram_id,
            UserBet.bet_date >= datetime.now().date() - timedelta(days=30)  # Last 30 days
        ).order_by(UserBet.created_at.desc()).limit(limit).all()
        
        return {
            "recentBets": [
                {
                    "id": bet.id,
                    "dropEventId": bet.drop_event_id,
                    "betType": bet.bet_type,
                    "matchName": bet.match_name,
                    "sport": bet.sport,
                    "totalStake": bet.total_stake,
                    "expectedProfit": bet.expected_profit,
                    "actualProfit": bet.actual_profit,
                    "status": bet.status,
                    "betDate": bet.bet_date.isoformat() if bet.bet_date else None,
                    "matchDate": bet.match_date.isoformat() if bet.match_date else None,
                    "createdAt": bet.created_at.isoformat() if bet.created_at else None,
                }
                for bet in bets
            ]
        }
    finally:
        db.close()


# ========================================
# USER SETTINGS (full sync with Telegram)
# ========================================

class UserSettingsUpdate(BaseModel):
    """All settings that can be updated from web"""
    language: Optional[str] = None
    defaultBankroll: Optional[float] = None
    # Percentage filters
    minArbPercent: Optional[float] = None
    maxArbPercent: Optional[float] = None
    minMiddlePercent: Optional[float] = None
    maxMiddlePercent: Optional[float] = None
    minGoodEvPercent: Optional[float] = None
    maxGoodEvPercent: Optional[float] = None
    # Casino and Sport filters (JSON strings)
    selectedCasinos: Optional[str] = None
    selectedSports: Optional[str] = None
    # Stake rounding
    stakeRounding: Optional[int] = None
    roundingMode: Optional[str] = None
    # Stake randomizer
    randomizerEnabled: Optional[bool] = None
    randomizerAmounts: Optional[str] = None
    randomizerMode: Optional[str] = None
    # Feature toggles
    enableGoodOdds: Optional[bool] = None
    enableMiddle: Optional[bool] = None
    betFocusMode: Optional[bool] = None
    matchTodayOnly: Optional[bool] = None
    notificationsEnabled: Optional[bool] = None


@router.get("/user/{telegram_id}/settings")
async def get_user_settings(telegram_id: int):
    """Get ALL user settings (for web settings page)"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Parse casino and sport filters
        try:
            casinos = json.loads(user.selected_casinos) if user.selected_casinos else None
        except:
            casinos = None
        
        try:
            sports = json.loads(user.selected_sports) if user.selected_sports else None
        except:
            sports = None
        
        return {
            "settings": {
                # Basic info
                "language": user.language or "en",
                "defaultBankroll": user.default_bankroll or 400,
                "tier": user.tier.value if user.tier else "free",
                "isActive": user.is_active,
                
                # Percentage filters
                "minArbPercent": user.min_arb_percent or 0.5,
                "maxArbPercent": user.max_arb_percent or 100.0,
                "minMiddlePercent": user.min_middle_percent or 0.5,
                "maxMiddlePercent": user.max_middle_percent or 100.0,
                "minGoodEvPercent": user.min_good_ev_percent or 0.5,
                "maxGoodEvPercent": user.max_good_ev_percent or 100.0,
                
                # Casino and Sport filters
                "selectedCasinos": casinos,  # List or null (null = all)
                "selectedSports": sports,  # List or null (null = all)
                
                # Stake rounding
                "stakeRounding": user.stake_rounding or 0,
                "roundingMode": user.rounding_mode or "nearest",
                
                # Stake randomizer
                "randomizerEnabled": user.stake_randomizer_enabled or False,
                "randomizerAmounts": user.stake_randomizer_amounts or "",
                "randomizerMode": user.stake_randomizer_mode or "random",
                
                # Feature toggles
                "enableGoodOdds": user.enable_good_odds if user.enable_good_odds is not None else False,
                "enableMiddle": user.enable_middle if user.enable_middle is not None else False,
                "betFocusMode": user.bet_focus_mode if user.bet_focus_mode is not None else False,
                "matchTodayOnly": user.match_today_only if user.match_today_only is not None else False,
                "notificationsEnabled": user.notifications_enabled if user.notifications_enabled is not None else True,
            }
        }
    finally:
        db.close()


@router.put("/user/{telegram_id}/settings")
async def update_user_settings(telegram_id: int, settings: UserSettingsUpdate):
    """Update user settings from web (syncs with Telegram)"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update only provided fields
        if settings.language is not None:
            user.language = settings.language
        if settings.defaultBankroll is not None:
            user.default_bankroll = settings.defaultBankroll
        if settings.minArbPercent is not None:
            user.min_arb_percent = settings.minArbPercent
        if settings.maxArbPercent is not None:
            user.max_arb_percent = settings.maxArbPercent
        if settings.minMiddlePercent is not None:
            user.min_middle_percent = settings.minMiddlePercent
        if settings.maxMiddlePercent is not None:
            user.max_middle_percent = settings.maxMiddlePercent
        if settings.minGoodEvPercent is not None:
            user.min_good_ev_percent = settings.minGoodEvPercent
        if settings.maxGoodEvPercent is not None:
            user.max_good_ev_percent = settings.maxGoodEvPercent
        if settings.selectedCasinos is not None:
            user.selected_casinos = settings.selectedCasinos
        if settings.selectedSports is not None:
            user.selected_sports = settings.selectedSports
        if settings.stakeRounding is not None:
            user.stake_rounding = settings.stakeRounding
        if settings.roundingMode is not None:
            user.rounding_mode = settings.roundingMode
        if settings.randomizerEnabled is not None:
            user.stake_randomizer_enabled = settings.randomizerEnabled
        if settings.randomizerAmounts is not None:
            user.stake_randomizer_amounts = settings.randomizerAmounts
        if settings.randomizerMode is not None:
            user.stake_randomizer_mode = settings.randomizerMode
        if settings.enableGoodOdds is not None:
            user.enable_good_odds = settings.enableGoodOdds
        if settings.enableMiddle is not None:
            user.enable_middle = settings.enableMiddle
        if settings.betFocusMode is not None:
            user.bet_focus_mode = settings.betFocusMode
        if settings.matchTodayOnly is not None:
            user.match_today_only = settings.matchTodayOnly
        if settings.notificationsEnabled is not None:
            user.notifications_enabled = settings.notificationsEnabled
        
        db.commit()
        
        return {"success": True, "message": "Settings updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# ========================================
# AVAILABLE OPTIONS (for settings dropdowns)
# ========================================

@router.get("/options/casinos")
async def get_available_casinos():
    """Get list of all available casinos for filter"""
    # Same list as in bot/casino_filter_handlers.py
    casinos = [
        "Bet99", "Betway", "BetVictor", "FanDuel", "DraftKings", "888Sport",
        "Betsson", "LeoVegas", "Pinnacle", "Bodog", "Coolbet", "Rivalry",
        "Sports Interaction", "BetMGM", "Mise-o-jeu", "Pointsbet", "Caesars",
        "NorthStar Bets"
    ]
    return {"casinos": sorted(casinos)}


@router.get("/options/sports")
async def get_available_sports():
    """Get list of all available sports for filter"""
    # Same list as in bot/sport_filter.py
    sports = [
        {"key": "nfl", "name": "NFL", "emoji": "🏈"},
        {"key": "nba", "name": "NBA", "emoji": "🏀"},
        {"key": "nhl", "name": "NHL", "emoji": "🏒"},
        {"key": "mlb", "name": "MLB", "emoji": "⚾"},
        {"key": "ncaaf", "name": "NCAAF", "emoji": "🏈"},
        {"key": "ncaab", "name": "NCAAB", "emoji": "🏀"},
        {"key": "soccer", "name": "Soccer", "emoji": "⚽"},
        {"key": "tennis", "name": "Tennis", "emoji": "🎾"},
    ]
    return {"sports": sports}


# ========================================
# PARLAYS (sync from Telegram)
# ========================================

@router.get("/parlays")
async def get_parlays(risk: str = None, casino: str = None, limit: int = 50):
    """Get all active parlays with full leg details"""
    db = SessionLocal()
    try:
        from sqlalchemy import text
        
        # Build query
        query = "SELECT * FROM parlays WHERE status = 'active'"
        params = {}
        
        if risk:
            query += " AND risk_level = :risk"
            params['risk'] = risk.upper()
        if casino:
            query += " AND casino = :casino"
            params['casino'] = casino
            
        query += " ORDER BY id DESC LIMIT :limit"
        params['limit'] = limit
        
        result = db.execute(text(query), params)
        rows = result.fetchall()
        columns = result.keys()
        
        parlays = []
        for row in rows:
            parlay = dict(zip(columns, row))
            
            # Parse legs_json
            legs = []
            if parlay.get('legs_json'):
                try:
                    legs = json.loads(parlay['legs_json'])
                except:
                    legs = []
            
            # Map risk level to display name
            risk_map = {
                'LOW': 'Conservative',
                'MEDIUM': 'Balanced', 
                'HIGH': 'Aggressive',
                'EXTREME': 'Lottery'
            }
            
            parlays.append({
                "id": parlay['id'],
                "strategy": parlay['strategy'],
                "numLegs": parlay['num_legs'],
                "totalOdds": round(parlay['combined_odds'], 2),
                "avgEdge": round(parlay['avg_edge'] * 100, 1) if parlay['avg_edge'] else 0,
                "winProb": round(parlay['estimated_win_prob'] * 100, 0) if parlay['estimated_win_prob'] else 0,
                "expectedValue": round(parlay['expected_value'] * 100, 1) if parlay['expected_value'] else 0,
                "riskLevel": parlay['risk_level'],
                "riskDisplay": risk_map.get(parlay['risk_level'], parlay['risk_level']),
                "casino": parlay['casino'],
                "status": parlay['status'],
                "createdAt": parlay['created_at'],
                "legs": legs,
                # Calculate potential profit for $100 stake
                "potentialProfit": round((parlay['combined_odds'] - 1) * 100, 0) if parlay['combined_odds'] else 0,
            })
        
        # Count by risk level
        counts_query = """
            SELECT risk_level, COUNT(*) as count 
            FROM parlays WHERE status = 'active' 
            GROUP BY risk_level
        """
        counts_result = db.execute(text(counts_query))
        counts = {row[0]: row[1] for row in counts_result.fetchall()}
        
        return {
            "parlays": parlays,
            "counts": {
                "conservative": counts.get('LOW', 0),
                "balanced": counts.get('MEDIUM', 0),
                "aggressive": counts.get('HIGH', 0),
                "lottery": counts.get('EXTREME', 0),
                "total": sum(counts.values())
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/parlays/{parlay_id}")
async def get_parlay_detail(parlay_id: int):
    """Get single parlay with full leg details"""
    db = SessionLocal()
    try:
        from sqlalchemy import text
        
        result = db.execute(
            text("SELECT * FROM parlays WHERE id = :id"),
            {"id": parlay_id}
        )
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Parlay not found")
        
        columns = result.keys()
        parlay = dict(zip(columns, row))
        
        # Parse legs_json
        legs = []
        if parlay.get('legs_json'):
            try:
                legs = json.loads(parlay['legs_json'])
            except:
                legs = []
        
        risk_map = {
            'LOW': 'Conservative',
            'MEDIUM': 'Balanced', 
            'HIGH': 'Aggressive',
            'EXTREME': 'Lottery'
        }
        
        return {
            "parlay": {
                "id": parlay['id'],
                "strategy": parlay['strategy'],
                "numLegs": parlay['num_legs'],
                "totalOdds": round(parlay['combined_odds'], 2),
                "avgEdge": round(parlay['avg_edge'] * 100, 1) if parlay['avg_edge'] else 0,
                "winProb": round(parlay['estimated_win_prob'] * 100, 0) if parlay['estimated_win_prob'] else 0,
                "expectedValue": round(parlay['expected_value'] * 100, 1) if parlay['expected_value'] else 0,
                "riskLevel": parlay['risk_level'],
                "riskDisplay": risk_map.get(parlay['risk_level'], parlay['risk_level']),
                "casino": parlay['casino'],
                "status": parlay['status'],
                "createdAt": parlay['created_at'],
                "legs": legs,
                "potentialProfit": round((parlay['combined_odds'] - 1) * 100, 0) if parlay['combined_odds'] else 0,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.delete("/bets/{drop_event_id}")
async def remove_bet(drop_event_id: int, user_id: int):
    """Remove ALL bets for a drop_event_id (undo I BET, handles duplicates)"""
    db = SessionLocal()
    try:
        # Find ALL bets by drop_event_id and user_id (in case of duplicates)
        bets = db.query(UserBet).filter(
            UserBet.drop_event_id == drop_event_id,
            UserBet.user_id == user_id
        ).all()
        
        if not bets:
            raise HTTPException(status_code=404, detail="Bet not found")
        
        # Use the first bet for stats reversal, delete all
        bet = bets[0]
        
        if not bet:
            raise HTTPException(status_code=404, detail="Bet not found")
        
        # Update user stats (reverse the bet)
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if user:
            user.total_bets = max(0, (user.total_bets or 0) - 1)
            user.total_profit = (user.total_profit or 0) - (bet.expected_profit or 0)
            
            if bet.bet_type == "arbitrage":
                user.arbitrage_bets = max(0, (user.arbitrage_bets or 0) - 1)
                user.arbitrage_profit = (user.arbitrage_profit or 0) - (bet.expected_profit or 0)
            elif bet.bet_type == "good_ev":
                user.good_ev_bets = max(0, (user.good_ev_bets or 0) - 1)
                user.good_ev_profit = (user.good_ev_profit or 0) - (bet.expected_profit or 0)
            elif bet.bet_type == "middle":
                user.middle_bets = max(0, (user.middle_bets or 0) - 1)
                user.middle_profit = (user.middle_profit or 0) - (bet.expected_profit or 0)
        
        # Delete ALL bets for this drop_event_id (handles duplicates)
        for b in bets:
            db.delete(b)
        db.commit()
        
        return {"success": True, "message": f"Removed {len(bets)} bet(s)"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.get("/calendar/{telegram_id}")
async def get_calendar_data(
    telegram_id: int,
    year: int = Query(None, description="Year (defaults to current)"),
    month: int = Query(None, description="Month 1-12 (defaults to current)")
):
    """
    Get P&L calendar data for a specific month
    Returns daily P&L, bets count, and strategy breakdown
    """
    db = SessionLocal()
    try:
        # Default to current month if not specified
        now = datetime.now()
        target_year = year if year else now.year
        target_month = month if month else now.month
        
        # Get all bets for this user in the target month (any status)
        bets = db.query(UserBet).filter(
            and_(
                UserBet.user_id == telegram_id,
                extract('year', UserBet.bet_date) == target_year,
                extract('month', UserBet.bet_date) == target_month
            )
        ).all()
        
        # Group bets by day
        days_data = {}
        for bet in bets:
            if not bet.bet_date:
                continue
                
            day = bet.bet_date.day
            if day not in days_data:
                days_data[day] = {
                    'date': day,
                    'pnl': 0,
                    'bets': 0,
                    'stake': 0,  # REAL total stake
                    'wins': 0,
                    'losses': 0,
                    'strategies': {
                        'arb': 0,
                        'mid': 0,
                        'ev': 0,
                        'parlays': 0,
                        'arbBets': 0,
                        'midBets': 0,
                        'evBets': 0,
                        'parlayBets': 0,
                        'arbWins': 0,
                        'midWins': 0,
                        'evWins': 0
                    }
                }
            
            # Add P&L and REAL stake
            profit = bet.actual_profit if bet.actual_profit is not None else (bet.expected_profit or 0)
            days_data[day]['pnl'] += profit
            days_data[day]['bets'] += 1
            days_data[day]['stake'] += bet.total_stake or 0  # Add REAL stake
            
            # Track wins/losses
            if profit > 0:
                days_data[day]['wins'] += 1
            elif profit < 0:
                days_data[day]['losses'] += 1
            
            # Track by strategy (profit, bet count, AND wins)
            bet_type = bet.bet_type or 'arbitrage'
            if bet_type == 'arbitrage':
                days_data[day]['strategies']['arb'] += profit
                days_data[day]['strategies']['arbBets'] += 1
                if profit > 0:
                    days_data[day]['strategies']['arbWins'] += 1
            elif bet_type == 'middle':
                days_data[day]['strategies']['mid'] += profit
                days_data[day]['strategies']['midBets'] += 1
                if profit > 0:
                    days_data[day]['strategies']['midWins'] += 1
            elif bet_type == 'good_ev':
                days_data[day]['strategies']['ev'] += profit
                days_data[day]['strategies']['evBets'] += 1
                if profit > 0:
                    days_data[day]['strategies']['evWins'] += 1
            elif bet_type == 'parlay':
                days_data[day]['strategies']['parlays'] += profit
                days_data[day]['strategies']['parlayBets'] += 1
        
        # Calculate win rate per day
        for day_data in days_data.values():
            total = day_data['wins'] + day_data['losses']
            day_data['winRate'] = (day_data['wins'] / total * 100) if total > 0 else 0
        
        # Convert to list and sort by date
        days_list = sorted(days_data.values(), key=lambda x: x['date'])
        
        return {
            "year": target_year,
            "month": target_month,
            "days": days_list
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# ========== AUTH ENDPOINTS ==========
# Store pending auth codes (in-memory, persistent since this runs continuously)
import time
import bcrypt
import json
import secrets
import jwt
from functools import wraps
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel

class AuthConfirm(BaseModel):
    code: str
    telegramId: int
    username: str
    token: str  # The full token to return to the web

class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str
    telegram_username: Optional[str] = None  # Optional Telegram username for account linking
    referral_code: Optional[str] = None  # Referral code from ?ref= parameter

class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/auth/confirm")
async def confirm_auth(data: AuthConfirm):
    """Called by Telegram bot when user authenticates"""
    pending_auth_codes[data.code] = {
        "authenticated": True,
        "telegramId": data.telegramId,
        "username": data.username,
        "token": data.token,
        "timestamp": time.time()
    }
    print(f"✅ Auth confirmed for code {data.code}, user {data.username}")
    return {"success": True}


@router.get("/auth/check")
async def check_auth(code: str):
    """Called by web frontend to check if auth is complete"""
    # Clean old codes (> 5 minutes)
    now = time.time()
    expired = [k for k, v in pending_auth_codes.items() if now - v["timestamp"] > 300]
    for k in expired:
        del pending_auth_codes[k]
    
    if code not in pending_auth_codes:
        return {"authenticated": False}
    
    auth_data = pending_auth_codes[code]
    if auth_data["authenticated"]:
        # Return the token and clean up
        token = auth_data["token"]
        del pending_auth_codes[code]
        return {
            "authenticated": True,
            "token": token,
            "user": {
                "telegramId": auth_data["telegramId"],
                "username": auth_data["username"]
            }
        }
    
    return {"authenticated": False}


def generate_jwt_token(user_data: dict) -> str:
    """Generate JWT token for website authentication"""
    token_data = {
        "id": user_data["id"],
        "email": user_data["email"],
        "username": user_data["username"],
        "tier": user_data["tier"],
        "auth_method": user_data["auth_method"],
        "ts": int(time.time())
    }
    # Simple base64 encoding (matching existing Telegram token format)
    token_json = json.dumps(token_data)
    token_b64 = base64.b64encode(token_json.encode()).decode()
    return token_b64.replace('+', '-').replace('/', '_')  # URL-safe


@router.post("/auth/register")
async def register_user(data: RegisterRequest):
    """Register new website user"""
    db = SessionLocal()
    try:
        # Validate email format
        import re
        email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if not re.match(email_regex, data.email):
            raise HTTPException(status_code=400, detail="Format email invalide")
        
        # Validate username format
        username_regex = r'^[a-zA-Z0-9_]{3,20}$'
        if not re.match(username_regex, data.username):
            raise HTTPException(status_code=400, detail="Username: 3-20 caractères, lettres/chiffres/_")
        
        # Validate password strength
        if len(data.password) < 8:
            raise HTTPException(status_code=400, detail="Mot de passe: minimum 8 caractères")
        if not re.search(r'[A-Z]', data.password):
            raise HTTPException(status_code=400, detail="Mot de passe: au moins 1 majuscule requise")
        if not re.search(r'[0-9]', data.password):
            raise HTTPException(status_code=400, detail="Mot de passe: au moins 1 chiffre requis")
        
        # Check if email already exists
        existing_email = db.query(User).filter(User.email == data.email).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email déjà utilisé")
        
        # Check if username already exists (for website users)
        existing_username = db.query(User).filter(
            User.username == data.username,
            User.auth_method == 'website'
        ).first()
        if existing_username:
            raise HTTPException(status_code=400, detail="Username déjà pris")
        
        # Hash password
        password_hash = bcrypt.hashpw(data.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Generate unique telegram_id for website users (negative numbers to avoid conflicts)
        # Find the lowest telegram_id available (including 0 and negatives)
        last_website_user = db.query(User).filter(
            User.auth_method == 'website',
            User.telegram_id <= 0
        ).order_by(User.telegram_id.asc()).first()
        
        if last_website_user:
            next_telegram_id = last_website_user.telegram_id - 1
        else:
            next_telegram_id = -1  # Start with -1 for first website user
        
        # Store telegram_username if provided (for account linking)
        telegram_username = data.telegram_username.strip() if data.telegram_username else None
        if telegram_username and not telegram_username.startswith('@'):
            telegram_username = f"@{telegram_username}"
        
        # Create new user
        new_user = User(
            telegram_id=next_telegram_id,  # Use negative IDs for website users
            username=data.username,
            email=data.email,
            auth_method='website',
            password_hash=password_hash,
            tier=TierLevel.FREE,  # Default to FREE tier
            language='fr',  # Default to French
            is_active=True,
            
            # Website-specific quotas
            daily_ai_questions=5,
            daily_ai_questions_used=0,
            daily_calls_under_2_percent=5,
            daily_calls_under_2_percent_used=0,
            last_quota_reset=datetime.now().date(),
            
            # Default settings
            default_bankroll=400.0,
            default_risk_percentage=5.0,
            notifications_enabled=True
        )
        
        # Set telegram username if provided (store in username field for website users)
        if telegram_username:
            # For website users, we can store the telegram username in a comment or separate field
            # For now, we'll add it to the user record after creation
            pass
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Handle referral tracking if referral_code provided
        if data.referral_code:
            try:
                # Convert referral_code to int (user ID)
                referrer_id = int(data.referral_code)
                
                # Find the referrer user
                referrer = db.query(User).filter(User.id == referrer_id).first()
                if referrer:
                    print(f"🎯 REFERRAL TRACKED: User {new_user.id} ({new_user.email}) referred by User {referrer_id} ({referrer.email if referrer.email else referrer.username})")
                    
                    # Create a simple referral record using the User table
                    # We'll add a comment field to track the referrer relationship
                    # For now, we'll use a simple approach until we have a dedicated Referral table
                    
                    # We could add referral info to user's data or create a simple tracking mechanism
                    # For immediate implementation, let's store this in the user record
                    try:
                        # Update the new user with referrer info (for now using a field if available)
                        # This is a temporary solution - in production we'd have a proper Referrals table
                        
                        # Create referral tracking entry (simplified approach)
                        referral_data = {
                            "referred_user_id": new_user.id,
                            "referrer_user_id": referrer_id,
                            "referred_email": new_user.email,
                            "referred_username": new_user.username,
                            "referrer_email": referrer.email,
                            "referrer_username": referrer.username,
                            "registration_date": datetime.now().isoformat(),
                            "tier": new_user.tier.value,
                            "status": "active"
                        }
                        
                        # Save to persistent storage (file-based until proper database)
                        # Convert referrer_id to string for consistent storage keys
                        referrer_key = str(referrer_id)
                        if referrer_key not in referrals_storage:
                            referrals_storage[referrer_key] = []
                        referrals_storage[referrer_key].append(referral_data)
                        
                        # Save to file for persistence across server restarts
                        save_referrals_to_file()
                        
                        print(f"💾 REFERRAL SAVED: {referral_data}")
                        print(f"📊 REFERRALS STORAGE: User {referrer_id} now has {len(referrals_storage[referrer_key])} referrals")
                        print(f"🔄 REFERRALS PERSISTED to file storage")
                        
                    except Exception as save_error:
                        print(f"⚠️ REFERRAL SAVE ERROR: {save_error}")
                        
                else:
                    print(f"⚠️ REFERRAL WARNING: Referrer ID {referrer_id} not found")
            except ValueError:
                print(f"⚠️ REFERRAL ERROR: Invalid referral code format: {data.referral_code}")
            except Exception as e:
                print(f"⚠️ REFERRAL ERROR: {e}")
        
        # Generate JWT token
        user_data = {
            "id": new_user.id,
            "email": new_user.email,
            "username": new_user.username,
            "tier": new_user.tier.value,
            "auth_method": new_user.auth_method,
            "telegram_id": new_user.telegram_id  # Include telegram_id for compatibility
        }
        token = generate_jwt_token(user_data)
        
        return {
            "success": True,
            "token": token,
            "user": {
                "id": new_user.id,
                "email": new_user.email,
                "username": new_user.username,
                "tier": new_user.tier.value,
                "quotas": {
                    "ai_questions": new_user.daily_ai_questions,
                    "calls_under_2": new_user.daily_calls_under_2_percent
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")
    finally:
        db.close()


@router.get("/referrals")
async def get_user_referrals(request: Request):
    """Get referrals for the authenticated user"""
    try:
        # Get user from token
        auth_header = request.headers.get("Authorization")
        print(f"🔑 AUTH DEBUG: Authorization header: {auth_header}")
        
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Token manquant")
        
        token = auth_header.replace("Bearer ", "")
        user_data = get_user_from_token(token)
        
        if not user_data:
            raise HTTPException(status_code=401, detail="Token invalide")
        
        # Handle different token formats (website vs telegram)
        user_id = user_data.get("id") or user_data.get("telegramId")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token invalide - pas d'ID utilisateur")
        
        user_id = str(user_id)
        print(f"🔑 AUTH DEBUG: Using real user_id from token: {user_id}")
        
        db = SessionLocal()
        
        # Get real referral data from storage
        referrals_data = referrals_storage.get(user_id, [])
        
        # Transform the stored data to match API format
        api_referrals = []
        for referral in referrals_data:
            api_referrals.append({
                "id": referral.get("referred_user_id"),
                "username": referral.get("referred_username"),
                "email": referral.get("referred_email"),
                "registration_date": referral.get("registration_date"),
                "tier": referral.get("tier"),
                "status": referral.get("status")
            })
        
        # Calculate commission info with manual override check
        referral_count = len(api_referrals)
        
        # Get user's actual alpha status from database
        user_record = db.query(User).filter(User.id == int(user_id)).first()
        is_alpha = user_record and user_record.tier.value == 'alpha' if user_record else False
        
        commission_info = calculate_commission_rate(referral_count, is_alpha, user_id, db)
        
        # Return only real referral data - no demo fallback
        if not api_referrals:
            print(f"📊 REFERRALS API: User {user_id} has no referrals yet")
        else:
            print(f"🎯 REFERRALS API: User {user_id} has {len(api_referrals)} REAL referrals")
        
        # Always show commission info (even with 0 referrals)
        print(f"💰 COMMISSION: {commission_info['tier']} - {commission_info['rate']}%")
        
        referrals_data = api_referrals
        
        return {
            "success": True,
            "referrals": referrals_data,
            "total_referrals": len(referrals_data),
            "commission": commission_info,
            "stats": {
                "active_referrals": len([r for r in referrals_data if r.get("status") == "active"]),
                "total_earnings": 0.0,  # TODO: Calculate based on referral activity
                "monthly_earnings": 0.0  # TODO: Calculate based on referral activity
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Referrals error: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")
    finally:
        if 'db' in locals():
            db.close()


@router.post("/auth/login")
async def login_user(data: LoginRequest):
    """Login website user with email/password"""
    db = SessionLocal()
    try:
        # Find user by email
        user = db.query(User).filter(
            User.email == data.email,
            User.auth_method == 'website'
        ).first()
        
        if not user:
            raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
        
        # Check password
        if not bcrypt.checkpw(data.password.encode('utf-8'), user.password_hash.encode('utf-8')):
            raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
        
        # Check if user is banned
        if user.is_banned:
            raise HTTPException(status_code=403, detail="Compte suspendu")
        
        # Reset quotas if new day
        today = datetime.now().date()
        if user.last_quota_reset != today:
            user.daily_ai_questions_used = 0
            user.daily_calls_under_2_percent_used = 0
            user.last_quota_reset = today
            db.commit()
        
        # Update last seen
        user.last_seen = datetime.now()
        db.commit()
        
        # Generate JWT token
        user_data = {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "tier": user.tier.value,
            "auth_method": user.auth_method,
            "telegram_id": user.telegram_id  # Include telegram_id for compatibility
        }
        token = generate_jwt_token(user_data)
        
        return {
            "success": True,
            "token": token,
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "tier": user.tier.value,
                "quotas": {
                    "ai_questions": user.daily_ai_questions - user.daily_ai_questions_used,
                    "calls_under_2": user.daily_calls_under_2_percent - user.daily_calls_under_2_percent_used
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")
    finally:
        db.close()


def get_user_from_token(token: str) -> dict:
    """Extract user data from JWT token"""
    try:
        # Handle URL-safe base64
        token_clean = token.replace('-', '+').replace('_', '/')
        decoded = json.loads(base64.b64decode(token_clean).decode())
        return decoded
    except:
        return None


def check_website_quotas(quota_type: str):
    """
    Middleware decorator to check quotas for website users
    quota_type: 'ai_questions' or 'calls_under_2'
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get token from request headers
            from fastapi import Request, HTTPException
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                return await func(*args, **kwargs)
            
            # Get Authorization header
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return await func(*args, **kwargs)
            
            token = auth_header.replace('Bearer ', '')
            user_data = get_user_from_token(token)
            
            if not user_data or user_data.get('auth_method') != 'website':
                # Not a website user, skip quota check
                return await func(*args, **kwargs)
            
            # Check quotas for website users
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.id == user_data['id']).first()
                if not user:
                    raise HTTPException(status_code=401, detail="Utilisateur non trouvé")
                
                # Reset quotas if new day
                today = datetime.now().date()
                if user.last_quota_reset != today:
                    user.daily_ai_questions_used = 0
                    user.daily_calls_under_2_percent_used = 0
                    user.last_quota_reset = today
                    db.commit()
                
                # Check specific quota
                if quota_type == 'ai_questions':
                    if user.daily_ai_questions_used >= user.daily_ai_questions:
                        raise HTTPException(
                            status_code=429, 
                            detail={
                                "error": "Quota IA épuisé",
                                "message": f"Vous avez utilisé vos {user.daily_ai_questions} questions IA aujourd'hui. Revenez demain ou passez premium!",
                                "quota_reset": "minuit",
                                "remaining": 0,
                                "total": user.daily_ai_questions
                            }
                        )
                    # Increment usage after successful check
                    user.daily_ai_questions_used += 1
                    db.commit()
                
                elif quota_type == 'calls_under_2':
                    if user.daily_calls_under_2_percent_used >= user.daily_calls_under_2_percent:
                        raise HTTPException(
                            status_code=429,
                            detail={
                                "error": "Quota calls <2% épuisé", 
                                "message": f"Vous avez utilisé vos {user.daily_calls_under_2_percent} calls sous 2% aujourd'hui. Upgrade pour unlimited!",
                                "quota_reset": "minuit",
                                "remaining": 0,
                                "total": user.daily_calls_under_2_percent
                            }
                        )
                    # Increment usage after successful check
                    user.daily_calls_under_2_percent_used += 1
                    db.commit()
                
                return await func(*args, **kwargs)
                
            finally:
                db.close()
        
        return wrapper
    return decorator


@router.get("/quotas")
async def get_user_quotas(request: Request):
    """Get current user quotas"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Token manquant")
    
    token = auth_header.replace('Bearer ', '')
    user_data = get_user_from_token(token)
    
    if not user_data:
        raise HTTPException(status_code=401, detail="Token invalide")
    
    db = SessionLocal()
    try:
        if user_data.get('auth_method') == 'website':
            # Website user - return quotas
            user = db.query(User).filter(User.id == user_data['id']).first()
            if not user:
                raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
            
            # Reset quotas if new day
            today = datetime.now().date()
            if user.last_quota_reset != today:
                user.daily_ai_questions_used = 0
                user.daily_calls_under_2_percent_used = 0
                user.last_quota_reset = today
                db.commit()
            
            # Map tier to frontend expected format
            tier_mapping = {
                TierLevel.FREE: 'FREE',
                TierLevel.PREMIUM: 'ALPHA'
            }
            tier_str = tier_mapping.get(user.tier, 'FREE')
            
            return {
                "auth_method": "website",
                "tier": tier_str,
                "quotas": {
                    "ai_questions": {
                        "total": user.daily_ai_questions,
                        "used": user.daily_ai_questions_used,
                        "remaining": user.daily_ai_questions - user.daily_ai_questions_used
                    },
                    "calls_under_2": {
                        "total": user.daily_calls_under_2_percent,
                        "used": user.daily_calls_under_2_percent_used,
                        "remaining": user.daily_calls_under_2_percent - user.daily_calls_under_2_percent_used
                    }
                },
                "reset_time": "minuit"
            }
        else:
            # Telegram user - no quotas
            return {
                "auth_method": "telegram",
                "tier": user_data.get('tier', 'free'),
                "quotas": {
                    "ai_questions": {"total": "unlimited", "used": 0, "remaining": "unlimited"},
                    "calls_under_2": {"total": "unlimited", "used": 0, "remaining": "unlimited"}
                }
            }
    finally:
        db.close()


# Example usage of quota middleware
@router.post("/ai/question")
@check_website_quotas('ai_questions')
async def ask_ai_question(request: Request, question: dict):
    """AI question endpoint with quota checking"""
    # This endpoint will automatically check quotas for website users
    # and increment usage count
    return {"response": "AI response here", "question": question.get("text", "")}


@router.post("/calls/under-2-percent")
@check_website_quotas('calls_under_2')
async def get_calls_under_2_percent(request: Request, filters: dict):
    """Get calls under 2% with quota checking"""
    # This endpoint will automatically check quotas for website users
    return {"calls": [], "message": "Calls under 2% here"}


# ===== REFERRAL SYSTEM ENDPOINTS =====

@router.get("/referrals/stats")
async def get_referral_stats(telegram_id: int):
    """
    Get referral statistics for a user
    Returns commission rate, active referrals, earnings, and referral list
    """
    db = SessionLocal()
    try:
        # Get user
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get or create referral code
        referral_code = user.referral_code
        if not referral_code:
            referral_code = ReferralManager.create_user_referral_code(db, telegram_id)
        
        # Get dynamic commission rate
        current_rate = ReferralManager.get_dynamic_tier1_rate(db, telegram_id)
        
        # Count active direct referrals
        active_directs = ReferralManager.count_active_tier1(db, telegram_id)
        
        # Get all referrals with details
        referrals_query = db.query(Referral, User).join(
            User, User.telegram_id == Referral.referee_id
        ).filter(
            Referral.referrer_id == telegram_id
        ).all()
        
        referrals_list = []
        total_earnings = 0.0
        monthly_recurring = 0.0
        
        for ref, ref_user in referrals_query:
            # Calculate earnings from this referral
            ref_earnings = ref.total_commission_earned or 0.0
            total_earnings += ref_earnings
            
            # Calculate monthly value if active
            if ref.is_active and ref_user.tier == TierLevel.PREMIUM:
                # Assume $20/month subscription
                monthly_value = 20.0 * current_rate
                monthly_recurring += monthly_value
            else:
                monthly_value = 0.0
            
            referrals_list.append({
                "username": ref_user.username or f"User{ref_user.telegram_id}",
                "joinDate": ref.created_at.isoformat() if ref.created_at else datetime.now().isoformat(),
                "status": "active" if ref.is_active else "inactive",
                "monthlyValue": round(monthly_value, 2),
                "totalEarned": round(ref_earnings, 2)
            })
        
        # Check if user is Alpha (PREMIUM tier)
        is_alpha = user.tier == TierLevel.PREMIUM
        
        return {
            "currentRate": int(current_rate * 100),  # Convert to percentage
            "activeDirects": active_directs,
            "totalEarnings": round(total_earnings, 2),
            "monthlyRecurring": round(monthly_recurring, 2),
            "referralLink": f"https://t.me/risk0_bot?start=ref_{referral_code}",
            "isAlpha": is_alpha,
            "referrals": referrals_list
        }
        
    except Exception as e:
        print(f"Error fetching referral stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/referrals/link")
async def get_referral_link(telegram_id: int):
    """Get or create referral link for a user"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get or create referral code
        referral_code = user.referral_code
        if not referral_code:
            referral_code = ReferralManager.create_user_referral_code(db, telegram_id)
        
        return {
            "referralCode": referral_code,
            "referralLink": f"https://t.me/risk0_bot?start=ref_{referral_code}"
        }
    finally:
        db.close()


@router.get("/demo/access")
async def demo_access(request: Request):
    """Allow FREE users to access dashboard with limitations"""
    try:
        # Get Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            raise HTTPException(status_code=401, detail="Token manquant")
        
        token = auth_header.replace('Bearer ', '')
        user_data = get_user_from_token(token)
        
        if not user_data:
            raise HTTPException(status_code=401, detail="Token invalide")
        
        db = SessionLocal()
        try:
            # Find user
            if user_data.get('auth_method') == 'website':
                user = db.query(User).filter(User.id == user_data['id']).first()
            else:
                telegram_id = user_data.get('tid') or user_data.get('telegramId')
                user = db.query(User).filter(User.telegram_id == telegram_id).first()
            
            if not user:
                raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
            
            # All users can access demo (FREE with limitations, PREMIUM unlimited)
            tier_mapping = {
                TierLevel.FREE: 'FREE',
                TierLevel.PREMIUM: 'ALPHA'
            }
            tier_str = tier_mapping.get(user.tier, 'FREE')
            
            return {
                "success": True,
                "access_granted": True,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "tier": tier_str,
                    "auth_method": user.auth_method
                },
                "limitations": {
                    "ai_questions_per_day": 5 if user.tier == TierLevel.FREE else "unlimited",
                    "calls_per_day": 5 if user.tier == TierLevel.FREE else "unlimited",
                    "max_profit_percentage": 2.0 if user.tier == TierLevel.FREE else None
                },
                "redirect": "/dashboard"
            }
            
        finally:
            db.close()
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Demo access error: {e}")
        raise HTTPException(status_code=500, detail="Erreur serveur")


# ============================================================================
# TELEGRAM LINKING ENDPOINTS
# ============================================================================

# Pydantic models for Telegram linking
class TelegramLinkRequest(BaseModel):
    userId: str
    otpCode: str
    telegramUsername: str
    email: Optional[str] = None

class TelegramVerifyRequest(BaseModel):
    userId: str
    otpCode: str

# Temporary storage for OTP codes (in production, use Redis)
otp_storage = {}

# Temporary storage for referrals (in production, use proper database table)
referrals_storage = {}

def load_referrals_from_file():
    """Load referrals from file storage"""
    try:
        import os
        referrals_file = "/tmp/referrals_storage.json"
        if os.path.exists(referrals_file):
            import json
            with open(referrals_file, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"⚠️ REFERRALS LOAD ERROR: {e}")
    return {}

def save_referrals_to_file():
    """Save referrals to file storage"""
    try:
        import json
        referrals_file = "/tmp/referrals_storage.json"
        with open(referrals_file, 'w') as f:
            json.dump(referrals_storage, f, indent=2)
        print(f"💾 REFERRALS SAVED to file: {len(referrals_storage)} users")
    except Exception as e:
        print(f"⚠️ REFERRALS SAVE ERROR: {e}")

# Load existing referrals on startup
referrals_storage = load_referrals_from_file()
print(f"🔄 STARTUP: Loaded {len(referrals_storage)} users with referrals from storage")
if referrals_storage:
    total_referrals = sum(len(refs) for refs in referrals_storage.values())
    print(f"📊 STARTUP: Total {total_referrals} referrals across all users")
    for user_id, refs in referrals_storage.items():
        print(f"   User {user_id}: {len(refs)} referrals")

# JWT functions
JWT_SECRET = "your-secret-key-here"  # In production, use env variable

def decode_jwt_token(token: str):
    """Decode JWT token and return user data"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        print(f"🔑 JWT ERROR: Token expired")
        return None
    except jwt.InvalidTokenError as e:
        print(f"🔑 JWT ERROR: Invalid token - {e}")
        return None
    except Exception as e:
        print(f"🔑 JWT ERROR: Decode error - {e}")
        return None

# Commission Tiers System
def calculate_commission_rate(referral_count: int, is_alpha: bool = False, user_id: str = None, db = None) -> dict:
    """Calculate commission rate based on referral count and tier + manual overrides"""
    
    # Check for manual override first (admin set %)
    if user_id and db:
        try:
            override = db.query(ReferralSettings).filter(ReferralSettings.referrer_id == int(user_id)).first()
            if override and override.override_rate is not None:
                manual_rate = float(override.override_rate) * 100  # Convert to percentage
                return {
                    "rate": manual_rate,
                    "tier": f"🔧 Manual Override",
                    "is_alpha": is_alpha,
                    "referral_count": referral_count,
                    "next_milestone": None,
                    "is_manual_override": True
                }
        except Exception as e:
            print(f"💰 OVERRIDE CHECK ERROR: {e}")
    
    # Base automatic rates
    if referral_count >= 30:
        rate = 40.0
        tier = "🏆 Champion"
        next_milestone = None
    elif referral_count >= 20:
        rate = 30.0
        tier = "🌟 Elite"
        next_milestone = {"count": 30, "rate": 40.0}
    elif referral_count >= 10:
        rate = 25.0
        tier = "💎 Diamond"
        next_milestone = {"count": 20, "rate": 30.0}
    elif referral_count >= 5:
        rate = 15.0
        tier = "⭐ Star"
        # Auto-upgrade to Alpha at 5 referrals
        is_alpha = True
        next_milestone = {"count": 10, "rate": 25.0}
    elif is_alpha:
        rate = 12.5
        tier = "👑 Alpha"
        next_milestone = {"count": 5, "rate": 15.0}
    else:
        rate = 10.0
        tier = "🎯 Base"
        next_milestone = {"count": 5, "rate": 15.0}
    
    return {
        "rate": rate,
        "tier": tier,
        "is_alpha": is_alpha,
        "referral_count": referral_count,
        "next_milestone": next_milestone,
        "is_manual_override": False
    }

# In-memory storage for OTP codes (in production, use Redis or database)
telegram_otp_storage = {}

@router.post("/telegram/link-request")
async def telegram_link_request(request: TelegramLinkRequest):
    """
    Initiate Telegram account linking by generating and sending OTP
    """
    try:
        print(f"🔧 DEBUG: Received request - userId: {request.userId}, telegramUsername: {request.telegramUsername}")
        print(f"🔧 DEBUG: Request payload validation passed")
        db = SessionLocal()
        
        # Find user by ID
        user = db.query(User).filter(User.id == request.userId).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Store OTP code temporarily (expires in 10 minutes)
        expiry_time = datetime.now() + timedelta(minutes=10)
        telegram_otp_storage[request.userId] = {
            'otp_code': request.otpCode,
            'expiry': expiry_time,
            'email': request.email or user.email
        }
        
        # TODO: Send OTP via Telegram bot
        # This would integrate with the existing Telegram bot to send the OTP
        # For now, we'll return success and the OTP will be stored for verification
        
        print(f"📱 Telegram OTP generated for user {request.userId}: {request.otpCode}")
        print(f"📱 Username: @{request.telegramUsername}")
        print(f"📱 OTP stored and ready for verification")
        
        return {
            "success": True,
            "message": "Verification code generated. Please check your Telegram for the code.",
            "expires_in": 600  # 10 minutes
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Telegram link request error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate OTP")
    finally:
        db.close()


@router.post("/telegram/verify-link")
async def telegram_verify_link(request: TelegramVerifyRequest):
    """
    Verify OTP and link Telegram account to website account
    """
    try:
        db = SessionLocal()
        
        # Check if OTP exists and is valid
        if request.userId not in telegram_otp_storage:
            raise HTTPException(status_code=400, detail="No OTP found for this user")
        
        stored_data = telegram_otp_storage[request.userId]
        
        # Check if OTP has expired
        if datetime.now() > stored_data['expiry']:
            del telegram_otp_storage[request.userId]
            raise HTTPException(status_code=400, detail="OTP has expired")
        
        # Verify OTP code
        if request.otpCode != stored_data['otp_code']:
            raise HTTPException(status_code=400, detail="Invalid OTP code")
        
        # Find user
        user = db.query(User).filter(User.id == request.userId).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Generate a telegram_id for linking (in production, this would come from the bot)
        # For now, we'll generate a unique ID based on user ID
        import hashlib
        telegram_id = int(hashlib.md5(f"tg_{user.id}_{datetime.now().timestamp()}".encode()).hexdigest()[:8], 16)
        
        # Update user with telegram_id (create the link)
        user.telegram_id = telegram_id
        db.commit()
        
        # Clean up OTP
        del telegram_otp_storage[request.userId]
        
        print(f"✅ Telegram account linked for user {request.userId} -> telegram_id: {telegram_id}")
        
        return {
            "success": True,
            "message": "Telegram account successfully linked",
            "telegramId": telegram_id,
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "tier": user.tier.value if user.tier else "FREE",
                "telegram_id": telegram_id
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Telegram verify link error: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify OTP")
    finally:
        db.close()


@router.get("/telegram/link-status/{user_id}")
async def telegram_link_status(user_id: str):
    """
    Check if user has Telegram account linked
    """
    try:
        db = SessionLocal()
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "linked": user.telegram_id is not None,
            "telegram_id": user.telegram_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Telegram link status error: {e}")
        raise HTTPException(status_code=500, detail="Failed to check link status")
    finally:
        db.close()


@router.delete("/telegram/unlink/{user_id}")
async def telegram_unlink(user_id: str):
    """
    Unlink Telegram account from website account
    """
    try:
        db = SessionLocal()
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Remove telegram_id link
        old_telegram_id = user.telegram_id
        user.telegram_id = None
        db.commit()
        
        print(f"🔗 Telegram account unlinked for user {user_id} (was: {old_telegram_id})")
        
        return {
            "success": True,
            "message": "Telegram account successfully unlinked"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Telegram unlink error: {e}")
        raise HTTPException(status_code=500, detail="Failed to unlink Telegram")
    finally:
        db.close()
