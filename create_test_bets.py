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
            'odds': '+150',
            'stake': 300.0,
            'payout': 750.0
        },
        {
            'casino': 'FanDuel', 
            'outcome': 'Celtics ML',
            'odds': '-110',
            'stake': 330.0,
            'payout': 630.0
        }
    ]
}

# Bet 2: Middle avec données complètes
middle_payload = {
    'outcomes': [
        {
            'casino': 'BetMGM',
            'outcome': 'Chiefs -2.5',
            'odds': '-110'
        },
        {
            'casino': 'Caesars',
            'outcome': 'Bills +3.5', 
            'odds': '+100'
        }
    ],
    'side_a': {
        'casino': 'BetMGM',
        'odds': -110,
        'line': -2.5,
        'stake': 275.0
    },
    'side_b': {
        'casino': 'Caesars',
        'odds': 100,
        'line': 3.5,
        'stake': 250.0
    }
}

# Bet 3: Good EV avec données complètes
ev_payload = {
    'outcomes': [
        {
            'casino': 'PointsBet',
            'outcome': 'Bucks ML',
            'odds': '+180',
            'stake': 500.0,
            'payout': 1400.0
        }
    ]
}

# Insérer les bets (simplifié sans drop_event)
bets_data = [
    (user_id, 'arbitrage', 'Lakers vs Celtics', 'NBA', 630.0, 20.0, 'pending', yesterday, None),
    (user_id, 'middle', 'Chiefs vs Bills', 'NFL', 525.0, 150.0, 'pending', yesterday, None),
    (user_id, 'good_ev', 'Bucks vs Nets', 'NBA', 500.0, 85.0, 'pending', yesterday, None)
]

for bet_data in bets_data:
    # Créer le bet simplement
    db.execute(text('''
        INSERT INTO user_bets (
            user_id, bet_type, match_name, sport, total_stake, 
            expected_profit, status, bet_date, match_date
        ) VALUES (
            :uid, :type, :match, :sport, :stake,
            :profit, :status, :date, :mdate
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
        'mdate': bet_data[8]
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
