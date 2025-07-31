# 🎯 Keno Analyzer Pro - Plateforme d'Analyse Keno avec IA

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-blue.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Description

Keno Analyzer Pro est une application web complète d'analyse des tirages Keno avec intelligence artificielle. L'application utilise Flask comme backend et propose plusieurs méthodes d'analyse avancées.

## ✨ Fonctionnalités Avancées

### 🔍 Analyse Avancée
- **Méthodes d'analyse** : 8 méthodes intégrées (Fréquences, Écarts, Cycles, Mixte, Machine Learning, Fibonacci, Sommes, Analyse Complète)
- **Analyse des finales** : Détection des motifs de numéros finaux
- **Analyse des écarts** : Identification des tendances basées sur les écarts entre les numéros
- **Analyse temporelle** : Suivi des performances par jour de la semaine et heure
- **Simulations Monte Carlo** : Prédictions basées sur des milliers de simulations

### 🎨 Interface Utilisateur
- **Tableau de bord interactif** : Visualisation des données en temps réel
- **Système d'authentification** : Comptes utilisateurs sécurisés
- **Espace administrateur** : Gestion complète des utilisateurs et des modèles
- **Design responsive** : Compatible mobile et desktop
- **Thème sombre/clair** : Confort visuel personnalisable

### 🤖 Intelligence Artificielle
- **Modèles ML entraînables** : Random Forest, Réseaux de Neurones
- **Métriques détaillées** : Précision, Rappel, F1-Score
- **Historique des entraînements** : Suivi des performances des modèles
- **Auto-optimisation** : Ajustement automatique des hyperparamètres
- **Sélection de caractéristiques** : Identification des facteurs les plus prédictifs

## 🗂 Structure du Projet

```
keno-analyzer/
├── src/
│   ├── main.py                     # Application Flask principale
│   ├── database_manager_postgresql.py  # Gestionnaire de base de données
│   ├── auth_system.py              # Système d'authentification
│   ├── keno_*_analysis.py          # Modules d'analyse avancée
│   ├── static/
│   │   ├── css/                   # Feuilles de style
│   │   ├── js/                    # Scripts JavaScript
│   │   └── img/                   # Images et ressources
│   └── templates/
│       ├── admin/                 # Vues administrateur
│       ├── auth/                  # Vues d'authentification
│       └── *.html                 # Templates principaux
├── requirements.txt               # Dépendances Python
├── README.md                      # Ce fichier
└── .env.example                   # Exemple de configuration
```

## ⚙️ Prérequis

- **Python 3.8+** avec pip
- **PostgreSQL 13+**
- **Compte SendGrid** (pour la réinitialisation des mots de passe)
- **Variables d'environnement** (voir `.env.example`)
  - `DATABASE_URL` : URL de connexion PostgreSQL
  - `SECRET_KEY` : Clé secrète pour les sessions
  - `SENDGRID_API_KEY` : Clé API SendGrid (optionnel)
  - `FLASK_ENV` : Environnement (development/production)

## 🚀 Installation Locale

1. **Cloner le dépôt**
   ```bash
   git clone [URL_DU_DEPOT]
   cd keno-analyzer
   ```

2. **Configurer l'environnement**
   ```bash
   # Copier le fichier d'exemple
   cp .env.example .env
   
   # Créer et activer l'environnement virtuel
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # OU
   .\venv\Scripts\activate  # Windows
   
   # Installer les dépendances
   pip install -r requirements.txt
   ```

3. **Configurer la base de données**
   ```bash
   # Créer la base de données PostgreSQL
   createdb keno_analyzer
   
   # Initialiser le schéma
   python -c "from database_manager_postgresql import PostgreSQLManager; db = PostgreSQLManager(); db.create_schema_if_needed()"
   ```

4. **Lancer l'application**
   ```bash
   # Mode développement
   flask run --debug
   
   # OU en production avec Gunicorn
   gunicorn "src.main:create_app()" -w 4 -b 0.0.0.0:5000
   ```

5. **Accéder à l'application**
   - Interface utilisateur : http://localhost:5000
   - Interface admin : http://localhost:5000/admin
   - API Documentation : http://localhost:5000/api/docs

## Déploiement sur OVH

### Option 1 : Hébergement Web OVH (Recommandé)

1. **Préparer les fichiers**
   - Uploader tous les fichiers du dossier `src/` vers le répertoire web
   - Placer `main.py` à la racine du domaine
   - Placer `index.html` dans le dossier `static/`

2. **Configuration OVH**
   - Activer Python dans l'espace client OVH
   - Configurer le fichier `.htaccess` si nécessaire
   - Installer les dépendances via SSH ou l'interface OVH

3. **Variables d'environnement**
   - Configurer `FLASK_ENV=production`
   - Ajuster les paramètres de sécurité

### Option 2 : VPS OVH

1. **Connexion SSH**
   ```bash
   ssh user@your-vps-ip
   ```

2. **Installation des dépendances système**
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip python3-venv nginx
   ```

3. **Déploiement de l'application**
   ```bash
   git clone [votre-repo] /var/www/keno-analyzer
   cd /var/www/keno-analyzer
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Configuration Nginx**
   - Créer un fichier de configuration Nginx
   - Configurer le proxy vers l'application Flask
   - Activer HTTPS avec Let's Encrypt

5. **Service systemd**
   - Créer un service pour démarrer automatiquement l'application
   - Configurer les logs et la surveillance

## 🔒 Configuration de Production

### Sécurité
- **Toujours** utiliser HTTPS en production
- Configurer `SECRET_KEY` avec une valeur forte
- Activer l'authentification à deux facteurs pour les comptes admin
- Configurer les en-têtes de sécurité (CSP, HSTS, etc.)
- Mettre en place une limitation de débit (rate limiting)

### Performance
- **Serveur WSGI** : Gunicorn avec 2-4 workers (selon les ressources)
- **Base de données** : PostgreSQL avec connexion pool
- **Cache** : Redis pour les sessions et le cache de requêtes
- **CDN** : Pour les ressources statiques
- **Optimisation** : Activer GZIP, minifier les assets

### Surveillance
- **Logs** : Centralisation avec ELK ou équivalent
- **Métriques** : Prometheus + Grafana
- **Alertes** : Seuils sur les erreurs et la performance
- **Sauvegardes** : Automatisation des backups de la base de données

## 🌐 API Endpoints

### Authentification
- `POST /login` - Connexion utilisateur
- `POST /register` - Création de compte
- `POST /forgot-password` - Réinitialisation du mot de passe
- `POST /reset-password` - Définition d'un nouveau mot de passe

### Analyse
- `GET /api/analyze` - Analyse complète des tirages
- `GET /api/analyze/frequencies` - Analyse des fréquences
- `GET /api/analyze/gaps` - Analyse des écarts
- `GET /api/analyze/cycles` - Analyse des cycles
- `POST /api/simulate` - Simulation de résultats

### Administration
- `GET /admin` - Tableau de bord administrateur
- `GET /admin/users` - Gestion des utilisateurs
- `POST /admin/train-model` - Entraîner un nouveau modèle
- `GET /admin/training-runs` - Historique des entraînements

### Statistiques
- `GET /api/stats/performance` - Performances des modèles
- `GET /api/stats/usage` - Statistiques d'utilisation
- `GET /api/health` - État du service

## 🔄 Maintenance

### Mise à jour des Données
- **Mise à jour automatique** : Toutes les heures via une tâche planifiée
- **Mise à jour manuelle** : Via l'interface d'administration
- **Import/Export** : Formats CSV et JSON supportés

### Sauvegardes
- **Base de données** : Dumps PostgreSQL quotidiens
- **Modèles ML** : Sauvegarde des versions stables
- **Logs** : Rotation et archivage automatiques

### Mises à jour
- **Sécurité** : Mise à jour automatique des dépendances
- **Fonctionnalités** : Releases sémantiques (SemVer)
- **Documentation** : Mise à jour continue

## 📚 Documentation Complète

- [Guide d'installation détaillé](docs/INSTALLATION.md)
- [Guide d'administration](docs/ADMIN_GUIDE.md)
- [Documentation de l'API](docs/API.md)
- [FAQ](docs/FAQ.md)

## 🤝 Contribuer

Les contributions sont les bienvenues ! Voici comment contribuer :

1. Fork le projet
2. Crée ta branche (`git checkout -b feature/AmazingFeature`)
3. Commit tes changements (`git commit -m 'Add some AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvre une Pull Request

## 📝 Licence

Ce projet est sous licence MIT - voir le fichier [LICENSE](LICENSE) pour plus de détails.

## 🙏 Remerciements

- À toute l'équipe de développement pour leur travail acharné
- À la communauté open source pour les incroyables bibliothèques utilisées
- À vous, utilisateur, pour votre confiance et vos retours

---

**Version :** 2.0.0  
**Dernière mise à jour :** 31 Juillet 2025  
**Compatibilité :** Python 3.8+, Flask 3.x, PostgreSQL 13+

