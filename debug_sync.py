"""
Debug script to check sync between DailyStats and UserBet
"""
from database import SessionLocal
from models.bet import DailyStats, UserBet
from datetime import date

db = SessionLocal()

print("=== DAILYSTATS ===")
daily_stats = db.query(DailyStats).all()
for ds in daily_stats:
    print(f"User {ds.user_id} | Date {ds.date} | Bets: {ds.total_bets} | Staked: ${ds.total_staked} | Profit: ${ds.total_profit}")

print("\n=== USERBETS ===")
user_bets = db.query(UserBet).all()
for ub in user_bets:
    print(f"ID: {ub.id} | User: {ub.user_id} | Type: {ub.bet_type} | Date: {ub.bet_date} | Stake: ${ub.total_stake} | Profit: ${ub.expected_profit}")

print(f"\n=== SUMMARY ===")
print(f"Total DailyStats records: {len(daily_stats)}")
print(f"Total UserBet records: {len(user_bets)}")

# Check for specific user
user_id = 8213628656  # Ton ID
print(f"\n=== YOUR DATA (User {user_id}) ===")
your_daily = db.query(DailyStats).filter(DailyStats.user_id == user_id).all()
your_bets = db.query(UserBet).filter(UserBet.user_id == user_id).all()

print(f"DailyStats count: {len(your_daily)}")
for ds in your_daily:
    print(f"  Date {ds.date}: {ds.total_bets} bets, ${ds.total_staked} staked")

print(f"UserBet count: {len(your_bets)}")
for ub in your_bets:
    print(f"  {ub.bet_type} on {ub.bet_date}: ${ub.total_stake}")

db.close()
