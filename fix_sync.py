"""
Fix sync between DailyStats and UserBet
Create missing UserBet records from DailyStats
"""
from database import SessionLocal
from models.bet import DailyStats, UserBet
from models.drop_event import DropEvent  # Import pour la foreign key
from datetime import date, datetime

db = SessionLocal()

print("=== FIXING SYNC ===\n")

# Get all DailyStats with bets but check if UserBets exist
daily_stats = db.query(DailyStats).filter(DailyStats.total_bets > 0).all()

for ds in daily_stats:
    user_id = ds.user_id
    bet_date = ds.date
    
    # Check how many UserBets exist for this user/date
    existing_bets = db.query(UserBet).filter(
        UserBet.user_id == user_id,
        UserBet.bet_date == bet_date
    ).count()
    
    expected_bets = ds.total_bets
    missing = expected_bets - existing_bets
    
    if missing > 0:
        print(f"User {user_id} on {bet_date}:")
        print(f"  Expected: {expected_bets} bets")
        print(f"  Found: {existing_bets} bets")
        print(f"  Missing: {missing} bets")
        print(f"  Total staked: ${ds.total_staked}")
        print(f"  Total profit: ${ds.total_profit}\n")
        
        # Create missing bet(s) as generic "unknown" type
        # We'll create 1 bet with the total amounts
        avg_stake = ds.total_staked / expected_bets if expected_bets > 0 else ds.total_staked
        avg_profit = ds.total_profit / expected_bets if expected_bets > 0 else ds.total_profit
        
        for i in range(missing):
            user_bet = UserBet(
                user_id=user_id,
                drop_event_id=None,
                bet_type='arbitrage',  # Default to arbitrage
                bet_date=bet_date,
                total_stake=avg_stake,
                expected_profit=avg_profit,
                actual_profit=avg_profit,  # Assume it's realized
                status='completed'
            )
            db.add(user_bet)
            print(f"  ✅ Created UserBet: ${avg_stake} → ${avg_profit:+.2f}")
        
        db.commit()
        print(f"  💾 Committed!\n")

print("=== SYNC COMPLETE ===")
db.close()
