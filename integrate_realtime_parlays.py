#!/usr/bin/env python3
"""
Script d'intégration automatique du système de parlays temps réel
Modifie main_new.py pour activer la génération temps réel
"""
import re

def integrate_realtime_parlays():
    """Intègre le système de parlays temps réel dans main_new.py"""
    
    main_file = "main_new.py"
    
    # Lire le fichier
    with open(main_file, 'r') as f:
        content = f.read()
    
    # Vérifier si déjà intégré
    if 'from realtime_parlay_generator import on_drop_received' in content:
        print("⚠️  Déjà intégré! Rien à faire.")
        return
    
    print("🔧 Intégration du système de parlays temps réel...")
    
    # 1. Ajouter l'import
    import_line = "from realtime_parlay_generator import on_drop_received\n"
    
    # Trouver où ajouter l'import (après les autres imports from)
    import_pattern = r'(from utils\.drops_stats import.*\n)'
    content = re.sub(import_pattern, r'\1' + import_line, content)
    print("✅ Import ajouté")
    
    # 2. Modifier tous les record_drop() pour ajouter on_drop_received()
    # Pattern: record_drop(xxx)
    # Remplacer par: drop_id = record_drop(xxx)\n    if drop_id:\n        on_drop_received(drop_id)
    
    replacements = 0
    
    # Pattern 1: try: record_drop(d)
    pattern1 = r'try:\s*\n\s*record_drop\((d|drop|drop_record)\)'
    def replace1(match):
        var = match.group(1)
        return f'''try:
        drop_id = record_drop({var})
        if drop_id:
            on_drop_received(drop_id)  # 🔥 Génère parlays en temps réel!'''
    
    new_content = re.sub(pattern1, replace1, content)
    if new_content != content:
        replacements += content.count('record_drop(') - new_content.count('record_drop(')
        content = new_content
    
    # Pattern 2: Standalone record_drop(drop_record)
    pattern2 = r'(\s+)record_drop\((drop_record|drop|d)\)\s*\n'
    def replace2(match):
        indent = match.group(1)
        var = match.group(2)
        return f'''{indent}drop_id = record_drop({var})
{indent}if drop_id:
{indent}    on_drop_received(drop_id)  # 🔥 Génère parlays en temps réel!
'''
    
    new_content = re.sub(pattern2, replace2, content)
    if new_content != content:
        replacements += 1
        content = new_content
    
    # Écrire le fichier modifié
    with open(main_file, 'w') as f:
        f.write(content)
    
    print(f"✅ {replacements} appels à record_drop() modifiés")
    print("")
    print("🎉 Intégration terminée!")
    print("")
    print("📋 Prochaines étapes:")
    print("   1. Redémarre le bot")
    print("   2. Envoie un drop de test")
    print("   3. Vérifie les logs: 🔥 New drop X - Analyzing for parlays...")
    print("   4. Teste /parlays dans Telegram")
    print("")

if __name__ == "__main__":
    try:
        integrate_realtime_parlays()
    except Exception as e:
        print(f"❌ Erreur: {e}")
        print("")
        print("ℹ️  Intégration manuelle nécessaire.")
        print("   Voir: INTEGRATION_REALTIME_PARLAYS.md")
