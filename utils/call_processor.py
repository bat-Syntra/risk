"""
Call Processor - Enrichissement et vérification des calls d'arbitrage
Récupère dates, cotes actuelles, recalcule profits et génère liens directs
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Tuple
from zoneinfo import ZoneInfo
import logging
import requests
import re
import hashlib

from utils.odds_api_links import (
    fetch_event_links, 
    find_outcome_link,
    determine_market_type,
    get_fallback_url,
    BOOKMAKER_API_KEYS,
    ODDS_API_KEY,
    ODDS_API_BASE
)
from core.casinos import get_casino_referral_link, get_casino_logo
from core.calculator import ArbitrageCalculator

logger = logging.getLogger(__name__)

# ============== Data Structures ==============

@dataclass
class Side:
    """Représente un côté d'un arbitrage/middle"""
    book_key: str            # "betway" (API key)
    book_name: str           # "Betway" (display name)
    market_key: str          # "h2h", "spreads", "totals", "team_totals"
    outcome_name: str        # "Massachusetts +15.5", "Over 220.5"
    odds_initial: float      # Cote initiale en décimal (1.90)
    odds_american: int       # Cote américaine (-110, +150)
    stake: float = 0.0       # Mise
    deep_link: Optional[str] = None       # Lien exact si dispo
    fallback_link: Optional[str] = None   # Lien générique
    odds_current: Optional[float] = None  # Cote actuelle via API
    odds_current_american: Optional[int] = None

@dataclass
class EventDatetime:
    """Info date/heure du match"""
    utc: Optional[datetime] = None
    local: Optional[datetime] = None
    display: str = ""
    iso: str = ""

@dataclass
class ArbAnalysis:
    """Analyse de l'arbitrage"""
    profit_if_side0_wins: float = 0.0
    profit_if_side1_wins: float = 0.0
    min_profit: float = 0.0
    max_profit: float = 0.0
    roi_min_pct: float = 0.0
    roi_max_pct: float = 0.0
    status: str = "UNKNOWN"  # "ARB", "NO_ARB", "MIDDLE", "BREAKEVEN"
    has_changed: bool = False  # True si les cotes ont changé
    
@dataclass
class MiddleAnalysis:
    """Analyse spécifique middle (optionnel)"""
    middle_zone_start: float = 0.0
    middle_zone_end: float = 0.0
    middle_description: str = ""
    double_win_profit: float = 0.0
    
@dataclass
class BettingCall:
    """Structure complète d'un call"""
    call_id: str             # ID unique
    sport: str               # "basketball"
    league: str              # "NBA"
    team1: str
    team2: str
    match: str               # "Team1 vs Team2"
    market: str              # "Point Spread", "Total Points"
    call_type: str           # "arbitrage", "middle", "positive_ev"
    expected_edge_pct: float # Edge annoncé (2.14, 5.6, etc.)
    
    sides: List[Side] = field(default_factory=list)
    event_datetime: Optional[EventDatetime] = None
    arb_analysis: Optional[ArbAnalysis] = None
    middle_analysis: Optional[MiddleAnalysis] = None
    
    # Tracking
    last_checked_at: Optional[datetime] = None
    last_checked_source: str = ""  # "auto", "user", "webhook"
    sport_key: Optional[str] = None  # API sport key
    event_id_api: Optional[str] = None  # API event ID
    odds_fetched: bool = False  # True si on a tenté/réussi à récupérer des cotes via l'API
    api_supported_books: List[str] = field(default_factory=list)  # Bookmakers supportés par l'API

# ============== API Helpers ==============

def _american_to_decimal(odds: int) -> float:
    """Convertit cote américaine en décimale"""
    if odds > 0:
        return 1 + (odds / 100.0)
    else:
        return 1 + (100.0 / abs(odds))

def _decimal_to_american(decimal: float) -> int:
    """Convertit cote décimale en américaine"""
    if decimal >= 2.0:
        return int((decimal - 1) * 100)
    else:
        return int(-100 / (decimal - 1))

def _guess_sport_key(sport: str, league: str) -> Optional[str]:
    """Devine la clé sport API depuis sport/league"""
    ls = (league or "").lower()
    ss = (sport or "").lower()
    
    if 'nfl' in ls or 'nfl' in ss:
        return 'americanfootball_nfl'
    if 'nba' in ls or 'nba' in ss:
        return 'basketball_nba'
    if 'nhl' in ls or 'nhl' in ss:
        return 'icehockey_nhl'
    if 'ncaab' in ls:
        return 'basketball_ncaab'
    if 'ncaaf' in ls:
        return 'americanfootball_ncaaf'
    if 'premier league' in ls:
        return 'soccer_epl'
    if 'serie a' in ls and 'italy' in ls:
        return 'soccer_italy_serie_a'
    if 'champions league' in ls or 'uefa' in ls:
        return 'soccer_uefa_champs_league'
    if 'mls' in ls:
        return 'soccer_usa_mls'
    
    # Tennis leagues
    if any(x in ls for x in ['atp', 'wta', 'challenger', 'itf']) or 'tennis' in ss:
        return 'tennis_atp'  # The Odds API tennis key
    
    # Fallback basé sur sport
    if 'basketball' in ss:
        return 'basketball_nba'
    if 'football' in ss and 'american' not in ss:
        return 'soccer_epl'  # European football
    if 'soccer' in ss:
        return 'soccer_epl'
    if 'hockey' in ss:
        return 'icehockey_nhl'
    if 'tennis' in ss:
        return 'tennis_atp'
        
    return None

def find_event_by_teams(sport_key: str, team1: str, team2: str) -> Optional[Dict]:
    """Trouve un événement via The Odds API par noms d'équipes"""
    if not sport_key:
        return None
        
    try:
        url = f"{ODDS_API_BASE}/sports/{sport_key}/events"
        params = {
            "apiKey": ODDS_API_KEY,
            "dateFormat": "iso"
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        events = response.json() or []
        
        # Normaliser pour comparaison
        t1_norm = team1.lower().strip()
        t2_norm = team2.lower().strip()
        
        for event in events:
            home = (event.get('home_team') or '').lower().strip()
            away = (event.get('away_team') or '').lower().strip()
            
            # Match flexible
            if ((t1_norm in home or home in t1_norm) and (t2_norm in away or away in t2_norm)) or \
               ((t2_norm in home or home in t2_norm) and (t1_norm in away or away in t1_norm)):
                return event
                
    except Exception as e:
        logger.error(f"Failed to find event: {e}")
    
    return None

# ============== Enrichissement ==============

def enrich_call_with_odds_api(call: BettingCall) -> BettingCall:
    """
    Enrichit le call avec:
    - Date/heure du match
    - Cotes actuelles
    - Liens directs
    """
    # 1. Trouver le sport key si pas déjà set
    if not call.sport_key:
        call.sport_key = _guess_sport_key(call.sport, call.league)
    
    if not call.sport_key:
        logger.warning(f"Could not determine sport key for {call.sport}/{call.league}")
        return call
    
    # 2. Trouver l'event si pas déjà set
    event = None
    if call.event_id_api:
        # On a déjà l'ID, fetch directement
        event_data = fetch_event_links(
            sport_key=call.sport_key,
            event_id=call.event_id_api,
            markets=None  # Fetch all markets
        )
        if event_data:
            event = event_data
    else:
        # Chercher par noms d'équipes
        event_basic = find_event_by_teams(call.sport_key, call.team1, call.team2)
        if event_basic:
            call.event_id_api = event_basic.get('id')
            # Fetch avec odds
            event_data = fetch_event_links(
                sport_key=call.sport_key,
                event_id=call.event_id_api,
                markets=None
            )
            if event_data:
                event = event_data
    
    if not event:
        logger.warning(f"Could not find event for {call.match}")
        call.odds_fetched = False
        return call
    
    # 3. Extraire date/heure
    commence_iso = event.get("commence_time")
    if commence_iso:
        try:
            dt_utc = datetime.fromisoformat(commence_iso.replace("Z", "+00:00"))
            tz_et = ZoneInfo("America/New_York")  # Eastern Time (ET) correct
            dt_et = dt_utc.astimezone(tz_et)
            
            # Format base: "Monday, Nov 24 - 7:30 PM ET"
            base_format = dt_et.strftime("%A, %b %d - %I:%M %p ET")
            
            # Calculate time until match starts
            now_utc = datetime.now(ZoneInfo("UTC"))
            time_delta = dt_utc - now_utc
            
            if time_delta.total_seconds() > 0:
                hours = int(time_delta.total_seconds() // 3600)
                minutes = int((time_delta.total_seconds() % 3600) // 60)
                
                if hours > 0:
                    time_until = f"débute dans {hours}h {minutes}min"
                    time_until_en = f"starts in {hours}h {minutes}min"
                else:
                    time_until = f"débute dans {minutes}min"
                    time_until_en = f"starts in {minutes}min"
                
                display = f"{base_format} ({time_until})"
                display_en = f"{base_format} ({time_until_en})"
            else:
                display = f"{base_format} (en cours)"
                display_en = f"{base_format} (live)"
            
            call.event_datetime = EventDatetime(
                utc=dt_utc,
                local=dt_et,
                display=display,  # French by default
                iso=commence_iso
            )
        except Exception as e:
            logger.error(f"Failed to parse date: {e}")
    
    # 4. Mapper market type
    market_type = determine_market_type(call.market)
    
    # 5. Pour chaque side, récupérer cote actuelle et lien
    bookmakers = event.get("bookmakers", [])
    
    # Vérifier si au moins un bookmaker du call est dans l'API
    api_supported_bookmakers = []
    for side in call.sides:
        book_key = BOOKMAKER_API_KEYS.get(side.book_name)
        if book_key:
            api_supported_bookmakers.append(side.book_name)
    
    for side in call.sides:
        # Trouver le bookmaker
        book_key = BOOKMAKER_API_KEYS.get(side.book_name)
        if not book_key:
            # Bookmaker pas dans l'API
            side.fallback_link = get_fallback_url(side.book_name)
            continue
        
        book_data = next((b for b in bookmakers if b.get("key") == book_key), None)
        if not book_data:
            side.fallback_link = get_fallback_url(side.book_name)
            continue
        
        # Chercher le marché et outcome
        side.market_key = market_type
        
        # Utiliser find_outcome_link pour récupérer le meilleur lien
        best_link = find_outcome_link(
            event,
            side.book_name,
            market_type,
            side.outcome_name
        )
        
        if best_link:
            side.deep_link = best_link
        else:
            side.fallback_link = get_fallback_url(side.book_name)
        
        # Chercher la cote actuelle
        for market in book_data.get("markets", []):
            if market.get("key") != market_type:
                continue
            
            for outcome in market.get("outcomes", []):
                outcome_name = (outcome.get("name") or "").lower()
                side_outcome = side.outcome_name.lower()
                
                # Match flexible
                if side_outcome in outcome_name or outcome_name in side_outcome:
                    try:
                        # The Odds API retourne en américain
                        side.odds_current_american = int(outcome.get("price", 0))
                        side.odds_current = _american_to_decimal(side.odds_current_american)
                        break
                    except Exception:
                        pass
    
    call.last_checked_at = datetime.now()
    call.last_checked_source = "auto"
    
    # Marquer comme fetchées seulement si on a au moins un bookmaker supporté
    call.odds_fetched = len(api_supported_bookmakers) > 0
    
    # Stocker les bookmakers supportés pour le message
    call.api_supported_books = api_supported_bookmakers
    
    return call

# ============== Analyse Arbitrage ==============

def analyze_arbitrage_two_way(call: BettingCall) -> BettingCall:
    """Calcule/recalcule l'arbitrage avec les cotes actuelles"""
    
    if len(call.sides) != 2:
        return call
    
    s0, s1 = call.sides[0], call.sides[1]
    
    # Utiliser cotes actuelles si dispo, sinon initiales
    o0 = s0.odds_current or s0.odds_initial
    o1 = s1.odds_current or s1.odds_initial
    
    stake0 = s0.stake
    stake1 = s1.stake
    
    total_stake = stake0 + stake1
    if total_stake <= 0:
        return call
    
    # Calculer profits
    profit0 = stake0 * o0 - total_stake
    profit1 = stake1 * o1 - total_stake
    
    min_profit = min(profit0, profit1)
    max_profit = max(profit0, profit1)
    roi_min = (min_profit / total_stake) * 100.0
    roi_max = (max_profit / total_stake) * 100.0
    
    # Déterminer statut
    if min_profit > 0:
        status = "ARB"
    elif min_profit > -1:  # Quasi break-even
        status = "BREAKEVEN"
    elif max_profit > total_stake * 0.5:  # Middle potentiel
        status = "MIDDLE"
    else:
        status = "NO_ARB"
    
    # Détecter si les cotes ont changé (seulement si on a des cotes actuelles)
    has_changed = False
    if s0.odds_current is not None and s1.odds_current is not None:
        has_changed = (abs(s0.odds_current - s0.odds_initial) > 0.01) or \
                      (abs(s1.odds_current - s1.odds_initial) > 0.01)
    
    call.arb_analysis = ArbAnalysis(
        profit_if_side0_wins=profit0,
        profit_if_side1_wins=profit1,
        min_profit=min_profit,
        max_profit=max_profit,
        roi_min_pct=roi_min,
        roi_max_pct=roi_max,
        status=status,
        has_changed=has_changed
    )
    
    return call

# ============== Formatage Messages ==============

def format_odds_change(initial: float, current: Optional[float], american_format: bool = True) -> str:
    """Formate le changement de cote avec flèche"""
    if current is None:
        if american_format:
            am = _decimal_to_american(initial)
            return f"{'+' if am > 0 else ''}{am}"
        return f"{initial:.2f}"
    
    if american_format:
        am_init = _decimal_to_american(initial)
        am_curr = _decimal_to_american(current)
        init_str = f"{'+' if am_init > 0 else ''}{am_init}"
        curr_str = f"{'+' if am_curr > 0 else ''}{am_curr}"
        
        if abs(am_curr - am_init) < 5:
            return curr_str
        arrow = "↑" if am_curr > am_init else "↓"
        return f"{init_str} → {curr_str} {arrow}"
    else:
        if abs(current - initial) < 0.01:
            return f"{current:.2f}"
        arrow = "↑" if current > initial else "↓"
        return f"{initial:.2f} → {current:.2f} {arrow}"

def format_call_message(call: BettingCall, lang: str = "fr", verified: bool = False) -> str:
    """
    Génère le message formaté pour Telegram
    
    Args:
        call: BettingCall enrichi
        lang: Langue ("fr" ou "en")
        verified: True si on affiche les cotes vérifiées
    
    Returns:
        Message formaté
    """
    lines = []
    
    # === Header ===
    # Utiliser le pourcentage d'arbitrage recalculé si disponible et valide
    # Si les cotes actuelles ne sont pas disponibles, garder l'original
    if (call.arb_analysis and 
        call.sides[0].odds_current is not None and 
        call.sides[1].odds_current is not None and 
        call.arb_analysis.roi_min_pct > 0):
        edge_str = f"{call.arb_analysis.roi_min_pct:.2f}%"
    else:
        edge_str = f"{call.expected_edge_pct:.2f}%"
    
    if call.arb_analysis:
        status = call.arb_analysis.status
        # Si edge positif annoncé et pas encore expiré → toujours "ALERTE ARBITRAGE"
        if call.expected_edge_pct > 0 and status != "NO_ARB":
            emoji = "🚨"
            header = f"{emoji} ALERTE ARBITRAGE - {edge_str} {emoji}"
        elif status == "NO_ARB" and verified:
            emoji = "⚠️"
            header = f"{emoji} ARBITRAGE EXPIRÉ - {edge_str} {emoji}"
        elif status == "MIDDLE":
            emoji = "🎯"
            header = f"{emoji} MIDDLE OPPORTUNITY - {edge_str} {emoji}"
        else:
            emoji = "📊"
            header = f"{emoji} SIGNAL - {edge_str} {emoji}"
    else:
        # Si pas d'analyse mais call_type arbitrage → ALERTE
        if call.call_type == "arbitrage" and call.expected_edge_pct > 0:
            emoji = "🚨"
            header = f"{emoji} ALERTE ARBITRAGE - {edge_str} {emoji}"
        else:
            header = f"📊 {call.call_type.upper()} - {edge_str} 📊"
    
    lines.append(header)
    
    # Indicateur si vérifié
    if verified and call.last_checked_at:
        check_time = call.last_checked_at.strftime("%H:%M")
        lines.append(f"🔍 Vérifié à {check_time}")
    
    lines.append("")
    
    # === Match Info ===
    lines.append(f"🏟️ {call.match}")
    
    # Sport/League avec emoji
    sport_emoji = "🏈" if "football" in call.sport.lower() else \
                  "🏀" if "basketball" in call.sport.lower() else \
                  "⚽" if "soccer" in call.sport.lower() else \
                  "🏒" if "hockey" in call.sport.lower() else "🏅"
    
    lines.append(f"{sport_emoji} {call.league} - {call.market}")
    
    # Date/heure
    if call.event_datetime:
        lines.append(f"🕐 {call.event_datetime.display}")
    else:
        lines.append("🕐 Date à confirmer")
    
    lines.append("")
    
    # === Configuration ===
    total_stake = sum(s.stake for s in call.sides)
    lines.append(f"💰 CASHH: ${total_stake:.1f}")
    
    # === Analyse (toujours afficher profit si dispo) ===
    if call.arb_analysis:
        a = call.arb_analysis
        lines.append(f"✅ Profit Garanti: ${a.min_profit:.2f} (ROI: {a.roi_min_pct:.2f}%)")
        
        if call.call_type == "middle" and abs(a.max_profit - a.min_profit) > 10:
            lines.append(f"🎯 Profit Max (middle): ${a.max_profit:.2f}")
    
    lines.append("")
    
    # === Sides ===
    for i, side in enumerate(call.sides):
        # Emoji bookmaker
        logo = get_casino_logo(side.book_name)
        
        # Lien (priorité: deep link > referral > fallback)
        link = side.deep_link or None
        if not link:
            link = get_casino_referral_link(side.book_name)
        if not link:
            link = side.fallback_link
        
        lines.append(f"{logo} [{side.book_name}] {side.outcome_name}")
        
        # Cotes
        if verified and side.odds_current_american:
            odds_str = format_odds_change(
                side.odds_initial, 
                side.odds_current,
                american_format=True
            )
            ret = side.stake * (side.odds_current or side.odds_initial)
            lines.append(f"💵 Miser: ${side.stake:.2f} ({odds_str}) → Retour: ${ret:.2f}")
        else:
            am = side.odds_american
            odds_str = f"{'+' if am > 0 else ''}{am}"
            ret = side.stake * side.odds_initial
            lines.append(f"💵 Miser: ${side.stake:.2f} ({odds_str}) → Retour: ${ret:.2f}")
        
        lines.append("")

    # === Avertissement global sur les cotes ===
    if lang == "fr":
        lines.append("⚠️ Attention: les cotes peuvent changer - toujours vérifier avant de bet!")
    else:
        lines.append("⚠️ Odds can change - always verify before betting!")
    
    # === Section vérification des cotes (si vérifiées) ===
    if verified and call.last_checked_at:
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        if lang == "fr":
            lines.append("🔍 VÉRIFICATION DES COTES")
        else:
            lines.append("🔍 ODDS VERIFICATION")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("")
        
        # Statut
        if call.arb_analysis:
            if call.arb_analysis.status == "ARB":
                status_text = "✅ Arbitrage toujours valide" if lang == "fr" else "✅ Arbitrage still valid"
            elif call.arb_analysis.status == "NO_ARB":
                status_text = "❌ Arbitrage expiré" if lang == "fr" else "❌ Arbitrage expired"
            elif call.arb_analysis.status == "BREAKEVEN":
                status_text = "⚠️ Break-even (profit minimal)" if lang == "fr" else "⚠️ Break-even (minimal profit)"
            else:
                status_text = "📊 Vérification effectuée" if lang == "fr" else "📊 Verification completed"
        else:
            status_text = "📊 Vérification effectuée" if lang == "fr" else "📊 Verification completed"
        
        lines.append(f"• Statut: {status_text}")
        
        # Heure de vérification
        check_time = call.last_checked_at.strftime("%H:%M:%S")
        if lang == "fr":
            lines.append(f"• Dernière vérification: {check_time}")
        else:
            lines.append(f"• Last check: {check_time}")
        
        # Changements de cotes
        if call.odds_fetched:
            # Si on n'a pas pu récupérer les cotes actuelles (ex: Player Props)
            if call.sides[0].odds_current is None or call.sides[1].odds_current is None:
                lines.append("")
                
                # Logique plus fine selon le marché et les bookmakers
                market_type = determine_market_type(call.market)
                is_player_prop = market_type.startswith('player_')
                
                if not is_player_prop:
                    # Marché standard mais pas de cotes → problème technique
                    if lang == "fr":
                        lines.append("⚠️ Impossible de vérifier ces cotes (problème technique)")
                    else:
                        lines.append("⚠️ Cannot verify these odds (technical issue)")
                elif len(call.api_supported_books) == 0:
                    # Player prop mais aucun bookmaker dans l'API
                    if lang == "fr":
                        lines.append("⚠️ Vérification manuelle requise (bookmakers non couverts par l'API)")
                    else:
                        lines.append("⚠️ Manual verification required (bookmakers not covered by API)")
                else:
                    # Player prop supporté mais pas de match trouvé
                    if lang == "fr":
                        lines.append("⚠️ Impossible de vérifier ces cotes (marché non supporté par l'API)")
                    else:
                        lines.append("⚠️ Cannot verify these odds (market not supported by API)")
            elif call.arb_analysis and call.arb_analysis.has_changed:
                lines.append("")
                if lang == "fr":
                    lines.append("📊 Changements de cotes:")
                else:
                    lines.append("📊 Odds changes:")
            else:
                lines.append("")
                if lang == "fr":
                    lines.append("✅ Aucun changement de cotes détecté")
                else:
                    lines.append("✅ No odds changes detected")
        else:
            # Aucune donnée API récupérée
            lines.append("")
            if lang == "fr":
                lines.append("⚠️ Vérification manuelle requise (sport/bookmakers non couverts)")
            else:
                lines.append("⚠️ Manual verification required (sport/bookmakers not covered)")
    
    return "\n".join(lines)

# ============== Processing Pipeline ==============

def process_call_from_drop(drop_data: Dict, bankroll: float = 750.0) -> Optional[BettingCall]:
    """
    Crée un BettingCall depuis un drop d'arbitrage et l'enrichit
    
    Args:
        drop_data: Dict depuis /public/drop ou parser
        bankroll: Bankroll totale à répartir
    
    Returns:
        BettingCall enrichi ou None si échec
    """
    try:
        # Générer un call_id stable basé sur le contenu
        match_str = drop_data.get('match', '')
        market_str = drop_data.get('market', '')
        casinos = [o.get('casino', '') for o in drop_data.get('outcomes', [])[:2]]
        casino_str = '-'.join(sorted(casinos))
        id_base = f"{match_str}:{market_str}:{casino_str}"
        call_id = hashlib.md5(id_base.encode()).hexdigest()[:12]
        
        # Créer la structure de base
        call = BettingCall(
            call_id=call_id,
            sport=drop_data.get('sport', ''),
            league=drop_data.get('league', ''),
            team1='',
            team2='',
            match=drop_data.get('match', ''),
            market=drop_data.get('market', ''),
            call_type='arbitrage',
            expected_edge_pct=float(drop_data.get('arb_percentage', 0)),
            # Optionnel: identifiants Odds API fournis en amont
            sport_key=drop_data.get('sport_key'),
            event_id_api=drop_data.get('event_id_api'),
        )
        
        # Extraire équipes du match
        if ' vs ' in call.match:
            parts = call.match.split(' vs ', 1)
            call.team1 = parts[0].strip()
            call.team2 = parts[1].strip()
        
        # Créer les sides depuis outcomes
        outcomes = drop_data.get('outcomes', [])
        if len(outcomes) >= 2:
            # Calculer stakes optimales
            odds_list = []
            for o in outcomes[:2]:
                am_odds = int(o.get('odds', 0))
                dec_odds = _american_to_decimal(am_odds)
                odds_list.append(dec_odds)
            
            # Utiliser ArbitrageCalculator pour stakes optimales
            calc = ArbitrageCalculator()
            result = calc.calculate_safe_stakes(bankroll, [_decimal_to_american(o) for o in odds_list])
            
            stakes = result.get('stakes', [bankroll/2, bankroll/2])
            
            for i, outcome in enumerate(outcomes[:2]):
                casino = outcome.get('casino', '')
                am_odds = int(outcome.get('odds', 0))
                dec_odds = _american_to_decimal(am_odds)
                
                side = Side(
                    book_key=casino.lower(),
                    book_name=casino,
                    market_key='',  # Sera set par enrichissement
                    outcome_name=outcome.get('outcome', ''),
                    odds_initial=dec_odds,
                    odds_american=am_odds,
                    stake=stakes[i] if i < len(stakes) else bankroll/2
                )
                call.sides.append(side)
        
        # Enrichir avec The Odds API
        call = enrich_call_with_odds_api(call)
        
        # Analyser arbitrage
        call = analyze_arbitrage_two_way(call)
        
        return call
        
    except Exception as e:
        logger.error(f"Failed to process call: {e}")
        return None

def should_send_call(call: BettingCall, min_profit: float = 0) -> bool:
    """
    Décide si un call doit être envoyé
    
    Args:
        call: BettingCall analysé
        min_profit: Profit minimum requis
    
    Returns:
        True si le call doit être envoyé
    """
    if not call.arb_analysis:
        return False
    
    # Envoyer si arbitrage positif
    if call.arb_analysis.min_profit >= min_profit:
        return True
    
    # Envoyer si middle intéressant
    if call.arb_analysis.status == "MIDDLE" and call.arb_analysis.max_profit > 100:
        return True
    
    return False
