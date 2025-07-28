# 🎯 Keno Analyzer Pro - Guide de Déploiement 

## Description

Keno Analyzer Pro est une application web complète d'analyse des tirages Keno avec intelligence artificielle. L'application utilise Flask comme backend et propose plusieurs méthodes d'analyse avancées.

## Fonctionnalités

- ✅ **8 méthodes d'analyse** : Fréquences, Écarts, Cycles, Mixte, Machine Learning, Fibonacci, Sommes, Analyse Complète
- ✅ **Interface moderne** : Design responsive avec grille interactive
- ✅ **Statistiques en temps réel** : Suivi des performances de chaque méthode
- ✅ **Historique des prédictions** : Sauvegarde et suivi des résultats
- ✅ **Simulation de résultats** : Test et apprentissage automatique
- ✅ **API REST complète** : Endpoints pour toutes les fonctionnalités
- ✅ **Données réelles** : Plus de 4800 tirages historiques inclus

## Structure du Projet

```
keno-web-app/
├── src/
│   ├── main.py              # Application Flask principale
│   ├── tirages_keno.csv     # Données des tirages historiques
│   └── static/
│       └── index.html       # Interface utilisateur
├── requirements.txt         # Dépendances Python
├── README.md               # Ce fichier
└── DEPLOYMENT_GUIDE.md    # Guide de déploiement détaillé
```

## Prérequis

- Python 3.8+
- Hébergement web compatible Python/Flask (OVH Web Hosting Pro ou supérieur)
- Accès SSH ou interface de gestion de fichiers

## Installation Locale (Test)

1. **Cloner/Extraire le projet**
   ```bash
   cd keno-web-app
   ```

2. **Créer un environnement virtuel**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Linux/Mac
   # ou
   venv\Scripts\activate     # Windows
   ```

3. **Installer les dépendances**
   ```bash
   pip install -r requirements.txt
   ```

4. **Lancer l'application**
   ```bash
   python src/main.py
   ```

5. **Accéder à l'application**
   - Ouvrir http://localhost:5000 dans votre navigateur

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

## Configuration de Production

### Sécurité

- Changer la `SECRET_KEY` dans `main.py`
- Configurer HTTPS
- Limiter les requêtes CORS si nécessaire
- Activer les logs de sécurité

### Performance

- Utiliser un serveur WSGI (Gunicorn, uWSGI)
- Configurer un reverse proxy (Nginx)
- Optimiser la base de données SQLite ou migrer vers PostgreSQL
- Mettre en place un cache Redis si nécessaire

### Monitoring

- Configurer les logs applicatifs
- Surveiller les performances
- Mettre en place des alertes

## API Endpoints

- `GET /` - Interface utilisateur
- `POST /api/analyze` - Analyse des tirages
- `GET /api/stats` - Statistiques de performance
- `GET /api/user-predictions` - Prédictions utilisateurs
- `POST /api/simulate` - Simulation de résultats
- `POST /api/update` - Mise à jour des données
- `GET /health` - Vérification de l'état du service

## Maintenance

### Mise à jour des données

Les données de tirages peuvent être mises à jour en remplaçant le fichier `tirages_keno.csv` ou en implémentant un système de scraping automatique.

### Sauvegarde

- Sauvegarder régulièrement la base de données SQLite
- Sauvegarder les fichiers de configuration
- Conserver une copie des logs importants

## Support

Pour toute question ou problème :
- Vérifier les logs de l'application
- Consulter la documentation Flask
- Contacter le support technique OVH si nécessaire

## Licence

Ce projet est fourni tel quel pour usage personnel ou commercial.

---

**Version :** 1.0.0  
**Dernière mise à jour :** Juillet 2025  
**Compatibilité :** Python 3.8+, Flask 3.x

