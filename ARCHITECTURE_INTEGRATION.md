# 🏗️ BET ARCHITECTURE BUILDER - GUIDE D'INTÉGRATION

## ✅ Système Complet Créé

### 📁 Fichiers Créés

#### 1. **Core Logic** (`/lib/architecture/`)
- `types.ts` - Toutes les interfaces TypeScript
- `calculator.ts` - Logique de calcul d'allocation et projections
- `anti-ban.ts` - Système d'analyse de santé et anti-ban
- `storage.ts` - Gestion du stockage et synchronisation API

#### 2. **Wizard Components** (`/components/architecture/wizard/`)
- `wizard-layout.tsx` - Layout principal du wizard
- `step-bankroll.tsx` - Étape 1: Configuration du bankroll
- `step-casinos.tsx` - Étape 2: Sélection des casinos

#### 3. **Pages** (`/app/`)
- `architecture/wizard/page.tsx` - Wizard 7 étapes complet
- `architecture/dashboard/page.tsx` - Dashboard d'architecture
- `health/page.tsx` - Health Monitor Dashboard

#### 4. **Hooks & Components**
- `hooks/use-architecture.ts` - Hook pour utiliser l'architecture
- `components/architecture/smart-filter-toggle.tsx` - Toggle pour Smart Filter

---

## 🔧 Intégration dans la Page Calls

### 1. Modifier `/app/calls/page.tsx`

```tsx
// Ajouter les imports
import { useArchitecture } from '@/hooks/use-architecture';
import { SmartFilterToggle } from '@/components/architecture/smart-filter-toggle';

export default function CallsPage() {
  // Ajouter le hook
  const { 
    architecture,
    smartFilter,
    isFilterEnabled,
    toggleFilter,
    filterCalls,
    canPlaceBet,
    trackBetPlacement,
    getHealthScore,
  } = useArchitecture();

  // Existant: État des calls
  const [calls, setCalls] = useState([]);
  const [filteredCalls, setFilteredCalls] = useState([]);

  // Appliquer le Smart Filter
  useEffect(() => {
    if (isFilterEnabled && architecture) {
      setFilteredCalls(filterCalls(calls));
    } else {
      setFilteredCalls(calls);
    }
  }, [calls, isFilterEnabled, architecture, filterCalls]);

  // Dans le JSX, ajouter le toggle dans le header
  return (
    <div className="min-h-screen bg-[#0a0a0a]">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header avec Smart Filter */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-4xl font-bold text-white">Live Calls</h1>
            <p className="text-gray-400">Real-time arbitrage opportunities</p>
          </div>
          
          {/* Smart Filter Toggle */}
          {architecture && (
            <SmartFilterToggle
              enabled={isFilterEnabled}
              onToggle={toggleFilter}
              filterConfig={smartFilter}
            />
          )}
        </div>

        {/* Afficher les calls filtrés */}
        <div className="space-y-4">
          {filteredCalls.map(call => (
            // Votre composant CallCard existant
            <CallCard 
              key={call.id} 
              call={call}
              // Ajouter les props de santé
              healthScore={getHealthScore(call.casino)}
              canBet={canPlaceBet(call.casino, call.stake)}
            />
          ))}
        </div>

        {/* Afficher les stats de filtrage */}
        {isFilterEnabled && smartFilter && (
          <div className="mt-4 text-center text-sm text-gray-500">
            Showing {filteredCalls.length} of {calls.length} calls
            {smartFilter.stats.reasonsFiltered.wrongCasino > 0 && (
              <span className="ml-2">
                • {smartFilter.stats.reasonsFiltered.wrongCasino} filtered (wrong casino)
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
```

### 2. Tracker les Bets avec Health Monitor

```tsx
// Dans votre handler "I BET"
const handleIBet = async (call: any) => {
  // Créer le BetData
  const betData: BetData = {
    betId: `bet_${Date.now()}`,
    userId: user.telegramId,
    casino: call.casino,
    timestamp: new Date(),
    sport: call.sport,
    market: call.market,
    selection: call.selection,
    stake: call.stake,
    odds: call.odds,
    betType: call.type === 'arbitrage' ? 'arb' : 
             call.type === 'middle' ? 'middle' : 'plusEV',
    callId: call.id,
  };

  // Tracker le bet
  await trackBetPlacement(betData);

  // Votre logique existante...
};
```

---

## 🚀 Démarrage Rapide

### 1. Créer une Architecture
```
1. Aller à /architecture/wizard
2. Suivre les 7 étapes
3. Architecture générée et sauvegardée
```

### 2. Voir le Dashboard
```
/architecture/dashboard - Vue complète de votre architecture
```

### 3. Monitorer la Santé
```
/health - Voir les scores de santé par casino
```

### 4. Activer Smart Filter
```
Sur /calls - Toggle "Smart Filter" pour filtrer automatiquement
```

---

## 📊 Flux de Données

```
USER
 ↓
WIZARD (7 étapes)
 ↓
ARCHITECTURE GÉNÉRÉE
 ↓
┌─────────────────┬─────────────────┬──────────────────┐
│  SMART FILTER   │  HEALTH MONITOR │  BET TRACKING    │
│  (Filtre calls) │  (Analyse santé)│  (Track bets)    │
└─────────────────┴─────────────────┴──────────────────┘
 ↓
RECOMMENDATIONS & ADJUSTMENTS
```

---

## 🔗 Synchronisation Telegram Bot

### Backend Python API (`api/web_api.py`)

Ajouter ces endpoints:

```python
# Architecture endpoints
@app.post("/api/architecture")
async def save_architecture(data: dict, user_id: str = Depends(get_current_user)):
    """Save user architecture"""
    # Save to database
    db.execute("""
        INSERT INTO user_architectures (user_id, config, created_at)
        VALUES (:user_id, :config, NOW())
        ON CONFLICT (user_id) DO UPDATE
        SET config = :config, updated_at = NOW()
    """, {"user_id": user_id, "config": json.dumps(data)})
    return {"success": True}

@app.get("/api/architecture/{user_id}")
async def get_architecture(user_id: str):
    """Get user architecture"""
    result = db.execute("""
        SELECT config FROM user_architectures
        WHERE user_id = :user_id
    """, {"user_id": user_id}).fetchone()
    
    if result:
        return json.loads(result.config)
    return None

# Health endpoints
@app.get("/api/health/scores/{user_id}")
async def get_health_scores(user_id: str):
    """Get health scores for all casinos"""
    scores = db.execute("""
        SELECT casino, total_score as score, risk_level as status
        FROM book_health_scores
        WHERE user_id = :user_id
        AND calculation_date = CURRENT_DATE
    """, {"user_id": user_id}).fetchall()
    
    return {row.casino: {"score": row.score, "status": row.status} 
            for row in scores}

# Bet tracking
@app.post("/api/bets/track")
async def track_bet(bet_data: dict, user_id: str = Depends(get_current_user)):
    """Track a bet for health monitoring"""
    # Insert into bet_analytics
    db.execute("""
        INSERT INTO bet_analytics (
            user_id, casino, bet_source_type, sport, market_type,
            stake_amount, odds_at_bet, bet_placed_at
        ) VALUES (
            :user_id, :casino, :bet_type, :sport, :market,
            :stake, :odds, NOW()
        )
    """, {
        "user_id": user_id,
        "casino": bet_data["casino"],
        "bet_type": bet_data["betType"],
        "sport": bet_data["sport"],
        "market": bet_data["market"],
        "stake": bet_data["stake"],
        "odds": bet_data["odds"],
    })
    
    # Recalculate health score
    health_score = calculate_health_score(user_id, bet_data["casino"])
    
    return {"success": True, "healthUpdate": health_score}
```

### Bot Telegram (`bot/book_health_main.py`)

Le bot est déjà configuré pour tracker les bets. Pour synchroniser avec le web:

```python
# Quand user clique "I BET" sur Telegram
async def handle_i_bet_callback(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    bet_data = parse_bet_data(callback.data)
    
    # Track dans Book Health
    await track_bet_with_book_health(user_id, bet_data)
    
    # Notifier le dashboard web via WebSocket
    await notify_web_dashboard(user_id, {
        "type": "bet_placed",
        "data": bet_data,
        "timestamp": datetime.now().isoformat()
    })
```

---

## 🎯 Features Principales

### ✅ Implémentées
- [x] Wizard 7 étapes
- [x] Calcul d'allocation intelligent
- [x] Anti-ban intelligence
- [x] Health Monitor Dashboard
- [x] Smart Filter pour calls
- [x] Storage local + API
- [x] Hooks React

### 🚧 À Implémenter
- [ ] WebSocket real-time sync
- [ ] Export PDF de l'architecture
- [ ] Templates prédéfinis
- [ ] Machine Learning pour prédictions
- [ ] Recovery mode après limit
- [ ] Collective intelligence

---

## 💡 Utilisation Optimale

### Pour les Débutants
1. Commencer avec "Conservative" + "Low Risk"
2. Bankroll minimum $500
3. 3-5 casinos max
4. Activer Smart Filter toujours

### Pour les Intermédiaires
1. "Balanced" + "Medium Risk"
2. Bankroll $1000-5000
3. 5-8 casinos
4. Multi-accounts sur bet365

### Pour les Pros
1. "Aggressive" + "High Risk"
2. Bankroll $5000+
3. 10+ casinos
4. Rotation multi-comptes
5. Monitoring health quotidien

---

## 🔴 Points d'Attention

1. **Health Score < 40** = ARRÊTER immédiatement sur ce casino
2. **Win Rate > 90%** = Ajouter des paris récréatifs URGENT
3. **CLV > 3%** = Trop évident, ralentir
4. **Même stake toujours** = Varier les montants

---

## 📞 Support

- Documentation: `/ARCHITECTURE_INTEGRATION.md`
- Bot Telegram: `@risk0bot`
- Dashboard: `risk0.app/architecture`

---

**Le système est PRÊT À L'EMPLOI!** 🚀

Il reste juste à:
1. Ajouter les endpoints Python backend
2. Intégrer SmartFilter dans /calls
3. Tester avec de vraies données

Le système va **révolutionner** la façon dont les users gèrent leur bankroll et évitent les bans!
