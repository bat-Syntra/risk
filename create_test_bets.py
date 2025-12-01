#!/usr/bin/env python3
"""Create test bets for web confirmation testing"""

from database import SessionLocal
from sqlalchemy import text
from datetime import date, timedelta
import json

db = SessionLocal()
user_id = 8004919557
yesterday = date.today() - timedelta(days=1)

# Bet 1: Arbitrage avec données complètes
arb_payload = {
    'outcomes': [
        {
            'casino': 'DraftKings',
            'outcome': 'Lakers ML',
            'odds': 150,  # Numeric not string!
        },
        {
            'casino': 'FanDuel', 
            'outcome': 'Celtics ML',
            'odds': -110,  # Numeric not string!
        }
    ]
}

# Bet 2: Middle avec profit garanti (both sides positive)
middle_payload = {
    'outcomes': [
        {
            'casino': 'BetMGM',
            'outcome': 'Over 45.5',
            'odds': -105,  # Better odds
            'stake': 262.5
        },
        {
            'casino': 'Caesars',
            'outcome': 'Under 48.5', 
            'odds': 110,  # Better odds
            'stake': 262.5
        }
    ]
}

# Bet 3: Good EV avec données complètes
ev_payload = {
    'outcomes': [
        {
            'casino': 'PointsBet',
            'outcome': 'Bucks ML',
            'odds': 180
        }
    ]
}

# Insérer les bets AVEC drop_events
bets_data = [
    (user_id, 'arbitrage', 'Lakers vs Celtics', 'NBA', 630.0, 20.0, 'pending', yesterday, None, arb_payload),
    (user_id, 'middle', 'Chiefs vs Bills', 'NFL', 525.0, 150.0, 'pending', yesterday, None, middle_payload),
    (user_id, 'good_ev', 'Bucks vs Nets', 'NBA', 500.0, 85.0, 'pending', yesterday, None, ev_payload)
]

for bet_data in bets_data:
    # Créer le drop_event avec le payload et event_id
    event_id = f"test_{bet_data[1]}_{bet_data[2].replace(' ', '_')}"
    db.execute(text('''
        INSERT INTO drop_events (event_id, payload)
        VALUES (:event_id, :payload)
    '''), {'event_id': event_id, 'payload': json.dumps(bet_data[9])})
    
    drop_event_id = db.execute(text('SELECT last_insert_rowid()')).scalar()
    
    # Créer le bet avec drop_event_id
    db.execute(text('''
        INSERT INTO user_bets (
            user_id, bet_type, match_name, sport, total_stake, 
            expected_profit, status, bet_date, match_date, drop_event_id
        ) VALUES (
            :uid, :type, :match, :sport, :stake,
            :profit, :status, :date, :mdate, :drop_id
        )
    '''), {
        'uid': bet_data[0],
        'type': bet_data[1],
        'match': bet_data[2],
        'sport': bet_data[3],
        'stake': bet_data[4],
        'profit': bet_data[5],
        'status': bet_data[6],
        'date': bet_data[7],
        'mdate': bet_data[8],
        'drop_id': drop_event_id
    })

db.commit()

# Afficher les bets créés
result = db.execute(text('''
    SELECT id, bet_type, match_name, sport, total_stake, expected_profit
    FROM user_bets 
    WHERE user_id = :uid AND bet_date = :yesterday
    ORDER BY id DESC LIMIT 3
'''), {'uid': user_id, 'yesterday': yesterday})

print('✅ Créé 3 bets de test:')
for row in result:
    print(f'  • Bet {row[0]}: [{row[1].upper()}] {row[2]} ({row[3]}) - ${row[4]:.0f} → ${row[5]:+.2f}')

db.close()
print('\n🌐 Ouvre le site web et connecte-toi!')
print('Le popup va apparaître automatiquement avec les 3 confirmations!')
