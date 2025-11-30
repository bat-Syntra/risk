#!/usr/bin/env python3
"""
Test rapide pour vérifier la résolution des casinos
"""
from bookmakers import resolve_bookmaker

# Test les cas problématiques
test_cases = [
    "ibet",
    "iBet", 
    "cootsecr",
    "costser",
    "coolbet",
    "Coolbet",
    "betsson",
    "Betsson",
    "Mallorca",  # Should not match
    "$90",       # Should not match
]

print("🔍 Test de résolution des casinos:")
print("-" * 50)

for test in test_cases:
    result = resolve_bookmaker(test)
    if result.get("found"):
        print(f"✅ '{test}' → {result.get('name')} {result.get('emoji')}")
    else:
        print(f"❌ '{test}' → Non trouvé")

print("\n" + "=" * 50)
print("\n📝 Test du texte OCR problématique:")

# Simule le texte OCR
ocr_text = """
Real Club Deportivo Mallorca Over 3
ibet $90 +145

Real Club Deportivo Mallorca Under 3  
$100 +111 cootsecr
"""

print(f"Texte OCR:\n{ocr_text}")
print("\n🎯 Recherche des casinos...")

import re
words = re.findall(r'\b[A-Za-z][A-Za-z0-9]{2,}\b', ocr_text)
casinos_found = []

for word in words:
    result = resolve_bookmaker(word)
    if result.get("found"):
        casinos_found.append(result.get("name"))
        print(f"  → Trouvé: {word} = {result.get('name')}")

print(f"\n📊 Casinos finaux: {casinos_found}")

# Test spécifique pour les variantes
print("\n" + "=" * 50)
print("🔧 Fix spécifiques:")

if 'cootsecr' in ocr_text.lower():
    print("  → 'cootsecr' détecté → Coolbet")
if 'ibet' in ocr_text.lower():
    print("  → 'ibet' détecté → iBet")
