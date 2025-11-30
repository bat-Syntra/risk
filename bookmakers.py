import os
import re
import json
import difflib

# Load casino data from JSON file
def _load_casino_logos():
    try:
        fname = "casino_logos.json"
        if not os.path.exists(fname) and os.path.exists("casinos.json"):
            fname = "casinos.json"
        with open(fname, "r", encoding="utf-8") as f:
            data = json.load(f)
            casinos = {}
            aliases = {}
            for c in data.get("casinos", []):
                name = c.get("name")
                if not name:
                    continue
                casinos[name.lower()] = {
                    "name": name,
                    "emoji": c.get("emoji", "🎰"),
                    "url": c.get("url") or f"https://www.{name.lower().replace(' ', '').replace('-', '')}.com",
                    "logo_file": c.get("logo_file"),
                    "aliases": list(c.get("aliases", [])),
                    "ocr_patterns": list(c.get("ocr_patterns", [])),
                }
                for alias in c.get("aliases", []):
                    aliases[alias.lower()] = name.lower()
                for pattern in c.get("ocr_patterns", []):
                    aliases[pattern.lower()] = name.lower()
            return casinos, aliases
    except Exception:
        pass
    # Fallback if JSON doesn't exist
    return {}, {}

_CASINO_DATA, _CASINO_ALIASES = _load_casino_logos()

# Keep original BOOKMAKERS for compatibility but merge with JSON data
BOOKMAKERS = {
    "888sport": {"name": "888sport", "emoji": "🏛️", "url": "https://www.888sport.com"},
    "bet365": {"name": "bet365", "emoji": "📗", "url": "https://www.bet365.com"},
    "bet99": {"name": "BET99", "emoji": "💯", "url": "https://www.bet99.com"},
    "betvictor": {"name": "BetVictor", "emoji": "🎯", "url": "https://www.betvictor.com"},
    "bwin": {"name": "bwin", "emoji": "⚫", "url": "https://www.bwin.com"},
    "coolbet": {"name": "Coolbet", "emoji": "❄️", "url": "https://www.coolbet.com"},
    "jackpotbet": {"name": "Jackpot.bet", "emoji": "💎", "url": "https://jackpot.bet"},
    "miseojeu": {"name": "Mise-o-jeu", "emoji": "🎟️", "url": "https://miseojeu.lotoquebec.com"},
    "proline": {"name": "Proline", "emoji": "✨", "url": "https://www.proline.ca"},
    "sportsinteraction": {"name": "Sports Interaction", "emoji": "🏒", "url": "https://www.sportsinteraction.com"},
    "stake": {"name": "Stake", "emoji": "🟣", "url": "https://stake.com"},
    "tonybet": {"name": "TonyBet", "emoji": "🏦", "url": "https://www.tonybet.com"},
    "betsson": {"name": "Betsson", "emoji": "🔶", "url": "https://www.betsson.com"},
    "betway": {"name": "Betway", "emoji": "⚡", "url": "https://www.betway.com"},
    "casumo": {"name": "Casumo", "emoji": "💜", "url": "https://www.casumo.com"},
    "ibet": {"name": "iBet", "emoji": "🧱", "url": "https://www.ibet.com"},
    "leovegas": {"name": "LeoVegas", "emoji": "🦁", "url": "https://www.leovegas.com"},
    "pinnacle": {"name": "Pinnacle", "emoji": "📈", "url": "https://www.pinnacle.com"},
}

ALIASES = {
    "888": "888sport",
    "888 sport": "888sport",
    "365": "bet365",
    "bet 365": "bet365",
    "bet105": "bet365",
    "b365": "bet365",
    "bet99": "bet99",
    "bet 99": "bet99",
    "b99": "bet99",
    "bet victor": "betvictor",
    "b win": "bwin",
    "cool bet": "coolbet",
    "coobet": "coolbet",
    "coolser": "coolbet",
    "coouser": "coolbet",
    "cootsecr": "coolbet",
    "coolsecr": "coolbet",
    "cootsec": "coolbet",
    "coosecr": "coolbet",
    "cooser": "coolbet",
    "cooser|": "coolbet",
    "coolber": "coolbet",
    "coolbet": "coolbet",
    "coolbet": "coolbet",
    "ibet": "ibet",
    "i bet": "ibet",
    "lbet": "ibet",
    "1bet": "ibet",
    "jackpot bet": "jackpotbet",
    "jackpotbet": "jackpotbet",
    "mise o jeu": "miseojeu",
    "miseojeu": "miseojeu",
    "mise-o-jeu": "miseojeu",
    "pro line": "proline",
    "sports interaction": "sportsinteraction",
    "sports inter": "sportsinteraction",
    "sia": "sportsinteraction",
    "tony bet": "tonybet",
    "leo vegas": "leovegas",
    "leovegas": "leovegas",
    "tony bet": "tonybet",
    "jackpot.bet": "jackpotbet",
    "bets9": "bet99",
    "betsg": "bet99",
    "betss0": "betsson",
    "betsso": "betsson",
}


def _norm(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s


def _apply_env_overrides():
    # Env var pattern: BOOKMAKER_<CANONICAL>_URL and BOOKMAKER_<CANONICAL>_EMOJI
    for canon in list(BOOKMAKERS.keys()):
        key_base = re.sub(r"[^A-Z0-9]+", "_", canon.upper())
        url_key = f"BOOKMAKER_{key_base}_URL"
        emoji_key = f"BOOKMAKER_{key_base}_EMOJI"
        url_val = os.getenv(url_key)
        if url_val:
            BOOKMAKERS[canon]["url"] = url_val.strip()
        emoji_val = os.getenv(emoji_key)
        if emoji_val:
            BOOKMAKERS[canon]["emoji"] = emoji_val.strip()


def _apply_json_overrides():
    path = os.getenv("BOOKMAKERS_JSON_PATH", "").strip()
    if not path:
        return
    try:
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return
        for canon, override in data.items():
            key = _norm(canon)
            # find matching canonical in catalog
            target = None
            for k in BOOKMAKERS.keys():
                if _norm(k) == key:
                    target = k
                    break
            if not target:
                continue
            if isinstance(override, str):
                BOOKMAKERS[target]["url"] = override
            elif isinstance(override, dict):
                if "url" in override and isinstance(override["url"], str):
                    BOOKMAKERS[target]["url"] = override["url"]
                if "emoji" in override and isinstance(override["emoji"], str):
                    BOOKMAKERS[target]["emoji"] = override["emoji"]
    except Exception:
        # Fail silent; keep defaults
        pass


_apply_env_overrides()
_apply_json_overrides()


def identify_bookmaker(text: str) -> dict:
    raw = text or ""
    lowered = raw.lower().strip()
    if not lowered:
        return {"found": False, "canonical": "", "name": raw.strip() or "Unknown", "emoji": "🎰", "url": None}
    # Alias/direct contains
    if lowered in _CASINO_ALIASES:
        canon = _CASINO_ALIASES[lowered]
        d = _CASINO_DATA.get(canon)
        if d:
            return {"found": True, "canonical": canon, "name": d.get("name"), "emoji": d.get("emoji"), "url": d.get("url"), "logo_file": d.get("logo_file")}
    for canon, d in _CASINO_DATA.items():
        pats = (d.get("ocr_patterns") or []) + (d.get("aliases") or []) + [d.get("name", "")]
        for p in pats:
            if p and p.lower() in lowered:
                return {"found": True, "canonical": canon, "name": d.get("name"), "emoji": d.get("emoji"), "url": d.get("url"), "logo_file": d.get("logo_file")}
    # Fuzzy across all patterns/aliases
    all_names = []
    idx = {}
    for canon, d in _CASINO_DATA.items():
        pats = (d.get("ocr_patterns") or []) + (d.get("aliases") or []) + [d.get("name", "")]
        for p in pats:
            if p:
                k = p.lower()
                all_names.append(k)
                idx[k] = canon
    if all_names:
        match = difflib.get_close_matches(lowered, all_names, n=1, cutoff=0.72)
        if match:
            canon = idx[match[0]]
            d = _CASINO_DATA.get(canon)
            return {"found": True, "canonical": canon, "name": d.get("name"), "emoji": d.get("emoji"), "url": d.get("url"), "logo_file": d.get("logo_file")}
    return {"found": False, "canonical": _norm(lowered), "name": raw.strip() or "Unknown", "emoji": "🎰", "url": None}


def resolve_bookmaker(name: str) -> dict:
    raw = name or ""
    key = _norm(raw)
    
    # Check JSON aliases first
    if key in _CASINO_ALIASES:
        canon_key = _CASINO_ALIASES[key]
        if canon_key in _CASINO_DATA:
            data = _CASINO_DATA[canon_key]
            return {"found": True, "canonical": canon_key, "name": data["name"], "emoji": data["emoji"], "url": data["url"], "logo_file": data.get("logo_file")}
    
    # Check JSON direct match
    if key in _CASINO_DATA:
        data = _CASINO_DATA[key]
        return {"found": True, "canonical": key, "name": data["name"], "emoji": data["emoji"], "url": data["url"], "logo_file": data.get("logo_file")}
    
    # Fallback to original BOOKMAKERS
    for k, v in ALIASES.items():
        if _norm(k) == key:
            key = v
            break
    for canon, data in BOOKMAKERS.items():
        if key == _norm(canon):
            return {"found": True, "canonical": canon, "name": data["name"], "emoji": data["emoji"], "url": data["url"]}
    for canon, data in BOOKMAKERS.items():
        if _norm(data["name"]) == key:
            return {"found": True, "canonical": canon, "name": data["name"], "emoji": data["emoji"], "url": data["url"]}
    fuzzy = identify_bookmaker(raw)
    if fuzzy.get("found"):
        return fuzzy
    return {"found": False, "canonical": key, "name": raw.strip() or "Unknown", "emoji": "🎰", "url": None}
