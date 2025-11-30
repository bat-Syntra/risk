#!/usr/bin/env python3
"""
Real-Time Parlay Generator
Se déclenche automatiquement quand un nouveau drop arrive
- Génère IMMÉDIATEMENT après chaque drop arbitrage/middle/good_ev
- Utilise drops AVEC OU SANS date (économise API!)
- Optimise pour les meilleurs % et multiplicateurs
"""
import json
from datetime import datetime
from database import SessionLocal
from sqlalchemy import text
from smart_parlay_generator import SmartParlayGenerator

class RealtimeParlayGenerator:
    
    def __init__(self):
        self.db = SessionLocal()
        self.generator = SmartParlayGenerator()
        
        # Seuils optimisés pour MEILLEURS parlays
        self.thresholds = {
            'arbitrage_min': 4.0,      # 4%+ arb
            'middle_min': 2.0,         # 2%+ middle  
            'good_ev_min': 10.0,       # 10%+ EV
            'parlay_min_combined': 3.0, # 3x minimum combined odds
            'parlay_max_combined': 15.0 # 15x maximum (pas trop risqué)
        }
    
    def should_generate(self, new_drop):
        """
        Décide si on doit générer un nouveau parlay
        Basé sur la qualité du drop
        """
        bet_type = new_drop.get('bet_type', '')
        edge = new_drop.get('arb_percentage', 0)
        
        # Vérifier si le drop est assez bon
        if bet_type == 'arbitrage' and edge >= self.thresholds['arbitrage_min']:
            return True
        elif bet_type == 'middle' and edge >= self.thresholds['middle_min']:
            return True
        elif bet_type == 'good_ev' and edge >= self.thresholds['good_ev_min']:
            return True
        
        return False
    
    def generate_on_new_drop(self, drop_event_id):
        """
        Génère un ou plusieurs parlays quand un nouveau drop arrive
        
        Args:
            drop_event_id: ID du drop qui vient d'arriver
        """
        try:
            print(f"🔥 New drop {drop_event_id} - Analyzing for parlays...")
            
            # Récupérer le nouveau drop
            new_drop_row = self.db.execute(text("""
                SELECT * FROM drop_events WHERE id = :id
            """), {'id': drop_event_id}).fetchone()
            
            if not new_drop_row:
                print("❌ Drop not found")
                return
            
            # Parser le drop
            new_drop = {
                'bet_type': new_drop_row.bet_type,
                'arb_percentage': new_drop_row.arb_percentage
            }
            
            # Vérifier s'il mérite un parlay
            if not self.should_generate(new_drop):
                print(f"⚠️ Drop edge too low ({new_drop['arb_percentage']:.1f}%), skipping")
                return
            
            # Parser le nouveau drop en leg
            new_leg = self.generator.parse_drop_to_leg(new_drop_row)
            if not new_leg:
                print("❌ Could not parse drop as leg")
                return
            
            print(f"✅ New leg: {new_leg['market']} @ {new_leg['odds']} ({new_leg['bookmaker']})")
            
            # Récupérer les MEILLEURS drops récents pour combiner
            recent_drops = self.db.execute(text("""
                SELECT * FROM drop_events
                WHERE date(received_at) >= date('now', '-2 days')
                AND id != :new_id
                AND (
                    (bet_type = 'arbitrage' AND arb_percentage >= :arb_threshold)
                    OR (bet_type = 'middle' AND arb_percentage >= :middle_threshold)
                    OR (bet_type = 'good_ev' AND arb_percentage >= :ev_threshold)
                )
                ORDER BY arb_percentage DESC
                LIMIT 100
            """), {
                'new_id': drop_event_id,
                'arb_threshold': self.thresholds['arbitrage_min'],
                'middle_threshold': self.thresholds['middle_min'],
                'ev_threshold': self.thresholds['good_ev_min']
            }).fetchall()
            
            print(f"📊 Found {len(recent_drops)} quality drops to combine with")
            
            # Parser en legs
            available_legs = [new_leg]  # Commencer avec le nouveau
            for drop in recent_drops:
                leg = self.generator.parse_drop_to_leg(drop)
                if leg:
                    available_legs.append(leg)
            
            if len(available_legs) < 2:
                print("⚠️ Not enough legs to create parlays")
                return
            
            print(f"✅ {len(available_legs)} legs available for parlays")
            
            # Créer des parlays INTELLIGENTS
            parlays_created = 0
            
            # STRATÉGIE 1: Parlay avec le nouveau leg + meilleur leg dispo
            # (2 legs = meilleur ROI)
            best_partner = self._find_best_partner(new_leg, available_legs[1:])
            if best_partner:
                parlay = self.generator.create_parlay([new_leg, best_partner], 'BALANCED')
                combined_odds = parlay['combined_decimal_odds']
                
                # Vérifier si dans les limites
                if self.thresholds['parlay_min_combined'] <= combined_odds <= self.thresholds['parlay_max_combined']:
                    self.generator.save_parlay(parlay)
                    parlays_created += 1
                    print(f"✅ Created 2-leg parlay: {combined_odds:.2f}x")
            
            # STRATÉGIE 2: Si le nouveau leg est TRÈS bon (>8%), créer un 3-leg
            if new_leg['edge'] >= 8.0 and len(available_legs) >= 3:
                partners = self._find_best_partners(new_leg, available_legs[1:], count=2)
                if len(partners) == 2:
                    parlay = self.generator.create_parlay([new_leg] + partners, 'AGGRESSIVE')
                    combined_odds = parlay['combined_decimal_odds']
                    
                    if self.thresholds['parlay_min_combined'] <= combined_odds <= self.thresholds['parlay_max_combined']:
                        self.generator.save_parlay(parlay)
                        parlays_created += 1
                        print(f"✅ Created 3-leg parlay: {combined_odds:.2f}x")
            
            # STRATÉGIE 3: Parlay SAFE (2 legs avec edge très élevé)
            if new_leg['edge'] >= 6.0:
                safe_partners = [l for l in available_legs[1:] if l['edge'] >= 6.0]
                if safe_partners:
                    partner = safe_partners[0]
                    parlay = self.generator.create_parlay([new_leg, partner], 'CONSERVATIVE')
                    combined_odds = parlay['combined_decimal_odds']
                    
                    if combined_odds >= self.thresholds['parlay_min_combined']:
                        self.generator.save_parlay(parlay)
                        parlays_created += 1
                        print(f"✅ Created SAFE parlay: {combined_odds:.2f}x (high edge)")
            
            self.db.commit()
            
            if parlays_created > 0:
                print(f"🎉 Generated {parlays_created} new parlay(s) in REAL-TIME!")
            else:
                print("⚠️ No suitable parlays created (odds out of range)")
            
            # Nettoyer les vieux parlays (>48h)
            self._cleanup_old_parlays()
        except Exception as e:
            self.db.rollback()
            print(f"❌ Error generating parlays: {e}")
            import traceback
            traceback.print_exc()
    
    def _find_best_partner(self, anchor_leg, candidates):
        """Trouve le meilleur leg partenaire pour l'anchor"""
        if not candidates:
            return None
        
        # Critères de sélection:
        # 1. Bookmaker différent (diversification)
        # 2. Edge élevé
        # 3. Sport différent (moins de corrélation)
        
        best = None
        best_score = 0
        
        for candidate in candidates:
            score = 0
            
            # +3 points si bookmaker différent
            if candidate['bookmaker'] != anchor_leg['bookmaker']:
                score += 3
            
            # +edge points pour l'edge
            score += candidate['edge']
            
            # +2 points si sport différent
            if candidate['sport'] != anchor_leg['sport']:
                score += 2
            
            if score > best_score:
                best_score = score
                best = candidate
        
        return best
    
    def _find_best_partners(self, anchor_leg, candidates, count=2):
        """Trouve les N meilleurs legs partenaires"""
        if len(candidates) < count:
            return candidates[:count]
        
        # Scorer tous les candidats
        scored = []
        for candidate in candidates:
            score = 0
            
            if candidate['bookmaker'] != anchor_leg['bookmaker']:
                score += 3
            
            score += candidate['edge']
            
            if candidate['sport'] != anchor_leg['sport']:
                score += 2
            
            scored.append((candidate, score))
        
        # Trier par score
        scored.sort(key=lambda x: x[1], reverse=True)
        
        # Prendre les N meilleurs
        return [leg for leg, score in scored[:count]]
    
    def _cleanup_old_parlays(self):
        """Supprime les parlays de plus de 48h"""
        # Use a separate session to avoid locking conflicts
        db = SessionLocal()
        try:
            result = db.execute(text("""
                UPDATE parlays 
                SET status = 'expired'
                WHERE status = 'pending'
                AND created_at < datetime('now', '-2 days')
            """))
            
            deleted = result.rowcount
            if deleted > 0:
                db.commit()
                print(f" Cleaned up {deleted} old parlay(s)")
        except Exception as e:
            db.rollback()  # ROLLBACK pour libérer le lock!
            print(f" Error cleaning up old parlays: {e}")
        finally:
            db.close()  # Fermer la session proprement
    
    def close(self):
        self.db.close()

# Fonction hook pour main_new.py
def on_drop_received(drop_event_id):
    """
    À appeler depuis main_new.py après qu'un drop soit enregistré
    
    Usage dans main_new.py:
        from realtime_parlay_generator import on_drop_received
        
        # Après avoir enregistré le drop:
        drop_id = record_drop(drop_data)
        on_drop_received(drop_id)  # Génère parlays en temps réel!
    """
    try:
        generator = RealtimeParlayGenerator()
        generator.generate_on_new_drop(drop_event_id)
        generator.close()
    except Exception as e:
        print(f"Error generating real-time parlays: {e}")

if __name__ == "__main__":
    # Test
    import sys
    if len(sys.argv) > 1:
        drop_id = int(sys.argv[1])
        generator = RealtimeParlayGenerator()
        generator.generate_on_new_drop(drop_id)
        generator.close()
    else:
        print("Usage: python3 realtime_parlay_generator.py <drop_event_id>")
