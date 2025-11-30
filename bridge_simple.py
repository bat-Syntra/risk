#!/usr/bin/env python3
from __future__ import annotations
"""
Bridge Telegram - GPT Vision Pur (SIMPLIFIÉ)
Pas d'OCR, pas de détection logos - juste GPT qui voit l'image directement
"""

import os
import json
import base64
import hashlib
import sqlite3
import logging
import re
from datetime import datetime
from typing import Dict, List
from io import BytesIO
try:
    from PIL import Image
except Exception:
    Image = None

import openai
import httpx
from dotenv import load_dotenv

# Config - LOAD ENV FIRST before importing local modules!
load_dotenv()

from core.parser import parse_arbitrage_alert
from telethon import TelegramClient, events, Button
from telethon.errors import SessionPasswordNeededError
API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
PHONE = os.getenv("TELEGRAM_PHONE", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
SOURCE_BOT_USERNAME = os.getenv("SOURCE_BOT_USERNAME", "Nonoriribot")
DESTINATION_CHAT_ID_ENV = os.getenv("DESTINATION_CHAT_ID", "").strip()
DESTINATION_CHAT_ID = int(DESTINATION_CHAT_ID_ENV) if DESTINATION_CHAT_ID_ENV.lstrip("-").isdigit() else None
RISK0_API_URL = os.getenv("RISK0_API_URL", "http://localhost:8000")
BRIDGE_ALLOW_DUPLICATE_SEND = os.getenv("BRIDGE_ALLOW_DUPLICATE_SEND", "0").strip() in ("1", "true", "True")
try:
    BRIDGE_DEDUP_WINDOW_MINUTES = int(os.getenv("BRIDGE_DEDUP_WINDOW_MINUTES", "0") or 0)
except Exception:
    BRIDGE_DEDUP_WINDOW_MINUTES = 0
STRICT_BOOKS = os.getenv("STRICT_BOOKS", "1").strip() in ("1", "true", "True")
STRICT_TEAMS = os.getenv("STRICT_TEAMS", "1").strip() in ("1", "true", "True")
VERIFY_LOGOS = os.getenv("VERIFY_LOGOS", "1").strip() in ("1", "true", "True")

# Initialize Telethon client
client = TelegramClient('bridge_simple_session', API_ID, API_HASH)

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Database
DB_FILE = 'calls_simple.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sent_calls 
                 (hash TEXT PRIMARY KEY, 
                  teams TEXT, 
                  market TEXT, 
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# ============================================================
# CHARGEMENT CASINOS + PROMPT DYNAMIQUE
# ============================================================

# Charger casino_logos.json
LOGO_DIR = "logos"
def load_casinos():
    try:
        fname = "casino_logos.json"
        if not os.path.exists(fname) and os.path.exists("casinos.json"):
            fname = "casinos.json"
        with open(fname, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Set global logo directory
            global LOGO_DIR
            LOGO_DIR = data.get('logo_directory', LOGO_DIR).rstrip('/')
            return data.get('casinos', [])
    except Exception as e:
        logger.error(f"Failed to load casinos JSON: {e}")
        return []

CASINOS_DATA = load_casinos()

# Build a set of known bookmaker names/aliases for safer logo verification
KNOWN_BOOKMAKERS = set()
for c in CASINOS_DATA:
    try:
        nm = str(c.get('name') or '').strip().lower()
        if nm:
            KNOWN_BOOKMAKERS.add(nm)
        for alias in c.get('aliases') or []:
            alias_norm = str(alias or '').strip().lower()
            if alias_norm:
                KNOWN_BOOKMAKERS.add(alias_norm)
    except Exception:
        continue

# Créer la liste des bookmakers pour le prompt
def build_bookmakers_guide():
    """Génère la section bookmakers du prompt depuis le JSON"""
    if not CASINOS_DATA:
        return "- iBet 🧱\n- Coolbet ❄️\n- Betsson 🔶\n- bet365 📗"
    
    lines = []
    for casino in CASINOS_DATA:
        name = casino.get('name', '')
        emoji = casino.get('emoji', '🎰')
        colors = casino.get('colors', [])
        aliases = casino.get('aliases', [])
        
        # Exemple: - Logo "iBet" (noir/rouge) → "iBet" 🧱 (aussi: ibet, i bet)
        colors_str = "/".join(colors[:2]) if colors else "multi"
        aliases_str = f" (aussi: {', '.join(aliases[:3])})" if aliases else ""
        
        lines.append(f"- {emoji} Logo \"{name}\" ({colors_str}) → \"{name}\" {emoji}{aliases_str}")
    
    return "\n".join(lines)

BOOKMAKERS_GUIDE = build_bookmakers_guide()

# Pré-calcul des empreintes de logos (perceptual hash)
def _avg_hash(img: Image.Image, hash_size: int = 16) -> int:
    try:
        g = img.convert('L').resize((hash_size, hash_size))
        pixels = list(g.getdata())
        avg = sum(pixels) / float(len(pixels) or 1)
        bits = 0
        for i, px in enumerate(pixels):
            if px > avg:
                bits |= (1 << i)
        return bits
    except Exception:
        return 0

def _hamming(a: int, b: int) -> int:
    return bin((a or 0) ^ (b or 0)).count('1')

LOGO_HASHES: Dict[str, int] = {}
if Image is None:
    logger.warning("PIL not available — logo verification disabled")
else:
    for c in CASINOS_DATA:
        try:
            name = str(c.get('name'))
            file = str(c.get('logo_file') or '')
            if not name or not file:
                continue
            path = os.path.join(LOGO_DIR, file)
            if not os.path.exists(path):
                continue
            with Image.open(path) as im:
                LOGO_HASHES[name] = _avg_hash(im)
        except Exception:
            continue

# Max Hamming distance (on 16x16 hash) to trust a logo-based correction.
# 256 bits total -> a very low threshold means we only override GPT when
# the logo hash is an extremely strong match.
LOGO_MAX_HAMMING = 32

# Prompt GPT avec liste complète des bookmakers
GPT_PROMPT = f"""Tu es un expert en extraction visuelle de données d'arbitrage sportif.

🎯 **TA MISSION:** REGARDE VISUELLEMENT cette image et extrait TOUS les calls d'arbitrage.

⚠️⚠️⚠️ CRITIQUE - NE PAS EXTRAIRE LES MONTANTS ⚠️⚠️⚠️
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Tu vois des montants $ dans l'image ($699, $270, etc.) 
→ **IGNORE-LES COMPLÈTEMENT!**

❌ NE mets PAS: "stake", "cash", "profit", "return"
✅ Extrais SEULEMENT: odds (cotes comme +285, -200)

On calculera les montants selon le budget de chaque utilisateur.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ **RÈGLES CRITIQUES - LIS ÇA ATTENTIVEMENT:**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. ÉQUIPES (ULTRA-IMPORTANT!)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Il y a TOUJOURS 2 équipes DIFFÉRENTES dans un match:
- Exemple: "CR Flamengo vs Red Bull Bragantino"
  → team1 = "CR Flamengo"
  → team2 = "Red Bull Bragantino"

❌ JAMAIS: "Red Bull Bragantino vs Red Bull Bragantino"
✅ TOUJOURS: 2 noms DIFFÉRENTS

**COMMENT TROUVER:**
1. REGARDE en haut du bloc de call
2. Tu verras: "[Équipe A] vs [Équipe B]"
3. Copie EXACTEMENT ces 2 noms différents
4. NE les confonds PAS avec les sélections (Over/Under)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2. SÉLECTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

La sélection peut être:
- Basée ÉQUIPE (ex: "Red Bull Bragantino Over 4")
- Basée JOUEUR (ex: "Calvin Austin III Over 1.5")

Tu dois copier EXACTEMENT le texte de la sélection pour chaque côté.
Ne rejette PAS un call juste parce que la sélection mentionne un joueur.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3. BOOKMAKERS - LISTE COMPLÈTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REGARDE VISUELLEMENT les LOGOS dans l'image et identifie:

{BOOKMAKERS_GUIDE}

**IMPORTANT (CHOIX CONTRAINT):**
- Tu DOIS choisir le bookmaker UNIQUEMENT parmi la liste ci-dessus.
- Ne crée PAS de nouveaux noms. Si incertain, regarde encore l'image.
- Le logo carré avec juste la lettre « P » correspond à « Pinnacle ».
- Le carré rouge « ibet » correspond à « iBet ».
- Le rectangle orange correspond à « Betsson ».
- La tête de lion correspond à « LeoVegas ».
- NE devine PAS, base-toi sur ce que tu VOIS.

🧠 Délimitation visuelle du bloc: Ignore TOTALEMENT la barre d'état/record en haut (icônes batterie, wifi, point rouge REC, horloge). Ne prends PAS ces icônes comme des bookmakers.
Ne prends en compte que les DEUX cases/logo à l'intérieur du bloc d'appel (colonnes gauche/droite au centre du bloc).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
4. LEAGUE (OBLIGATOIRE!)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REGARDE sous le pourcentage, tu verras:

Soccer • Brazil - Serie A → league: "Brazil - Serie A"
Soccer • Italy - Serie A → league: "Italy - Serie A"
Soccer • Argentina - Primera → league: "Argentina - Primera Division"

**NE mets PAS juste "Soccer" ou le sport!**
Inclus TOUJOURS le pays/compétition.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
5. DATE/HEURE DU MATCH (OBLIGATOIRE!)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REGARDE en HAUT À DROITE de chaque call, tu verras la date:

**Exemples visuels:**
- "Tomorrow, 9:30AM" → time: "Tomorrow, 9:30AM"
- "Tomorrow, 6:00PM" → time: "Tomorrow, 6:00PM"
- "Today, 8:00PM" → time: "Today, 8:00PM"
- "Mon, 10:00PM" → time: "Mon, 10:00PM"

**C'est TOUJOURS affiché en haut à droite du bloc!**
Copie EXACTEMENT le texte que tu vois.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
6. STRUCTURE VISUELLE D'UN CALL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Chaque call d'arbitrage a cette structure:

┌────────────────────────────────────────┐
│ 8.69%  ~$90.58   Tomorrow, 7:30PM     │ ← Pourcentage, profit, temps
│ Soccer • Brazil - Serie A             │ ← Sport et LEAGUE
│ CR Flamengo vs Red Bull Bragantino    │ ← LES 2 ÉQUIPES (différentes!)
│ Team Total Corners                    │ ← Type de marché
├──────────────────┬────────────────────┤
│ [Logo Coolbet]   │ [Logo iBet]        │ ← LOGOS des bookmakers
│ Over 4           │ Under 4            │ ← Sélections
│ $240  +330       │ $699  -213         │ ← Stakes et cotes
└──────────────────┴────────────────────┘

**Compte les calls:** Une image peut avoir 1, 2, 3 ou plus de calls!
Chaque bloc avec un % = 1 call.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
7. MULTI-BLOCS AVEC BOOKMAKERS DIFFÉRENTS (OBLIGATOIRE!)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Il peut y avoir PLUSIEURS BLOCS pour le MÊME match, la MÊME league et la MÊME heure, 
mais avec des COMBINAISONS DE BOOKMAKERS DIFFÉRENTES (ex: Coolbet+iBet puis Coolbet+Betsson).

✅ TU DOIS RENVOYER 1 call PAR BLOC, SANS FUSIONNER.
❌ NE PAS dédupliquer si les bookmakers ne sont pas exactement les mêmes.

 Exemple attendu (même match/time mais 2 calls séparés):
 - Call A: outcomes = [{{"bookmaker": "Coolbet", ...}}, {{"bookmaker": "iBet", ...}}]
 - Call B: outcomes = [{{"bookmaker": "Coolbet", ...}}, {{"bookmaker": "Betsson", ...}}]

Ces 2 calls sont DISTINCTS et doivent tous les deux apparaître dans "calls".

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
8. COMPTE EXACT DES BLOCS (OBLIGATOIRE!)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Compte TOUS les pourcentages verts (ex: "6.50%") visibles.
- Le nombre d'éléments dans "calls" DOIT être EXACTEMENT égal au nombre de ces pourcentages.
- Si tu vois 3 blocs identiques sauf les bookmakers, tu dois renvoyer 3 calls.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 FORMAT JSON REQUIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```json
{{
  "blocks_count": 2,
  "calls": [
    {{
      "percentage": "8.69%",
      "profit": "$90.58",
      "sport": "Soccer",
      "league": "Brazil - Serie A",
      "team1": "CR Flamengo",
      "team2": "Red Bull Bragantino",
      "market": "Team Total Corners",
      "time": "Tomorrow, 7:30PM",
      "outcomes": [
        {{
          "bookmaker": "Coolbet",
          "emoji": "❄️",
          "bbox": {{"x": 0.12, "y": 0.55, "w": 0.12, "h": 0.08}},
          "selection": "Red Bull Bragantino Over 4",
          "odds": "+330"
        }},
        {{
          "bookmaker": "iBet",
          "emoji": "🧱",
          "bbox": {{"x": 0.68, "y": 0.55, "w": 0.12, "h": 0.08}},
          "selection": "Red Bull Bragantino Under 4",
          "odds": "-213"
        }}
      ]
    }}
  ]
}}
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ VALIDATION AVANT ENVOI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Avant de retourner le JSON, VÉRIFIE ces 6 points:

✅ team1 ≠ team2 (JAMAIS la même équipe 2 fois!)
✅ league contient pays/compétition (pas juste "Soccer")
✅ Chaque call a EXACTEMENT 2 outcomes
✅ outcomes[0].bookmaker ≠ outcomes[1].bookmaker (bookmakers différents)
✅ Les emojis correspondent aux bookmakers (vérifie la liste)
✅ Les sélections mentionnent une équipe OU un joueur

Si UN SEUL de ces points ne passe pas, REGARDE L'IMAGE ENCORE!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RAPPEL FINAL:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- REGARDE l'image VISUELLEMENT, ne devine pas
- Les 2 équipes sont TOUJOURS différentes
- Utilise les NOMS EXACTS et EMOJIS de la liste bookmakers
- Inclus TOUJOURS la league complète

OUTPUT: JSON uniquement, aucun texte avant ou après."""


# ============================================================
# PARSING GPT VISION PUR
# ============================================================

def _verify_and_correct_books(calls: List[Dict], photo_bytes: bytes) -> None:
    if not (VERIFY_LOGOS and Image and LOGO_HASHES):
        return
    try:
        with Image.open(BytesIO(photo_bytes)) as full:
            W, H = full.size
            for call in calls:
                outs = call.get('outcomes') or []
                for o in outs:
                    bbox = o.get('bbox') or {}
                    try:
                        x = float(bbox.get('x', 0))
                        y = float(bbox.get('y', 0))
                        w = float(bbox.get('w', 0))
                        h = float(bbox.get('h', 0))
                    except Exception:
                        x = y = w = h = 0.0
                    if w <= 0 or h <= 0:
                        continue
                    # Normalize: if values > 1, assume absolute px
                    if x <= 1 and y <= 1 and w <= 1 and h <= 1:
                        left = int(max(0, x) * W)
                        top = int(max(0, y) * H)
                        right = int(min(1, x + w) * W)
                        bottom = int(min(1, y + h) * H)
                    else:
                        left = int(max(0, x))
                        top = int(max(0, y))
                        right = int(min(W, x + w))
                        bottom = int(min(H, y + h))
                    if right - left < 8 or bottom - top < 8:
                        continue
                    try:
                        crop = full.crop((left, top, right, bottom))
                        ch = _avg_hash(crop)
                        # Find best logo match
                        best_name = None
                        best_dist = 1e9
                        for nm, lh in LOGO_HASHES.items():
                            d = _hamming(ch, lh)
                            if d < best_dist:
                                best_dist = d
                                best_name = nm
                        if not best_name:
                            continue

                        raw = o.get('bookmaker', '')
                        raw_norm = str(raw or '').strip().lower()
                        best_norm = str(best_name or '').strip().lower()

                        # If the logo hash is too far, ignore this match entirely
                        if best_dist > LOGO_MAX_HAMMING:
                            try:
                                logger.debug(f"🖼️ Logo verify: ignoring weak match '{raw}' -> '{best_name}' (d={best_dist})")
                            except Exception:
                                pass
                            continue

                        # If GPT already produced a known bookmaker/alias, prefer GPT over logo
                        if raw_norm and raw_norm in KNOWN_BOOKMAKERS and raw_norm != best_norm:
                            try:
                                logger.info(f"🖼️ Logo verify: keeping GPT bookmaker '{raw}' over '{best_name}' (d={best_dist})")
                            except Exception:
                                pass
                            continue

                        # Otherwise, apply the correction
                        if raw_norm != best_norm:
                            try:
                                logger.info(f"🖼️ Logo verify: correcting '{raw}' -> '{best_name}' (d={best_dist})")
                            except Exception:
                                pass
                            o['bookmaker'] = best_name
                    except Exception as _e:
                        continue
    except Exception:
        pass

async def parse_screenshot(photo_bytes: bytes) -> List[Dict]:
    """Parse avec GPT Vision pur - pas d'OCR"""
    try:
        base64_image = base64.b64encode(photo_bytes).decode('utf-8')
        
        client_openai = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client_openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": GPT_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                            "detail": "high"
                        }
                    }
                ]
            }],
            max_tokens=4096,
            temperature=0
        )
        
        content = response.choices[0].message.content
        
        # Extract JSON from markdown blocks if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        result = json.loads(content.strip())
        calls = result.get('calls', [])
        bc = result.get('blocks_count')
        if isinstance(bc, int) and bc > len(calls):
            logger.warning(f"⚠️ blocks_count mismatch: expected {bc}, got {len(calls)} — retrying strict parse")
            # One strict retry asking for EXACT count
            strict_prompt = GPT_PROMPT + "\n\nIMPORTANT: You MUST return exactly blocks_count calls. Do NOT deduplicate blocks. One JSON only."
            try:
                response2 = client_openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": strict_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }],
                    max_tokens=4096,
                    temperature=0
                )
                content2 = response2.choices[0].message.content
                if "```json" in content2:
                    content2 = content2.split("```json")[1].split("```")[0]
                elif "```" in content2:
                    content2 = content2.split("```")[1].split("```")[0]
                result2 = json.loads(content2.strip())
                calls2 = result2.get('calls', [])
                if len(calls2) >= len(calls):
                    calls = calls2
            except Exception as e:
                logger.error(f"Strict retry failed: {e}")
        # If blocks_count is missing OR not trusted (<= parsed calls), ask for a recount
        try:
            recount_needed = not isinstance(bc, int) or (isinstance(bc, int) and bc <= len(calls))
            if recount_needed:
                COUNT_PROMPT = "Compte VISUELLEMENT le nombre de blocs d'arbitrage (chaque bloc a un pourcentage vert et DEUX logos bookmakers). Retourne UNIQUEMENT: {\"blocks_count\": <int>}"
                rcount = client_openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": COUNT_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }],
                    max_tokens=256,
                    temperature=0
                )
                ctext = rcount.choices[0].message.content
                if "```json" in ctext:
                    ctext = ctext.split("```json")[1].split("```")[0]
                elif "```" in ctext:
                    ctext = ctext.split("```")[1].split("```")[0]
                recount_obj = json.loads(ctext.strip())
                bc2 = int(recount_obj.get('blocks_count') or 0)
                if bc2 > len(calls):
                    logger.warning(f"⚠️ recount found {bc2} blocks, parsed {len(calls)} — re-parsing strictly")
                    strict_prompt2 = GPT_PROMPT + f"\n\nIMPORTANT: You MUST return exactly {bc2} calls. No dedup."
                    try:
                        response3 = client_openai.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[{
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": strict_prompt2},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{base64_image}",
                                            "detail": "high"
                                        }
                                    }
                                ]
                            }],
                            max_tokens=4096,
                            temperature=0
                        )
                        content3 = response3.choices[0].message.content
                        if "```json" in content3:
                            content3 = content3.split("```json")[1].split("```")[0]
                        elif "```" in content3:
                            content3 = content3.split("```")[1].split("```")[0]
                        result3 = json.loads(content3.strip())
                        calls3 = result3.get('calls', [])
                        if len(calls3) >= len(calls):
                            calls = calls3
                    except Exception as e:
                        logger.error(f"Strict recount parse failed: {e}")
        except Exception as e:
            logger.error(f"Recount step failed: {e}")
        # Sanitize/normalize after GPT extraction (ensure allowed bookmaker names)
        if isinstance(calls, list):
            for call in calls:
                for o in call.get('outcomes', []) or []:
                    # Force bookmaker to be a string, strip spaces
                    if not isinstance(o.get('bookmaker'), str):
                        o['bookmaker'] = str(o.get('bookmaker', '')).strip()
                    else:
                        o['bookmaker'] = o['bookmaker'].strip()
        # Verify logos by comparing cropped regions to local logo files
        try:
            _verify_and_correct_books(calls, photo_bytes)
        except Exception as _e:
            logger.error(f"Logo verification failed: {_e}")
        return calls
        
    except Exception as e:
        logger.error(f"❌ GPT Vision failed: {e}")
        return []


# ============================================================
# VALIDATION STRICTE
# ============================================================

def validate_call(call: Dict) -> bool:
    """Validation stricte avant envoi"""
    
    # 1. team1 ≠ team2
    t1 = (call.get('team1') or '').strip()
    t2 = (call.get('team2') or '').strip()
    if not t1 or not t2:
        logger.error(f"❌ Team manquante: team1='{t1}', team2='{t2}'")
        return False
    if t1.lower() == t2.lower():
        if STRICT_TEAMS:
            logger.error(f"❌ team1 = team2: '{t1}'")
            return False
        else:
            logger.warning(f"⚠️ team1 = team2: '{t1}' — STRICT_TEAMS=0, accepting")
    
    # 2. League présente et complète
    league = (call.get('league') or '').strip()
    if not league or league.lower() in ['soccer', 'basketball', 'hockey', 'football']:
        logger.error(f"❌ League manquante ou incomplète: '{league}'")
        return False
    
    # 3. 2 outcomes exactement
    outcomes = call.get('outcomes', [])
    if len(outcomes) != 2:
        logger.error(f"❌ Outcomes count: {len(outcomes)} (need 2)")
        return False
    
    # 4. Bookmakers différents
    b1 = (outcomes[0].get('bookmaker') or '').strip()
    b2 = (outcomes[1].get('bookmaker') or '').strip()
    e1 = (outcomes[0].get('emoji') or '').strip()
    e2 = (outcomes[1].get('emoji') or '').strip()
    if not b1 or not b2:
        logger.error(f"❌ Bookmaker manquant: b1='{b1}', b2='{b2}'")
        return False
    # Try emoji-based disambiguation
    def emoji_map() -> dict:
        em = {
            '🧱': 'iBet',
            '🔶': 'Betsson',
            '🅿️': 'Pinnacle',
            '❄️': 'Coolbet',
            '🦁': 'LeoVegas',
        }
        try:
            for c in CASINOS_DATA:
                nm = c.get('name')
                eo = c.get('emoji')
                if nm and eo:
                    em[str(eo)] = str(nm)
        except Exception:
            pass
        return em
    EM = emoji_map()
    b1_eff = EM.get(e1, b1)
    b2_eff = EM.get(e2, b2)
    try:
        logger.info(f"🔎 Books resolved (pre-send): {b1_eff} vs {b2_eff} (raw '{b1}'/'{b2}', emojis '{e1}'/'{e2}')")
    except Exception:
        pass
    if b1_eff.lower() == b2_eff.lower():
        if STRICT_BOOKS:
            logger.error(f"❌ Same bookmaker: '{b1_eff}' (from names '{b1}'/'{b2}', emojis '{e1}'/'{e2}')")
            return False
        else:
            logger.warning(f"⚠️ Same bookmaker but STRICT_BOOKS=0 — accepting")
    
    # 5. Sélections non vides
    s1 = (outcomes[0].get('selection') or '').strip()
    s2 = (outcomes[1].get('selection') or '').strip()
    if not s1 or not s2:
        logger.error(f"❌ Selection manquante")
        return False
    
    # 6. Time présent (warning seulement, pas bloquant)
    time_str = (call.get('time') or '').strip()
    if not time_str or time_str == 'TBD':
        logger.warning(f"⚠️ Time manquant ou TBD (non bloquant)")
    
    return True


# ============================================================
# DEDUPLICATION
# ============================================================

def generate_hash(call: Dict) -> str:
    """Hash robuste - ordre-indépendant pour détecter vrais doublons"""
    # Normaliser équipes
    t1 = re.sub(r'\s+', ' ', (call.get('team1') or '').lower().strip())
    t2 = re.sub(r'\s+', ' ', (call.get('team2') or '').lower().strip())
    
    # Trier alphabétiquement (ordre indépendant)
    teams = tuple(sorted([t1, t2]))
    
    # Normaliser marché et time
    market = (call.get('market') or '').lower().strip()
    time_str = (call.get('time') or '').lower().strip()
    
    # Canonicalisation des bookmakers pour la stabilité du hash
    def _canon(name: str) -> str:
        n = (name or '').strip()
        m = {
            'betsson': 'betsson',
            'ibet': 'ibet',
            'coolbet': 'coolbet',
            'bet365': 'bet365', 'bet 365': 'bet365', 'bet-365': 'bet365',
            'betvictor': 'betvictor',
            'bwin': 'bwin',
            '888sport': '888sport',
            'betway': 'betway',
            'casumo': 'casumo',
            'jackpot.bet': 'jackpot.bet',
            'mise-o-jeu': 'mise-o-jeu',
            'proline': 'proline',
            'sports interaction': 'sports interaction', 'si': 'sports interaction', 'sportsinteraction': 'sports interaction', 'sports-interaction': 'sports interaction',
            'stake': 'stake',
            'tonybet': 'tonybet',
            'leovegas': 'leovegas',
            'pinnacle': 'pinnacle', 'p': 'pinnacle',
            'bet99': 'bet99',
            'bet105': 'bet105', 'bet 105': 'bet105', '105': 'bet105',
        }
        k = n.lower()
        return m.get(k, k)
    
    # Extraire outcomes et TRIER (ordre indépendant)
    outcomes_data = []
    for outcome in call.get('outcomes', []):
        book = _canon(outcome.get('bookmaker'))
        odds = (outcome.get('odds') or '').strip()
        sel = re.sub(r'\s+', ' ', (outcome.get('selection') or '').lower().strip())
        outcomes_data.append(f"{book}|{odds}|{sel}")
    
    # IMPORTANT: Trier pour que l'ordre n'affecte pas le hash
    outcomes_data.sort()
    
    # Hash final (inclut time pour éviter collisions inter-matches mêmes équipes)
    unique_str = f"{teams[0]}|{teams[1]}|{market}|{time_str}|{'|'.join(outcomes_data)}"
    hash_value = hashlib.md5(unique_str.encode('utf-8')).hexdigest()
    
    logger.debug(f"Hash string: {unique_str[:160]}...")
    logger.debug(f"Hash value: {hash_value}")
    
    return hash_value


def is_duplicate(call_hash: str) -> bool:
    """Check si déjà envoyé; honor time-window and env flags."""
    if BRIDGE_ALLOW_DUPLICATE_SEND:
        return False
    conn = sqlite3.connect(DB_FILE)
    try:
        c = conn.cursor()
        if BRIDGE_DEDUP_WINDOW_MINUTES and BRIDGE_DEDUP_WINDOW_MINUTES > 0:
            c.execute('SELECT timestamp FROM sent_calls WHERE hash = ?', (call_hash,))
            row = c.fetchone()
            if not row:
                return False
            try:
                from datetime import datetime, timedelta
                last_ts = row[0]
                # SQLite default format: YYYY-MM-DD HH:MM:SS
                last_dt = datetime.strptime(last_ts.split('.')[0], '%Y-%m-%d %H:%M:%S')
                return (datetime.utcnow() - last_dt) < timedelta(minutes=BRIDGE_DEDUP_WINDOW_MINUTES)
            except Exception:
                return True
        else:
            c.execute('SELECT 1 FROM sent_calls WHERE hash = ?', (call_hash,))
            return c.fetchone() is not None
    finally:
        conn.close()


def save_call(call: Dict, call_hash: str):
    """Save to DB"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    teams = f"{call.get('team1')} vs {call.get('team2')}"
    market = call.get('market', '')
    c.execute('INSERT OR REPLACE INTO sent_calls (hash, teams, market) VALUES (?, ?, ?)',
              (call_hash, teams, market))
    conn.commit()
    conn.close()


# ============================================================
# FORMATAGE MESSAGE
# ============================================================

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


def convert_to_risk0_format(call: Dict) -> Dict:
    """Convert GPT call format to risk0_bot API format"""
    team1 = call.get('team1', 'Unknown')
    team2 = call.get('team2', 'Unknown')
    match = f"{team1} vs {team2}"
    
    # Generate event_id from hash
    event_id = generate_hash(call)[:12]
    
    # Canonicalize bookmaker names to match core.casinos keys
    def canonical_book(name: str) -> str:
        n = (name or '').strip()
        n_lower = n.lower()
        mapping = {
            'betsson': 'Betsson',
            'ibet': 'iBet',
            'coolbet': 'Coolbet',
            'bet365': 'bet365',
            'bet 365': 'bet365',
            'bet-365': 'bet365',
            'betvictor': 'BetVictor',
            'bwin': 'bwin',
            '888sport': '888sport',
            'betway': 'Betway',
            'casumo': 'Casumo',
            'jackpot.bet': 'Jackpot.bet',
            'mise-o-jeu': 'Mise-o-jeu',
            'proline': 'Proline',
            'sports interaction': 'Sports Interaction', 'si': 'Sports Interaction', 'sportsinteraction': 'Sports Interaction', 'sports-interaction': 'Sports Interaction',
            'stake': 'Stake',
            'tonybet': 'TonyBet',
            'leovegas': 'LeoVegas',
            'pinnacle': 'Pinnacle', 'p': 'Pinnacle',
            'bet99': 'BET99',
            'bet105': 'bet105',
            'bet 105': 'bet105',
            '105': 'bet105',
        }
        return mapping.get(n_lower, n)

    # Build emoji->book map from CASINOS_DATA (fallback defaults for common ones)
    def emoji_to_book() -> dict:
        emap = {
            '🧱': 'iBet',
            '🔶': 'Betsson',
            '🅿️': 'Pinnacle',
            '❄️': 'Coolbet',
            '🦁': 'LeoVegas',
        }
        try:
            for c in CASINOS_DATA:
                nm = c.get('name')
                em = c.get('emoji')
                if nm and em:
                    emap[str(em)] = str(nm)
        except Exception:
            pass
        return emap

    EMOJI_MAP = emoji_to_book()

    def disambiguate_name(raw_name: str, emoji_val: str) -> str:
        rn = (raw_name or '').strip()
        ev = (emoji_val or '').strip()
        # If emoji maps to a known book and conflicts with name, prefer emoji (logo is visual ground truth)
        if ev and ev in EMOJI_MAP:
            return EMOJI_MAP[ev]
        # Heuristic: single letter 'P' means Pinnacle
        if rn.lower() in {'p', 'pin', 'pinn'}:
            return 'Pinnacle'
        # Heuristic: 'S'/'SI' often means Sports Interaction logo
        if rn.lower() in {'s', 'si', 'sportsinteraction', 'sports-interaction'}:
            return 'Sports Interaction'
        return rn
    
    # Convert odds from "+220" to integer 220
    def parse_odds(odds_str: str) -> int:
        try:
            match = re.search(r'([+\-])(\d+)', odds_str or '')
            if not match:
                return 0
            sign = match.group(1)
            value = int(match.group(2))
            return value if sign == '+' else -value
        except:
            return 0
    
    outcomes = []
    for o in call.get('outcomes', []):
        raw_name = o.get('bookmaker', 'Unknown')
        emoji_val = o.get('emoji', '')
        picked = disambiguate_name(raw_name, emoji_val)
        outcomes.append({
            'casino': canonical_book(picked),
            'outcome': o.get('selection', ''),
            'odds': parse_odds(o.get('odds', '+0'))
        })
    
    # Parse percentage to numeric float (strip '%')
    raw_pct = str(call.get('percentage', '0'))
    try:
        pct_val = float(re.sub(r"[^0-9.]", "", raw_pct) or 0.0)
    except Exception:
        pct_val = 0.0
    
    return {
        'event_id': event_id,
        'arb_percentage': pct_val,
        'match': match,
        'league': call.get('league', ''),
        'market': call.get('market', ''),
        'time': call.get('time', 'TBD'),
        'outcomes': outcomes
    }


async def send_to_risk0_api(call: Dict) -> bool:
    """Send call to risk0_bot API endpoint"""
    try:
        risk0_data = convert_to_risk0_format(call)
        
        async with httpx.AsyncClient(timeout=10.0) as client_http:
            response = await client_http.post(
                f"{RISK0_API_URL}/public/drop",
                json=risk0_data
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    logger.info(f"✅ Sent to risk0_bot API: {risk0_data['event_id']}")
                    return True
                else:
                    logger.error(f"❌ API rejected: {result}")
                    return False
            else:
                logger.error(f"❌ API error {response.status_code}: {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Failed to send to API: {e}")
        return False


# ============================================================
# HANDLER TELEGRAM
# ============================================================

@client.on(events.NewMessage)
async def handle_new_message(event):
    """Handler principal pour les photos de Nonoriribot"""
    try:
        message = event.message
        
        # Filter: only from Nonoriribot
        sender = await message.get_sender()
        sender_username = (getattr(sender, "username", "") or "").lower()
        
        if sender_username != SOURCE_BOT_USERNAME.lower():
            return
        
        # Ensure raw_text is always defined before any use
        raw_text = (getattr(message, "message", None) or getattr(message, "raw_text", "") or "").strip()
        
        # ===== PRIORITY ROUTING: Typed alerts first =====
        # 1. Positive EV Alert (explicit)
        if raw_text and "Positive EV Alert" in raw_text:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client_http:
                    r = await client_http.post(f"{RISK0_API_URL}/api/oddsjam/positive_ev", json={"text": raw_text})
                if r.status_code == 200:
                    logger.info("✅ Forwarded Positive EV to /api/oddsjam/positive_ev")
                else:
                    logger.error(f"❌ Positive EV API error {r.status_code}: {r.text}")
            except Exception as e:
                logger.error(f"❌ Failed to POST Positive EV: {e}")
            return
        
        # 2. Middle Alert (explicit)
        if raw_text and "Middle Alert" in raw_text:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client_http:
                    r = await client_http.post(f"{RISK0_API_URL}/api/oddsjam/middle", json={"text": raw_text})
                if r.status_code == 200:
                    logger.info("✅ Forwarded Middle to /api/oddsjam/middle")
                else:
                    logger.error(f"❌ Middle API error {r.status_code}: {r.text}")
            except Exception as e:
                logger.error(f"❌ Failed to POST Middle: {e}")
            return
        
        # 3. Arbitrage Alert (explicit)
        if raw_text and "Arbitrage Alert" in raw_text:
            try:
                parsed = parse_arbitrage_alert(raw_text)
            except Exception as e:
                logger.error(f"❌ Text parse failed: {e}")
                return
            if not parsed:
                logger.warning("⚠️ Text alert did not parse into a drop")
                return
            # Ensure event_id exists
            if not parsed.get('event_id'):
                try:
                    mm = f"{parsed.get('match','')}|{parsed.get('market','')}"
                    oo = "|".join([f"{o.get('casino','')}:{o.get('odds','')}" for o in parsed.get('outcomes',[])])
                    eid = hashlib.md5(f"{mm}|{oo}".encode('utf-8')).hexdigest()[:12]
                    parsed['event_id'] = eid
                except Exception:
                    parsed['event_id'] = hashlib.md5(raw_text.encode('utf-8')).hexdigest()[:12]
            try:
                async with httpx.AsyncClient(timeout=10.0) as client_http:
                    r = await client_http.post(f"{RISK0_API_URL}/public/drop", json=parsed)
                if r.status_code == 200:
                    logger.info(f"✅ Sent text arbitrage to /public/drop: {parsed.get('event_id')}")
                else:
                    logger.error(f"❌ API error {r.status_code}: {r.text}")
            except Exception as e:
                logger.error(f"❌ Failed to POST arbitrage: {e}")
            return
        
        # ===== FALLBACK: Generic "Odds Alert" without explicit type =====
        if raw_text and "Odds Alert" in raw_text:
            try:
                at_count = len(re.findall(r"@\s*[A-Za-z0-9 ][A-Za-z0-9 \-]*", raw_text))
            except Exception:
                at_count = 0
            # 1 book => Good Odds
            if at_count <= 1:
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client_http:
                        r = await client_http.post(f"{RISK0_API_URL}/api/oddsjam/positive_ev", json={"text": raw_text})
                    if r.status_code == 200:
                        logger.info("✅ Fallback routed to Positive EV")
                    else:
                        logger.error(f"❌ Fallback Positive EV API error {r.status_code}: {r.text}")
                except Exception as e:
                    logger.error(f"❌ Fallback Positive EV failed: {e}")
                return
            # 2+ books => try to recognize Middle pattern: team +line/-line odds @ book
            try:
                after_bracket = raw_text.split(']', 1)[1] if ']' in raw_text else raw_text
                middle_matches = re.findall(r"[A-Za-z\s]+\s+[+\-]\d+\.?\d*\s+[+\-]\d+\s*@\s*[A-Za-z0-9 ][A-Za-z0-9 \-]*", after_bracket)
            except Exception:
                middle_matches = []
            if len(middle_matches) >= 2:
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client_http:
                        r = await client_http.post(f"{RISK0_API_URL}/api/oddsjam/middle", json={"text": raw_text})
                    if r.status_code == 200:
                        logger.info("✅ Fallback routed to Middle")
                    else:
                        logger.error(f"❌ Fallback Middle API error {r.status_code}: {r.text}")
                except Exception as e:
                    logger.error(f"❌ Fallback Middle failed: {e}")
                return
            # Otherwise treat as arbitrage
            try:
                parsed = parse_arbitrage_alert(raw_text)
            except Exception as e:
                logger.error(f"❌ Fallback arbitrage parse failed: {e}")
                return
            if not parsed:
                logger.warning("⚠️ Fallback: could not parse to arbitrage drop")
                return
            if not parsed.get('event_id'):
                try:
                    mm = f"{parsed.get('match','')}|{parsed.get('market','')}"
                    oo = "|".join([f"{o.get('casino','')}:{o.get('odds','')}" for o in parsed.get('outcomes',[])])
                    eid = hashlib.md5(f"{mm}|{oo}".encode('utf-8')).hexdigest()[:12]
                    parsed['event_id'] = eid
                except Exception:
                    parsed['event_id'] = hashlib.md5(raw_text.encode('utf-8')).hexdigest()[:12]
            try:
                async with httpx.AsyncClient(timeout=10.0) as client_http:
                    r = await client_http.post(f"{RISK0_API_URL}/public/drop", json=parsed)
                if r.status_code == 200:
                    logger.info(f"✅ Fallback routed to /public/drop: {parsed.get('event_id')}")
                else:
                    logger.error(f"❌ Fallback arbitrage API error {r.status_code}: {r.text}")
            except Exception as e:
                logger.error(f"❌ Fallback arbitrage failed: {e}")
            return
            # Branch 1: Photo → GPT Vision
        if message.photo:
            logger.info(f"📸 Screenshot received from @{sender_username}")
            # Download photo
            photo_bytes = await message.download_media(file=bytes)
            
            # Parse avec GPT Vision PUR
            calls = await parse_screenshot(photo_bytes)
            logger.info(f"🧠 GPT Vision extracted {len(calls)} call(s)")
            
            if not calls:
                logger.warning("⚠️ No calls extracted")
                return
            
            sent = 0
            seen_hashes = set()
            for call in calls:
                # Validation stricte
                if not validate_call(call):
                    continue
                
                # Dedup avec logs détaillés
                call_hash = generate_hash(call)
                if call_hash in seen_hashes:
                    logger.warning(f"🚨 DUPLICATE IN BATCH! Hash: {call_hash}")
                    continue
                seen_hashes.add(call_hash)
                
                outcomes = call.get('outcomes', [])
                o1 = outcomes[0] if len(outcomes) > 0 else {}
                o2 = outcomes[1] if len(outcomes) > 1 else {}
                
                logger.info(f"""\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n📊 CALL PROCESSING:\nTeams: {call.get('team1')} vs {call.get('team2')}\nLeague: {call.get('league')}\nMarket: {call.get('market')}\nTime: {call.get('time', 'TBD')}\nBooks: {o1.get('bookmaker', 'N/A')} vs {o2.get('bookmaker', 'N/A')}\nOdds: {o1.get('odds', 'N/A')} vs {o2.get('odds', 'N/A')}\nHash: {call_hash}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━""")
                
                if is_duplicate(call_hash):
                    logger.warning(f"🚨 DUPLICATE DETECTED! Hash: {call_hash}")
                    logger.warning(f"   Same as previous call with same teams/market/books/odds")
                    if not BRIDGE_ALLOW_DUPLICATE_SEND:
                        continue
                    else:
                        logger.info("⚙️ BRIDGE_ALLOW_DUPLICATE_SEND=1 — forwarding anyway")
                
                # Send to risk0_bot API
                try:
                    success = await send_to_risk0_api(call)
                    if success:
                        save_call(call, call_hash)
                        sent += 1
                        logger.info(f"✅ Sent: {call.get('team1')} vs {call.get('team2')}")
                    else:
                        logger.error(f"❌ Failed to send: {call.get('team1')} vs {call.get('team2')}")
                except Exception as e:
                    logger.error(f"❌ Send failed: {e}")
            
            logger.info(f"📊 {sent}/{len(calls)} sent")
            return
        
        sent = 0
        seen_hashes = set()
        for call in calls:
            # Validation stricte
            if not validate_call(call):
                continue
            
            # Dedup avec logs détaillés
            call_hash = generate_hash(call)
            if call_hash in seen_hashes:
                logger.warning(f"🚨 DUPLICATE IN BATCH! Hash: {call_hash}")
                continue
            seen_hashes.add(call_hash)
            
            outcomes = call.get('outcomes', [])
            o1 = outcomes[0] if len(outcomes) > 0 else {}
            o2 = outcomes[1] if len(outcomes) > 1 else {}
            
            logger.info(f"""\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n📊 CALL PROCESSING:\nTeams: {call.get('team1')} vs {call.get('team2')}\nLeague: {call.get('league')}\nMarket: {call.get('market')}\nTime: {call.get('time', 'TBD')}\nBooks: {o1.get('bookmaker', 'N/A')} vs {o2.get('bookmaker', 'N/A')}\nOdds: {o1.get('odds', 'N/A')} vs {o2.get('odds', 'N/A')}\nHash: {call_hash}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━""")
            
            if is_duplicate(call_hash):
                logger.warning(f"🚨 DUPLICATE DETECTED! Hash: {call_hash}")
                logger.warning(f"   Same as previous call with same teams/market/books/odds")
                continue
            
            # Send to risk0_bot API
            try:
                success = await send_to_risk0_api(call)
                if success:
                    save_call(call, call_hash)
                    sent += 1
                    logger.info(f"✅ Sent: {call.get('team1')} vs {call.get('team2')}")
                else:
                    logger.error(f"❌ Failed to send: {call.get('team1')} vs {call.get('team2')}")
            except Exception as e:
                logger.error(f"❌ Send failed: {e}")
        
        logger.info(f"📊 {sent}/{len(calls)} sent")
        
    except Exception as e:
        logger.error(f"❌ Handler error: {e}", exc_info=True)


# ============================================================
# MAIN
# ============================================================

async def main():
    logger.info("🚀 Starting bridge_simple...")
    logger.info(f"📋 Loaded {len(CASINOS_DATA)} casinos from JSON")
    
    await client.start(phone=PHONE)
    logger.info("✅ Bot connected and ready")
    logger.info(f"👂 Listening to @{SOURCE_BOT_USERNAME}")
    logger.info(f"📤 Sending to risk0_bot API: {RISK0_API_URL}/public/drop")
    
    await client.run_until_disconnected()


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
