# PLAN DE CORRECTION - SYSTÈME D'AUTHENTIFICATION RISK0

## PHASE 1: Backend API Fixes (CRITIQUE)

### 1.1 Créer l'endpoint `/api/web/quotas` manquant
**Fichier:** `/api/web_api.py`

```python
@router.get("/quotas")
async def get_user_quotas(request: Request):
    """Get user quotas for both Telegram and Website users"""
    try:
        # Get Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            raise HTTPException(status_code=401, detail="Token manquant")
        
        token = auth_header.replace('Bearer ', '')
        user_data = get_user_from_token(token)
        
        if not user_data:
            raise HTTPException(status_code=401, detail="Token invalide")
        
        db = SessionLocal()
        try:
            # Find user by ID (for website users) or telegram_id (for Telegram users)
            if user_data.get('auth_method') == 'website':
                user = db.query(User).filter(User.id == user_data['id']).first()
            else:
                # Telegram user
                telegram_id = user_data.get('tid') or user_data.get('telegramId')
                user = db.query(User).filter(User.telegram_id == telegram_id).first()
            
            if not user:
                raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
            
            # Reset quotas if new day
            today = datetime.now().date()
            if user.last_quota_reset != today:
                user.daily_ai_questions_used = 0
                user.daily_calls_under_2_percent_used = 0
                user.last_quota_reset = today
                db.commit()
            
            # Determine tier string for frontend
            tier_mapping = {
                TierLevel.FREE: 'FREE',
                TierLevel.PREMIUM: 'ALPHA'  # Map PREMIUM to ALPHA for frontend
            }
            tier_str = tier_mapping.get(user.tier, 'FREE')
            
            # Calculate quotas based on tier
            if user.tier == TierLevel.FREE:
                ai_total = user.daily_ai_questions
                ai_used = user.daily_ai_questions_used
                calls_total = user.daily_calls_under_2_percent
                calls_used = user.daily_calls_under_2_percent_used
            else:
                # PREMIUM/ALPHA users have unlimited
                ai_total = "unlimited"
                ai_used = 0
                calls_total = "unlimited"
                calls_used = 0
            
            return {
                "auth_method": user.auth_method,
                "tier": tier_str,
                "quotas": {
                    "ai_questions": {
                        "total": ai_total,
                        "used": ai_used,
                        "remaining": ai_total - ai_used if isinstance(ai_total, int) else "unlimited"
                    },
                    "calls_under_2": {
                        "total": calls_total,
                        "used": calls_used,
                        "remaining": calls_total - calls_used if isinstance(calls_total, int) else "unlimited"
                    }
                },
                "reset_time": "minuit"
            }
            
        finally:
            db.close()
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Quotas error: {e}")
        raise HTTPException(status_code=500, detail="Erreur serveur")
```

### 1.2 Créer l'endpoint `/api/web/demo/access`
**Fichier:** `/api/web_api.py`

```python
@router.get("/demo/access")
async def demo_access(request: Request):
    """Allow FREE users to access dashboard with limitations"""
    try:
        # Get Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            raise HTTPException(status_code=401, detail="Token manquant")
        
        token = auth_header.replace('Bearer ', '')
        user_data = get_user_from_token(token)
        
        if not user_data:
            raise HTTPException(status_code=401, detail="Token invalide")
        
        db = SessionLocal()
        try:
            # Find user
            if user_data.get('auth_method') == 'website':
                user = db.query(User).filter(User.id == user_data['id']).first()
            else:
                telegram_id = user_data.get('tid') or user_data.get('telegramId')
                user = db.query(User).filter(User.telegram_id == telegram_id).first()
            
            if not user:
                raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
            
            # All users can access demo (FREE with limitations, PREMIUM unlimited)
            tier_mapping = {
                TierLevel.FREE: 'FREE',
                TierLevel.PREMIUM: 'ALPHA'
            }
            tier_str = tier_mapping.get(user.tier, 'FREE')
            
            return {
                "success": True,
                "access_granted": True,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "tier": tier_str,
                    "auth_method": user.auth_method
                },
                "limitations": {
                    "ai_questions_per_day": 5 if user.tier == TierLevel.FREE else "unlimited",
                    "calls_per_day": 5 if user.tier == TierLevel.FREE else "unlimited",
                    "max_profit_percentage": 2.0 if user.tier == TierLevel.FREE else None
                },
                "redirect": "/dashboard"
            }
            
        finally:
            db.close()
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Demo access error: {e}")
        raise HTTPException(status_code=500, detail="Erreur serveur")
```

### 1.3 Corriger le token JWT pour inclure telegram_id
**Fichier:** `/api/web_api.py` - Ligne 1216-1229

```python
def generate_jwt_token(user_data: dict) -> str:
    """Generate JWT token for website authentication"""
    token_data = {
        "id": user_data["id"],
        "email": user_data["email"],
        "username": user_data["username"],
        "tier": user_data["tier"],
        "auth_method": user_data["auth_method"],
        "telegram_id": user_data.get("telegram_id"),  # Include telegram_id for compatibility
        "ts": int(time.time())
    }
    # Simple base64 encoding (matching existing Telegram token format)
    token_json = json.dumps(token_data)
    token_b64 = base64.b64encode(token_json.encode()).decode()
    return token_b64.replace('+', '-').replace('/', '_')  # URL-safe
```

## PHASE 2: Frontend Authentication Fixes (CRITIQUE)

### 2.1 Corriger la logique d'authentification dans le Dashboard
**Fichier:** `/dashboard-risk0/app/dashboard/page.tsx` - Ligne 76-83

```typescript
// CRITICAL: Check if user has access (including FREE users)
const token = localStorage.getItem('risk0_token');
let tier = '';
let authMethod = '';
try {
  const decoded = JSON.parse(atob(token || ''));
  tier = decoded.tier?.toUpperCase() || '';
  authMethod = decoded.auth_method || 'telegram';
} catch (e) {
  console.error('Error parsing token for tier:', e);
}

// Allow FREE, ALPHA, PREMIUM, ADMIN, LIFETIME users
const hasAccess = tier === 'ALPHA' || tier === 'PREMIUM' || tier === 'ADMIN' || tier === 'LIFETIME' || tier === 'FREE';

if (!hasAccess) {
  // Only block if no valid tier at all
  forceLogout();
  return;
}

// Set user with tier information
setUser({ ...tokenUser, tier, authMethod });
setAuthChecked(true);
```

### 2.2 Corriger la fonction hasWebAccess pour FREE users
**Fichier:** `/dashboard-risk0/lib/auth-utils.ts` - Ligne 78-117

```typescript
// SECURITY: Check if user has web access (including FREE users)
export async function hasWebAccess(): Promise<boolean> {
  const user = getUserFromToken();
  if (!user) return false;
  
  try {
    const token = localStorage.getItem('risk0_token');
    const decoded = JSON.parse(atob(token || ''));
    const tier = decoded.tier?.toUpperCase() || '';
    const authMethod = decoded.auth_method || 'telegram';
    
    console.log('[SECURITY CHECK]', {
      telegramId: user.telegramId,
      username: user.username,
      tier: tier,
      authMethod: authMethod,
      hasAccess: tier === 'FREE' || tier === 'ALPHA' || tier === 'PREMIUM' || tier === 'ADMIN' || tier === 'LIFETIME'
    });
    
    // FREE users can access with limitations
    if (tier === 'FREE') {
      console.log('[ACCESS GRANTED] FREE user with limitations');
      return true;
    }
    
    // ALPHA and PREMIUM tier can access
    if (tier === 'ALPHA' || tier === 'PREMIUM') {
      console.log('[ACCESS GRANTED] ALPHA/PREMIUM tier detected');
      return true;
    }
    
    // Admin access
    if (tier === 'ADMIN' || tier === 'LIFETIME') {
      console.log('[ACCESS GRANTED] Admin/Lifetime access');
      return true;
    }
    
    console.log('[ACCESS DENIED] No valid tier');
    return false;
  } catch (error) {
    console.error('Error checking web access:', error);
    return false;
  }
}
```

### 2.3 Implémenter le flow "See Demo" 
**Fichier:** `/dashboard-risk0/app/dash/page.tsx` - Remplacer le lien statique

```typescript
const handleSeeDemo = async () => {
  try {
    // Check if user is authenticated
    const token = localStorage.getItem('risk0_token');
    
    if (!token) {
      // Redirect to login if not authenticated
      window.location.href = '/login?redirect=/dash';
      return;
    }

    // Call API to verify demo access
    const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://api.syntra-trade.xyz';
    const response = await fetch(`${API_BASE}/api/web/demo/access`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });

    const data = await response.json();

    if (response.ok && data.access_granted) {
      // Redirect to dashboard with demo access
      window.location.href = data.redirect; // '/dashboard'
    } else {
      // Handle error - maybe show upgrade prompt
      console.error('Demo access denied:', data);
      alert('Accès demo refusé. Veuillez vous connecter ou créer un compte.');
    }
  } catch (error) {
    console.error('Demo access failed:', error);
    alert('Erreur lors de l\'accès au demo. Veuillez réessayer.');
  }
};

// Replace the static link with a button
<button onClick={handleSeeDemo}
  style={{ 
    display: 'inline-flex', alignItems: 'center', padding: '16px 32px', 
    background: 'linear-gradient(135deg, #10b981, #059669)', 
    borderRadius: 12, color: '#fff', fontSize: 14, fontWeight: 600, 
    textDecoration: 'none', textTransform: 'uppercase', letterSpacing: 1, 
    boxShadow: '0 8px 32px rgba(16, 185, 129, 0.4)', 
    transition: 'all 0.3s ease',
    border: 'none',
    cursor: 'pointer'
  }}>
  <svg style={{ width: 18, height: 18, marginRight: 10 }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
  </svg>
  SEE A DEMO
</button>
```

## PHASE 3: Limitations FREE Member (CRITIQUE)

### 3.1 Créer le composant LimitationsDisplay
**Fichier:** `/dashboard-risk0/components/LimitationsDisplay.tsx` (NOUVEAU)

```typescript
'use client';

import { useState, useEffect } from 'react';

interface UserLimitations {
  tier: string;
  limitations: {
    ai_questions_per_day: number | string;
    calls_per_day: number | string;
    max_profit_percentage: number | null;
  };
  quotas: {
    ai_questions: { used: number; remaining: number | string };
    calls_under_2: { used: number; remaining: number | string };
  };
}

export default function LimitationsDisplay() {
  const [limitations, setLimitations] = useState<UserLimitations | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchLimitations();
  }, []);

  const fetchLimitations = async () => {
    try {
      const token = localStorage.getItem('risk0_token');
      if (!token) return;

      const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://api.syntra-trade.xyz';
      const response = await fetch(`${API_BASE}/api/web/quotas`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        setLimitations({
          tier: data.tier,
          limitations: {
            ai_questions_per_day: data.tier === 'FREE' ? 5 : 'unlimited',
            calls_per_day: data.tier === 'FREE' ? 5 : 'unlimited',
            max_profit_percentage: data.tier === 'FREE' ? 2.0 : null
          },
          quotas: data.quotas
        });
      }
    } catch (error) {
      console.error('Error fetching limitations:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !limitations) return null;

  if (limitations.tier !== 'FREE') return null; // Only show for FREE users

  return (
    <div style={{
      padding: '16px',
      background: 'rgba(255, 193, 7, 0.1)',
      border: '1px solid rgba(255, 193, 7, 0.3)',
      borderRadius: '12px',
      marginBottom: '20px'
    }}>
      <h3 style={{ margin: '0 0 12px 0', color: '#ffc107', fontSize: '16px' }}>
        🚀 Limitations FREE Member
      </h3>
      
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
        <div>
          <p style={{ margin: '0 0 4px 0', fontSize: '12px', color: 'rgba(255,255,255,0.7)' }}>
            Questions IA
          </p>
          <p style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: '#fff' }}>
            {limitations.quotas.ai_questions.remaining}/5 restantes
          </p>
        </div>
        
        <div>
          <p style={{ margin: '0 0 4px 0', fontSize: '12px', color: 'rgba(255,255,255,0.7)' }}>
            Calls &lt;2%
          </p>
          <p style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: '#fff' }}>
            {limitations.quotas.calls_under_2.remaining}/5 restantes
          </p>
        </div>
      </div>
      
      <div style={{ 
        padding: '8px 12px', 
        background: 'rgba(16, 185, 129, 0.1)', 
        borderRadius: '8px',
        textAlign: 'center'
      }}>
        <p style={{ margin: '0 0 8px 0', fontSize: '12px', color: 'rgba(255,255,255,0.8)' }}>
          Passez ALPHA pour des quotas illimités et des profits &gt;2%
        </p>
        <a href="/pricing" style={{
          display: 'inline-block',
          padding: '6px 16px',
          background: '#10b981',
          borderRadius: '6px',
          color: '#fff',
          fontSize: '12px',
          fontWeight: 600,
          textDecoration: 'none',
          textTransform: 'uppercase'
        }}>
          Upgrade ALPHA
        </a>
      </div>
    </div>
  );
}
```

### 3.2 Intégrer LimitationsDisplay dans le Dashboard
**Fichier:** `/dashboard-risk0/app/dashboard/page.tsx`

```typescript
import LimitationsDisplay from '@/components/LimitationsDisplay';

// Dans le JSX du dashboard, ajouter après le header:
<LimitationsDisplay />
```

## PHASE 4: Tests et Validation

### 4.1 Tests Backend
```bash
# Test 1: Registration FREE user
curl -X POST https://api.syntra-trade.xyz/api/web/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","username":"testuser","password":"Test123!"}'

# Test 2: Login FREE user  
curl -X POST https://api.syntra-trade.xyz/api/web/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test123!"}'

# Test 3: Get quotas
curl -X GET https://api.syntra-trade.xyz/api/web/quotas \
  -H "Authorization: Bearer [TOKEN]"

# Test 4: Demo access
curl -X GET https://api.syntra-trade.xyz/api/web/demo/access \
  -H "Authorization: Bearer [TOKEN]"
```

### 4.2 Tests Frontend
1. **Registration Flow:** Créer compte → Vérifier redirection dashboard
2. **Login Flow:** Se connecter → Vérifier accès dashboard  
3. **See Demo Flow:** Cliquer "See Demo" → Vérifier accès dashboard
4. **Limitations Display:** Vérifier affichage quotas FREE
5. **Upgrade Prompt:** Vérifier liens vers pricing

### 4.3 Checklist de Validation
- [ ] Les utilisateurs FREE peuvent s'enregistrer
- [ ] Les utilisateurs FREE peuvent se connecter
- [ ] Le bouton "See Demo" fonctionne pour les utilisateurs authentifiés
- [ ] Le dashboard affiche les limitations FREE
- [ ] Les quotas s'affichent correctement (5/5)
- [ ] Les utilisateurs ALPHA n'ont pas de limitations
- [ ] L'upgrade prompt est visible pour les FREE users

## ORDRE D'IMPLÉMENTATION

1. **PHASE 1:** Backend API endpoints (quotas + demo access)
2. **PHASE 2:** Frontend auth fixes (dashboard + hasWebAccess)  
3. **PHASE 3:** Limitations display + See Demo button
4. **PHASE 4:** Tests complets

**Chaque phase doit être testée avant de passer à la suivante.**
