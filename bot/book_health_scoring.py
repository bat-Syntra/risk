"""
Book Health Scoring Engine
Advanced algorithm with 8 factors to predict casino limits
"""
import logging
import math
import uuid
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple
from decimal import Decimal

from database import SessionLocal
from sqlalchemy import text as sql_text

logger = logging.getLogger(__name__)


class BookHealthScoring:
    """Advanced scoring algorithm with 8 factors"""
    
    def calculate_health_score(self, user_id: str, casino: str) -> Dict:
        """Calculate comprehensive health score for user-casino pair"""
        logger.info(f"📊 Calculating health score for {user_id} @ {casino}")
        
        db = SessionLocal()
        try:
            # Get user profile
            profile = db.execute(sql_text("""
                SELECT * FROM user_casino_profiles 
                WHERE user_id = :user_id AND casino = :casino
            """), {"user_id": user_id, "casino": casino}).first()
            
            if not profile:
                return {
                    'score': 0,
                    'risk_level': 'NO_PROFILE',
                    'message': 'Profile not found. Run onboarding first.'
                }
            
            # Get betting history from bet_analytics
            bets = db.execute(sql_text("""
                SELECT * FROM bet_analytics
                WHERE user_id = :user_id AND casino = :casino
                ORDER BY bet_placed_at DESC
            """), {"user_id": user_id, "casino": casino}).fetchall()
            
            if len(bets) < 10:
                return {
                    'score': 0,
                    'risk_level': 'INSUFFICIENT_DATA',
                    'message': f'Need at least 10 bets (current: {len(bets)})',
                    'total_bets': len(bets)
                }
            
            # Calculate individual factors
            factors = {
                'win_rate': self._calculate_win_rate_factor(bets),
                'clv': self._calculate_clv_factor(bets),
                'diversity': self._calculate_diversity_factor(bets),
                'timing': self._calculate_timing_factor(bets),
                'stake_pattern': self._calculate_stake_pattern_factor(bets),
                'bet_type': self._calculate_bet_type_factor(bets),
                'activity_change': self._calculate_activity_change_factor(bets, profile),
                'withdrawal': self._calculate_withdrawal_factor(user_id, casino, db)
            }
            
            # Combine factors
            total_score = sum(f['score'] for f in factors.values())
            
            # Determine risk level
            risk_level = self._get_risk_level(total_score)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(factors, total_score)
            
            # Estimate time until limit
            estimated_months = self._estimate_months_until_limit(total_score, profile)
            
            # Calculate limit probability
            limit_probability = self._calculate_limit_probability(total_score)
            
            # Store score in database
            self._store_score(db, user_id, casino, factors, total_score, risk_level, 
                            estimated_months, limit_probability, len(bets))
            
            # Get trend
            trend = self._calculate_trend(db, user_id, casino)
            
            return {
                'score': total_score,
                'risk_level': risk_level,
                'factors': factors,
                'recommendations': recommendations,
                'estimated_months': estimated_months,
                'limit_probability': limit_probability,
                'trend': trend,
                'total_bets': len(bets)
            }
            
        finally:
            db.close()
    
    def _calculate_win_rate_factor(self, bets) -> Dict:
        """Win rate factor (0-25 points) - Too high win rate is suspicious"""
        completed = [b for b in bets if b.result in ['won', 'lost']]
        if not completed:
            return {'score': 0, 'value': None, 'max': 25, 'label': 'No completed bets'}
        
        wins = len([b for b in completed if b.result == 'won'])
        win_rate = wins / len(completed)
        
        # Score based on win rate
        if win_rate >= 0.65: score = 25  # 🔴 65%+ = VERY suspicious
        elif win_rate >= 0.60: score = 20
        elif win_rate >= 0.57: score = 15
        elif win_rate >= 0.55: score = 10
        elif win_rate >= 0.53: score = 5
        else: score = 0  # < 53% = normal
        
        return {
            'score': score,
            'value': win_rate,
            'max': 25,
            'label': f'{win_rate*100:.1f}% win rate'
        }
    
    def _calculate_clv_factor(self, bets) -> Dict:
        """CLV factor (0-30 points) - Most important factor"""
        bets_with_clv = [b for b in bets if b.clv is not None]
        if not bets_with_clv:
            return {'score': 0, 'value': None, 'max': 30, 'label': 'No CLV data'}
        
        avg_clv = sum(float(b.clv) for b in bets_with_clv) / len(bets_with_clv)
        
        # Score based on CLV
        if avg_clv >= 0.08: score = 30  # 🔴 8%+ CLV = EXTREME sharp
        elif avg_clv >= 0.05: score = 25
        elif avg_clv >= 0.03: score = 20
        elif avg_clv >= 0.02: score = 15
        elif avg_clv >= 0.01: score = 10
        elif avg_clv >= 0: score = 5
        else: score = 0  # Negative CLV = good for books
        
        return {
            'score': score,
            'value': avg_clv,
            'max': 30,
            'label': f'{avg_clv*100:.1f}% avg CLV'
        }
    
    def _calculate_diversity_factor(self, bets) -> Dict:
        """Diversity factor (0-15 points) - Low diversity is suspicious"""
        sports = set(b.sport for b in bets if b.sport)
        markets = set(b.market_type for b in bets if b.market_type)
        
        sports_count = len(sports)
        markets_count = len(markets)
        
        # Low diversity = focusing on specific edges
        if sports_count <= 1 and markets_count <= 2: score = 15  # 🔴 ONE sport, TWO markets
        elif sports_count <= 2 and markets_count <= 3: score = 10
        elif sports_count <= 3: score = 5
        else: score = 0  # Good diversity
        
        return {
            'score': score,
            'value': {'sports': sports_count, 'markets': markets_count},
            'max': 15,
            'label': f'{sports_count} sports, {markets_count} markets'
        }
    
    def _calculate_timing_factor(self, bets) -> Dict:
        """Timing factor (0-15 points) - Fast betting = bot-like"""
        bets_with_timing = [b for b in bets if b.seconds_after_post is not None]
        if not bets_with_timing:
            return {'score': 0, 'value': None, 'max': 15, 'label': 'No timing data'}
        
        avg_delay = sum(b.seconds_after_post for b in bets_with_timing) / len(bets_with_timing)
        
        # Fast betting = bot-like behavior
        if avg_delay < 20: score = 15  # 🔴 < 20 seconds = BOT
        elif avg_delay < 60: score = 12
        elif avg_delay < 120: score = 8
        elif avg_delay < 300: score = 4
        else: score = 0  # 5+ minutes = normal
        
        return {
            'score': score,
            'value': avg_delay,
            'max': 15,
            'label': f'{int(avg_delay)}s avg delay'
        }
    
    def _calculate_stake_pattern_factor(self, bets) -> Dict:
        """Stake pattern factor (0-10 points) - Precise stakes = calculator user"""
        stakes = [float(b.stake_amount) for b in bets if b.stake_amount]
        if not stakes:
            return {'score': 0, 'value': None, 'max': 10, 'label': 'No stake data'}
        
        # Check if stakes are rounded
        rounded = sum(1 for s in stakes if s % 5 == 0 or s % 10 == 0)
        rounded_ratio = rounded / len(stakes)
        
        # Calculate coefficient of variation
        avg_stake = sum(stakes) / len(stakes)
        if avg_stake > 0:
            variance = sum((s - avg_stake) ** 2 for s in stakes) / len(stakes)
            std_dev = math.sqrt(variance)
            cv = std_dev / avg_stake
        else:
            cv = 0
        
        # Low variance + non-rounded = calculator user
        if rounded_ratio < 0.3 and cv < 0.2: score = 10  # 🔴 VERY precise stakes
        elif rounded_ratio < 0.5: score = 6
        elif rounded_ratio < 0.7: score = 3
        else: score = 0
        
        return {
            'score': score,
            'value': {'rounded_ratio': rounded_ratio, 'cv': cv},
            'max': 10,
            'label': f'{rounded_ratio*100:.0f}% rounded stakes'
        }
    
    def _calculate_bet_type_factor(self, bets) -> Dict:
        """Bet type factor (0-20 points) - Too many sharp bets"""
        total = len(bets)
        
        # Count by source type
        plus_ev = len([b for b in bets if b.bet_source_type == 'plus_ev'])
        arbitrage = len([b for b in bets if b.bet_source_type == 'arbitrage'])
        middle = len([b for b in bets if b.bet_source_type == 'middle'])
        recreational = len([b for b in bets if b.bet_source_type == 'recreational'])
        
        sharp_ratio = (plus_ev + arbitrage + middle) / total if total > 0 else 0
        rec_ratio = recreational / total if total > 0 else 0
        
        # High sharp ratio = suspicious
        if sharp_ratio >= 0.95 and rec_ratio < 0.05: score = 20  # 🔴 95%+ sharp
        elif sharp_ratio >= 0.90 and rec_ratio < 0.10: score = 16
        elif sharp_ratio >= 0.85 and rec_ratio < 0.15: score = 12
        elif sharp_ratio >= 0.80 and rec_ratio < 0.20: score = 8
        elif sharp_ratio >= 0.70: score = 4
        else: score = 0
        
        return {
            'score': score,
            'value': {
                'sharp_ratio': sharp_ratio,
                'rec_ratio': rec_ratio,
                'plus_ev': plus_ev / total if total > 0 else 0,
                'arbitrage': arbitrage / total if total > 0 else 0,
                'middle': middle / total if total > 0 else 0
            },
            'max': 20,
            'label': f'{sharp_ratio*100:.0f}% sharp bets'
        }
    
    def _calculate_activity_change_factor(self, bets, profile) -> Dict:
        """Activity change factor (0-15 points) - Sudden increase suspicious"""
        if not profile.was_active_before:
            # User wasn't active before - sudden activity is suspicious
            
            # Calculate activity rate
            if profile.created_at:
                days_since_joined = (datetime.utcnow() - profile.created_at).days
                if days_since_joined > 0:
                    bets_per_month = (len(bets) / days_since_joined) * 30
                else:
                    bets_per_month = len(bets) * 30
            else:
                bets_per_month = 100  # Default high value
            
            # Score based on activity change
            if bets_per_month > 200: score = 15  # 🔴 200+ bets/month from inactive
            elif bets_per_month > 150: score = 12
            elif bets_per_month > 100: score = 8
            elif bets_per_month > 50: score = 4
            else: score = 0
            
            return {
                'score': score,
                'value': bets_per_month,
                'max': 15,
                'label': f'{bets_per_month:.0f} bets/month (was inactive)'
            }
        else:
            # Was already active - no penalty
            return {
                'score': 0,
                'value': 0,
                'max': 15,
                'label': 'Was already active'
            }
    
    def _calculate_withdrawal_factor(self, user_id: str, casino: str, db) -> Dict:
        """Withdrawal factor (0-5 points) - Frequent withdrawals suspicious"""
        # This would track withdrawal history if available
        # For now, placeholder
        return {
            'score': 0,
            'value': None,
            'max': 5,
            'label': 'Not tracked yet'
        }
    
    def _get_risk_level(self, score: float) -> str:
        """Determine risk level from total score"""
        if score >= 86: return 'CRITICAL'      # ⛔ Limit imminent
        if score >= 71: return 'HIGH_RISK'     # 🔴 High risk
        if score >= 51: return 'WARNING'       # 🟠 Warning
        if score >= 31: return 'MONITOR'       # 🟡 Monitor
        return 'SAFE'                          # 🟢 Safe
    
    def _estimate_months_until_limit(self, score: float, profile) -> float:
        """Estimate months until limit based on score and account age"""
        account_age_months = profile.account_age_months or 6
        
        # Base estimate from score
        if score >= 86: base_months = 0.5      # Weeks
        elif score >= 71: base_months = 3
        elif score >= 51: base_months = 9
        elif score >= 31: base_months = 15
        else: base_months = 24                 # 2+ years
        
        # Adjust for account age (newer = faster limits)
        if account_age_months < 6: age_factor = 0.7    # 30% faster
        elif account_age_months < 12: age_factor = 0.85
        elif account_age_months > 24: age_factor = 1.2  # 20% slower
        else: age_factor = 1.0
        
        return round(base_months * age_factor * 10) / 10
    
    def _calculate_limit_probability(self, score: float) -> float:
        """Calculate probability of being limited (0-1)"""
        # Sigmoid function for smooth probability
        # Maps score 0-100 to probability 0-1
        # Score 50 = 50% probability, Score 75 = ~88% probability
        x = (score - 50) / 10  # Center at 50, scale factor 10
        probability = 1 / (1 + math.exp(-x))
        return min(0.99, max(0.01, probability))  # Clamp between 1-99%
    
    def _generate_recommendations(self, factors: Dict, total_score: float) -> List[Dict]:
        """Generate personalized recommendations based on factors"""
        recommendations = []
        
        # Win rate too high
        if factors['win_rate']['score'] >= 15:
            recommendations.append({
                'type': 'reduce_win_rate',
                'priority': 'HIGH' if factors['win_rate']['score'] >= 20 else 'MEDIUM',
                'text': f"Ta win rate ({factors['win_rate']['value']*100:.1f}%) est trop élevée. "
                       f"Ajoute quelques paris récréatifs ou skip certains arbs marginaux."
            })
        
        # CLV too high
        if factors['clv']['score'] >= 15:
            recommendations.append({
                'type': 'reduce_clv',
                'priority': 'CRITICAL' if factors['clv']['score'] >= 25 else 'HIGH',
                'text': f"Ton CLV (+{factors['clv']['value']*100:.1f}%) est TRÈS élevé. "
                       f"Les books savent que tu bats le marché. Attends plus avant de parier ou skip les sharp plays."
            })
        
        # Low diversity
        if factors['diversity']['score'] >= 10:
            sports = factors['diversity']['value']['sports']
            recommendations.append({
                'type': 'diversify_sports',
                'priority': 'MEDIUM',
                'text': f"Tu paries sur seulement {sports} sport(s). "
                       f"Ajoute 2-3 sports de plus pour paraître moins spécialisé."
            })
        
        # Timing too fast
        if factors['timing']['score'] >= 8:
            avg_delay = factors['timing']['value']
            recommendations.append({
                'type': 'increase_delay',
                'priority': 'HIGH' if factors['timing']['score'] >= 12 else 'MEDIUM',
                'text': f"Tu paries en moyenne {int(avg_delay)}s après les lignes. "
                       f"Attends au moins 5 minutes pour éviter de paraître bot-like."
            })
        
        # Stakes too precise
        if factors['stake_pattern']['score'] >= 6:
            rounded_ratio = factors['stake_pattern']['value']['rounded_ratio']
            recommendations.append({
                'type': 'round_stakes',
                'priority': 'LOW',
                'text': f"Seulement {rounded_ratio*100:.0f}% de tes mises sont arrondies. "
                       f"Utilise des montants ronds ($50, $100) au lieu de $47.23."
            })
        
        # Too many sharp bets
        if factors['bet_type']['score'] >= 12:
            sharp_ratio = factors['bet_type']['value']['sharp_ratio']
            recommendations.append({
                'type': 'add_recreational',
                'priority': 'CRITICAL' if factors['bet_type']['score'] >= 16 else 'HIGH',
                'text': f"{sharp_ratio*100:.0f}% de tes paris sont des sharp plays. "
                       f"AJOUTE 20-30% de paris récréatifs (petites mises sur favoris, etc.)."
            })
        
        # Activity change suspicious
        if factors['activity_change']['score'] >= 8:
            bets_per_month = factors['activity_change']['value']
            recommendations.append({
                'type': 'slow_down_activity',
                'priority': 'HIGH' if factors['activity_change']['score'] >= 12 else 'MEDIUM',
                'text': f"Tu fais {bets_per_month:.0f} paris/mois alors que tu étais inactif avant. "
                       f"Ralentis un peu (réduis 20-30%)."
            })
        
        # Critical score - emergency actions
        if total_score >= 86:
            recommendations.insert(0, {
                'type': 'extract_funds',
                'priority': 'CRITICAL',
                'text': f"⛔ URGENT: Score critique ({total_score:.0f}/100). "
                       f"Limite attendue BIENTÔT. Retire tes fonds lentement sur 1-2 semaines. "
                       f"Stop TOUS les arbs évidents."
            })
        
        # Sort by priority
        priority_order = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
        recommendations.sort(key=lambda r: priority_order.index(r['priority']))
        
        return recommendations[:5]  # Top 5 recommendations
    
    def _store_score(self, db, user_id: str, casino: str, factors: Dict, 
                    total_score: float, risk_level: str, estimated_months: float,
                    limit_probability: float, total_bets: int):
        """Store calculated score in database"""
        try:
            # Calculate metrics snapshot
            win_rate = factors['win_rate']['value']
            avg_clv = factors['clv']['value']
            sports_count = factors['diversity']['value']['sports'] if factors['diversity']['value'] else 0
            avg_delay = factors['timing']['value']
            
            # Insert new score record
            db.execute(sql_text("""
                INSERT INTO book_health_scores (
                    score_id, user_id, casino, calculation_date,
                    win_rate_score, clv_score, diversity_score, timing_score,
                    stake_pattern_score, withdrawal_score, bet_type_score, activity_change_score,
                    total_score, risk_level, total_bets, win_rate, avg_clv,
                    sports_count, avg_delay_seconds, estimated_months_until_limit,
                    limit_probability
                ) VALUES (
                    :id, :user_id, :casino, :date,
                    :win_rate_score, :clv_score, :diversity_score, :timing_score,
                    :stake_score, :withdrawal_score, :bet_type_score, :activity_score,
                    :total_score, :risk_level, :total_bets, :win_rate, :avg_clv,
                    :sports_count, :avg_delay, :estimated_months, :limit_prob
                )
                ON CONFLICT (user_id, casino, calculation_date) DO UPDATE SET
                    total_score = EXCLUDED.total_score,
                    risk_level = EXCLUDED.risk_level,
                    created_at = now()
            """), {
                'id': str(uuid.uuid4()),
                'user_id': user_id,
                'casino': casino,
                'date': date.today(),
                'win_rate_score': factors['win_rate']['score'],
                'clv_score': factors['clv']['score'],
                'diversity_score': factors['diversity']['score'],
                'timing_score': factors['timing']['score'],
                'stake_score': factors['stake_pattern']['score'],
                'withdrawal_score': factors['withdrawal']['score'],
                'bet_type_score': factors['bet_type']['score'],
                'activity_score': factors['activity_change']['score'],
                'total_score': total_score,
                'risk_level': risk_level,
                'total_bets': total_bets,
                'win_rate': win_rate,
                'avg_clv': avg_clv,
                'sports_count': sports_count,
                'avg_delay': int(avg_delay) if avg_delay else None,
                'estimated_months': estimated_months,
                'limit_prob': limit_probability
            })
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Error storing score: {e}")
            db.rollback()
    
    def _calculate_trend(self, db, user_id: str, casino: str) -> Dict:
        """Calculate score trend over time"""
        # Get historical scores
        scores = db.execute(sql_text("""
            SELECT total_score, calculation_date
            FROM book_health_scores
            WHERE user_id = :user_id AND casino = :casino
            ORDER BY calculation_date DESC
            LIMIT 30
        """), {'user_id': user_id, 'casino': casino}).fetchall()
        
        if len(scores) < 2:
            return {'change_7d': None, 'change_30d': None, 'trend': 'INSUFFICIENT_DATA'}
        
        current_score = scores[0].total_score
        
        # Find 7 days ago
        week_ago = date.today() - timedelta(days=7)
        score_7d = None
        for s in scores:
            if s.calculation_date <= week_ago:
                score_7d = s.total_score
                break
        
        # Find 30 days ago
        month_ago = date.today() - timedelta(days=30)
        score_30d = None
        for s in scores:
            if s.calculation_date <= month_ago:
                score_30d = s.total_score
                break
        
        # Calculate changes
        change_7d = float(current_score - score_7d) if score_7d else None
        change_30d = float(current_score - score_30d) if score_30d else None
        
        # Determine trend
        if change_30d is None:
            trend = 'INSUFFICIENT_DATA'
        elif change_30d > 15:
            trend = 'RAPIDLY_WORSENING'
        elif change_30d > 8:
            trend = 'WORSENING'
        elif change_30d > 3:
            trend = 'SLOWLY_WORSENING'
        elif change_30d < -3:
            trend = 'IMPROVING'
        else:
            trend = 'STABLE'
        
        return {
            'change_7d': change_7d,
            'change_30d': change_30d,
            'trend': trend
        }
