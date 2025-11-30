#!/usr/bin/env python3
"""
Bridge Telegram avec système 3 couches anti-erreur
Architecture: Logo Detection (OpenCV) → GPT-4o-mini Vision → OCR Validation + SQLite Dedup
"""

import os
import io
import sys
import atexit
import signal
import re
import json
import base64
import hashlib
import sqlite3
import logging
from datetime import datetime
from difflib import SequenceMatcher
from typing import List, Dict, Tuple, Optional

try:
    import cv2
    CV2_AVAILABLE = True
except Exception:
    CV2_AVAILABLE = False
import numpy as np
import openai
import pytesseract
from PIL import Image
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# Configuration
load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
SOURCE_GROUP_ID = int(os.getenv('SOURCE_GROUP_ID', '0'))
DESTINATION_GROUP_ID = int(os.getenv('DESTINATION_GROUP_ID', '0'))

openai.api_key = OPENAI_API_KEY

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

DB_FILE = 'calls_history.db'
MIN_ARBITRAGE_PERCENTAGE = 2.0
LOGO_MATCH_THRESHOLD = 0.7
SIMILARITY_THRESHOLD = 0.9
LOCK_FILE = '.bridge_hybrid.lock'

# Load casinos DB
try:
    with open('casino_logos.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        CASINOS_DB = data.get('casinos', [])
except FileNotFoundError:
    with open('casinos.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        CASINOS_DB = data.get('casinos', [])

CASINO_LOOKUP = {}
for casino in CASINOS_DB:
    name = casino.get('name', '')
    CASINO_LOOKUP[name.lower()] = casino
    for alias in casino.get('aliases', []):
        CASINO_LOOKUP[alias.lower()] = casino

logging.info(f"✅ Loaded {len(CASINOS_DB)} casinos")


def init_database():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS sent_calls (
            hash TEXT PRIMARY KEY,
            match_teams TEXT,
            market TEXT,
            percentage TEXT,
            bookmakers TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    logging.info(f"✅ Database initialized: {DB_FILE}")


init_database()

# Load logo templates
LOGO_TEMPLATES = {}
logo_dir = 'logos'
if CV2_AVAILABLE:
    if os.path.exists(logo_dir):
        for casino in CASINOS_DB:
            logo_file = casino.get('logo_file', '')
            if logo_file:
                logo_path = os.path.join(logo_dir, logo_file)
                if os.path.exists(logo_path):
                    LOGO_TEMPLATES[casino['name']] = cv2.imread(logo_path)
    logging.info(f"✅ Loaded {len(LOGO_TEMPLATES)} logo templates")
else:
    logging.warning("⚠️ OpenCV non disponible - couche logos désactivée (pip install opencv-python-headless)")


def detect_bookmaker_logos(photo_bytes: bytes) -> List[Dict]:
    detected = []
    try:
        if not CV2_AVAILABLE:
            return []
        nparr = np.frombuffer(photo_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        for casino_name, template in LOGO_TEMPLATES.items():
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            best_match = 0.0
            
            for scale in [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]:
                h, w = template_gray.shape
                new_h, new_w = int(h * scale), int(w * scale)
                
                if new_h > img_gray.shape[0] or new_w > img_gray.shape[1]:
                    continue
                
                resized = cv2.resize(template_gray, (new_w, new_h))
                result = cv2.matchTemplate(img_gray, resized, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(result)
                
                if max_val > best_match:
                    best_match = max_val
            
            if best_match > LOGO_MATCH_THRESHOLD:
                casino_info = next((c for c in CASINOS_DB if c['name'] == casino_name), None)
                if casino_info:
                    detected.append({
                        'name': casino_name,
                        'emoji': casino_info.get('emoji', '🎰'),
                        'confidence': best_match
                    })
        
        unique = {}
        for d in detected:
            if d['name'] not in unique or d['confidence'] > unique[d['name']]['confidence']:
                unique[d['name']] = d
        
        result = sorted(unique.values(), key=lambda x: x['confidence'], reverse=True)
        logging.info(f"🎯 Detected {len(result)} logo(s): {[l['name'] for l in result]}")
        return result
    except Exception as e:
        logging.error(f"❌ Logo detection failed: {e}")
        return []


def build_gpt_prompt(detected_logos: List[Dict]) -> str:
    bookmakers_guide = "\n".join([
        f"- {logo['name']} {logo['emoji']} (confiance: {logo['confidence']:.0%})"
        for logo in detected_logos
    ]) if detected_logos else "Aucun logo détecté - utilise ta vision"
    
    return f"""Tu es un expert en extraction de données d'arbitrage sportif.

**LOGOS DÉTECTÉS:** 
{bookmakers_guide}

**MISSION:** Analyse VISUELLEMENT cette image et extrait TOUS les calls d'arbitrage.

**RÈGLES CRITIQUES:**
1. Compte TOUS les blocs avec pourcentages (XX.XX%)
2. Chaque call a EXACTEMENT 2 outcomes (2 bookmakers différents)
3. Vérifie visuellement les logos et confirme avec la liste ci-dessus
4. Nettoie le texte OCR (ignore "SITE", "GAME", boutons UI)
5. Si logo détecté mais nom mal écrit, corrige avec la liste

**FORMAT JSON:**
{{
  "total_calls_detected": 3,
  "calls": [
    {{
      "percentage": "11.79%",
      "profit": "$25.75",
      "sport": "Soccer",
      "league": "Spain - La Liga",
      "team1": "Villarreal CF",
      "team2": "Real Club Deportivo Mallorca",
      "market": "Team Total Corners",
      "time": "Tomorrow, 3:00PM",
      "outcomes": [
        {{
          "bookmaker": "iBet",
          "emoji": "🧱",
          "selection": "Mallorca Over 3",
          "odds": "+145",
          "stake": "$90"
        }},
        {{
          "bookmaker": "Coolbet",
          "emoji": "❄️",
          "selection": "Mallorca Under 3",
          "odds": "+111",
          "stake": "$100"
        }}
      ]
    }}
  ]
}}

Retourne UNIQUEMENT le JSON, rien d'autre."""


async def parse_with_gpt_vision(photo_bytes: bytes, detected_logos: List[Dict]) -> Dict:
    try:
        base64_image = base64.b64encode(photo_bytes).decode('utf-8')
        prompt = build_gpt_prompt(detected_logos)
        
        # Use new OpenAI client API (v1.x)
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                            "detail": "high"
                        }
                    }
                ]
            }],
            max_tokens=3000,
            temperature=0
        )
        
        content = response.choices[0].message.content
        
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        result = json.loads(content.strip())
        logging.info(f"🧠 GPT: {result.get('total_calls_detected', 0)} call(s) claimed, {len(result.get('calls', []))} returned")
        return result
    except Exception as e:
        logging.error(f"❌ GPT vision failed: {e}")
        return {"total_calls_detected": 0, "calls": []}


def extract_text_ocr(photo_bytes: bytes) -> str:
    try:
        image = Image.open(io.BytesIO(photo_bytes))
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        logging.error(f"❌ OCR failed: {e}")
        return ""


def cross_validate_with_ocr(gpt_result: Dict, ocr_text: str) -> Tuple[bool, List[str]]:
    warnings = []
    ocr_percentages = re.findall(r'\d+\.\d+%', ocr_text)
    ocr_call_count = len(set(ocr_percentages))
    
    gpt_claimed = gpt_result.get('total_calls_detected', len(gpt_result['calls']))
    gpt_actual = len(gpt_result['calls'])
    
    if gpt_claimed != gpt_actual:
        warnings.append(f"⚠️ GPT mismatch: claims {gpt_claimed}, returns {gpt_actual}")
    
    if ocr_call_count > gpt_actual:
        warnings.append(f"🚨 OCR sees {ocr_call_count} calls but GPT returns {gpt_actual}")
        return False, warnings
    
    for i, call in enumerate(gpt_result['calls']):
        if len(call.get('outcomes', [])) != 2:
            warnings.append(f"⚠️ Call {i+1} has {len(call['outcomes'])} outcomes (expected 2)")
            return False, warnings
    
    if warnings:
        for w in warnings:
            logging.warning(w)
    
    return True, warnings


def generate_robust_hash(call: Dict) -> str:
    team1 = re.sub(r'\s+', ' ', call['team1'].lower().strip())
    team2 = re.sub(r'\s+', ' ', call['team2'].lower().strip())
    teams = tuple(sorted([team1, team2]))
    market = call['market'].lower().strip()
    outcomes = sorted([
        f"{o['bookmaker'].lower()}:{o['odds']}:{o['stake']}"
        for o in call['outcomes']
    ])
    unique_string = f"{teams[0]}|{teams[1]}|{market}|{'|'.join(outcomes)}"
    return hashlib.md5(unique_string.encode()).hexdigest()


def check_similarity_in_db(call: Dict) -> Tuple[bool, Optional[str]]:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute('''
            SELECT hash, match_teams, market, percentage
            FROM sent_calls
            WHERE match_teams LIKE ?
            AND timestamp > datetime('now', '-2 hours')
            LIMIT 20
        ''', (f"%{call['team1'][:20]}%",))
        
        recent = c.fetchall()
        for stored_hash, stored_teams, stored_market, stored_pct in recent:
            team_sim = SequenceMatcher(None, f"{call['team1']} {call['team2']}".lower(), stored_teams.lower()).ratio()
            market_sim = SequenceMatcher(None, call['market'].lower(), stored_market.lower()).ratio()
            
            if team_sim > SIMILARITY_THRESHOLD and market_sim > SIMILARITY_THRESHOLD:
                try:
                    current_pct = float(call['percentage'].replace('%', ''))
                    stored_pct_val = float(stored_pct.replace('%', ''))
                    if abs(current_pct - stored_pct_val) < 0.5:
                        return True, stored_hash
                except:
                    pass
        return False, None
    finally:
        conn.close()


def save_call_to_db(call: Dict, call_hash: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        bookmakers = ",".join([o['bookmaker'] for o in call['outcomes']])
        match_teams = f"{call['team1']} vs {call['team2']}"
        c.execute('''
            INSERT OR REPLACE INTO sent_calls
            (hash, match_teams, market, percentage, bookmakers)
            VALUES (?, ?, ?, ?, ?)
        ''', (call_hash, match_teams, call['market'], call['percentage'], bookmakers))
        conn.commit()
    finally:
        conn.close()


def validate_call(call: Dict) -> bool:
    required = ['percentage', 'team1', 'team2', 'market', 'outcomes']
    for field in required:
        if not call.get(field):
            logging.warning(f"⚠️ Missing: {field}")
            return False
    
    if len(call['outcomes']) != 2:
        return False
    
    b1 = call['outcomes'][0]['bookmaker']
    b2 = call['outcomes'][1]['bookmaker']
    if b1 == b2:
        logging.warning(f"⚠️ Same bookmaker twice: {b1}")
        return False
    
    try:
        pct = float(call['percentage'].replace('%', ''))
        if pct < MIN_ARBITRAGE_PERCENTAGE:
            logging.info(f"⏭️ Low %: {pct}%")
            return False
    except:
        pass
    
    noise = ['wy)', 'rs ', '~"', 'fe}', '|']
    for outcome in call['outcomes']:
        sel = outcome.get('selection', '')
        if any(n in sel for n in noise):
            logging.warning(f"⚠️ OCR noise: {sel}")
            return False
    
    return True


def calculate_returns(stake: str, odds: str) -> float:
    try:
        stake_val = float(stake.replace('$', ''))
        odds_val = int(odds)
        if odds_val > 0:
            return stake_val * (1 + odds_val/100)
        else:
            return stake_val * (1 + 100/abs(odds_val))
    except:
        return 0.0


def format_call_output(call: Dict) -> str:
    o1, o2 = call['outcomes'][0], call['outcomes'][1]
    stake1 = float(o1['stake'].replace('$', ''))
    stake2 = float(o2['stake'].replace('$', ''))
    total = stake1 + stake2
    return1 = calculate_returns(o1['stake'], o1['odds'])
    return2 = calculate_returns(o2['stake'], o2['odds'])
    
    return f"""🚨 ARBITRAGE ALERT - {call['percentage']} 🚨

🏟️ {call['team1']} vs {call['team2']}
⚽ {call.get('league', call.get('sport', ''))} - {call['market']}
🕐 {call.get('time', 'TBD')}
💰 CASH: ${total:.1f} ✅ Profit: {call.get('profit', 'TBD')}

{o1['emoji']} [{o1['bookmaker']}] {o1['selection']} @ {o1['odds']}
💵 Stake: {o1['stake']} → Return: ${return1:.2f}

{o2['emoji']} [{o2['bookmaker']}] {o2['selection']} @ {o2['odds']}
💵 Stake: {o2['stake']} → Return: ${return2:.2f}"""


def _ensure_single_instance():
    """Prevent running multiple local instances (best-effort)."""
    try:
        if os.path.exists(LOCK_FILE):
            try:
                with open(LOCK_FILE, 'r') as f:
                    pid_str = f.read().strip()
                pid = int(pid_str) if pid_str.isdigit() else None
            except Exception:
                pid = None
            # Check if process still exists
            if pid:
                try:
                    os.kill(pid, 0)
                    logging.error(f"⚠️ Another local instance appears to be running (pid={pid}). Exiting.")
                    sys.exit(1)
                except ProcessLookupError:
                    # Stale lock
                    pass
            try:
                os.remove(LOCK_FILE)
            except Exception:
                pass
        with open(LOCK_FILE, 'w') as f:
            f.write(str(os.getpid()))
        def _cleanup():
            try:
                if os.path.exists(LOCK_FILE):
                    os.remove(LOCK_FILE)
            except Exception:
                pass
        atexit.register(_cleanup)
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, lambda *_: sys.exit(0))
    except Exception:
        # Non-fatal
        pass


async def _error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    err = getattr(context, 'error', None)
    logging.error(f"❌ Error in handler: {err}")
    if err and 'Conflict: terminated by other getUpdates request' in str(err):
        logging.error("🔒 Another bot instance is polling with this token. Stop other instance or rotate token.")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Accept photos from SOURCE_GROUP_ID OR from Nonoriribot (username: nonoriribot)
    chat_id = update.message.chat_id
    sender = update.message.from_user
    sender_username = sender.username.lower() if sender and sender.username else ""
    
    # Log for debugging
    logging.info(f"📸 Photo reçue de chat_id={chat_id}, user=@{sender_username}")
    
    # Accept if from configured source group OR from nonoriribot
    if chat_id != SOURCE_GROUP_ID and sender_username != "nonoriribot":
        logging.info(f"⏭️ Ignored - not from source group ({SOURCE_GROUP_ID}) or nonoriribot")
        return
    
    logging.info(f"\n{'='*60}\n📸 Processing screenshot from @{sender_username}\n{'='*60}")
    
    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        photo_bytes = await file.download_as_bytearray()
        photo_bytes = bytes(photo_bytes)
        
        # LAYER 1: Logo detection
        detected_logos = detect_bookmaker_logos(photo_bytes)
        
        # LAYER 2: GPT Vision
        gpt_result = await parse_with_gpt_vision(photo_bytes, detected_logos)
        if not gpt_result.get('calls'):
            logging.error("❌ No calls from GPT")
            return
        
        # LAYER 3: OCR validation
        ocr_text = extract_text_ocr(photo_bytes)
        valid, warnings = cross_validate_with_ocr(gpt_result, ocr_text)
        if not valid:
            logging.error("❌ Cross-validation failed")
            return
        
        # Send
        sent = 0
        skipped = 0
        for i, call in enumerate(gpt_result['calls'], 1):
            logging.info(f"\n--- Call {i}/{len(gpt_result['calls'])} ---")
            
            if not validate_call(call):
                skipped += 1
                continue
            
            call_hash = generate_robust_hash(call)
            is_similar, _ = check_similarity_in_db(call)
            if is_similar:
                logging.info(f"⏭️ Similar call exists")
                skipped += 1
                continue
            
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('SELECT hash FROM sent_calls WHERE hash = ?', (call_hash,))
            exists = c.fetchone()
            conn.close()
            
            if exists:
                logging.info(f"⏭️ Duplicate hash")
                skipped += 1
                continue
            
            formatted = format_call_output(call)
            await context.bot.send_message(chat_id=DESTINATION_GROUP_ID, text=formatted)
            save_call_to_db(call, call_hash)
            sent += 1
            logging.info(f"✅ Sent: {call['percentage']} - {call['team1']} vs {call['team2']}")
        
        logging.info(f"\n{'='*60}\n📊 {sent} sent, {skipped} skipped\n{'='*60}\n")
    
    except Exception as e:
        logging.error(f"❌ Handler failed: {e}", exc_info=True)


def main():
    logging.info("="*60)
    logging.info("🚀 Bridge Hybrid - 3 Layer System")
    logging.info("="*60)
    logging.info(f"📱 Source: {SOURCE_GROUP_ID}")
    logging.info(f"📤 Destination: {DESTINATION_GROUP_ID}")
    logging.info(f"🎯 Min %: {MIN_ARBITRAGE_PERCENTAGE}%")
    logging.info(f"🏢 Casinos: {len(CASINOS_DB)}")
    logging.info(f"🖼️ Logos: {len(LOGO_TEMPLATES)}")
    logging.info("="*60)
    
    _ensure_single_instance()
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_error_handler(_error_handler)
    # Accept ALL photos, filtering happens inside handle_photo
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    logging.info("✅ Bot ready")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
