#!/usr/bin/env python3
"""
Test complet du parsing OCR pour vérifier l'extraction des casinos
"""
import re
from bookmakers import resolve_bookmaker

# Simule le texte OCR du screenshot
ocr_text_block = """
11.79% -$25.75
Soccer • Spain - La Liga
Villarreal CF vs Real Club Deportivo Mallorca
Team Total Corners

Real Club Deportivo Mallorca Over 3
ibet $90 +145

Real Club Deportivo Mallorca Under 3  
$100 +111 cootsecr
"""

def test_book_extraction():
    """Test l'extraction des books avec les nouveaux patterns"""
    print("🔍 Test d'extraction des casinos")
    print("=" * 50)
    
    lines = [ln.strip() for ln in ocr_text_block.splitlines() if ln.strip()]
    
    # Pattern 1: casino avant stake (ex: "ibet $90 +145")
    pat1 = re.compile(r"([A-Za-z][A-Za-z0-9]+)\s*\$\s*(\d+(?:[\.,]\d{1,2})?)\s*([+\-−]\d{2,4})")
    # Pattern 2: stake et odds avec casino après (ex: "$100 +111 cootsecr")
    pat2 = re.compile(r"\$\s*(\d+(?:[\.,]\d{1,2})?)\s*([+\-−]\d{2,4})\s*([A-Za-z][A-Za-z0-9]+)")
    
    books_found = []
    
    for ln in lines:
        print(f"\nLigne: {ln}")
        
        # Test Pattern 1
        m1 = pat1.search(ln)
        if m1:
            book = m1.group(1)
            stake = m1.group(2)
            odds = m1.group(3)
            print(f"  → Pattern 1: book='{book}' stake=${stake} odds={odds}")
            resolved = resolve_bookmaker(book)
            if resolved.get("found"):
                print(f"  ✅ Résolu: {resolved.get('name')} {resolved.get('emoji')}")
                books_found.append(resolved.get('name'))
        
        # Test Pattern 2
        m2 = pat2.search(ln)
        if m2:
            stake = m2.group(1)
            odds = m2.group(2)
            book = m2.group(3)
            print(f"  → Pattern 2: stake=${stake} odds={odds} book='{book}'")
            resolved = resolve_bookmaker(book)
            if resolved.get("found"):
                print(f"  ✅ Résolu: {resolved.get('name')} {resolved.get('emoji')}")
                books_found.append(resolved.get('name'))
    
    print("\n" + "=" * 50)
    print(f"📊 Casinos extraits: {books_found}")
    
    if len(books_found) == 2 and books_found == ['iBet', 'Coolbet']:
        print("✅ SUCCESS! Les deux casinos sont correctement extraits!")
        return True
    else:
        print("❌ ÉCHEC! Casinos attendus: ['iBet', 'Coolbet']")
        return False

def test_specific_patterns():
    """Test des patterns spécifiques problématiques"""
    print("\n🎯 Test des patterns spécifiques:")
    print("-" * 50)
    
    test_lines = [
        "ibet $90 +145",
        "$100 +111 cootsecr",
        "betsson $50 +200",
        "$75 -150 bet365"
    ]
    
    pat1 = re.compile(r"([A-Za-z][A-Za-z0-9]+)\s*\$\s*(\d+(?:[\.,]\d{1,2})?)\s*([+\-−]\d{2,4})")
    pat2 = re.compile(r"\$\s*(\d+(?:[\.,]\d{1,2})?)\s*([+\-−]\d{2,4})\s*([A-Za-z][A-Za-z0-9]+)")
    
    for line in test_lines:
        print(f"\nTest: '{line}'")
        
        m1 = pat1.search(line)
        m2 = pat2.search(line)
        
        if m1:
            book = m1.group(1)
            resolved = resolve_bookmaker(book)
            print(f"  Pattern 1 → {book} → {resolved.get('name') if resolved.get('found') else 'NON TROUVÉ'}")
        elif m2:
            book = m2.group(3)
            resolved = resolve_bookmaker(book)
            print(f"  Pattern 2 → {book} → {resolved.get('name') if resolved.get('found') else 'NON TROUVÉ'}")
        else:
            print(f"  ❌ Aucun pattern ne correspond")

if __name__ == "__main__":
    print("=" * 60)
    print("TEST COMPLET DU PARSING DES CASINOS")
    print("=" * 60)
    
    # Test principal
    success = test_book_extraction()
    
    # Tests supplémentaires
    test_specific_patterns()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 Tous les tests passent! Le parsing fonctionne correctement.")
    else:
        print("⚠️ Des problèmes subsistent dans le parsing.")
