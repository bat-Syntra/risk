from __future__ import annotations
# -------- Image rendering for pretty alerts (optional) --------
def _load_logo_image(name: str):
    try:
        # Map canonical bookmaker to logo filename guess
        key = (name or "").strip()
        if not key:
            return None
        fname = key.replace(" ", "_") + ".png"
        path = os.path.join("logos", fname)
        if not os.path.exists(path):
            # Try alternative casings
            alts = [
                os.path.join("logos", key + ".png"),
                os.path.join("logos", key.lower() + ".png"),
                os.path.join("logos", key.title() + ".png"),
            ]
            for p in alts:
                if os.path.exists(p):
                    path = p
                    break
        if os.path.exists(path):
            img = Image.open(path).convert("RGBA")
            # Fit to box 140x140
            img.thumbnail((140, 140))
            return img
    except Exception:
        return None
    return None


def render_alert_image(call: dict) -> BytesIO | None:
    try:
        W, H = 1000, 520
        bg = Image.new("RGB", (W, H), (18, 22, 28))
        draw = ImageDraw.Draw(bg)
        # Fallback fonts
        try:
            font_big = ImageFont.truetype("Arial.ttf", 40)
            font_med = ImageFont.truetype("Arial.ttf", 28)
            font_small = ImageFont.truetype("Arial.ttf", 24)
        except Exception:
            font_big = ImageFont.load_default()
            font_med = ImageFont.load_default()
            font_small = ImageFont.load_default()

        pct = _sanitize_percentage_str(call.get("percentage", ""))
        team1 = call.get("team1", "")
        team2 = call.get("team2", "")
        sport = (call.get('sport','') or '').strip()
        league = (call.get('league','') or '').strip()
        market = (call.get('market','') or '').strip()
        time_str = (call.get('time','') or '').strip()

        # Header
        draw.text((24, 20), f"Arbitrage - {pct}", fill=(255, 255, 255), font=font_big)
        meta = " • ".join([s for s in [sport, league, time_str] if s])
        draw.text((24, 70), meta, fill=(180, 200, 220), font=font_small)
        draw.text((24, 100), f"{team1} vs {team2}", fill=(220, 230, 240), font=font_med)
        draw.text((24, 135), f"{market}", fill=(160, 180, 200), font=font_small)

        # Outcomes boxes
        box1 = (24, 180, 24+460, 480)
        box2 = (516, 180, 516+460, 480)
        for bx in (box1, box2):
            draw.rectangle(bx, outline=(70,80,95), width=2)

        # Left outcome
        b1 = resolve_bookmaker(call.get('book1',''))
        sel1 = _clean_selection(call.get('selection1',''))
        o1 = str(call.get('odds1','')).replace('−','-').strip()
        stake1 = call.get('stake1', '$0')
        ret1 = _calculate_return(stake1, o1)
        logo1 = _load_logo_image(b1.get('name'))
        if logo1:
            bg.paste(logo1, (box1[0]+16, box1[1]+16), logo1)
        draw.text((box1[0]+180, box1[1]+20), b1.get('name', ''), fill=(250, 250, 250), font=font_med)
        draw.text((box1[0]+16, box1[1]+180), f"{sel1}", fill=(220, 230, 240), font=font_med)
        draw.text((box1[0]+16, box1[1]+230), f"Stake: {stake1}", fill=(200, 210, 220), font=font_small)
        draw.text((box1[0]+16, box1[1]+260), f"Return: ${ret1:.2f}", fill=(200, 210, 220), font=font_small)

        # Right outcome
        b2 = resolve_bookmaker(call.get('book2',''))
        sel2 = _clean_selection(call.get('selection2',''))
        o2 = str(call.get('odds2','')).replace('−','-').strip()
        stake2 = call.get('stake2', '$0')
        ret2 = _calculate_return(stake2, o2)
        logo2 = _load_logo_image(b2.get('name'))
        if logo2:
            bg.paste(logo2, (box2[0]+16, box2[1]+16), logo2)
        draw.text((box2[0]+180, box2[1]+20), b2.get('name', ''), fill=(250, 250, 250), font=font_med)
        draw.text((box2[0]+16, box2[1]+180), f"{sel2}", fill=(220, 230, 240), font=font_med)
        draw.text((box2[0]+16, box2[1]+230), f"Stake: {stake2}", fill=(200, 210, 220), font=font_small)
        draw.text((box2[0]+16, box2[1]+260), f"Return: ${ret2:.2f}", fill=(200, 210, 220), font=font_small)

        # Footer cash/profit
        stake1_val = float(re.sub(r'[^\d.]', '', stake1 or '0'))
        stake2_val = float(re.sub(r'[^\d.]', '', stake2 or '0'))
        total_cash = stake1_val + stake2_val
        profit = min(ret1, ret2) - total_cash
        draw.text((24, 480-28), f"Cash: ${total_cash:.1f}   •   Profit: ${profit:.2f}", fill=(240, 240, 240), font=font_small)

        buf = BytesIO()
        bg.save(buf, format='PNG')
        buf.seek(0)
        return buf
    except Exception as e:
        logger.warning(f"Render image failed: {e}")
        return None

"""
Bridge entre Nonoriribot et Risk0_bot
Écoute les messages de Nonoriribot et les forward à l'API Risk0_bot
"""
import asyncio
import os
import re
from datetime import datetime
from typing import Optional
from io import BytesIO
from PIL import Image, ImageOps, ImageFilter, ImageDraw, ImageFont
import pytesseract
import hashlib
import sqlite3
import logging

from telethon import TelegramClient, events, Button
from telethon.errors import SessionPasswordNeededError
from telethon.errors.rpcerrorlist import PhoneCodeInvalidError, PhoneCodeExpiredError
import aiohttp
import base64
import json
from dotenv import load_dotenv
from bookmakers import resolve_bookmaker, identify_bookmaker
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️ OpenAI not available. Install: pip install openai")
try:
    from logo_detector import detect_casinos_in_image
    LOGO_DETECTION_ENABLED = True
except ImportError:
    LOGO_DETECTION_ENABLED = False
    print("⚠️ Logo detection not available. Install opencv-python: pip install opencv-python")

try:
    from simple_logo_detector import SimpleLogoDetector
    SIMPLE_DETECTION_ENABLED = True
except ImportError:
    SIMPLE_DETECTION_ENABLED = False

# Configuration
load_dotenv()
API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))  # Get from my.telegram.org
API_HASH = os.getenv("TELEGRAM_API_HASH", "")    # Get from my.telegram.org
PHONE = os.getenv("TELEGRAM_PHONE", "")           # Ton numéro de téléphone

# Bot IDs / Sources
SOURCE_BOT_USERNAME = os.getenv("SOURCE_BOT_USERNAME", "Nonoriribot")  # Bot source qui envoie les alertes
SOURCE_CHAT_ID_ENV = os.getenv("SOURCE_CHAT_ID", "").strip()
SOURCE_CHAT_ID = int(SOURCE_CHAT_ID_ENV) if SOURCE_CHAT_ID_ENV.isdigit() else None
RISK0_API_URL = os.getenv("RISK0_API_URL", "http://localhost:8080/public/drop")  # API du Risk0_bot
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
USE_GPT_VISION = os.getenv("USE_GPT_VISION", "true").lower() in ("true", "1", "yes")
API_SEND_ODDS = os.getenv("API_SEND_ODDS", "false").lower() in ("true", "1", "yes")
RENDER_IMAGE_ALERTS = os.getenv("RENDER_IMAGE_ALERTS", "false").lower() in ("true", "1", "yes")

# Destination Telegram (optionnel): envoie aussi le message formaté vers ce chat/groupe
DESTINATION_CHAT_ID_ENV = os.getenv("DESTINATION_CHAT_ID", "").strip()
DESTINATION_CHAT_ID = int(DESTINATION_CHAT_ID_ENV) if DESTINATION_CHAT_ID_ENV.lstrip("-").isdigit() else None
STRICT_BOOKS = os.getenv("STRICT_BOOKS", "0").strip() == "1"

# Initialize Telethon client (user account)
client = TelegramClient('bridge_session', API_ID, API_HASH)

# Logging setup
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger("ocr_bridge")


def parse_arbitrage_message(text: str) -> Optional[dict]:
    """
    Parse un message d'arbitrage du bot source
    
    Expected format:
    🚨 Arbitrage Alert X.XX% 🚨
    Match: Team A vs Team B
    League: NBA
    Market: Total Points
    
    Outcome 1: Over 200 @ -200 (Betsson)
    Outcome 2: Under 200 @ +255 (Coolbet)
    """
    try:
        # Extract arbitrage percentage
        arb_match = re.search(r'(\d+\.?\d*)%', text)
        if not arb_match:
            return None
        arb_percentage = float(arb_match.group(1))

        # Defaults
        match = "Unknown Match"
        league = "Unknown League"
        market = "Moneyline"
        sport = "Unknown"

        # Try labeled fields first (legacy format)
        match_match = re.search(r'Match:\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
        if match_match:
            match = match_match.group(1).strip()
        league_match = re.search(r'League:\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
        if league_match:
            league = league_match.group(1).strip()
        market_match = re.search(r'Market:\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
        if market_match:
            market = market_match.group(1).strip()

        # Fallback for Nonoriribot compact format
        # e.g. "Houston Texans vs Buffalo Bills [Player Extra Points Made : ...] ... (Football, NFL)"
        if match == "Unknown Match":
            # Line containing 'vs'
            vs_line = None
            for line in text.splitlines():
                if ' vs ' in line.lower():
                    vs_line = line.strip()
                    break
            if vs_line:
                # Extract [ ... ] as market hint
                bracket = re.search(r'\[(.*?)\]', vs_line)
                if bracket:
                    market_hint = bracket.group(1)
                    # Before colon is market name if present
                    parts = market_hint.split(':', 1)
                    market = parts[0].strip() if parts else market
                # Match name is before '[' if exists, else before first two outcomes
                match = vs_line.split('[')[0].strip()

            # League at the end in parentheses
            paren = re.search(r'\(([^()]+)\)\s*$', vs_line or text)
            if paren:
                league = paren.group(1).strip()

        # Infer sport from league
        up = (league or '').upper()
        if any(x in up for x in ["NBA", "NCAA BASKET", "BASKET"]):
            sport = "Basketball"
        elif any(x in up for x in ["NFL", "NCAA FOOT", "FOOTBALL"]):
            sport = "Football"
        elif any(x in up for x in ["NHL", "HOCKEY"]):
            sport = "Hockey"
        elif any(x in up for x in ["MLB", "BASEBALL"]):
            sport = "Baseball"
        elif any(x in up for x in ["MLS", "SOCCER", "EPL", "FOOT"]):
            sport = "Soccer"

        # Extract outcomes
        outcomes: list[dict] = []

        # Try legacy "Outcome X:" blocks
        for m in re.finditer(r'Outcome\s+\d+:\s*(.+?)\s*@\s*([+-]?\d+)\s*\((.+?)\)', text, re.IGNORECASE):
            outcomes.append({
                "outcome": m.group(1).strip(),
                "odds": int(m.group(2)),
                "casino": m.group(3).strip(),
            })

        # Fallback: "... Over 2.5 +100 @ bwin, ... Under 2.5 +118 @ iBet"
        if len(outcomes) < 2:
            for m in re.finditer(r'([^,\n]+?)\s+([+-]?\d+)\s*@\s*([A-Za-z0-9 _.-]+)', text):
                outcome_text = m.group(1).strip()
                odds = int(m.group(2))
                casino = m.group(3).strip().strip(',')
                # Filter out trailing parentheses like (Football, NFL)
                casino = re.sub(r'\s*\([^)]*\)\s*$', '', casino).strip()
                outcomes.append({
                    "outcome": outcome_text,
                    "odds": odds,
                    "casino": casino,
                })

        # Need at least two
        # Deduplicate first two unique outcomes
        uniq = []
        seen = set()
        for o in outcomes:
            key = (o['outcome'], o['odds'], o['casino'].lower())
            if key in seen:
                continue
            seen.add(key)
            uniq.append(o)
            if len(uniq) >= 2:
                break

        if len(uniq) < 2:
            print(f"⚠️ Pas assez d'outcomes trouvés: {len(uniq)}")
            return None

        # Generate event
        event_id = f"arb_{int(datetime.now().timestamp())}_{arb_percentage}"
        return {
            "event_id": event_id,
            "arb_percentage": arb_percentage,
            "match": match,
            "league": league,
            "market": market,
            "sport": sport,
            "outcomes": uniq,
            "raw_message": text,
        }
    
    except Exception as e:
        print(f"❌ Erreur parsing: {e}")
        return None


SENT_CALLS: set[str] = set()

# SQLite persistent dedup store
DEDUP_DB_PATH = os.getenv("DEDUP_DB_PATH", "ocr_calls.db")
_dedup_conn = sqlite3.connect(DEDUP_DB_PATH, check_same_thread=False)
_dedup_conn.execute(
    """
    CREATE TABLE IF NOT EXISTS sent_calls (
        hash TEXT PRIMARY KEY,
        created_at TEXT DEFAULT (datetime('now'))
    )
    """
)
_dedup_conn.commit()

def _mark_if_new(hash_str: str) -> bool:
    """Return True if this hash is new (and mark it), False if already seen."""
    if hash_str in SENT_CALLS:
        return False
    try:
        cur = _dedup_conn.cursor()
        cur.execute("SELECT 1 FROM sent_calls WHERE hash=?", (hash_str,))
        row = cur.fetchone()
        if row:
            return False
        cur.execute("INSERT INTO sent_calls(hash) VALUES (?)", (hash_str,))
        _dedup_conn.commit()
        SENT_CALLS.add(hash_str)
        return True
    except Exception as e:
        logger.warning(f"Dedup DB error: {e}")
        # Fallback to memory-only
        SENT_CALLS.add(hash_str)
        return True


# ===== OCR + Parsing for image screenshots =====
def extract_text_from_image(photo_bytes: bytes) -> str:
    """OCR the image bytes to text using Tesseract.
    Requires tesseract engine installed on system.
    """
    try:
        image = Image.open(BytesIO(photo_bytes))
        # Basic upscale and preprocessing for better OCR on small or noisy text
        try:
            w, h = image.size
            scale = float(os.getenv("OCR_SCALE", "1.5"))
            if max(w, h) < 1400:
                image = image.resize((int(w*scale), int(h*scale)), resample=Image.BICUBIC)
        except Exception:
            pass
        try:
            image = image.convert("L")
            image = ImageOps.autocontrast(image)
            image = image.filter(ImageFilter.SHARPEN)
        except Exception:
            pass

        # Tesseract configuration
        tess_cmd = os.getenv("TESSERACT_CMD", "")
        if tess_cmd:
            pytesseract.pytesseract.tesseract_cmd = tess_cmd
        lang = os.getenv("TESSERACT_LANG", "eng")
        cfg = os.getenv("TESSERACT_CONFIG", "--oem 3 --psm 6")

        text = pytesseract.image_to_string(image, lang=lang, config=cfg)
        return text or ""
    except Exception as e:
        print(f"❌ OCR error: {e}")
        return ""


def _split_call_blocks(text: str) -> list[tuple[str, str]]:
    """Split OCR text into blocks by percentage markers.
    Returns list of (percentage, block_text).
    """
    blocks: list[tuple[str, str]] = []
    perc_re = re.compile(r"(\d+(?:[\.,]\d+)?%)")
    matches = list(perc_re.finditer(text))
    if not matches:
        return blocks
    for i, m in enumerate(matches):
        # Include up to 1200 chars of preceding context (to capture stake/odds printed far before %)
        start = max(0, m.start() - 1200)
        end = matches[i+1].start() if i+1 < len(matches) else len(text)
        block = text[start:end]
        blocks.append((m.group(1), block))
    return blocks


def parse_calls_from_ocr(text: str, visual_casinos: list = None) -> list[dict]:
    """Extract 1..n calls from OCR text."""
    calls: list[dict] = []
    blocks: list[tuple[str, str]] = []
    # Primary: by percentage
    blocks.extend(_split_call_blocks(text))
    # Secondary: by time markers
    blocks.extend(_split_call_blocks_by_time(text))
    # Tertiary: by team vs markers
    blocks.extend(_split_call_blocks_by_vs(text))
    if not blocks:
        blocks = [("0%", text)]
    for perc, block in blocks:
        s_perc = _sanitize_percentage_str(perc)
        call = parse_single_call(block, s_perc, visual_casinos=visual_casinos)
        if call:
            # Check minimum percentage threshold
            try:
                min_pct = float(os.getenv("MIN_ARB_PERCENT", "2.0"))
                call_pct = float(s_perc.replace("%", "").strip())
                if call_pct < min_pct:
                    logger.info(f"Skipped low arbitrage call: {call_pct:.2f}% < {min_pct}%")
                    continue
            except Exception:
                pass
            calls.append(call)
    return calls


def _split_call_blocks_by_vs(text: str) -> list[tuple[str, str]]:
    """Split OCR text by 'Team A vs Team B' anchors to capture 2-4 calls per image.
    Returns list of (percentage_guess, block_text).
    """
    res: list[tuple[str, str]] = []
    pat = re.compile(r"[^\n]{0,60}?\b([A-Za-z0-9][^\n]{1,80}?)\s+v(?:s)?\s+([^\n]{1,80})")
    ms = list(pat.finditer(text))
    if not ms:
        return res
    for i, m in enumerate(ms):
        start = max(0, m.start() - 300)
        end = ms[i+1].start() if i+1 < len(ms) else len(text)
        block = text[start:end]
        # Try to guess percentage within the block
        pm = re.search(r"(\d+(?:[\.,]\d+)?%)", block)
        perc = pm.group(1) if pm else "0%"
        res.append((perc, block))
    return res


def _split_call_blocks_by_time(text: str) -> list[tuple[str, str]]:
    """Split OCR text into blocks by day/time markers.
    Returns list of (percentage, block_text) with percentage unknown ("0%").
    """
    res: list[tuple[str, str]] = []
    pat = re.compile(
        r"(Sun|Mon|Tue|Wed|Thu|Fri|Sat|Tomorrow|Today|Tonight|Tomorow|Tomorw|Tommorow|Tmrw|Tmrrw)[a-z]*,?\s+\d{1,2}(?::\d{2})?\s*[AP]M",
        re.IGNORECASE,
    )
    ms = list(pat.finditer(text))
    if not ms:
        return res
    for i, m in enumerate(ms):
        # Include up to 1200 chars of preceding context
        start = max(0, m.start() - 1200)
        end = ms[i+1].start() if i+1 < len(ms) else len(text)
        block = text[start:end]
        res.append(("0%", block))
    return res


def _sanitize_percentage_str(perc: str) -> str:
    raw = (perc or "").strip().replace("%", "").replace(",", ".")
    try:
        val = float(raw)
    except Exception:
        return "0%"
    # Only apply divide-by-10 if value is implausibly high AND has no decimal
    if val > 100:
        # 990% -> 9.9%, 999% -> 9.99%
        while val > 100:
            val /= 10.0
    elif val > 50 and "." not in raw:
        # For values like "99" without decimal, assume it's 9.9%
        val /= 10.0
    # Clamp to [MIN, MAX]
    try:
        min_pct = float(os.getenv("MIN_ARB_PERCENT", "2.0"))
        max_pct = float(os.getenv("MAX_ARB_PERCENT", "35.0"))
    except Exception:
        min_pct = 2.0
        max_pct = 35.0
    # Return real value even if below min (will be skipped later)
    val = min(val, max_pct)
    if val >= 10:
        return f"{val:.1f}%"
    return f"{val:.2f}%"


def _find_sport_league(block: str) -> tuple[str, str]:
    sport = "Unknown"
    league = ""
    m = re.search(
        r"(Soccer|Basketball|eSports|Hockey|Tennis|Baseball|Football)\s*(?:[•·]|-|—|–|\be\b)\s+([^\n]+)",
        block,
        re.IGNORECASE,
    )
    if m:
        sport = m.group(1).strip().title()
        league = m.group(2).strip()
    else:
        # Fallback, detect sport only
        m2 = re.search(r"(Soccer|Basketball|eSports|Hockey|Tennis|Baseball|Football)", block, re.IGNORECASE)
        if m2:
            sport = m2.group(1).strip().title()
    return sport, league


def _find_teams(block: str) -> tuple[str, str] | tuple[None, None]:
    m = re.search(r"([^\n]+?)\s+v(?:s)?\s+([^\n]+)", block, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return None, None


def _find_time(block: str) -> str:
    m = re.search(
        r"(Sun|Mon|Tue|Wed|Thu|Fri|Sat|Tomorrow|Today|Tonight|Tomorow|Tomorw|Tommorow|Tmrw|Tmrrw)[a-z]*,?\s+(\d{1,2}(?::\d{2})?\s*[AP]M)",
        block,
        re.IGNORECASE,
    )
    return f"{m.group(1).title()}, {m.group(2)}" if m else ""


def _find_market(block: str) -> str:
    # Common markets
    m = re.search(
        r"(Player\s+(Rebounds|Points|Assists|Steals|Blocks)|Team Total Corners|Total Corners|Total Goals|Moneyline|Totals?|Spread|Over\s*\d+(?:[\.,]\d+)?|Under\s*\d+(?:[\.,]\d+)?)",
        block,
        re.IGNORECASE,
    )
    return m.group(1).strip() if m else ""


def _find_profit(block: str) -> str:
    m = re.search(r"~?\s*\$[\d,.]+", block)
    return (m.group(0).strip() if m else "")


def _refine_selection(text: str) -> str:
    """Try to keep only the selection phrase close to Over/Under/Moneyline tokens."""
    s = (text or "").strip()
    try:
        # Prefer patterns like 'Aaron Gordon Over 5.5' or 'Team Total Corners Over 3'
        pat = re.compile(r"([A-Za-z][A-Za-z .]{0,60})\b(Over|Under|Moneyline|ML)\s*\d*(?:[\.,]\d+)?", re.IGNORECASE)
        matches = list(pat.finditer(s))
        if matches:
            m = matches[-1]
            cand = s[m.start():]
            cand = re.sub(r"\s+", " ", cand)
            # Strip noisy OCR artifacts
            cand = re.sub(r"[\[\]\|~]+", " ", cand)
            cand = re.sub(r"\b(?:rs|wy)\)\b", " ", cand, flags=re.IGNORECASE)
            return cand.strip()
    except Exception:
        pass
    s = re.sub(r"[\[\]\|~]+", " ", s)
    return re.sub(r"\s+", " ", s)


def _find_books(block: str, visual_casinos: list = None) -> list[dict]:
    """Find up to two book lines with selection, stake, odds.
    Strategy: locate 'Book $stake odds' and infer selection as the text before the book on the same line.
    """
    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
    out: list[dict] = []
    # Pattern 1: casino avant stake et odds (ex: "ibet $90 +145")
    pat = re.compile(r"([A-Za-z][A-Za-z0-9]+)\s*(?:\$|S)\s*(\d+(?:[\.,]\d{1,2})?)\s*([+\-−]\d{2,4})")
    # Pattern 2: stake et odds avec casino après (ex: "$100 +111 cootsecr")
    pat2 = re.compile(r"(?:\$|S)\s*(\d+(?:[\.,]\d{1,2})?)\s*([+\-−]\d{2,4})\s*([A-Za-z][A-Za-z0-9]+)")
    # Pattern 3: juste stake et odds (casino à deviner)
    alt = re.compile(r"(?:\$|S)\s*(\d+(?:[\.,]\d{1,2})?).*?([+\-−]\d{2,4})")
    
    # Log visual casinos if detected
    if visual_casinos:
        logger.info(f"Using visual casinos in _find_books: {visual_casinos}")

    def _guess_book_from_text(s: str) -> str | None:
        # First check if any visual casino matches tokens in text
        if visual_casinos:
            tokens = re.findall(r"[A-Za-z][A-Za-z0-9]+", s or "")
            for vc in visual_casinos:
                # Check if visual casino name appears in text (fuzzy)
                vc_norm = vc.lower().replace(" ", "")
                for t in tokens:
                    if len(t) >= 4 and (t.lower() in vc_norm or vc_norm in t.lower()):
                        return vc
        
        # Fallback to OCR text matching
        try:
            tokens = re.findall(r"[A-Za-z][A-Za-z0-9]+", s or "")
            for t in tokens:
                if len(t) < 4:
                    continue
                # Try JSON fuzzy first
                r = identify_bookmaker(t)
                if not r.get("found"):
                    r = resolve_bookmaker(t)
                if r.get("found"):
                    return r.get("name")
        except Exception:
            pass
        return None
    
    # If we have exactly 2 visual casinos detected, prefer them
    visual_idx = 0
    prev_line = ""
    for idx, ln in enumerate(lines):
        # Try Pattern 1: casino before stake (ex: "ibet $90 +145")
        matches = list(pat.finditer(ln))
        # Try Pattern 2: casino after odds (ex: "$100 +111 cootsecr")
        matches2 = list(pat2.finditer(ln))
        
        if matches:
            sel_hint = prev_line.strip()
            for mi in matches:
                book = mi.group(1)
                stake = f"${mi.group(2)}"
                odds = mi.group(3).replace("−", "-")
                # Try to resolve the book name
                # Try JSON patterns/fuzzy on full window first
                start_w = max(0, idx - 2)
                end_w = min(len(lines), idx + 3)
                window_text = " ".join(lines[start_w:end_w])
                rb = identify_bookmaker(window_text)
                if not rb.get("found"):
                    rb = identify_bookmaker(ln)
                if not rb.get("found"):
                    rb = resolve_bookmaker(book)
                resolved_book = rb
                if resolved_book.get("found"):
                    book_name = resolved_book.get("name")
                elif visual_casinos and len(out) < len(visual_casinos):
                    # Use visual casino if book not resolved
                    book_name = visual_casinos[len(out)]
                else:
                    book_name = book
                # Selection is the text before first book token on the line
                sel = ln.split(book, 1)[0].strip() or sel_hint or "[Selection]"
                sel = _refine_selection(sel)
                out.append({"book": book_name, "selection": sel, "odds": odds, "stake": stake})
                if len(out) >= 2:
                    break
            if len(out) >= 2:
                break
        elif matches2:
            # Pattern 2: casino after odds
            sel_hint = prev_line.strip()
            suspicious = {"Betway", "Casumo"}
            trusted = {"BET99", "iBet", "Betsson", "Coolbet"}
            for m2 in matches2:
                stake = f"${m2.group(1)}"
                odds = m2.group(2).replace("−", "-")
                book = m2.group(3)
                # Try resolve bookmaker from local window
                start_w = max(0, idx - 2)
                end_w = min(len(lines), idx + 3)
                window_text = " ".join(lines[start_w:end_w])
                rb = identify_bookmaker(window_text)
                if not rb.get("found"):
                    rb = identify_bookmaker(ln)
                if not rb.get("found"):
                    rb = resolve_bookmaker(book)
                # Decide book name with preference: text > trusted visual > raw token
                book_name = None
                if rb.get("found"):
                    book_name = rb.get("name")
                elif visual_casinos and len(out) < len(visual_casinos):
                    candidate = visual_casinos[len(out)]
                    if candidate not in suspicious:
                        book_name = candidate
                if not book_name:
                    book_name = book
                # Selection is from previous line or context
                sel = prev_line.strip() or "[Selection]"
                sel = _refine_selection(sel)
                out.append({"book": book_name, "selection": sel, "odds": odds, "stake": stake})
                if len(out) >= 2:
                    break
            if len(out) >= 2:
                break
        else:
            # Alt: only stake + odds on line (book missing); guess book token if any word nearby
            alts = list(alt.finditer(ln))
            if alts:
                # Heuristic for book guess: last CamelCase-ish word in line
                words = re.findall(r"[A-Za-z][A-Za-z0-9]+", ln)
                # Lookaround window: previous and next 2 lines
                start_w = max(0, idx - 2)
                end_w = min(len(lines), idx + 3)
                window_text = " ".join(lines[start_w:end_w])
                book_guess = _guess_book_from_text(ln) or _guess_book_from_text(window_text)
                blacklist = {"Over", "Under", "Team", "Total", "Corners", "Moneyline", "Spread", "GAMEA", "SITEA", "on", "On", "BON", "bon", "SITE", "GAME", "Return", "Stake", "Odds", "odds", "scan", "Scan", "Today", "Tomorrow", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"}
                if not book_guess:
                    for w in reversed(words):
                        if w not in blacklist and w.lower() not in {"vs", "odds", "scan", "tomorrow", "mon", "sun"}:
                            # try resolve
                            r = resolve_bookmaker(w)
                            if r.get("found"):
                                book_guess = r.get("name")
                                break
                sel_hint = _refine_selection(prev_line.strip() or "[Selection]")
                for ai in alts:
                    stake = f"${ai.group(1)}"
                    odds = ai.group(2).replace("−", "-")
                    # Try to extract selection from the text just before this match
                    local_ctx = ln[: ai.start()] if hasattr(ai, 'start') else ln
                    local_sel = _refine_selection(local_ctx) or sel_hint
                    # Prefer text-based guess; use visual only if not suspicious and no text
                    suspicious = {"Betway", "Casumo"}
                    if book_guess:
                        guess = book_guess
                    elif visual_casinos and visual_idx < len(visual_casinos):
                        candidate = visual_casinos[visual_idx]
                        visual_idx += 1
                        guess = candidate if candidate not in suspicious else "Unknown"
                    else:
                        guess = _guess_book_from_text(prev_line) or _guess_book_from_text(window_text) or "Unknown"
                    out.append({"book": guess, "selection": local_sel, "odds": odds, "stake": stake})
                    if len(out) >= 2:
                        break
                if len(out) >= 2:
                    break
            prev_line = ln
    if len(out) >= 2:
        # Ensure two distinct outcomes (prefer distinct bookmaker; fallback to selection+odds)
        uniq: list[dict] = []
        seen = set()
        for o in out:
            key = ((o.get("book") or "").lower(), o.get("odds") or "", o.get("selection") or "")
            if key in seen:
                continue
            seen.add(key)
            uniq.append(o)
            if len(uniq) >= 2:
                break
        return uniq[:2]

    # Fallback 2: block-wide scan allowing optional book token before $stake odds
    blk_pat = re.compile(
        r"(?:(?P<book>[A-Za-z][A-Za-z0-9]+)[^$\n]{0,20})?(?:\$|S)\s*(?P<stake>\d+(?:\.\d{1,2})?)\s*(?P<odds>[+\-−]\d{2,4})",
        re.MULTILINE,
    )
    matches = list(blk_pat.finditer(block))
    for m in matches:
        book = (m.group('book') or 'Unknown')
        stake = f"${m.group('stake')}"
        odds = (m.group('odds') or '').replace('−', '-')
        # Selection: take preceding non-empty line or up to 80 chars before match
        pre = block[:m.start()]
        last_nl = pre.rfind('\n')
        pre_line = pre[last_nl+1:].strip() if last_nl != -1 else pre.strip()
        if not pre_line:
            pre_line = pre[-80:].strip()
        sel = re.sub(r"\s+", " ", pre_line) or "[Selection]"
        out.append({"book": book, "selection": sel, "odds": odds, "stake": stake})
        if len(out) >= 2:
            break
    return out[:2]


def parse_single_call(block: str, percentage: str, visual_casinos: list = None) -> Optional[dict]:
    try:
        sport, league = _find_sport_league(block)
        team1, team2 = _find_teams(block)
        time_str = _find_time(block)
        market = _find_market(block)
        profit = _find_profit(block)
        books = _find_books(block, visual_casinos=visual_casinos)
        if not (team1 and team2) or len(books) < 2:
            return None
        b1, b2 = books[0], books[1]
        
        # Override with visual casinos if available and books are Unknown
        if visual_casinos and len(visual_casinos) >= 2:
            if b1.get("book") == "Unknown" or not resolve_bookmaker(b1.get("book")).get("found"):
                b1["book"] = visual_casinos[0]
            if b2.get("book") == "Unknown" or not resolve_bookmaker(b2.get("book")).get("found"):
                b2["book"] = visual_casinos[1]
        return {
            'percentage': percentage.strip(),
            'profit': profit,
            'sport': sport,
            'league': league,
            'team1': team1,
            'team2': team2,
            'market': market,
            'time': time_str,
            'book1': b1['book'],
            'selection1': b1['selection'],
            'odds1': b1['odds'],
            'stake1': b1['stake'],
            'book2': b2['book'],
            'selection2': b2['selection'],
            'odds2': b2['odds'],
            'stake2': b2['stake'],
        }
    except Exception as e:
        print(f"❌ OCR parse error: {e}")
        return None


def _calculate_return(stake_str: str, odds_str: str) -> float:
    """Calcule le return pour une cote américaine."""
    try:
        stake = float(re.sub(r'[^\d.]', '', stake_str or '0'))
        odds_match = re.search(r'([+\-])(\d+)', odds_str or '')
        if not odds_match:
            return stake
        
        sign = odds_match.group(1)
        value = int(odds_match.group(2))
        
        if sign == '+':
            profit = stake * (value / 100.0)
        else:  # sign == '-'
            profit = stake * (100.0 / value)
        
        return stake + profit
    except Exception:
        return 0.0


def _clean_selection(sel: str) -> str:
    """Nettoie complètement la sélection (retire OCR garbage)."""
    sel = str(sel or '').strip()
    # Retirer tout ce qui ressemble à stake+odds (ex: "$100 -143", "$50 +305")
    sel = re.sub(r'\$\d+\s*[+\-]?\d+', '', sel)
    sel = re.sub(r'\$\d+', '', sel)  # Retirer stakes seuls
    sel = re.sub(r'[+\-]\d{2,4}', '', sel)  # Retirer cotes seules
    # Retirer garbage OCR courant
    for noise in ['céouser', 'cootsecr', 'coolsecr', 'wy)', 'rs ', '|', '~', 'éoo', 'BET99', 'BET', 'BETS9', 'bet99', 'ibet', 'IBET', 'betsson', 'BETSSON']:
        sel = sel.replace(noise, '')
    # Nettoyer espaces multiples
    sel = re.sub(r'\s+', ' ', sel).strip()
    return sel


def format_call(call: dict) -> str:
    b1 = resolve_bookmaker(call.get('book1',''))
    b2 = resolve_bookmaker(call.get('book2',''))
    b1_emoji = b1.get('emoji','🎰')
    b2_emoji = b2.get('emoji','🎯')
    b1_name = b1.get('name', call.get('book1','Unknown'))
    b2_name = b2.get('name', call.get('book2','Unknown'))
    
    # Nettoyer les sélections
    sel1 = _clean_selection(call.get('selection1',''))
    sel2 = _clean_selection(call.get('selection2',''))
    
    stake1 = call.get('stake1', '$0')
    stake2 = call.get('stake2', '$0')
    
    # Calculer returns
    return1 = _calculate_return(stake1, call.get('odds1', '+0'))
    return2 = _calculate_return(stake2, call.get('odds2', '+0'))
    
    pct = _sanitize_percentage_str(call.get('percentage',''))
    sport = (call.get('sport','') or '').strip()
    league = (call.get('league','') or '').strip()
    market = (call.get('market','') or '').strip()
    time_str = (call.get('time','') or '').strip()
    
    # Calculer total cash et profit
    stake1_val = float(re.sub(r'[^\d.]', '', stake1 or '0'))
    stake2_val = float(re.sub(r'[^\d.]', '', stake2 or '0'))
    total_cash = stake1_val + stake2_val
    profit = min(return1, return2) - total_cash
    
    header_lines = []
    header_lines.append(f"🚨 ARBITRAGE ALERT - {pct} 🚨")
    header_lines.append("")
    header_lines.append(f"🏟️ {call.get('team1','Unknown')} vs {call.get('team2','Unknown')}")
    # Add sport/league/market
    meta = " - ".join([s for s in [sport, league, market] if s])
    if meta:
        header_lines.append(f"⚽ {meta}")
    if time_str:
        header_lines.append(f"🕐 {time_str}")
    header_lines.append("")
    header_lines.append(f"💰 CASH: ${total_cash:.1f}")
    header_lines.append(f"✅ Guaranteed Profit: ${profit:.2f}")
    header_lines.append("")
    body_lines = [
        f"{b1_emoji} [{b1_name}] {sel1}",
        f"💵 Stake: {stake1} → Return: ${return1:.2f}",
        "",
        f"{b2_emoji} [{b2_name}] {sel2}",
        f"💵 Stake: {stake2} → Return: ${return2:.2f}",
    ]
    return "\n".join(header_lines + body_lines)


def _norm_hash_text(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


def _norm_money(s: str) -> str:
    try:
        m = re.search(r"[\d,.]+", str(s) or "")
        if not m:
            return "0.00"
        v = float(m.group(0).replace(",", ""))
        return f"{v:.2f}"
    except Exception:
        return "0.00"


def _norm_odds(s: str) -> str:
    try:
        t = str(s or "").strip()
        m = re.search(r"([+\-−]?)(\d{2,4})", t)
        if not m:
            return "+0"
        sign = m.group(1) or "+"
        if sign == "−":
            sign = "-"
        return f"{sign}{int(m.group(2))}"
    except Exception:
        return "+0"


def _canon_book(name: str) -> str:
    try:
        r = resolve_bookmaker(name)
        return (r.get("name") or name or "").strip().lower()
    except Exception:
        return (name or "").strip().lower()


def generate_call_hash(call: dict) -> str:
    unique = (
        f"{_norm_hash_text(call.get('team1',''))}|{_norm_hash_text(call.get('team2',''))}|{_norm_hash_text(call.get('market',''))}|"
        f"{_canon_book(call.get('book1',''))}|{_canon_book(call.get('book2',''))}|"
        f"{_norm_odds(call.get('odds1',''))}|{_norm_odds(call.get('odds2',''))}|"
        f"{_norm_money(call.get('stake1',''))}|{_norm_money(call.get('stake2',''))}"
    )
    return hashlib.md5(unique.encode('utf-8')).hexdigest()


async def parse_with_gpt_vision(photo_bytes: bytes, detected_logos: list) -> list:
    """Parse screenshot avec GPT-4o-mini Vision - renvoie liste de calls."""
    if not OPENAI_AVAILABLE or not OPENAI_API_KEY or not USE_GPT_VISION:
        return []
    
    try:
        base64_image = base64.b64encode(photo_bytes).decode('utf-8')
        
        # Liste EXACTE des bookmakers autorisés
        valid_bookmakers = ["BET99", "iBet", "Betsson", "Coolbet", "bet365", "Betway", "Casumo", "888sport", "BetVictor", "bwin", "Jackpot.bet", "Mise-o-jeu", "Proline", "Sports Interaction", "Stake", "TonyBet", "LeoVegas", "Pinnacle"]
        bookmakers_list = ", ".join(valid_bookmakers)
        
        if detected_logos:
            logos_str = ", ".join(detected_logos)
            logos_hint = f"🎯 LOGOS DÉTECTÉS AVEC HAUTE CONFIANCE: {logos_str}\n⚠️ UTILISE UNIQUEMENT CES BOOKMAKERS: {logos_str}\n❌ N'UTILISE PAS: Betway, Casumo (ce sont des faux positifs fréquents)"
        else:
            logos_str = "Aucun logo détecté avec confiance"
            logos_hint = f"⚠️ Aucun logo détecté visuellement. Identifie les bookmakers en lisant le TEXTE visible dans l'image.\n✅ BOOKMAKERS POSSIBLES: {bookmakers_list}\n❌ ÉVITE Betway et Casumo si tu ne vois pas clairement leurs logos"
        
        prompt = f"""Tu es un expert en arbitrage sportif. Analyse cette capture d'écran et extrait TOUS les calls d'arbitrage.

{logos_hint}

🚨 RÈGLES CRITIQUES - IDENTIFICATION BOOKMAKERS:
1. Logo "BET99" (texte vert/blanc) = "BET99" (JAMAIS Betway)
2. Logo "ibet" (I rouge sur fond noir) = "iBet" (JAMAIS Casumo)
3. Logo ORANGE carré "betsson" = "Betsson" (JAMAIS Betway)
4. Logo multicolore arc-en-ciel = "Coolbet" (JAMAIS Casumo)
5. Si les logos détectés ci-dessus sont fournis, TU DOIS LES UTILISER
6. NE JAMAIS utiliser "Betway" ou "Casumo" à moins d'être 100% sûr de voir leur logo
7. Si tu ne vois pas clairement le logo, lis le TEXTE du bookmaker dans l'image

📋 FORMAT DE SORTIE:
Pour chaque call d'arbitrage:
{{
  "percentage": "21.60%",
  "team1": "Florida State",
  "team2": "North Carolina State",
  "market": "Player Touchdowns - Gavin Sawchuk",
  "time": "Today, 8:00PM",
  "outcome1": {{
    "bookmaker": "BET99",  # NOM EXACT de la liste autorisée
    "selection": "Over 0.5",  # JUSTE Over/Under + valeur, AUCUN chiffre de stake/cote
    "odds": "+305",
    "stake": "$50"
  }},
  "outcome2": {{
    "bookmaker": "iBet",
    "selection": "Under 0.5",
    "odds": "-116",
    "stake": "$100"
  }}
}}

🔥 RÈGLES ABSOLUES:
- "selection" = SEULEMENT "Over X" ou "Under X" ou nom du joueur + Over/Under
- NE PAS inclure $50, +305, -116, BET99, ibet dans "selection"
- Bookmaker = un des noms EXACTS de la liste autorisée
- Si tu vois BET99 logo → utilise "BET99" (pas "Betway")
- Si tu vois ibet logo → utilise "iBet" (pas "Casumo")

Renvoie JSON: {{"calls": [...]}}. RIEN d'autre."""
        
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}",
                        "detail": "high"
                    }}
                ]
            }],
            max_tokens=3000,
            temperature=0
        )
        
        content = response.choices[0].message.content
        json_match = re.search(r'\{.*"calls".*\}', content, re.DOTALL)
        if not json_match:
            logger.warning("⚠️ GPT Vision: no JSON found")
            return []
        
        data = json.loads(json_match.group(0))
        gpt_calls = data.get('calls', [])
        
        # Convertir au format bridge.py
        converted = []
        for c in gpt_calls:
            o1 = c.get('outcome1', {})
            o2 = c.get('outcome2', {})
            # Nettoyer les sélections avant conversion
            sel1 = _clean_selection(o1.get('selection', ''))
            sel2 = _clean_selection(o2.get('selection', ''))
            
            converted.append({
                'percentage': c.get('percentage', '0%'),
                'team1': c.get('team1', 'Unknown'),
                'team2': c.get('team2', 'Unknown'),
                'market': c.get('market', 'Unknown'),
                'time': c.get('time', 'TBD'),
                'book1': o1.get('bookmaker', 'Unknown'),
                'selection1': sel1 or 'Unknown',
                'odds1': o1.get('odds', '+0'),
                'stake1': o1.get('stake', '$0'),
                'book2': o2.get('bookmaker', 'Unknown'),
                'selection2': sel2 or 'Unknown',
                'odds2': o2.get('odds', '+0'),
                'stake2': o2.get('stake', '$0')
            })
        
        logger.info(f"🧠 GPT Vision: {len(converted)} call(s) parsed")
        return converted
        
    except Exception as e:
        logger.error(f"❌ GPT Vision error: {e}")
        return []


def validate_call(call: dict) -> bool:
    required = ['percentage', 'team1', 'team2', 'market', 'book1', 'book2', 'odds1', 'odds2', 'stake1', 'stake2', 'time']
    for field in required:
        val = str(call.get(field, '')).strip()
        if not val or val in {'Unknown', 'N/A'}:
            logger.warning(f"⚠️ Call invalide - champ manquant: {field}")
            return False
    # Different books
    if _canon_book(call.get('book1','')) == _canon_book(call.get('book2','')):
        logger.warning("⚠️ Call invalide - même bookmaker 2x")
        return False
    # Dirty OCR artifacts in selection
    for key in ('selection1', 'selection2'):
        sel = str(call.get(key, ''))
        if any(tok in sel for tok in ['wy)', 'rs ', '|', '~', '[', ']']):
            logger.warning("⚠️ Call invalide - texte OCR non nettoyé")
            return False
    return True


async def process_photo_event(event) -> None:
    """Download photo, OCR it, parse calls, deduplicate, format, and forward."""
    try:
        buf = BytesIO()
        await event.download_media(file=buf)
        photo_bytes = buf.getvalue()
    except Exception as e:
        print(f"❌ Download photo error: {e}")
        return

    text = extract_text_from_image(photo_bytes)
    
    # LAYER 1: Visual logo detection
    visual_casinos = []
    if LOGO_DETECTION_ENABLED:
        try:
            visual_casinos = detect_casinos_in_image(photo_bytes)
            if visual_casinos:
                logger.info(f"🎯 LAYER 1 - Visual logos: {visual_casinos}")
        except Exception as e:
            logger.warning(f"Logo detection error: {e}")
    
    # LAYER 2: GPT-4o-mini Vision parsing
    gpt_calls = []
    if USE_GPT_VISION and OPENAI_AVAILABLE and OPENAI_API_KEY:
        try:
            # Si aucun logo détecté visuellement, dire à GPT d'utiliser OCR seulement
            logos_for_gpt = visual_casinos if visual_casinos else []
            gpt_calls = await parse_with_gpt_vision(photo_bytes, logos_for_gpt)
            if gpt_calls:
                logger.info(f"🧠 LAYER 2 - GPT Vision: {len(gpt_calls)} call(s)")
        except Exception as e:
            logger.error(f"GPT Vision error: {e}")
    
    # Fallback to simple color-based detection if no logos found
    if not visual_casinos and SIMPLE_DETECTION_ENABLED:
        try:
            detector = SimpleLogoDetector()
            visual_casinos = detector.detect_from_image(photo_bytes)
            if visual_casinos:
                logger.info(f"🎨 Simple color detection found: {visual_casinos}")
        except Exception as e:
            logger.warning(f"Simple detection error: {e}")
    
    # Debug: optionally dump OCR text to disk for analysis
    try:
        if os.getenv("OCR_DEBUG", "0") == "1":
            os.makedirs("ocr_dumps", exist_ok=True)
            ts = int(datetime.now().timestamp())
            chat = getattr(event, 'chat_id', 'unknown')
            mid = getattr(event, 'id', 'x')
            with open(f"ocr_dumps/ocr_{chat}_{mid}_{ts}.txt", "w", encoding="utf-8") as f:
                f.write(text)
    except Exception:
        pass
    # Log small snippet for quick inspection
    try:
        snippet = re.sub(r"\s+", " ", text)[:300]
        logger.info(f"OCR snippet: {snippet}")
    except Exception:
        pass
    if not text.strip():
        print("⚠️ OCR returned empty text")
        return

    calls = parse_calls_from_ocr(text, visual_casinos=visual_casinos)
    if not calls:
        print("⚠️ No calls parsed from OCR")
        return
    logger.info(f"📝 LAYER 3 - OCR: {len(calls)} call(s)")
    
    # Si GPT a renvoyé des calls, on NE TRAITE QUE GPT (évite bruit OCR)
    if gpt_calls:
        logger.info(f"✅ Using {len(gpt_calls)} GPT call(s); ignoring {len(calls)} OCR call(s)")
        calls = gpt_calls
    
    logger.info(f"📊 Total: {len(calls)} call(s) to process")

    local_hashes: set[str] = set()
    for call in calls:
        # 0) Clean selections aggressively to remove stakes/odds/garbage
        try:
            call['selection1'] = _clean_selection(call.get('selection1',''))
            call['selection2'] = _clean_selection(call.get('selection2',''))
        except Exception:
            pass

        # 1) Canonicalize bookmaker names against our catalog
        try:
            b1r = resolve_bookmaker(call.get('book1',''))
            b2r = resolve_bookmaker(call.get('book2',''))
            if b1r.get('found'):
                call['book1'] = b1r.get('name')
            if b2r.get('found'):
                call['book2'] = b2r.get('name')
        except Exception:
            pass

        # 2) Fix Unknown or likely misclassified books using visual logos (left->right order)
        try:
            trusted = set(["BET99", "iBet", "Betsson", "Coolbet"])
            if visual_casinos and len(visual_casinos) >= 2:
                vc1, vc2 = visual_casinos[0], visual_casinos[1]
                # If either side is Unknown OR is a suspicious label (Betway/Casumo), override with visual
                if call.get('book1') in (None, '', 'Unknown', 'Betway', 'Casumo'):
                    call['book1'] = vc1
                if call.get('book2') in (None, '', 'Unknown', 'Betway', 'Casumo'):
                    call['book2'] = vc2
            elif visual_casinos and len(visual_casinos) == 1:
                # If only one trusted casino detected visually and the other side is Betway/Casumo, keep trusted and don't force the other
                if call.get('book1') in ('Betway', 'Casumo') and visual_casinos[0] in trusted:
                    call['book1'] = visual_casinos[0]
                if call.get('book2') in ('Betway', 'Casumo') and visual_casinos[0] in trusted:
                    call['book2'] = visual_casinos[0]
        except Exception:
            pass

        # 3) If market is Team Total* and selection lacks team name, prefix team1
        try:
            mk = (call.get('market','') or '').lower()
            t1 = (call.get('team1','') or '').strip()
            t2 = (call.get('team2','') or '').strip()
            if 'team total' in mk:
                s1 = call.get('selection1','') or ''
                s2 = call.get('selection2','') or ''
                if t1 and (t1.lower() not in s1.lower()) and (not t2 or t2.lower() not in s1.lower()):
                    call['selection1'] = f"{t1} {s1}".strip()
                if t1 and (t1.lower() not in s2.lower()) and (not t2 or t2.lower() not in s2.lower()):
                    call['selection2'] = f"{t1} {s2}".strip()
        except Exception:
            pass

        # Strict validation before dedup/sending
        if not validate_call(call):
            continue

        # Validate bookmaker resolution if STRICT_BOOKS
        b1r = resolve_bookmaker(call.get('book1',''))
        b2r = resolve_bookmaker(call.get('book2',''))
        if STRICT_BOOKS and (not b1r.get('found') or not b2r.get('found')):
            logger.info(
                f"⏭️ Skipped call due to unresolved bookmaker(s): "
                f"book1='{call.get('book1','')}' found={b1r.get('found')} | "
                f"book2='{call.get('book2','')}' found={b2r.get('found')}"
            )
            continue

        h = generate_call_hash(call)
        # Per-photo dedup to avoid 2-6 repeats within same image
        if h in local_hashes:
            logger.info(f"⏭️ Skipped duplicate call in image ({h})")
            continue
        local_hashes.add(h)
        if not _mark_if_new(h):
            logger.info(f"⏭️ Skipped duplicate call ({h})")
            continue

        # Send formatted message to destination chat if configured
        try:
            if DESTINATION_CHAT_ID is not None:
                buttons = None
                row: list = []
                if b1r.get('url'):
                    row.append(Button.url(f"{b1r.get('emoji','🎰')} {b1r.get('name', call.get('book1',''))}", b1r['url']))
                if b2r.get('url'):
                    row.append(Button.url(f"{b2r.get('emoji','🎯')} {b2r.get('name', call.get('book2',''))}", b2r['url']))
                if row:
                    buttons = [row]
                msg_text = format_call(call)
                if RENDER_IMAGE_ALERTS:
                    buf = render_alert_image(call)
                    if buf:
                        await client.send_file(DESTINATION_CHAT_ID, buf, caption=msg_text, buttons=buttons, file_name="alert.png")
                    else:
                        await client.send_message(DESTINATION_CHAT_ID, msg_text, buttons=buttons)
                else:
                    await client.send_message(DESTINATION_CHAT_ID, msg_text, buttons=buttons)
        except Exception as e:
            logger.warning(f"Failed sending formatted message: {e}")

        # Also forward to Risk0 API as a structured drop
        try:
            try:
                pct = float(str(call.get('percentage','')).replace('%','').replace(',', '.').strip() or 0)
            except Exception:
                pct = 0.0
            event_id = f"ocr_{h[:10]}_{int(datetime.now().timestamp())}"
            b1r = resolve_bookmaker(call.get('book1',''))
            b2r = resolve_bookmaker(call.get('book2',''))
            drop = {
                "event_id": event_id,
                "arb_percentage": pct,
                "match": f"{call.get('team1','')} vs {call.get('team2','')}",
                "league": call.get('league',''),
                "market": call.get('market',''),
                "outcomes": [
                    {"casino": b1r.get('name', call.get('book1','')), "outcome": call.get('selection1',''), "odds": int(str(call.get('odds1','0')).replace('+','')) if str(call.get('odds1','')).lstrip('+-').isdigit() else 0},
                    {"casino": b2r.get('name', call.get('book2','')), "outcome": call.get('selection2',''), "odds": int(str(call.get('odds2','0')).replace('+','')) if str(call.get('odds2','')).lstrip('+-').isdigit() else 0},
                ],
                "raw_message": text,
            }
            await send_to_risk0_api(drop)
        except Exception as e:
            logger.warning(f"Failed forwarding drop to API: {e}")

async def send_to_risk0_api(data: dict):
    """
    Envoie les données à l'API Risk0_bot
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(RISK0_API_URL, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ Envoyé à Risk0_bot: {data['event_id']}")
                    return result
                else:
                    print(f"❌ Erreur API: {response.status}")
                    return None
    except Exception as e:
        print(f"❌ Erreur connexion API: {e}")
        return None


PROCESSED_MESSAGES = set()


@client.on(events.NewMessage)
async def handle_new_message(event):
    """
    Handler pour les nouveaux messages de Nonoriribot
    """
    message_text = event.message.message or ""
    # Deduplicate per-chat per-message
    try:
        dedup_key = f"{event.chat_id}:{event.id}"
    except Exception:
        dedup_key = None
    if dedup_key and dedup_key in PROCESSED_MESSAGES:
        return
    
    # Determine if this message is relevant
    try:
        sender = await event.get_sender()
        sender_username = (getattr(sender, "username", "") or "").lower()
    except Exception:
        sender_username = ""

    chat_ok = (SOURCE_CHAT_ID is not None and event.chat_id == SOURCE_CHAT_ID)
    user_ok = (SOURCE_BOT_USERNAME and sender_username == SOURCE_BOT_USERNAME.lower())
    text_ok = ("arbitrage alert" in message_text.lower())
    # Detect images early
    try:
        is_photo = bool(getattr(event.message, 'photo', None))
        is_img_doc = bool(getattr(event.message, 'document', None) and getattr(event.message.document, 'mime_type', '').startswith('image/'))
    except Exception:
        is_photo, is_img_doc = False, False

    # Skip messages from the destination chat to avoid re-parsing our own formatted messages
    try:
        if DESTINATION_CHAT_ID is not None and event.chat_id == DESTINATION_CHAT_ID:
            return
    except Exception:
        pass
    
    # Skip messages from Risk0_bot to avoid re-parsing formatted alerts it sends back
    try:
        if sender_username == "risk0_bot":
            return
    except Exception:
        pass

    if not (chat_ok or user_ok or text_ok or is_photo or is_img_doc):
        return

    print(f"\n📨 Nouveau message reçu (chat_id={event.chat_id}, from=@{sender_username})")
    print(f"{'='*60}")
    print(message_text[:200] + "..." if len(message_text) > 200 else message_text)
    print(f"{'='*60}")
    # If photo/image: OCR pipeline
    if is_photo or is_img_doc:
        await process_photo_event(event)
        if dedup_key:
            PROCESSED_MESSAGES.add(dedup_key)
        return

    # Parse le message texte
    parsed = parse_arbitrage_message(message_text)
    
    if parsed:
        print(f"✅ Message parsé:")
        print(f"   Arbitrage: {parsed['arb_percentage']}%")
        print(f"   Match: {parsed['match']}")
        print(f"   Outcomes: {len(parsed['outcomes'])}")
        
        # Envoyer à l'API Risk0_bot
        result = await send_to_risk0_api(parsed)
        
        if result:
            print(f"✅ Alert distribuée aux users!")
        else:
            print(f"❌ Échec distribution")
    else:
        print(f"⚠️ Message non parsé (pas une alerte d'arbitrage?)")

    if dedup_key:
        PROCESSED_MESSAGES.add(dedup_key)


async def main():
    """
    Main function
    """
    print("🚀 Bridge Nonoriribot → Risk0_bot")
    print("="*60)
    # Connect and handle two-step sign-in via .env code
    await client.connect()
    if not await client.is_user_authorized():
        # Send login code to Telegram app
        await client.send_code_request(PHONE)
        print("📨 Code envoyé sur Telegram. Ajoute TELEGRAM_LOGIN_CODE=<code> dans .env. J'attends ton code...")
        # Poll .env for code and 2FA for up to 3 minutes
        for _ in range(120):
            # Reload env to pick up new values
            load_dotenv(override=True)
            code = os.getenv("TELEGRAM_LOGIN_CODE")
            if not code:
                await asyncio.sleep(1.5)
                continue
            # Try to complete sign-in
            try:
                await client.sign_in(phone=PHONE, code=code)
            except SessionPasswordNeededError:
                # 2FA required; poll for password if not set
                twofa = os.getenv("TELEGRAM_2FA_PASSWORD")
                if not twofa:
                    print("🔐 2FA activé. Ajoute TELEGRAM_2FA_PASSWORD=<motdepasse> dans .env. J'attends...")
                    for _ in range(60):
                        load_dotenv(override=True)
                        twofa = os.getenv("TELEGRAM_2FA_PASSWORD")
                        if twofa:
                            try:
                                await client.sign_in(password=twofa)
                                break
                            except Exception as e:
                                print(f"❌ Erreur 2FA: {e}")
                                return
                        await asyncio.sleep(1.5)
                    if not await client.is_user_authorized():
                        print("❌ 2FA manquant ou incorrect.")
                        return
                else:
                    await client.sign_in(password=twofa)
            except (PhoneCodeInvalidError, PhoneCodeExpiredError):
                print("❌ Code invalide/expiré. Un nouveau code vient d'être envoyé. Mets le nouveau code dans .env.")
                await client.send_code_request(PHONE)
                await asyncio.sleep(2)
                continue
            except Exception as e:
                print(f"❌ Erreur d'authentification: {e}")
                return
            # Authorized
            break
        if not await client.is_user_authorized():
            print("❌ Auth échouée: code non fourni à temps.")
            return
        print("✅ Authentification réussie.")
    
    me = await client.get_me()
    print(f"✅ Connecté en tant que: {me}")
    print(f"👂 Écoute les messages de: {SOURCE_BOT_USERNAME}")
    print(f"🔗 API Risk0_bot: {RISK0_API_URL}")
    print("="*60)
    print("\n⏳ En attente de messages...\n")
    
    # Keep running
    await client.run_until_disconnected()


if __name__ == "__main__":
    # Vérifier les credentials
    if not API_ID or not API_HASH or not PHONE:
        print("❌ ERREUR: Variables d'environnement manquantes!")
        print("\nIl te faut:")
        print("1. TELEGRAM_API_ID")
        print("2. TELEGRAM_API_HASH") 
        print("3. TELEGRAM_PHONE")
        print("\nObtiens API_ID et API_HASH sur: https://my.telegram.org")
        exit(1)
    
    asyncio.run(main())
