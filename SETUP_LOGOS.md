# Configuration des Logos de Casinos

## Structure des fichiers

Mets tes fichiers PNG de logos dans le dossier `casino_logos/` avec ces noms exacts:

- `888sport.png`
- `bet365.png`
- `bet99.png`
- `betsson.png`
- `betvictor.png`
- `betway.png`
- `bwin.png`
- `casumo.png`
- `coolbet.png`
- `ibet.png`
- `jackpotbet.png`
- `leovegas.png`
- `miseojeu.png`
- `pinnacle.png`
- `proline.png`
- `sportsinteraction.png`
- `stake.png`
- `tonybet.png`

## Mapping et alias

Le fichier `casino_logos.json` contient:
- **name**: Nom canonique du casino
- **logo_file**: Nom du fichier PNG
- **aliases**: Variantes OCR (ex: "costser" → Coolbet)
- **ocr_patterns**: Patterns à chercher dans l'OCR
- **emoji**: Emoji de fallback si pas de logo

## Comment ça marche

1. L'OCR lit le texte de l'image
2. Le système cherche les patterns dans `ocr_patterns`
3. Si trouvé, utilise le nom canonique + logo PNG
4. Les boutons Telegram affichent l'emoji + nom

## Test rapide

```bash
# Vérifie que tous les logos sont présents
ls -la casino_logos/
```

## Ajout d'un nouveau casino

1. Ajoute le PNG dans `casino_logos/`
2. Ajoute l'entrée dans `casino_logos.json`:
```json
{
  "name": "NouveauCasino",
  "aliases": ["nouveau casino"],
  "emoji": "🎲",
  "logo_file": "nouveaucasino.png",
  "colors": ["blue"],
  "ocr_patterns": ["NouveauCasino", "nouveau casino"]
}
```
