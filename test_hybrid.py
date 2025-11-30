#!/usr/bin/env python3
"""
Script de test pour vérifier chaque couche du système hybrid
"""

import os
import sys
from pathlib import Path

def test_dependencies():
    """Test 1: Vérifier toutes les dépendances"""
    print("\n" + "="*60)
    print("TEST 1: Dépendances")
    print("="*60)
    
    deps = {
        'cv2': 'opencv-python-headless',
        'numpy': 'numpy',
        'openai': 'openai',
        'pytesseract': 'pytesseract',
        'PIL': 'Pillow',
        'telegram': 'python-telegram-bot',
        'dotenv': 'python-dotenv'
    }
    
    failed = []
    for module, package in deps.items():
        try:
            __import__(module)
            print(f"✅ {module:20} OK")
        except ImportError:
            print(f"❌ {module:20} MISSING - pip install {package}")
            failed.append(package)
    
    if failed:
        print(f"\n⚠️ Installer: pip install {' '.join(failed)}")
        return False
    
    print("\n✅ Toutes les dépendances installées")
    return True


def test_tesseract():
    """Test 2: Vérifier Tesseract OCR"""
    print("\n" + "="*60)
    print("TEST 2: Tesseract OCR")
    print("="*60)
    
    import subprocess
    try:
        result = subprocess.run(['tesseract', '--version'], 
                              capture_output=True, text=True)
        version = result.stdout.split('\n')[0]
        print(f"✅ {version}")
        return True
    except FileNotFoundError:
        print("❌ Tesseract not found")
        print("\nInstaller:")
        print("  Mac:     brew install tesseract")
        print("  Linux:   sudo apt-get install tesseract-ocr")
        print("  Windows: https://github.com/UB-Mannheim/tesseract/wiki")
        return False


def test_env_config():
    """Test 3: Vérifier configuration .env"""
    print("\n" + "="*60)
    print("TEST 3: Configuration .env")
    print("="*60)
    
    from dotenv import load_dotenv
    load_dotenv()
    
    required = {
        'OPENAI_API_KEY': 'Clé OpenAI',
        'TELEGRAM_BOT_TOKEN': 'Token Telegram',
        'SOURCE_GROUP_ID': 'ID groupe source',
        'DESTINATION_GROUP_ID': 'ID groupe destination'
    }
    
    missing = []
    for key, desc in required.items():
        val = os.getenv(key)
        if val:
            masked = val[:8] + '...' if len(val) > 8 else val
            print(f"✅ {key:25} {masked}")
        else:
            print(f"❌ {key:25} MISSING - {desc}")
            missing.append(key)
    
    if missing:
        print(f"\n⚠️ Ajouter dans .env: {', '.join(missing)}")
        return False
    
    print("\n✅ Configuration complète")
    return True


def test_casinos_json():
    """Test 4: Vérifier casino_logos.json"""
    print("\n" + "="*60)
    print("TEST 4: Base de données casinos")
    print("="*60)
    
    import json
    
    files = ['casino_logos.json', 'casinos.json']
    casinos_file = None
    
    for f in files:
        if os.path.exists(f):
            casinos_file = f
            break
    
    if not casinos_file:
        print("❌ Aucun fichier casinos trouvé")
        print("   Fichiers cherchés: casino_logos.json, casinos.json")
        return False
    
    try:
        with open(casinos_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        casinos = data.get('casinos', [])
        print(f"✅ Fichier: {casinos_file}")
        print(f"✅ Casinos chargés: {len(casinos)}")
        
        # Vérifier structure
        required_fields = ['name', 'emoji', 'aliases']
        sample = casinos[0] if casinos else {}
        
        for field in required_fields:
            if field in sample:
                print(f"✅   {field:15} présent")
            else:
                print(f"⚠️   {field:15} manquant")
        
        return True
    
    except json.JSONDecodeError as e:
        print(f"❌ JSON invalide: {e}")
        return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False


def test_logos_directory():
    """Test 5: Vérifier dossier logos/"""
    print("\n" + "="*60)
    print("TEST 5: Logos PNG")
    print("="*60)
    
    logo_dir = 'logos'
    
    if not os.path.exists(logo_dir):
        print(f"❌ Dossier {logo_dir}/ introuvable")
        print(f"\n   Créer: mkdir {logo_dir}")
        return False
    
    logos = list(Path(logo_dir).glob('*.png'))
    
    if not logos:
        print(f"⚠️ Aucun logo PNG dans {logo_dir}/")
        print("\n   Ajouter les logos des bookmakers (format PNG)")
        return False
    
    print(f"✅ Dossier: {logo_dir}/")
    print(f"✅ Logos trouvés: {len(logos)}")
    
    # Afficher quelques exemples
    for logo in logos[:5]:
        size = logo.stat().st_size / 1024  # KB
        print(f"   📂 {logo.name:20} ({size:.1f} KB)")
    
    if len(logos) > 5:
        print(f"   ... et {len(logos) - 5} autres")
    
    return True


def test_openai_api():
    """Test 6: Vérifier connexion OpenAI"""
    print("\n" + "="*60)
    print("TEST 6: OpenAI API")
    print("="*60)
    
    from dotenv import load_dotenv
    import openai
    
    load_dotenv()
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        print("❌ OPENAI_API_KEY manquante dans .env")
        return False
    
    openai.api_key = api_key
    
    try:
        # Test simple - lister les modèles (nouvelle API OpenAI)
        import openai
        client = openai.OpenAI(api_key=api_key)
        models = client.models.list()
        model_data = list(models)
        print(f"✅ Connexion OK")
        print(f"✅ Modèles disponibles: {len(model_data)}")
        
        # Vérifier si gpt-4o-mini est disponible
        model_ids = [m.id for m in model_data]
        if 'gpt-4o-mini' in model_ids:
            print(f"✅ gpt-4o-mini disponible")
        else:
            print(f"⚠️ gpt-4o-mini non trouvé (mais API fonctionne)")
        
        return True
    
    except Exception as e:
        print(f"❌ Erreur: {e}")
        print(f"   Note: Si la clé est 'your_openai_api_key_here', la remplacer par une vraie clé")
        return False


def test_database():
    """Test 7: Vérifier SQLite"""
    print("\n" + "="*60)
    print("TEST 7: Base de données SQLite")
    print("="*60)
    
    import sqlite3
    
    db_file = 'calls_history.db'
    
    try:
        conn = sqlite3.connect(db_file)
        c = conn.cursor()
        
        # Créer table si pas existe
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
        
        # Compter entrées
        c.execute('SELECT COUNT(*) FROM sent_calls')
        count = c.fetchone()[0]
        
        conn.close()
        
        print(f"✅ Base de données: {db_file}")
        print(f"✅ Calls historiques: {count}")
        
        return True
    
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False


def run_all_tests():
    """Lancer tous les tests"""
    print("\n" + "="*60)
    print("🧪 TEST SUITE - Bridge Hybrid")
    print("="*60)
    
    tests = [
        ("Dépendances Python", test_dependencies),
        ("Tesseract OCR", test_tesseract),
        ("Configuration .env", test_env_config),
        ("Base casinos JSON", test_casinos_json),
        ("Logos PNG", test_logos_directory),
        ("OpenAI API", test_openai_api),
        ("SQLite Database", test_database),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n❌ Exception dans {name}: {e}")
            results.append((name, False))
    
    # Résumé
    print("\n" + "="*60)
    print("📊 RÉSUMÉ")
    print("="*60)
    
    passed = sum(1 for _, p in results if p)
    total = len(results)
    
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {name}")
    
    print("\n" + "="*60)
    print(f"Score: {passed}/{total} tests passés")
    print("="*60)
    
    if passed == total:
        print("\n🎉 Tous les tests passent! Le système est prêt.")
        print("\nLancer: python3 bridge_hybrid.py")
        return True
    else:
        print(f"\n⚠️ {total - passed} test(s) en échec - corriger avant de lancer")
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
