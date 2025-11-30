#!/usr/bin/env python3
"""
Smart Parlay Updater - Système intelligent de mise à jour des parlays
- Vérifie les cotes SEULEMENT quand user clique
- Update/Remplace/Supprime intelligemment
- Minimise les appels API
"""
import json
import asyncio
from datetime import datetime
from database import SessionLocal
from sqlalchemy import text
from utils.odds_verifier import OddsVerifier

class SmartParlayUpdater:
    
    def __init__(self):
        self.db = SessionLocal()
        self.verifier = OddsVerifier()
    
    async def smart_update_parlay(self, parlay_id):
        """
        Met à jour intelligemment un parlay après vérification
        
        Returns:
            dict avec status et action prise
        """
        # Récupérer le parlay
        parlay = self.db.execute(text("""
            SELECT * FROM parlays WHERE parlay_id = :id
        """), {'id': parlay_id}).fetchone()
        
        if not parlay:
            return {'status': 'error', 'message': 'Parlay not found'}
        
        # Parser les legs
        try:
            legs_detail = json.loads(parlay.legs_detail) if parlay.legs_detail else []
        except:
            return {'status': 'error', 'message': 'Invalid legs data'}
        
        if not legs_detail:
            return {'status': 'error', 'message': 'No legs found'}
        
        # Vérifier les cotes
        verification = await self.verifier.verify_parlay_odds(legs_detail)
        
        # DÉCISION INTELLIGENTE basée sur la vérification
        action = await self._decide_action(parlay, legs_detail, verification)
        
        return action
    
    async def _decide_action(self, parlay, legs_detail, verification):
        """Décide quelle action prendre basé sur la vérification"""
        
        total_legs = verification['total_legs']
        unavailable = verification['legs_unavailable']
        worse = verification['legs_worse']
        better = verification['legs_better']
        verified = verification['verified_legs']
        
        # CAS 1: Tout est bon ✅
        if verified == total_legs or better > 0:
            return {
                'status': 'keep',
                'action': 'kept',
                'message': f'✅ Parlay still good! {better} legs improved' if better > 0 else '✅ All odds verified',
                'changes': []
            }
        
        # CAS 2: Quelques cotes pires mais pas catastrophique ⚠️
        if worse > 0 and worse < total_legs and unavailable == 0:
            # Recalculer le edge avec les nouvelles cotes
            new_combined_odds = 1.0
            for detail in verification['details']:
                if detail['status'] in ['verified', 'better', 'worse']:
                    new_combined_odds *= detail.get('current_odds', detail['leg']['odds'])
            
            # Si le edge reste positif, on UPDATE
            old_edge = parlay.calculated_edge * 100
            new_edge = ((new_combined_odds - 1) / new_combined_odds) * 100  # Approximation
            
            if new_edge > 0:
                # UPDATE le parlay avec les nouvelles cotes
                await self._update_parlay_odds(parlay.parlay_id, verification['details'])
                return {
                    'status': 'updated',
                    'action': 'updated',
                    'message': f'⚠️ Updated: Edge {old_edge:.1f}% → {new_edge:.1f}%',
                    'changes': [f"Leg {i+1}: odds changed" for i, d in enumerate(verification['details']) if d['status'] == 'worse']
                }
            else:
                # Edge devient négatif → SUPPRIMER
                await self._delete_parlay(parlay.parlay_id)
                return {
                    'status': 'deleted',
                    'action': 'deleted',
                    'message': f'❌ Deleted: Edge too low ({new_edge:.1f}%)',
                    'changes': []
                }
        
        # CAS 3: Un ou plusieurs legs indisponibles 🔄
        if unavailable > 0:
            # Essayer de remplacer les legs morts
            replacement = await self._try_replace_legs(parlay, legs_detail, verification)
            
            if replacement['success']:
                return {
                    'status': 'replaced',
                    'action': 'replaced',
                    'message': f'🔄 Replaced {unavailable} unavailable leg(s)',
                    'changes': replacement['changes']
                }
            else:
                # Pas de remplacement possible → SUPPRIMER
                await self._delete_parlay(parlay.parlay_id)
                return {
                    'status': 'deleted',
                    'action': 'deleted',
                    'message': f'❌ Deleted: {unavailable} leg(s) unavailable, no replacement found',
                    'changes': []
                }
        
        # CAS 4: Catastrophe totale ❌
        if unavailable >= total_legs or worse >= total_legs:
            await self._delete_parlay(parlay.parlay_id)
            return {
                'status': 'deleted',
                'action': 'deleted',
                'message': '❌ Deleted: Parlay no longer viable',
                'changes': []
            }
        
        # Default: garder si incertain
        return {
            'status': 'keep',
            'action': 'kept',
            'message': '✅ Keeping parlay (uncertain but safe)',
            'changes': []
        }
    
    async def _update_parlay_odds(self, parlay_id, verification_details):
        """Met à jour les cotes d'un parlay"""
        try:
            # Récupérer le parlay
            parlay = self.db.execute(text("""
                SELECT legs_detail FROM parlays WHERE parlay_id = :id
            """), {'id': parlay_id}).fetchone()
            
            legs_detail = json.loads(parlay.legs_detail) if parlay.legs_detail else []
            
            # Mettre à jour les cotes
            new_combined_odds = 1.0
            for i, detail in enumerate(verification_details):
                if i < len(legs_detail):
                    current_odds = detail.get('current_odds')
                    if current_odds:
                        legs_detail[i]['odds'] = current_odds
                        new_combined_odds *= current_odds
            
            # Calculer le nouveau edge (approximation)
            new_edge = ((new_combined_odds - 1) / new_combined_odds) * 100 / 100
            
            # UPDATE en DB
            self.db.execute(text("""
                UPDATE parlays 
                SET legs_detail = :legs,
                    combined_decimal_odds = :odds,
                    calculated_edge = :edge,
                    updated_at = CURRENT_TIMESTAMP
                WHERE parlay_id = :id
            """), {
                'legs': json.dumps(legs_detail),
                'odds': new_combined_odds,
                'edge': new_edge,
                'id': parlay_id
            })
            self.db.commit()
            
        except Exception as e:
            print(f"Error updating parlay {parlay_id}: {e}")
    
    async def _try_replace_legs(self, parlay, legs_detail, verification):
        """Essaye de remplacer les legs morts avec de nouveaux drops"""
        try:
            # Identifier les legs à remplacer
            dead_indices = []
            for i, detail in enumerate(verification['details']):
                if detail['status'] == 'unavailable':
                    dead_indices.append(i)
            
            if not dead_indices:
                return {'success': False, 'changes': []}
            
            # Chercher des drops similaires pour remplacer
            from smart_parlay_generator import SmartParlayGenerator
            generator = SmartParlayGenerator()
            
            # Récupérer des drops récents de qualité
            drops = self.db.execute(text("""
                SELECT * FROM drop_events
                WHERE date(received_at) >= date('now', '-1 day')
                AND (
                    (bet_type = 'arbitrage' AND arb_percentage >= 4.0)
                    OR (bet_type = 'middle' AND arb_percentage >= 2.0)
                    OR (bet_type = 'good_ev' AND arb_percentage >= 10.0)
                )
                ORDER BY arb_percentage DESC
                LIMIT 50
            """)).fetchall()
            
            # Parser les drops en legs
            replacement_legs = []
            for drop in drops:
                leg = generator.parse_drop_to_leg(drop)
                if leg:
                    replacement_legs.append(leg)
            
            if len(replacement_legs) < len(dead_indices):
                return {'success': False, 'changes': []}
            
            # Remplacer les legs morts
            changes = []
            for idx in dead_indices:
                if replacement_legs:
                    new_leg = replacement_legs.pop(0)
                    old_leg = legs_detail[idx]
                    legs_detail[idx] = new_leg
                    changes.append(f"Replaced {old_leg['market']} with {new_leg['market']}")
            
            # Recalculer les cotes combinées
            new_combined_odds = 1.0
            new_bookmakers = set()
            for leg in legs_detail:
                new_combined_odds *= leg['odds']
                new_bookmakers.add(leg['bookmaker'])
            
            # UPDATE le parlay
            self.db.execute(text("""
                UPDATE parlays
                SET legs_detail = :legs,
                    bookmakers = :bookmakers,
                    combined_decimal_odds = :odds,
                    updated_at = CURRENT_TIMESTAMP
                WHERE parlay_id = :id
            """), {
                'legs': json.dumps(legs_detail),
                'bookmakers': json.dumps(list(new_bookmakers)),
                'odds': new_combined_odds,
                'id': parlay.parlay_id
            })
            self.db.commit()
            
            return {'success': True, 'changes': changes}
            
        except Exception as e:
            print(f"Error replacing legs: {e}")
            return {'success': False, 'changes': []}
    
    async def _delete_parlay(self, parlay_id):
        """Supprime un parlay devenu non viable"""
        try:
            self.db.execute(text("""
                UPDATE parlays 
                SET status = 'expired',
                    updated_at = CURRENT_TIMESTAMP
                WHERE parlay_id = :id
            """), {'id': parlay_id})
            self.db.commit()
        except Exception as e:
            print(f"Error deleting parlay {parlay_id}: {e}")
    
    def close(self):
        self.db.close()

if __name__ == "__main__":
    # Test
    import sys
    if len(sys.argv) > 1:
        parlay_id = int(sys.argv[1])
        updater = SmartParlayUpdater()
        result = asyncio.run(updater.smart_update_parlay(parlay_id))
        print(f"Result: {result}")
        updater.close()
    else:
        print("Usage: python3 smart_parlay_updater.py <parlay_id>")
