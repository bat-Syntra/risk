# Configuration de la Détection Visuelle des Logos

## Installation

1. **Installe OpenCV** (pour la reconnaissance d'images) :
```bash
pip install opencv-python numpy
```

2. **Place tes logos PNG** dans `casino_logos/` :
```
casino_logos/
├── 888sport.png
├── bet365.png
├── bet99.png
├── betsson.png
├── betvictor.png
├── betway.png
├── bwin.png
├── casumo.png
├── coolbet.png
├── ibet.png
├── jackpotbet.png
├── leovegas.png
├── miseojeu.png
├── pinnacle.png
├── proline.png
├── sportsinteraction.png
├── stake.png
└── tonybet.png
```

## Comment ça marche

1. **Template Matching** : Compare les logos dans les screenshots avec tes fichiers PNG
2. **Multi-échelle** : Teste différentes tailles (50%, 75%, 100%, 125%, 150%)
3. **Seuil de confiance** : Match accepté si similarité > 70%
4. **Priorité visuelle** : Si 2 logos détectés visuellement → utilise-les en priorité sur l'OCR

## Avantages

✅ **Plus précis** : Jamais d'erreur "costser" → trouve vraiment Coolbet par le logo
✅ **Résistant OCR** : Même si le texte est mal lu, le logo est reconnu
✅ **Automatique** : Pas besoin d'API externe, tout en local

## Test rapide

```python
# Test standalone
python logo_detector.py

# Avec une image test
# Place un screenshot "test_screenshot.png" puis:
python logo_detector.py
```

## Configuration avancée

Dans `.env` :
```bash
# Seuil de confiance (0.0 à 1.0)
LOGO_CONFIDENCE_THRESHOLD=0.70

# Activer debug
LOGO_DEBUG=1
```

## Workflow complet

1. 📸 Screenshot reçu
2. 🔍 Détection visuelle des logos (OpenCV)
3. 📝 OCR du texte (Tesseract)
4. 🎯 Si 2+ logos trouvés visuellement → les utilise
5. 📊 Sinon combine visuel + OCR pour meilleure précision
6. ✅ Résultat: bon casino identifié !

## Troubleshooting

- **"Logo detection not available"** : Installe `pip install opencv-python`
- **Logos non détectés** : Vérifie que les PNG sont dans `casino_logos/`
- **Mauvaise détection** : Ajuste le seuil dans `logo_detector.py` (threshold)

## Ajout d'un nouveau casino

1. Ajoute le PNG : `casino_logos/nouveaucasino.png`
2. Met à jour `casino_logos.json` :
```json
{
  "name": "NouveauCasino",
  "logo_file": "nouveaucasino.png",
  "aliases": ["nouveau", "newcasino"],
  "emoji": "🎲"
}
```
3. Redémarre le bridge
