"""
Parser for arbitrage alert messages from source bot
Handles message format:
🚨 Arbitrage Alert 5.16% 🚨
Ceará SC vs SC Internacional [Market] Outcome1 odds @ Casino1, Outcome2 odds @ Casino2 (Sport, League)
"""
import re
from typing import Dict, List, Optional
import hashlib
from datetime import datetime


class ArbitrageParser:
    """
    Parses arbitrage alert messages from source bot
    """
    
    # Regex pattern for arbitrage alerts
    # Example: "🚨 Arbitrage Alert 5.16% 🚨"
    ALERT_PATTERN = r"🚨\s*Arbitrage Alert\s+([\d.]+)%\s*🚨"
    
    # Pattern for match and market info
    # Example: "Ceará SC vs SC Internacional [Team Total Corners : SC Internacional Over 3/SC Internacional Under 3]"
    MATCH_PATTERN = r"(.+?)\s+\[(.+?)\]"
    
    # Pattern for odds and casinos
    # Example: "SC Internacional Over 3 -200 @ Betsson"
    ODDS_PATTERN = r"([^@]+?)\s+([-+]?\d+)\s+@\s*(.+?)(?:,|$|\s*\()"
    
    # Pattern for sport and league
    # Example: "(Soccer, Brazil - Serie A)"
    SPORT_LEAGUE_PATTERN = r"\(([^,]+),\s*([^)]+)\)"
    
    @staticmethod
    def parse_message(message: str) -> Optional[Dict]:
        """
        Parse arbitrage alert message
        
        Args:
            message: Raw message text from source bot
            
        Returns:
            Parsed arbitrage data or None if parsing fails
        """
        try:
            # Normalize lines (drop empties)
            raw_lines = [ln.strip() for ln in message.splitlines() if ln.strip()]

            # 1) Find percentage anywhere in the message
            arb_match = re.search(ArbitrageParser.ALERT_PATTERN, message)
            if not arb_match:
                return None
            arb_percentage = float(arb_match.group(1))

            # 2) Find the first line containing match + market in brackets
            # Example: "Green Bay Packers vs Minnesota Vikings [Player Receptions : Aaron Jones Over 2.5/Aaron Jones Under 2.5] ..."
            main_line = None
            for ln in raw_lines:
                if '[' in ln and ' vs ' in ln:
                    main_line = ln
                    break
            # Fallback: search across the whole message if not found line-wise
            if not main_line:
                mm = re.search(r"([\w .\-’'&]+\s+vs\s+[\w .\-’'&]+)\s*\[(.+?)\]", message, re.S)
                if not mm:
                    return None
                match = mm.group(1).strip()
                market = mm.group(2).strip()
            else:
                match_info_match = re.search(ArbitrageParser.MATCH_PATTERN, main_line)
                if not match_info_match:
                    return None
                match = match_info_match.group(1).strip()
                market = match_info_match.group(2).strip()

            # 3) Extract odds/casinos from the part of the message AFTER the match/market bracket.
            # This avoids capturing headers like "🎰 Odds Alert" or the alert line itself
            # as part of the outcome text.
            search_text = message
            if ']' in message:
                # Take everything after the first closing bracket
                search_text = message.split(']', 1)[1]

            odds_matches = list(re.finditer(ArbitrageParser.ODDS_PATTERN, search_text))
            outcomes: List[Dict] = []
            for om in odds_matches:
                outcome_text = om.group(1).strip()
                odds = int(om.group(2))
                casino = om.group(3).replace('@', '').strip()
                outcomes.append({
                    "outcome": outcome_text,
                    "odds": odds,
                    "casino": casino
                })

            # 4) Extract sport/league anywhere (e.g. "(Football, NFL)")
            sport = "Unknown"
            league = "Unknown"
            sport_league_match = re.search(ArbitrageParser.SPORT_LEAGUE_PATTERN, message)
            if sport_league_match:
                sport = sport_league_match.group(1).strip()
                league = sport_league_match.group(2).strip()

            # 5) Generate event_id and finalize
            event_id = ArbitrageParser._generate_event_id(match, market)
            player = ArbitrageParser._extract_player(market)

            return {
                "event_id": event_id,
                "arb_percentage": arb_percentage,
                "match": match,
                "market": market,
                "player": player,
                "outcomes": outcomes,
                "sport": sport,
                "league": league,
                "raw_message": message,
                "parsed_at": datetime.now().isoformat(),
            }
        
        except Exception as e:
            print(f"Error parsing message: {e}")
            return None
    
    @staticmethod
    def _generate_event_id(match: str, market: str) -> str:
        """
        Generate unique event ID from match and market
        
        Args:
            match: Match description
            market: Market description
            
        Returns:
            Unique event ID
        """
        combined = f"{match}_{market}_{datetime.now().strftime('%Y%m%d')}"
        hash_obj = hashlib.md5(combined.encode())
        return hash_obj.hexdigest()[:12]
    
    @staticmethod
    def _extract_player(market: str) -> Optional[str]:
        """
        Try to extract player name from market description
        
        Args:
            market: Market description
            
        Returns:
            Player name or None
        """
        # Common patterns for player props
        # Example: "Team Total Corners : SC Internacional Over 3"
        # Example: "Player Points : LeBron James Over 25.5"
        
        player_keywords = [
            "Player Points",
            "Player Rebounds",
            "Player Assists",
            "Player Shots",
            "Player Hits",
            "Total Bases",
            "Strikeouts",
        ]
        
        for keyword in player_keywords:
            if keyword in market:
                # Try to extract player name (usually after ":")
                parts = market.split(":")
                if len(parts) > 1:
                    player_part = parts[1].strip()
                    # Remove "Over" and "Under" and numbers
                    player = re.sub(r'\s+(Over|Under)\s+[\d.]+', '', player_part).strip()
                    return player
        
        return None
    
    @staticmethod
    def validate_parsed_data(data: Dict) -> bool:
        """
        Validate that parsed data has all required fields
        
        Args:
            data: Parsed data dictionary
            
        Returns:
            True if valid
        """
        required_fields = [
            "event_id",
            "arb_percentage",
            "match",
            "market",
            "outcomes",
            "sport",
            "league",
        ]
        
        for field in required_fields:
            if field not in data:
                return False
        
        # Validate outcomes
        outcomes = data.get("outcomes", [])
        if len(outcomes) < 2:
            return False
        
        for outcome in outcomes:
            if "outcome" not in outcome or "odds" not in outcome or "casino" not in outcome:
                return False
        
        return True
    
    @staticmethod
    def parse_multiline_format(message: str) -> Optional[Dict]:
        """
        Alternative parser for different message formats
        Handles variations in formatting
        
        Args:
            message: Raw message text
            
        Returns:
            Parsed data or None
        """
        # This is a more flexible parser for edge cases
        # Can be extended based on actual message variations
        
        try:
            # Try standard parser first
            result = ArbitrageParser.parse_message(message)
            if result and ArbitrageParser.validate_parsed_data(result):
                return result
            
            # Add alternative parsing logic here if needed
            
            return None
        
        except Exception as e:
            print(f"Error in multiline parser: {e}")
            return None


def parse_arbitrage_alert(message: str) -> Optional[Dict]:
    """
    Convenience function to parse arbitrage alert
    
    Args:
        message: Raw message from source bot
        
    Returns:
        Parsed arbitrage data
    """
    return ArbitrageParser.parse_message(message)


# Example usage and testing
if __name__ == "__main__":
    # Test message
    test_message = """🚨 Arbitrage Alert 5.16% 🚨

Ceará SC vs SC Internacional [Team Total Corners : SC Internacional Over 3/SC Internacional Under 3] SC Internacional Over 3 -200 @ Betsson, SC Internacional Under 3 +255 @ Coolbet (Soccer, Brazil - Serie A)"""
    
    parsed = parse_arbitrage_alert(test_message)
    
    if parsed:
        print("✅ Successfully parsed:")
        print(f"Event ID: {parsed['event_id']}")
        print(f"Arbitrage: {parsed['arb_percentage']}%")
        print(f"Match: {parsed['match']}")
        print(f"Market: {parsed['market']}")
        print(f"Sport: {parsed['sport']}")
        print(f"League: {parsed['league']}")
        print(f"\nOutcomes:")
        for outcome in parsed['outcomes']:
            print(f"  - {outcome['outcome']} @ {outcome['odds']} ({outcome['casino']})")
    else:
        print("❌ Failed to parse message")
