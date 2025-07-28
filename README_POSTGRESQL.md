# Projet Keno - Version PostgreSQL avec Persistance des Données

## 🚀 Nouvelles Fonctionnalités

### 1. Base de Données PostgreSQL
- **Persistance des données** : Tous les tirages, prédictions et erreurs du modèle sont maintenant stockés dans PostgreSQL
- **Pas de perte de données** lors des redémarrages sur Render.com
- **Performances améliorées** avec indexation optimisée

### 2. Gestion des Prédictions Utilisateur
- **Stockage par utilisateur** : `utilisateur1`, `utilisateur2`, etc.
- **Historique complet** des prédictions avec évaluation
- **Statistiques personnalisées** par utilisateur

### 3. Suivi des Erreurs du Modèle
- **Enregistrement automatique** des erreurs de prédiction
- **Analyse détaillée** des performances par modèle
- **Métriques de précision** pour chaque utilisateur

### 4. Interface d'Administration
- **Actualisation des tirages** sans redémarrage du serveur
- **Relancement de l'entraînement ML** à la demande
- **Nettoyage des anciennes données**
- **Monitoring du système** en temps réel

## 🔧 Configuration

### Variables d'Environnement
```bash
DATABASE_URL=postgresql://kenos_user:qYGSudoftPvnoxaT9Seh5IP4itP1kK0a@dpg-d1o9j7s9c44c73fapc40-a.frankfurt-postgres.render.com/kenos
```

### Démarrage
```bash
python3 run_app.py
```

## 📊 Nouvelles Routes API

### Prédictions Utilisateur
- `GET /api/predictions?user_id=utilisateur1` - Récupérer les prédictions
- `POST /api/predictions` - Sauvegarder de nouvelles prédictions
- `POST /api/evaluate-prediction` - Évaluer une prédiction avec les résultats réels

### Statistiques Utilisateur
- `GET /api/user-stats/<user_id>` - Statistiques d'un utilisateur
- `GET /api/model-errors/<user_id>` - Erreurs du modèle pour un utilisateur

### Administration (Token requis)
- `POST /api/admin/refresh-data` - Actualiser les tirages
- `POST /api/admin/retrain-ml` - Relancer l'entraînement ML
- `GET /api/admin/status` - Statut du système
- `POST /api/admin/clear-predictions` - Nettoyer les anciennes données

### Interface d'Administration
- `GET /admin` - Interface web d'administration

## 🔐 Sécurité

### Token d'Administration
Le token par défaut est : `keno_admin_2024_secure_token`

**⚠️ IMPORTANT** : Changez ce token en production dans `keno_web_app.py` :
```python
ADMIN_TOKEN = "votre_token_securise_ici"
```

### Utilisation du Token
```javascript
// Dans l'interface d'administration
headers: {
    'Authorization': 'Bearer keno_admin_2024_secure_token'
}
```

## 📈 Structure de la Base de Données

### Tables Principales
1. **tirages_keno** - Stockage des tirages historiques
2. **user_predictions** - Prédictions des utilisateurs
3. **model_errors** - Erreurs et performances des modèles
4. **ml_models** - Métadonnées des modèles ML
5. **analysis_results** - Résultats d'analyses

### Avantages
- ✅ **Persistance garantie** sur Render.com
- ✅ **Scalabilité** pour de nombreux utilisateurs
- ✅ **Performances optimisées** avec indexation
- ✅ **Sauvegarde automatique** des données
- ✅ **Analyse des performances** par utilisateur

## 🎯 Utilisation

### Pour les Utilisateurs
1. Effectuer des prédictions via l'interface web
2. Les prédictions sont automatiquement sauvegardées avec votre ID utilisateur
3. Consulter vos statistiques et historique

### Pour l'Administrateur
1. Accéder à `/admin` avec le token d'administration
2. Actualiser les données de tirages sans redémarrage
3. Relancer l'entraînement ML si nécessaire
4. Surveiller les performances du système

## 🔄 Migration depuis l'Ancienne Version

Les anciennes données CSV sont automatiquement importées dans PostgreSQL au premier démarrage.

## 📞 Support

Pour toute question ou problème, vérifiez :
1. La connexion à la base de données PostgreSQL
2. Les logs de l'application
3. L'interface d'administration pour le statut du système

