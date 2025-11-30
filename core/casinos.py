"""
Casino configuration and referral links
Canadian/Quebec market casinos
"""
import os

# Casino configuration with referral links
# TODO: Replace placeholder links with your actual referral links from affiliate programs
CASINOS = {
    "888sport": {
        "name": "888sport",
        "logo": "🎰",
        "referral_link": os.getenv("REFERRAL_888SPORT", "https://888sport.com"),  # TODO: Add your ref link
        "signup_bonus": "100$ bonus",
        "aliases": ["888", "888 sport"],
    },
    "bet105": {
        "name": "bet105",
        "logo": "🎲",
        "referral_link": os.getenv("REFERRAL_BET105", "https://bet105.com"),  # TODO: Add your ref link
        "signup_bonus": "Free bet",
        "aliases": ["105"],
    },
    "BET99": {
        "name": "BET99",
        "logo": "💯",
        "referral_link": os.getenv("REFERRAL_BET99", "https://bet99.com"),  # TODO: Add your ref link
        "signup_bonus": "200$ bonus",
        "aliases": ["bet 99", "99"],
    },
    "Betsson": {
        "name": "Betsson",
        "logo": "🔶",
        "referral_link": os.getenv("REFERRAL_BETSSON", "https://betsson.com"),  # TODO: Add your ref link
        "signup_bonus": "100$ bonus",
        "aliases": [],
    },
    "BetVictor": {
        "name": "BetVictor",
        "logo": "👑",
        "referral_link": os.getenv("REFERRAL_BETVICTOR", "https://betvictor.com"),  # TODO: Add your ref link
        "signup_bonus": "Free bet 50$",
        "aliases": ["bet victor"],
    },
    "Betway": {
        "name": "Betway",
        "logo": "⚡",
        "referral_link": os.getenv("REFERRAL_BETWAY", "https://betway.com"),  # TODO: Add your ref link
        "signup_bonus": "150$ bonus",
        "aliases": ["bet way"],
    },
    "bwin": {
        "name": "bwin",
        "logo": "🎯",
        "referral_link": os.getenv("REFERRAL_BWIN", "https://bwin.com"),  # TODO: Add your ref link
        "signup_bonus": "100$ bonus",
        "aliases": ["b win"],
    },
    "Casumo": {
        "name": "Casumo",
        "logo": "💜",
        "referral_link": os.getenv("REFERRAL_CASUMO", "https://casumo.com"),  # TODO: Add your ref link
        "signup_bonus": "200$ bonus",
        "aliases": [],
    },
    "Coolbet": {
        "name": "Coolbet",
        "logo": "❄️",
        "referral_link": os.getenv("REFERRAL_COOLBET", "https://coolbet.com"),  # TODO: Add your ref link
        "signup_bonus": "100$ bonus",
        "aliases": ["cool bet"],
    },
    "iBet": {
        "name": "iBet",
        "logo": "📱",
        "referral_link": os.getenv("REFERRAL_IBET", "https://ibet.com"),  # TODO: Add your ref link
        "signup_bonus": "50$ free bet",
        "aliases": ["i bet"],
    },
    "Jackpot.bet": {
        "name": "Jackpot.bet",
        "logo": "💎",
        "referral_link": os.getenv("REFERRAL_JACKPOT", "https://jackpot.bet"),  # TODO: Add your ref link
        "signup_bonus": "100$ bonus",
        "aliases": ["jackpot", "jackpotbet"],
    },
    "LeoVegas": {
        "name": "LeoVegas",
        "logo": "🦁",
        "referral_link": os.getenv("REFERRAL_LEOVEGAS", "https://leovegas.com"),  # TODO: Add your ref link
        "signup_bonus": "250$ bonus",
        "aliases": ["leo vegas", "leo"],
    },
    "Mise-o-jeu": {
        "name": "Mise-o-jeu",
        "logo": "🎪",
        "referral_link": os.getenv("REFERRAL_MISEOJEU", "https://lotoquebec.com/mise-o-jeu"),  # TODO: Add your ref link
        "signup_bonus": "N/A",
        "aliases": ["mise o jeu", "miseojeu", "lotoquebec"],
    },
    "Pinnacle": {
        "name": "Pinnacle",
        "logo": "⛰️",
        "referral_link": os.getenv("REFERRAL_PINNACLE", "https://pinnacle.com"),  # TODO: Add your ref link
        "signup_bonus": "Best odds",
        "aliases": ["Pinny", "pinny"],  # Important: source bot uses "Pinny"
    },
    "Proline": {
        "name": "Proline",
        "logo": "📊",
        "referral_link": os.getenv("REFERRAL_PROLINE", "https://proline.ca"),  # TODO: Add your ref link
        "signup_bonus": "N/A",
        "aliases": ["pro line"],
    },
    "Sports Interaction": {
        "name": "Sports Interaction",
        "logo": "🏟️",
        "referral_link": os.getenv("REFERRAL_SPORTS_INTERACTION", "https://sportsinteraction.com"),  # TODO: Add your ref link
        "signup_bonus": "100$ bonus",
        "aliases": ["sportsinteraction", "SI"],
    },
    "Stake": {
        "name": "Stake",
        "logo": "✨",
        "referral_link": os.getenv("REFERRAL_STAKE", "https://stake.com"),  # TODO: Add your ref link
        "signup_bonus": "Crypto bonus",
        "aliases": [],
    },
    "TonyBet": {
        "name": "TonyBet",
        "logo": "🎰",
        "referral_link": os.getenv("REFERRAL_TONYBET", "https://tonybet.com"),  # TODO: Add your ref link
        "signup_bonus": "150$ bonus",
        "aliases": ["tony bet", "tony"],
    },
}


def normalize_casino_name(name: str) -> str:
    """
    Normalize casino name for matching
    Handles variations like:
    - "@ Betsson" -> "betsson"
    - "PINNACLE" -> "pinnacle"
    - "Pinny" -> "pinnacle"
    
    Args:
        name: Raw casino name from source
        
    Returns:
        Normalized casino name or original if not found
    """
    if not name:
        return ""
    
    # Remove @ symbol and extra spaces
    cleaned = name.strip().replace("@", "").strip().lower()
    
    # Direct match
    for casino_key, casino_data in CASINOS.items():
        if cleaned == casino_key.lower():
            return casino_key
        
        # Check main name
        if cleaned == casino_data["name"].lower():
            return casino_key
        
        # Check aliases
        for alias in casino_data.get("aliases", []):
            if cleaned == alias.lower():
                return casino_key
    
    # Return original if no match
    return name


def get_casino(name: str) -> dict:
    """
    Get casino configuration by name
    
    Args:
        name: Casino name (will be normalized)
        
    Returns:
        Casino configuration dict or None if not found
    """
    normalized = normalize_casino_name(name)
    
    # Try direct lookup
    if normalized in CASINOS:
        return CASINOS[normalized]
    
    # Try case-insensitive search
    for key, value in CASINOS.items():
        if key.lower() == normalized.lower():
            return value
    
    return None


def get_casino_referral_link(name: str) -> str:
    """
    Get referral link for a casino
    
    Args:
        name: Casino name
        
    Returns:
        Referral link or empty string if not found
    """
    casino = get_casino(name)
    if casino:
        return casino.get("referral_link", "")
    return ""


def get_casino_logo(name: str) -> str:
    """
    Get logo emoji for a casino
    
    Args:
        name: Casino name
        
    Returns:
        Logo emoji or 🎰 as default
    """
    casino = get_casino(name)
    if casino:
        return casino.get("logo", "🎰")
    return "🎰"


def list_all_casinos() -> list:
    """
    Get list of all casino names
    
    Returns:
        List of casino names
    """
    return list(CASINOS.keys())


def get_casinos_by_market(market: str = "canada") -> dict:
    """
    Filter casinos by market (future extension)
    
    Args:
        market: Market identifier
        
    Returns:
        Filtered casino dictionary
    """
    # For now, all casinos are Canadian market
    # This can be extended with market filtering
    return CASINOS
