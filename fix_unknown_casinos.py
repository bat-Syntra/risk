#!/usr/bin/env python3
"""
Fix pour les casinos Unknown - détection améliorée
"""

def fix_unknown_books(call_data: dict, ocr_text: str) -> dict:
    """
    Fix les casinos Unknown en utilisant plusieurs stratégies
    """
    from bookmakers import resolve_bookmaker
    
    # Liste des mots trouvés dans l'OCR qui pourraient être des casinos
    potential_books = []
    
    # Patterns pour trouver les noms de casinos
    import re
    
    # Cherche tous les mots qui ressemblent à des noms de casinos
    words = re.findall(r'\b[A-Za-z][A-Za-z0-9]{2,}\b', ocr_text)
    
    for word in words:
        # Skip common non-casino words
        skip_words = {'Team', 'Total', 'Corners', 'Over', 'Under', 'Game', 'Site', 
                      'Scan', 'Tomorrow', 'Today', 'CASHH', 'Profit', 'Return', 'Stake',
                      'Villarreal', 'Mallorca', 'Real', 'Club', 'Deportivo', 'Spain'}
        if word in skip_words:
            continue
            
        # Try to resolve
        resolved = resolve_bookmaker(word)
        if resolved.get("found"):
            potential_books.append(resolved.get("name"))
    
    # Si on trouve exactement 2 casinos, les utiliser
    if len(potential_books) >= 2:
        if call_data.get('book1') == 'Unknown':
            call_data['book1'] = potential_books[0]
        if call_data.get('book2') == 'Unknown':
            call_data['book2'] = potential_books[1]
    
    # Patterns spécifiques observés
    if 'cootsecr' in ocr_text.lower() or 'costser' in ocr_text.lower():
        if call_data.get('book2') == 'Unknown':
            call_data['book2'] = 'Coolbet'
    
    # Si on voit des patterns de iBet
    if any(x in ocr_text.lower() for x in ['ibet', 'i bet']):
        if call_data.get('book1') == 'Unknown':
            call_data['book1'] = 'iBet'
    
    return call_data


def identify_casinos_from_context(ocr_text: str) -> list:
    """
    Identifie les casinos dans le texte OCR avec plus d'intelligence
    """
    casinos_found = []
    
    # Mapping direct des erreurs OCR communes
    ocr_fixes = {
        'cootsecr': 'Coolbet',
        'costser': 'Coolbet',
        'coouser': 'Coolbet',
        'coolser': 'Coolbet',
        'ibet': 'iBet',
        'bet99': 'BET99',
        'betsson': 'Betsson',
    }
    
    text_lower = ocr_text.lower()
    for ocr_error, correct_name in ocr_fixes.items():
        if ocr_error in text_lower and correct_name not in casinos_found:
            casinos_found.append(correct_name)
    
    return casinos_found


if __name__ == "__main__":
    # Test avec l'exemple problématique
    test_text = """
    🎰 [Unknown] Mallorca Mallorca @ +145
    💵 Stake: $323.44 → Return: $792.43

    🎰 [Unknown] $90 +145 cootsecr [] @ +111
    💵 Stake: $375.56 → Return: $792.43
    """
    
    test_call = {
        'book1': 'Unknown',
        'book2': 'Unknown',
        'percentage': '11.8%'
    }
    
    print("Avant fix:", test_call)
    fixed = fix_unknown_books(test_call, test_text)
    print("Après fix:", fixed)
    
    casinos = identify_casinos_from_context(test_text)
    print("Casinos identifiés:", casinos)
