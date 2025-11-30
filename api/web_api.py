"""
Web Dashboard API Endpoints
These endpoints are called by the web dashboard (risk0-web)
"""
import json
import asyncio
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Optional, List, Set
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
            
            result.append({
                "id": call.id,
                "eventId": call.event_id,
                "receivedAt": call.received_at.isoformat() if call.received_at else None,
                "betType": call.bet_type,
                "arbPercentage": call.arb_percentage,
                "match": call.match,
                "league": call.league,
                "market": call.market,
                "matchTime": payload.get("formatted_time") or payload.get("commence_time"),
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
        
        # Get today's stats
        today = datetime.now().date()
        today_bets = db.query(UserBet).filter(
            UserBet.user_id == telegram_id,
            UserBet.bet_date == today
        ).all()
        
        today_count = len(today_bets)
        today_profit = sum(b.expected_profit or 0 for b in today_bets)
        
        # Calculate win rate
        total_profit = user.total_profit or 0
        total_loss = user.total_loss or 0
        win_rate = 0
        if total_profit + total_loss > 0:
            win_rate = (total_profit / (total_profit + total_loss)) * 100
        
        return {
            "user": {
                "telegramId": user.telegram_id,
                "username": user.username,
                "firstName": user.first_name,
                "role": user.role,
                "tier": user.tier.value if user.tier else "free",
                "defaultBankroll": user.default_bankroll or 400,
                "settings": {
                    "minArbPercent": user.min_arb_percent,
                    "maxArbPercent": user.max_arb_percent,
                    "enableGoodOdds": user.enable_good_odds,
                    "enableMiddle": user.enable_middle,
                }
            },
            "stats": {
                "totalBets": user.total_bets or 0,
                "totalProfit": total_profit,
                "totalLoss": total_loss,
                "netProfit": total_profit - total_loss,
                "arbitrageBets": user.arbitrage_bets or 0,
                "arbitrageProfit": user.arbitrage_profit or 0,
                "goodEvBets": user.good_ev_bets or 0,
                "goodEvProfit": user.good_ev_profit or 0,
                "middleBets": user.middle_bets or 0,
                "middleProfit": user.middle_profit or 0,
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


@router.delete("/bets/{bet_id}")
async def remove_bet(bet_id: int, user_id: int):
    """Remove a bet (undo I BET)"""
    db = SessionLocal()
    try:
        bet = db.query(UserBet).filter(UserBet.id == bet_id).first()
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
        
        db.delete(bet)
        db.commit()
        
        return {"success": True, "message": "Bet removed"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
