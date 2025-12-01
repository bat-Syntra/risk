"""
Web Dashboard API Endpoints
These endpoints are called by the web dashboard (risk0-web)
"""
import json
import asyncio
import re
from datetime import datetime, timedelta, date
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel
from typing import Optional, List, Set
from sqlalchemy import func, and_, extract
from database import SessionLocal
from models.user import User
from models.drop_event import DropEvent
from models.bet import UserBet

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
        
        # Use user table columns (synchronized with Telegram!) for ALL-TIME stats
        # These are the source of truth maintained by the bot
        total_bets = user.total_bets or 0
        total_profit = user.total_profit or 0
        
        arb_profit = user.arbitrage_profit or 0
        mid_profit = user.middle_profit or 0
        ev_profit = user.good_ev_profit or 0
        
        arb_bets = user.arbitrage_bets or 0
        mid_bets = user.middle_bets or 0
        ev_bets = user.good_ev_bets or 0
        
        # Calculate win rate
        win_rate = 0
        if total_bets > 0 and total_profit > 0:
            # Simple approximation: if you have profit, most bets are wins
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
                    'wins': 0,
                    'losses': 0,
                    'strategies': {
                        'arb': 0,
                        'mid': 0,
                        'ev': 0,
                        'parlays': 0
                    }
                }
            
            # Add P&L
            profit = bet.actual_profit if bet.actual_profit is not None else (bet.expected_profit or 0)
            days_data[day]['pnl'] += profit
            days_data[day]['bets'] += 1
            
            # Track wins/losses
            if profit > 0:
                days_data[day]['wins'] += 1
            elif profit < 0:
                days_data[day]['losses'] += 1
            
            # Track by strategy
            bet_type = bet.bet_type or 'arbitrage'
            if bet_type == 'arbitrage':
                days_data[day]['strategies']['arb'] += profit
            elif bet_type == 'middle':
                days_data[day]['strategies']['mid'] += profit
            elif bet_type == 'good_ev':
                days_data[day]['strategies']['ev'] += profit
            elif bet_type == 'parlay':
                days_data[day]['strategies']['parlays'] += profit
        
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
