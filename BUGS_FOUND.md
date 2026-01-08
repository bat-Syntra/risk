# BUGS IDENTIFIÉS - SYSTÈME D'AUTHENTIFICATION RISK0

## BUG 1: Détection du Membership Tier (CRITIQUE)
- **Fichier:** `/dashboard-risk0/lib/auth-utils.ts`
- **Ligne:** 87-95
- **Problème:** La fonction `hasWebAccess()` ne reconnaît que les tiers "ALPHA" et "PREMIUM", mais les utilisateurs website sont créés avec le tier "FREE". Les utilisateurs FREE sont bloqués et ne peuvent pas accéder au dashboard.
- **Impact:** Les utilisateurs FREE ne sont pas reconnus comme ayant accès au dashboard avec limitations

## BUG 2: Token JWT ne contient pas le tier (CRITIQUE)
- **Fichier:** `/api/web_api.py`
- **Ligne:** 1216-1229
- **Problème:** La fonction `generate_jwt_token()` inclut le tier dans le token, mais le frontend ne l'utilise pas correctement pour déterminer les permissions
- **Impact:** Le frontend ne peut pas différencier les tiers FREE/ALPHA/PREMIUM

## BUG 3: Flow "See Demo" inexistant (CRITIQUE)
- **Fichier:** `/dashboard-risk0/app/dash/page.tsx`
- **Ligne:** 144
- **Problème:** Le bouton "SEE A DEMO" redirige vers `/dashboard` mais il n'y a pas de logique spécifique pour gérer l'accès demo des utilisateurs FREE
- **Impact:** Le bouton "See Demo" ne donne pas accès à la plateforme avec limitations

## BUG 4: Vérification des limitations FREE inexistante (CRITIQUE)
- **Fichier:** Manquant
- **Ligne:** N/A
- **Problème:** Il n'y a pas de middleware ou de logique frontend pour appliquer les limitations FREE (5 calls/jour, 5 questions IA/jour)
- **Impact:** Les limitations FREE ne sont pas appliquées dans l'interface

## BUG 5: Quotas Display ne gère pas les utilisateurs Website (MAJEUR)
- **Fichier:** `/dashboard-risk0/components/QuotasDisplay.tsx`
- **Ligne:** Toute la logique
- **Problème:** Le composant QuotasDisplay utilise l'API `/api/web/quotas` qui attend un token Telegram, mais les utilisateurs website ont des tokens différents
- **Impact:** Les quotas ne s'affichent pas pour les utilisateurs website

## BUG 6: Redirection Dashboard pour FREE users (MAJEUR)
- **Fichier:** `/dashboard-risk0/app/dashboard/page.tsx`
- **Ligne:** 76-83
- **Problème:** La logique vérifie seulement les tiers 'ALPHA', 'PREMIUM', 'ADMIN', 'LIFETIME' mais pas 'FREE'. Les utilisateurs FREE sont redirigés ou bloqués
- **Impact:** Les utilisateurs FREE ne peuvent pas accéder au dashboard

## BUG 7: API Quotas incompatible avec Website Users (MAJEUR)
- **Fichier:** `/api/web_api.py`
- **Ligne:** 1523-1570
- **Problème:** L'endpoint `/api/web/quotas` n'existe pas dans le code fourni, mais est appelé par le frontend
- **Impact:** Les quotas ne peuvent pas être récupérés pour les utilisateurs website

## BUG 8: Mismatch entre Telegram et Website Tier Systems (MAJEUR)
- **Fichier:** Multiple files
- **Ligne:** N/A
- **Problème:** Le système Telegram utilise TierLevel.FREE/PREMIUM, mais le frontend cherche des strings "ALPHA", "PREMIUM", etc.
- **Impact:** Incompatibilité entre les systèmes de tiers

## BUG 9: Pas de route API pour "See Demo" (CRITIQUE)
- **Fichier:** Manquant
- **Ligne:** N/A
- **Problème:** Il n'y a pas d'endpoint API pour gérer l'accès demo des utilisateurs FREE
- **Impact:** Impossible d'implémenter le flow "See Demo" correctement

## BUG 10: Frontend Auth Logic incomplète (MAJEUR)
- **Fichier:** `/dashboard-risk0/lib/auth-utils.ts`
- **Ligne:** 78-117
- **Problème:** La fonction `hasWebAccess()` fait un appel à `/api/user/${telegramId}` qui n'existe pas pour les utilisateurs website (telegram_id négatif)
- **Impact:** L'authentification échoue pour les utilisateurs website

## RÉSUMÉ DES PROBLÈMES CRITIQUES

### 1. ARCHITECTURE INCOMPATIBLE
- Le système Telegram et Website utilisent des logiques d'authentification différentes
- Les tiers ne sont pas mappés correctement entre backend et frontend
- Les tokens JWT ne sont pas traités uniformément

### 2. LOGIQUE FREE MEMBER MANQUANTE
- Aucune logique pour gérer les utilisateurs FREE avec limitations
- Pas de middleware pour appliquer les quotas (5 calls, 5 questions IA)
- Pas d'interface pour afficher les limitations

### 3. API ENDPOINTS MANQUANTS
- Pas d'endpoint pour l'accès demo
- Pas d'endpoint quotas compatible website
- Pas d'endpoint pour vérifier les permissions FREE

### 4. FRONTEND INCOMPLET
- Le dashboard bloque les utilisateurs FREE
- Les composants ne gèrent pas les limitations
- Le flow "See Demo" n'est pas implémenté

## PRIORITÉ DE CORRECTION

1. **CRITIQUE:** Créer la logique FREE member dans le dashboard
2. **CRITIQUE:** Créer l'endpoint API pour quotas website
3. **CRITIQUE:** Implémenter le middleware de limitations
4. **MAJEUR:** Corriger la détection des tiers dans le frontend
5. **MAJEUR:** Créer l'endpoint "See Demo"
