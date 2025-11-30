#!/usr/bin/env python3
"""
Real-Time Parlay Generator v2.0
Se déclenche automatiquement quand un nouveau drop arrive
- Génère TOUS les parlays possibles (PAS de filtrage par %)
- Same-day et Cross-day parlays
- Multiple stratégies: Safe, Balanced, Aggressive, Lottery
"""
import json
from datetime import datetime
from database import SessionLocal
from sqlalchemy import text

# Import du nouveau moteur intelligent
from smart_parlay_engine import SmartParlayEngine

class RealtimeParlayGenerator:
    
    def __init__(self):
        self.db = SessionLocal()
        self.engine = SmartParlayEngine()
    
    def should_generate(self, new_drop):
        """
        TOUJOURS générer - on ne filtre plus par %
        Le moteur intelligent décide quels parlays créer
        """
        # Générer pour TOUT drop valide
        bet_type = new_drop.get('bet_type', '')
        return bet_type in ['arbitrage', 'middle', 'good_ev']
    
    def generate_on_new_drop(self, drop_event_id):
        """
        Génère TOUS les parlays possibles quand un nouveau drop arrive
        Utilise le SmartParlayEngine pour générer:
        - Same-day parlays (même journée)
        - Cross-day parlays (jours différents)
        - Safe, Balanced, Aggressive, Lottery
        """
        try:
            print(f"🔥 New drop {drop_event_id} - Generating ALL parlay types...")
            
            # Utiliser le nouveau moteur intelligent
            parlays = self.engine.generate_all_parlays()
            
            if parlays:
                # Compter par stratégie
                strategies = {}
                for p in parlays:
                    s = p['strategy']
                    strategies[s] = strategies.get(s, 0) + 1
                
                print(f"🎉 Generated {len(parlays)} parlays:")
                for strat, count in strategies.items():
                    print(f"   • {strat}: {count}")
            else:
                print("⚠️ No parlays generated (need more drops)")
            
        except Exception as e:
            print(f"❌ Error generating parlays: {e}")
            import traceback
            traceback.print_exc()
    
    def close(self):
        self.db.close()

# Fonction hook pour main_new.py
def on_drop_received(drop_event_id):
    """
    À appeler depuis main_new.py après qu'un drop soit enregistré
    Génère TOUS les types de parlays automatiquement
    """
    try:
        generator = RealtimeParlayGenerator()
        generator.generate_on_new_drop(drop_event_id)
        generator.close()
    except Exception as e:
        print(f"Error generating real-time parlays: {e}")

if __name__ == "__main__":
    # Test - générer tous les parlays possibles
    print("🎰 Testing Parlay Generator...")
    generator = RealtimeParlayGenerator()
    generator.generate_on_new_drop(0)  # 0 = générer à partir de tous les drops
    generator.close()
