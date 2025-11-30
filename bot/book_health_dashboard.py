"""
Book Health Dashboard
Interactive UI for viewing health scores and trends
"""
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional
from aiogram import Router, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext

from database import SessionLocal
from bot.book_health_scoring import BookHealthScoring
from bot.book_health_onboarding import SUPPORTED_CASINOS
from sqlalchemy import text as sql_text

# Import ML tracker
try:
    from bot.ml_event_tracker import ml_tracker
    ML_TRACKING_ENABLED = True
except ImportError:
    ML_TRACKING_ENABLED = False
    logger = logging.getLogger(__name__)
    logger.warning("ML tracking not available")

router = Router()
if not ML_TRACKING_ENABLED:
    logger = logging.getLogger(__name__)


class BookHealthDashboard:
    """Dashboard for Book Health Monitor"""
    
    def __init__(self):
        self.scorer = BookHealthScoring()
    
    async def show_dashboard(self, callback: CallbackQuery):
        """Main dashboard view"""
        await callback.answer()
        user_id = str(callback.from_user.id)
        
        db = SessionLocal()
        try:
            # Get all user's casino profiles
            profiles = db.execute(sql_text("""
                SELECT casino, is_limited FROM user_casino_profiles
                WHERE user_id = :user_id
                ORDER BY casino
            """), {"user_id": user_id}).fetchall()
            
            if not profiles:
                # No profiles - show onboarding prompt
                await self.show_onboarding_prompt(callback)
                return
            
            # Get latest scores for each casino
            scores_data = []
            for profile in profiles:
                score_result = db.execute(sql_text("""
                    SELECT total_score, risk_level, estimated_months_until_limit,
                           score_change_7d, score_change_30d, total_bets
                    FROM book_health_scores
                    WHERE user_id = :user_id AND casino = :casino
                    ORDER BY calculation_date DESC
                    LIMIT 1
                """), {"user_id": user_id, "casino": profile.casino}).first()
                
                if score_result:
                    scores_data.append({
                        'casino': profile.casino,
                        'is_limited': profile.is_limited,
                        'total_score': score_result.total_score,
                        'risk_level': score_result.risk_level,
                        'estimated_months': score_result.estimated_months_until_limit,
                        'change_7d': score_result.score_change_7d,
                        'change_30d': score_result.score_change_30d,
                        'total_bets': score_result.total_bets
                    })
                else:
                    # Calculate score if not exists
                    score = self.scorer.calculate_health_score(user_id, profile.casino)
                    if score['risk_level'] != 'NO_PROFILE' and score['risk_level'] != 'INSUFFICIENT_DATA':
                        scores_data.append({
                            'casino': profile.casino,
                            'is_limited': profile.is_limited,
                            'total_score': score['score'],
                            'risk_level': score['risk_level'],
                            'estimated_months': score.get('estimated_months'),
                            'change_7d': score['trend'].get('change_7d'),
                            'change_30d': score['trend'].get('change_30d'),
                            'total_bets': score.get('total_bets', 0)
                        })
                    else:
                        scores_data.append({
                            'casino': profile.casino,
                            'is_limited': profile.is_limited,
                            'total_score': 0,
                            'risk_level': 'INSUFFICIENT_DATA',
                            'estimated_months': None,
                            'change_7d': None,
                            'change_30d': None,
                            'total_bets': score.get('total_bets', 0)
                        })
            
            # Format dashboard message
            text = self._format_dashboard(scores_data)
            
            # Create keyboard
            keyboard_rows = []
            
            # Sort by risk level (worst first)
            scores_data.sort(key=lambda s: s['total_score'], reverse=True)
            
            for score in scores_data:
                if score['is_limited']:
                    button_text = f"🚫 {SUPPORTED_CASINOS.get(score['casino'], {}).get('emoji', '🏢')} {score['casino']} - LIMITED"
                else:
                    emoji = self._get_risk_emoji(score['risk_level'])
                    button_text = f"{SUPPORTED_CASINOS.get(score['casino'], {}).get('emoji', '🏢')} {score['casino']} - {emoji} {score['total_score']:.0f}/100"
                
                keyboard_rows.append([InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"health_details_{score['casino']}"
                )])
            
            # Add action buttons
            keyboard_rows.extend([
                [
                    InlineKeyboardButton(text="➕ Ajouter Casino", callback_data="health_add_casino"),
                    InlineKeyboardButton(text="📊 Tendances", callback_data="health_trends")
                ],
                [
                    InlineKeyboardButton(text="🔄 Rafraîchir", callback_data="book_health_dashboard"),
                    InlineKeyboardButton(text="📈 Retour Stats", callback_data="my_stats")
                ]
            ])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
            
            await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
            
        finally:
            db.close()
    
    async def show_casino_details(self, callback: CallbackQuery, casino: str):
        """Show detailed view for specific casino"""
        await callback.answer()
        user_id = str(callback.from_user.id)
        
        # Calculate fresh score
        score_data = self.scorer.calculate_health_score(user_id, casino)
        
        if score_data['risk_level'] == 'NO_PROFILE':
            await callback.message.edit_text(
                "❌ Pas de profil pour ce casino. Configure-le d'abord.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⚙️ Configurer", callback_data="book_health_start")],
                    [InlineKeyboardButton(text="◀️ Retour", callback_data="book_health_dashboard")]
                ])
            )
            return
        
        if score_data['risk_level'] == 'INSUFFICIENT_DATA':
            text = f"""
{SUPPORTED_CASINOS.get(casino, {}).get('emoji', '🏢')} <b>{casino.upper()} - BOOK HEALTH</b>

⚠️ <b>Données insuffisantes</b>

J'ai besoin d'au moins 10 paris trackés pour calculer ton score.

<b>Actuellement:</b> {score_data.get('total_bets', 0)} paris trackés

Continue à utiliser RISK0 et clique "I BET" sur tes paris.
Le score sera disponible après 10 paris.
"""
            await callback.message.edit_text(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Retour", callback_data="book_health_dashboard")]
                ])
            )
            return
        
        # Format detailed view
        text = self._format_casino_details(casino, score_data)
        
        # Create keyboard
        keyboard_rows = [
            [
                InlineKeyboardButton(text="📊 Voir Graphique", callback_data=f"health_graph_{casino}"),
                InlineKeyboardButton(text="📋 Historique", callback_data=f"health_history_{casino}")
            ],
            [InlineKeyboardButton(text="⚠️ Marquer Limité", callback_data=f"health_limited_{casino}")],
            [InlineKeyboardButton(text="◀️ Retour", callback_data="book_health_dashboard")]
        ]
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
        
        await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    
    async def show_trend_graph(self, callback: CallbackQuery, casino: str):
        """Show trend graph for casino"""
        await callback.answer()
        user_id = str(callback.from_user.id)
        
        db = SessionLocal()
        try:
            # Get last 30 days of scores
            scores = db.execute(sql_text("""
                SELECT total_score, calculation_date
                FROM book_health_scores
                WHERE user_id = :user_id AND casino = :casino
                  AND calculation_date >= :start_date
                ORDER BY calculation_date ASC
            """), {
                "user_id": user_id,
                "casino": casino,
                "start_date": date.today() - timedelta(days=30)
            }).fetchall()
            
            if len(scores) < 2:
                await callback.message.edit_text(
                    "📊 Pas assez de données pour un graphique (besoin 2+ jours)",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="◀️ Retour", callback_data=f"health_details_{casino}")]
                    ])
                )
                return
            
            # Create ASCII graph
            graph = self._create_ascii_graph(scores)
            
            # Analyze trend
            trend_analysis = self._analyze_graph_trend(scores)
            
            text = f"""
📊 <b>TENDANCE - {casino.upper()}</b>

<pre>{graph}</pre>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{trend_analysis}
"""
            
            await callback.message.edit_text(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Retour", callback_data=f"health_details_{casino}")]
                ])
            )
            
        finally:
            db.close()
    
    async def report_limited(self, callback: CallbackQuery, casino: str):
        """Report being limited on a casino"""
        await callback.answer()
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💰 Stake réduit", callback_data=f"limit_type_stake_{casino}")],
            [InlineKeyboardButton(text="🚫 Compte banni", callback_data=f"limit_type_banned_{casino}")],
            [InlineKeyboardButton(text="📝 Vérification", callback_data=f"limit_type_verify_{casino}")],
            [InlineKeyboardButton(text="◀️ Annuler", callback_data=f"health_details_{casino}")]
        ])
        
        text = f"""
⚠️ <b>SIGNALER UNE LIMITE - {casino.upper()}</b>

Désolé d'apprendre ça! 😔

Ça va nous aider à améliorer les prédictions.

<b>Quel type de limite?</b>
"""
        
        await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    
    async def save_limit_event(self, callback: CallbackQuery, casino: str, limit_type: str):
        """Save limit event to database"""
        await callback.answer()
        user_id = str(callback.from_user.id)
        
        db = SessionLocal()
        try:
            # Get score at time of limit
            score_result = db.execute(sql_text("""
                SELECT total_score, win_rate, avg_clv, sports_count, avg_delay_seconds
                FROM book_health_scores
                WHERE user_id = :user_id AND casino = :casino
                ORDER BY calculation_date DESC
                LIMIT 1
            """), {"user_id": user_id, "casino": casino}).first()
            
            score_at_limit = score_result.total_score if score_result else None
            
            # Save event
            import uuid
            db.execute(sql_text("""
                INSERT INTO limit_events (
                    event_id, user_id, casino, limit_type, score_at_limit,
                    metrics_at_limit
                ) VALUES (
                    :id, :user_id, :casino, :limit_type, :score,
                    :metrics
                )
            """), {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "casino": casino,
                "limit_type": limit_type,
                "score": score_at_limit,
                "metrics": {
                    "win_rate": float(score_result.win_rate) if score_result and score_result.win_rate else None,
                    "avg_clv": float(score_result.avg_clv) if score_result and score_result.avg_clv else None,
                    "sports_count": score_result.sports_count if score_result else None,
                    "avg_delay": score_result.avg_delay_seconds if score_result else None
                } if score_result else {}
            })
            
            # Update profile
            db.execute(sql_text("""
                UPDATE user_casino_profiles
                SET is_limited = true, limited_at = :now
                WHERE user_id = :user_id AND casino = :casino
            """), {
                "user_id": user_id,
                "casino": casino,
                "now": datetime.utcnow()
            })
            
            db.commit()
            
            # Track for ML - CRITICAL EVENT
            if ML_TRACKING_ENABLED:
                try:
                    await ml_tracker.track_event(
                        'limit_reported',
                        {
                            'casino': casino,
                            'limit_type': limit_type,
                            'score_at_limit': score_at_limit,
                            'win_rate': float(score_result.win_rate) if score_result and score_result.win_rate else None,
                            'avg_clv': float(score_result.avg_clv) if score_result and score_result.avg_clv else None,
                            'sports_count': score_result.sports_count if score_result else None
                        },
                        user_id=user_id,
                        importance=10,  # CRITICAL for ML
                        tags=['critical', 'limit', casino, limit_type]
                    )
                except Exception as e:
                    logger.error(f"ML tracking failed: {e}")
            
            # Log for ML training
            logger.info(f"🚨 LIMIT EVENT: User {user_id} limited on {casino} "
                       f"(type: {limit_type}, score: {score_at_limit})")
            
            text = f"""
✅ <b>Limite enregistrée</b>

Merci pour le feedback! Ça va nous aider à améliorer le système.

<b>Casino:</b> {casino}
<b>Type:</b> {limit_type.replace('_', ' ').title()}
<b>Score au moment:</b> {score_at_limit:.0f}/100 si disponible

Cette info sera utilisée pour améliorer les prédictions futures.
"""
            
            await callback.message.edit_text(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Retour Dashboard", callback_data="book_health_dashboard")]
                ])
            )
            
        except Exception as e:
            logger.error(f"Error saving limit event: {e}")
            await callback.message.edit_text(
                "❌ Erreur lors de l'enregistrement. Réessaye plus tard.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Retour", callback_data="book_health_dashboard")]
                ])
            )
        finally:
            db.close()
    
    async def show_onboarding_prompt(self, callback: CallbackQuery):
        """Show prompt to start onboarding"""
        text = """
🏥 <b>BOOK HEALTH MONITOR</b>

Tu n'as pas encore configuré de casinos!

Le Book Health Monitor analyse ton comportement de paris pour prédire quand tu risques de te faire limiter.

<b>Fonctionnalités:</b>
• Score de risque 0-100
• Recommendations personnalisées
• Graphiques de tendance
• Alertes automatiques
• Tracking automatique des paris

⚠️ <b>BETA:</b> Système basé sur patterns observés, pas 100% précis.
"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚙️ Configurer", callback_data="book_health_start")],
            [InlineKeyboardButton(text="📈 Retour Stats", callback_data="my_stats")]
        ])
        
        await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    
    def _format_dashboard(self, scores_data: List[Dict]) -> str:
        """Format main dashboard message"""
        now = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        text = f"""
🏥 <b>BOOK HEALTH MONITOR</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📅 Mise à jour: {now}

⚠️ <b>DISCLAIMER:</b> Système en BETA
Pas 100% précis - Guide seulement

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>VOS CASINOS:</b>
"""
        
        for score in scores_data:
            if score['is_limited']:
                text += f"\n🚫 <b>{score['casino']}</b> - LIMITÉ\n\n"
                continue
            
            emoji = self._get_risk_emoji(score['risk_level'])
            trend = self._get_trend_arrow(score['change_7d'])
            
            if score['risk_level'] == 'INSUFFICIENT_DATA':
                text += f"""
{SUPPORTED_CASINOS.get(score['casino'], {}).get('emoji', '🏢')} <b>{score['casino']}</b>
├─ Score: ⏳ En attente ({score['total_bets']}/10 bets)
└─ Statut: Données insuffisantes

"""
            else:
                estimate = self._format_estimate(score['estimated_months'])
                
                text += f"""
{SUPPORTED_CASINOS.get(score['casino'], {}).get('emoji', '🏢')} <b>{score['casino']}</b>
├─ Score: {emoji} <b>{score['total_score']:.0f}/100</b> {trend}
├─ Statut: {score['risk_level']}
├─ Limite estimée: {estimate}
└─ Bets trackés: {score['total_bets']}

"""
        
        text += """━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Clique sur un casino pour détails</i>"""
        
        return text
    
    def _format_casino_details(self, casino: str, score_data: Dict) -> str:
        """Format casino details message"""
        emoji = self._get_risk_emoji(score_data['risk_level'])
        
        text = f"""
🏥 <b>BOOK HEALTH - {casino.upper()}</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>📊 SCORE GLOBAL</b>

{emoji} <b>{score_data['score']:.0f}/100</b> - {score_data['risk_level']}

Tendance 7j: {self._get_trend_arrow(score_data['trend'].get('change_7d'))} {self._format_change(score_data['trend'].get('change_7d'))}
Tendance 30j: {self._get_trend_arrow(score_data['trend'].get('change_30d'))} {self._format_change(score_data['trend'].get('change_30d'))}

⏳ Limite estimée: <b>{self._format_estimate(score_data.get('estimated_months'))}</b>
🎯 Probabilité: {score_data.get('limit_probability', 0)*100:.0f}%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>🔍 FACTEURS DE RISQUE</b>

"""
        
        # Add factor breakdown
        factors = score_data.get('factors', {})
        for name, factor in factors.items():
            if factor.get('score') is not None:
                percentage = (factor['score'] / factor['max']) * 100 if factor['max'] > 0 else 0
                bar = self._create_progress_bar(percentage)
                risk = '🔴' if percentage > 70 else '🟠' if percentage > 40 else '🟢'
                
                factor_name = {
                    'win_rate': 'Win Rate',
                    'clv': 'CLV',
                    'diversity': 'Diversité',
                    'timing': 'Timing',
                    'stake_pattern': 'Mises',
                    'bet_type': 'Type de bets',
                    'activity_change': 'Changement',
                    'withdrawal': 'Retraits'
                }.get(name, name)
                
                text += f"{risk} {factor_name}: {bar} {factor['score']:.0f}/{factor['max']}\n"
        
        text += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>💡 RECOMMENDATIONS</b>

"""
        
        recommendations = score_data.get('recommendations', [])
        if not recommendations:
            text += "✅ Aucune action requise - continue comme ça!\n"
        else:
            for i, rec in enumerate(recommendations[:5], 1):
                icon = self._get_priority_icon(rec['priority'])
                text += f"\n{icon} <b>{rec['priority']}</b>\n{rec['text']}\n"
            
            if len(recommendations) > 5:
                text += f"\n<i>... et {len(recommendations) - 5} autres recommendations</i>\n"
        
        text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        return text
    
    def _create_ascii_graph(self, scores) -> str:
        """Create ASCII graph for trend visualization"""
        if not scores:
            return "No data"
        
        # Convert to list of values
        values = [float(s.total_score) for s in scores]
        dates = [s.calculation_date for s in scores]
        
        # Calculate range
        max_val = max(values)
        min_val = min(values)
        range_val = max_val - min_val if max_val != min_val else 1
        
        # Graph dimensions
        height = 10
        width = min(len(values) * 2, 30)
        
        # Create graph
        graph = []
        
        # Y-axis labels
        for h in range(height, -1, -1):
            y_val = min_val + (range_val * h / height)
            line = f"{y_val:3.0f} ┤"
            
            # Plot points
            for i in range(len(values)):
                x_pos = int(i * width / len(values))
                val = values[i]
                
                # Check if this point should be plotted at this height
                val_height = int((val - min_val) / range_val * height)
                
                if val_height == h:
                    line += "█"
                elif val_height > h:
                    line += "│"
                else:
                    line += " "
            
            graph.append(line)
        
        # X-axis
        graph.append("    └" + "─" * width)
        
        # Date labels
        if dates:
            first_date = dates[0].strftime('%m/%d')
            last_date = dates[-1].strftime('%m/%d')
            date_line = "     " + first_date + " " * (width - len(first_date) - len(last_date)) + last_date
            graph.append(date_line)
        
        return "\n".join(graph)
    
    def _analyze_graph_trend(self, scores) -> str:
        """Analyze trend from scores"""
        if len(scores) < 2:
            return "Données insuffisantes pour analyser la tendance"
        
        first = float(scores[0].total_score)
        last = float(scores[-1].total_score)
        change = last - first
        
        if abs(change) < 5:
            return f"📊 Score stable autour de {last:.0f}/100"
        elif change > 0:
            return f"⚠️ Score en hausse de {change:.0f} points - risque augmente!"
        else:
            return f"✅ Score en baisse de {abs(change):.0f} points - bon signe!"
    
    def _create_progress_bar(self, percentage: float) -> str:
        """Create visual progress bar"""
        filled = int(percentage / 10)
        empty = 10 - filled
        return '█' * filled + '░' * empty
    
    def _get_risk_emoji(self, risk_level: str) -> str:
        """Get emoji for risk level"""
        return {
            'SAFE': '🟢',
            'MONITOR': '🟡',
            'WARNING': '🟠',
            'HIGH_RISK': '🔴',
            'CRITICAL': '⛔',
            'INSUFFICIENT_DATA': '⏳'
        }.get(risk_level, '❓')
    
    def _get_trend_arrow(self, change: Optional[float]) -> str:
        """Get trend arrow"""
        if change is None:
            return ''
        if abs(change) < 2:
            return '→'
        if change > 0:
            return '↗️'
        return '↘️'
    
    def _format_change(self, change: Optional[float]) -> str:
        """Format score change"""
        if change is None:
            return ''
        sign = '+' if change > 0 else ''
        return f"{sign}{change:.0f}"
    
    def _format_estimate(self, months: Optional[float]) -> str:
        """Format time estimate"""
        if months is None:
            return 'N/A'
        if months < 1:
            return 'Quelques semaines'
        if months < 2:
            return '1-2 mois'
        if months < 6:
            return f'{months:.0f} mois'
        if months < 12:
            return f'{months:.0f} mois'
        if months < 24:
            return '1-2 ans'
        return '2+ ans'
    
    def _get_priority_icon(self, priority: str) -> str:
        """Get icon for priority level"""
        return {
            'CRITICAL': '⛔',
            'HIGH': '🔴',
            'MEDIUM': '🟠',
            'LOW': '🟡'
        }.get(priority, '💡')


# Router handlers
dashboard = BookHealthDashboard()

@router.callback_query(F.data == "book_health_dashboard")
async def handle_dashboard(callback: CallbackQuery):
    """Show main dashboard - ALPHA only"""
    await callback.answer()
    
    from database import SessionLocal
    from models.user import User, TierLevel
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    from aiogram.enums import ParseMode
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = user.language if user else 'en'
        is_premium = user and user.tier != TierLevel.FREE
        
        if not is_premium:
            # FREE user → Show lock message
            if lang == 'fr':
                text = (
                    "🔒 <b>BOOK HEALTH MONITOR - ALPHA EXCLUSIF</b>\n\n"
                    "Le système Book Health Monitor est réservé aux membres ALPHA.\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "💎 <b>AVEC ALPHA, TU OBTIENS:</b>\n\n"
                    "✅ Book Health Monitor complet\n"
                    "✅ Prédiction des limites de casino\n"
                    "✅ Dashboard avec score de risque\n"
                    "✅ Alertes automatiques\n"
                    "✅ Recommendations personnalisées\n"
                    "✅ Tracking ML de ton comportement\n\n"
                    "Plus TOUS les autres avantages ALPHA:\n"
                    "• Good Odds (+EV bets)\n"
                    "• Middle Bets (lottery)\n"
                    "• Parlays optimisés\n"
                    "• Guides complets\n"
                    "• Support prioritaire\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "💰 <b>INVESTISSEMENT:</b>\n"
                    "$200 CAD/mois\n\n"
                    "🚀 <b>ROI:</b> 10-15x garanti!"
                )
            else:
                text = (
                    "🔒 <b>BOOK HEALTH MONITOR - ALPHA EXCLUSIVE</b>\n\n"
                    "The Book Health Monitor system is reserved for ALPHA members.\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "💎 <b>WITH ALPHA, YOU GET:</b>\n\n"
                    "✅ Complete Book Health Monitor\n"
                    "✅ Casino limit prediction\n"
                    "✅ Dashboard with risk score\n"
                    "✅ Automatic alerts\n"
                    "✅ Personalized recommendations\n"
                    "✅ ML tracking of your behavior\n\n"
                    "Plus ALL other ALPHA benefits:\n"
                    "• Good Odds (+EV bets)\n"
                    "• Middle Bets (lottery)\n"
                    "• Optimized Parlays\n"
                    "• Complete guides\n"
                    "• Priority support\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "💰 <b>INVESTMENT:</b>\n"
                    "$200 CAD/month\n\n"
                    "🚀 <b>ROI:</b> 10-15x guaranteed!"
                )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="💎 Devenir Membre ALPHA" if lang == 'fr' else "💎 Become ALPHA Member",
                    callback_data="show_tiers"
                )],
                [InlineKeyboardButton(
                    text="◀️ Retour" if lang == 'fr' else "◀️ Back",
                    callback_data="my_stats"
                )]
            ])
            
            await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        else:
            # ALPHA user → Show dashboard
            await dashboard.show_dashboard(callback)
    finally:
        db.close()

@router.callback_query(F.data.startswith("health_details_"))
async def handle_casino_details(callback: CallbackQuery):
    """Show casino details"""
    casino = callback.data.replace("health_details_", "")
    await dashboard.show_casino_details(callback, casino)

@router.callback_query(F.data.startswith("health_graph_"))
async def handle_trend_graph(callback: CallbackQuery):
    """Show trend graph"""
    casino = callback.data.replace("health_graph_", "")
    await dashboard.show_trend_graph(callback, casino)

@router.callback_query(F.data.startswith("health_limited_"))
async def handle_report_limited(callback: CallbackQuery):
    """Report being limited"""
    casino = callback.data.replace("health_limited_", "")
    await dashboard.report_limited(callback, casino)

@router.callback_query(F.data.startswith("limit_type_"))
async def handle_limit_type(callback: CallbackQuery):
    """Handle limit type selection"""
    parts = callback.data.split("_")
    limit_type = parts[2]  # stake, banned, or verify
    casino = "_".join(parts[3:])  # Handle casino names with underscores
    await dashboard.save_limit_event(callback, casino, limit_type)

@router.callback_query(F.data == "health_add_casino")
async def handle_add_casino(callback: CallbackQuery):
    """Add new casino"""
    # Redirect to onboarding
    from bot.book_health_onboarding import start_onboarding
    await start_onboarding(callback, FSMContext())

@router.callback_query(F.data == "health_trends")
async def handle_trends_overview(callback: CallbackQuery):
    """Show trends overview for all casinos"""
    await callback.answer()
    user_id = str(callback.from_user.id)
    
    db = SessionLocal()
    try:
        # Get all casinos with scores
        casinos = db.execute(sql_text("""
            SELECT DISTINCT casino FROM user_casino_profiles
            WHERE user_id = :user_id
            ORDER BY casino
        """), {"user_id": user_id}).fetchall()
        
        if not casinos:
            await callback.message.edit_text(
                "❌ Aucun casino configuré. Configure d'abord un casino!",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⚙️ Configurer", callback_data="book_health_start")],
                    [InlineKeyboardButton(text="◀️ Retour", callback_data="book_health_dashboard")]
                ])
            )
            return
        
        text = """
📊 <b>TENDANCES - VUE D'ENSEMBLE</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
        
        has_data = False
        
        for casino_row in casinos:
            casino = casino_row.casino
            
            # Get latest score and trend
            score_data = db.execute(sql_text("""
                SELECT total_score, risk_level, score_change_7d, score_change_30d,
                       calculation_date
                FROM book_health_scores
                WHERE user_id = :user_id AND casino = :casino
                ORDER BY calculation_date DESC
                LIMIT 1
            """), {"user_id": user_id, "casino": casino}).first()
            
            if score_data:
                has_data = True
                emoji = dashboard._get_risk_emoji(score_data.risk_level)
                trend_7d = dashboard._get_trend_arrow(score_data.score_change_7d)
                trend_30d = dashboard._get_trend_arrow(score_data.score_change_30d)
                
                text += f"""
🏢 <b>{SUPPORTED_CASINOS.get(casino, {}).get('emoji', '🏢')} {casino.upper()}</b>

Score actuel: {emoji} <b>{score_data.total_score:.0f}/100</b>
Tendance 7j: {trend_7d} {dashboard._format_change(score_data.score_change_7d)}
Tendance 30j: {trend_30d} {dashboard._format_change(score_data.score_change_30d)}
Statut: {score_data.risk_level}

"""
        
        if not has_data:
            text += """
⏳ <b>Pas encore de données</b>

Continue à utiliser RISK0 et tes scores seront calculés automatiquement après 10 bets trackés par casino.

"""
        
        text += """━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Clique sur un casino dans le dashboard pour voir le graphique détaillé</i>"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Retour Dashboard", callback_data="book_health_dashboard")]
        ])
        
        await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        
    finally:
        db.close()
