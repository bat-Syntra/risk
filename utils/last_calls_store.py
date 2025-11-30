"""
In-memory store for last Good EV and Middle calls.
Provides push/get helpers to avoid importing main_new from handlers.
"""
from typing import List, Dict

# Keep up to 10 recent items per type
_MAX = 10

_GOOD_ODDS: List[Dict] = []
_MIDDLE: List[Dict] = []

def push_good_odds(item: Dict) -> None:
    _GOOD_ODDS.insert(0, item)
    if len(_GOOD_ODDS) > _MAX:
        del _GOOD_ODDS[_MAX:]

def get_recent_good_odds(limit: int = 10) -> List[Dict]:
    return _GOOD_ODDS[: min(limit, _MAX)]

def push_middle(item: Dict) -> None:
    _MIDDLE.insert(0, item)
    if len(_MIDDLE) > _MAX:
        del _MIDDLE[_MAX:]

def get_recent_middle(limit: int = 10) -> List[Dict]:
    return _MIDDLE[: min(limit, _MAX)]
