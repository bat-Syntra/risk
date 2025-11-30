#!/usr/bin/env python3
"""
Test script pour vérifier que la détection de logos fonctionne
"""
import os
from logo_detector import LogoDetector

def test_logo_loading():
    """Test que tous les logos sont bien chargés"""
    detector = LogoDetector()
    
    print("\n✅ Logos chargés avec succès:")
    for casino_name in detector.templates.keys():
        print(f"  - {casino_name}")
    
    print(f"\n📊 Total: {len(detector.templates)} logos prêts")
    
    # Vérifier les fichiers manquants
    expected = ["888sport", "bet365", "BET99", "Betsson", "BetVictor", "Betway", 
                "bwin", "Casumo", "Coolbet", "iBet", "Jackpot.bet", "LeoVegas",
                "Mise-o-jeu", "Pinnacle", "Proline", "Sports Interaction", 
                "Stake", "TonyBet"]
    
    missing = [e for e in expected if e not in detector.templates]
    if missing:
        print(f"\n⚠️ Logos manquants:")
        for m in missing:
            print(f"  - {m}")
    
    return len(detector.templates) > 0

def test_with_image(image_path: str):
    """Test avec une vraie image"""
    if not os.path.exists(image_path):
        print(f"❌ Image non trouvée: {image_path}")
        return False
    
    detector = LogoDetector()
    
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    
    print(f"\n🔍 Analyse de {image_path}...")
    results = detector.detect_logos(image_bytes)
    
    if results:
        print("✅ Casinos détectés:")
        for r in results:
            print(f"  {r['emoji']} {r['casino']}: {r['confidence']:.2%} confiance")
    else:
        print("⚠️ Aucun casino détecté")
    
    return len(results) > 0

if __name__ == "__main__":
    print("=" * 50)
    print("🎰 TEST DE DÉTECTION DES LOGOS DE CASINOS")
    print("=" * 50)
    
    # Test 1: Chargement
    if test_logo_loading():
        print("\n✅ Système de détection prêt!")
    else:
        print("\n❌ Problème de chargement des logos")
    
    # Test 2: Avec image si disponible
    test_images = ["test_screenshot.png", "screenshot.png", "test.png"]
    for img in test_images:
        if os.path.exists(img):
            test_with_image(img)
            break
    
    print("\n" + "=" * 50)
    print("🎯 Pour tester avec tes screenshots:")
    print("  1. Place un screenshot comme 'test_screenshot.png'")
    print("  2. Relance: python test_logo_detection.py")
    print("=" * 50)
