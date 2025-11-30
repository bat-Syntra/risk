import os, json, re, hashlib, time
from typing import Dict, Any
from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL

# Initialize OpenAI client if key is properly set; else None
_key = (OPENAI_API_KEY or "").strip()
client = OpenAI(api_key=_key) if _key and _key.lower() not in {"set_me", "ton_token_ici"} else None

SCHEMA_HINT = {
    "type": "object",
    "properties": {
        "event_id": {"type": "string"},
        "league": {"type": "string"},
        "event": {"type": "string"},
        "kickoff_iso": {"type": "string"},
        "market": {"type": "string"},
        "player": {"type": "string"},
        "edge_percent": {"type": "number"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "selection_over": {
            "type": "object",
            "properties": {
                "label": {"type": "string"},
                "american": {"type": "integer"},
                "book": {"type": "string"},
                "url": {"type": "string"}
            },
            "required": ["label", "american", "book"]
        },
        "selection_under": {
            "type": "object",
            "properties": {
                "label": {"type": "string"},
                "american": {"type": "integer"},
                "book": {"type": "string"},
                "url": {"type": "string"}
            },
            "required": ["label", "american", "book"]
        }
    },
    "required": ["event_id", "event", "player", "selection_over", "selection_under"]
}

SYSTEM_MSG = (
    "Tu es un extracteur strict. Retourne UNIQUEMENT un JSON minifié valide selon le schéma fourni. "
    "Ne mets aucun texte hors JSON. Si une info manque, laisse la clé mais avec une valeur vide ('', 0 ou null). "
    "Les cotes sont au format américain (+250, -225). Les labels contiennent le marché (ex: 'Over 1.5 hits'). "
    "Les 'book' sont les noms de bookmakers (e.g., LeoVegas, BetVictor)."
)

USER_TEMPLATE = """EMAIL SUBJECT:
{subject}

EMAIL PLAIN TEXT:
{body}

OBJECTIF:
Extrait les champs suivants dans un JSON strict (minifié, une ligne):
- event_id: un identifiant stable (si absent, dérive depuis event+player+timestamp présent dans l'email)
- league, event, kickoff_iso (ISO8601 si possible)
- market, player, edge_percent
- selection_over: label, american, book, url (si connue)
- selection_under: label, american, book, url (si connue)

Schéma JSON (indicatif) :
{schema}
"""

def _fallback_regex(body: str) -> Dict[str, Any]:
    # Simple fallback if AI fails
    def m(rex, group=1, default=""):
        mm = re.search(rex, body, flags=re.I)
        return mm.group(group).strip() if mm else default

    def m_int(rex, group=1, default=0):
        try:
            val = m(rex, group, str(default))
            if val and not val.startswith(('+', '-')):
                val = '+' + val
            return int(val)
        except Exception:
            return default

    player = m(r"Player:\s*(.+)")
    over_odds = m_int(r"OverOdds:\s*([+\-]?\d+)")
    under_odds = m_int(r"UnderOdds:\s*([+\-]?\d+)")
    event = m(r"Event:\s*(.+)")
    league = m(r"League:\s*(.+)")
    market = m(r"Market:\s*(.+)")
    edge_raw = m(r"Edge:\s*([\d\.,]+)", default="0")
    try:
        edge = float((edge_raw or "0").replace(",", "."))
    except Exception:
        edge = 0.0

    # Stable-ish event_id from subject+fields
    seed = f"{subject}|{event}|{player}|{over_odds}|{under_odds}|{kickoff}"
    eid = "auto_" + hashlib.md5(seed.encode()).hexdigest()[:16]

    return {
        "event_id": eid,
        "league": league, "event": event, "kickoff_iso": "",
        "market": market, "player": player, "edge_percent": edge,
        "tags": [t for t in [league, "Baseball", market] if t][:3],
        "selection_over":  {"label": "Over 1.5 hits",  "american": over_odds,  "book": "LeoVegas",  "url": ""},
        "selection_under": {"label": "Under 1.5 hits", "american": under_odds, "book": "BetVictor", "url": ""}
    }


def _normalize(d: Dict[str, Any]) -> Dict[str, Any]:
    # Normalize decimal commas and american odds sign
    def _norm_american(v):
        s = str(v or 0).strip().replace(" ", "")
        if s and s[0].isdigit():
            s = "+" + s
        try:
            return int(s)
        except Exception:
            try:
                return int(float(s))
            except Exception:
                return 0

    d["edge_percent"] = float(str(d.get("edge_percent", 0)).replace(",", ".") or 0)
    for k in ("selection_over", "selection_under"):
        if isinstance(d.get(k), dict):
            d[k]["american"] = _norm_american(d[k].get("american"))
            if isinstance(d[k].get("label"), str):
                d[k]["label"] = d[k]["label"].replace(",", ".")
    tags = d.get("tags") or []
    if not isinstance(tags, list):
        tags = [str(tags)]
    d["tags"] = [t for t in tags if t][:3]
    if not d.get("event_id"):
        seed = f"{d.get('event','')}|{d.get('player','')}|{time.time()}"
        d["event_id"] = "auto_" + hashlib.md5(seed.encode()).hexdigest()[:16]
    return d


def extract_from_email(subject: str, body: str) -> Dict[str, Any]:
    # If no client, fallback immediately
    if client is None:
        return _fallback_regex(subject or "", body or "")
    try:
        user = USER_TEMPLATE.format(subject=subject or "", body=(body or "")[:8000], schema=json.dumps(SCHEMA_HINT))
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            response_format={"type": "json_object"},
            temperature=0,
            messages=[
                {"role": "system", "content": SYSTEM_MSG},
                {"role": "user", "content": user},
            ],
        )
        raw = resp.choices[0].message.content
        data = json.loads(raw)
        return _normalize(data)
    except Exception:
        return _normalize(_fallback_regex(subject or "", body or ""))
