# 🚀 Guide d'Installation - Keno Analyzer Pro

> **Note** : Ce guide couvre l'installation complète de Keno Analyzer Pro, y compris l'environnement de développement et de production.

## 📋 Prérequis Système

### Système d'Exploitation
- **Linux** : Ubuntu 20.04+ (recommandé)
- **Windows** : Windows 10+ avec WSL2
- **macOS** : macOS 10.15+

### Logiciels Requis
- **Python** : 3.8+ (3.11 recommandé)
- **Base de données** : PostgreSQL 13+ (obligatoire pour la production)
- **Git** : Pour le versioning (recommandé)
- **Pip** : Gestionnaire de paquets Python
- **virtualenv** : Pour les environnements virtuels (recommandé)

## 🔧 Installation Étape par Étape

### 1. Préparation de l'Environnement

#### Installation de Python et pip
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip python3-venv

# CentOS/RHEL
sudo yum install python3 python3-pip

# macOS (avec Homebrew)
brew install python3
```

#### Installation de PostgreSQL (Recommandé)
```bash
# Ubuntu/Debian
sudo apt install postgresql postgresql-contrib

# CentOS/RHEL
sudo yum install postgresql-server postgresql-contrib

# macOS
brew install postgresql
```

### 2. Configuration de la Base de Données PostgreSQL

#### Installation et Configuration
```bash
# Installation (Ubuntu/Debian)
sudo apt update
sudo apt install postgresql postgresql-contrib

# Démarrer et activer le service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Se connecter à PostgreSQL
sudo -u postgres psql
```

#### Création de l'Utilisateur et de la Base de Données
```sql
-- Créer un utilisateur dédié
CREATE USER keno_user WITH PASSWORD 'votre_mot_de_passe_securise';

-- Créer la base de données
CREATE DATABASE keno_analyzer OWNER keno_user;

-- Accorder les privilèges
GRANT ALL PRIVILEGES ON DATABASE keno_analyzer TO keno_user;

-- Pour les extensions PostgreSQL (optionnel mais recommandé)
\c keno_analyzer
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Vérifier la création
\du
\l
\q
```

#### Vérification de la Connexion (Optionnel)
```bash
# Tester la connexion
psql -U keno_user -d keno_analyzer -h 127.0.0.1 -W
```

> **Note** : Pour des raisons de performance et de fiabilité, PostgreSQL est obligatoire pour les environnements de production. SQLite n'est pas supporté en production.

### 3. Installation du Projet

#### Récupération du Code Source
```bash
# Cloner le dépôt (si disponible)
git clone https://github.com/votre-utilisateur/keno-analyzer.git
cd keno-analyzer/

# OU télécharger et extraire l'archive
# wget https://example.com/KenoAnalyzer-Pro-latest.tar.gz
# tar -xzf KenoAnalyzer-Pro-latest.tar.gz
# cd KenoAnalyzer-Pro/
```

#### Configuration de l'Environnement Virtuel
```bash
# Créer un environnement virtuel
python -m venv .venv

# Activer l'environnement
# Linux/macOS
source .venv/bin/activate

# Windows (PowerShell)
.\\.venv\\Scripts\\Activate.ps1

# Vérifier que Python pointe bien vers l'environnement virtuel
which python  # Doit pointer vers .venv/bin/python
```

#### Installation des Dépendances
```bash
# Mettre à jour pip
pip install --upgrade pip

# Installer les dépendances principales
pip install -r requirements.txt

# Pour le développement (optionnel)
pip install -r requirements-dev.txt

# Vérifier l'installation
pip list
```

> **Note** : Assurez-vous que toutes les dépendances sont correctement installées. En cas d'erreur avec psycopg2, installez les dépendances système nécessaires :
> ```bash
> # Ubuntu/Debian
> sudo apt-get install python3-dev libpq-dev
> 
> # RHEL/CentOS
> sudo yum install python3-devel postgresql-devel
> ```

### 4. Configuration de l'Application

#### Fichier de Configuration
Créez un fichier `.env` à la racine du projet :

```bash
# Dans le répertoire du projet
cp .env.example .env
```

#### Configuration de Base (Obligatoire)
```ini
# ===== CONFIGURATION OBLIGATOIRE =====

# Base de données PostgreSQL
DATABASE_URL="postgresql://keno_user:votre_mot_de_passe_securise@localhost:5432/keno_analyzer"

# Clé secrète pour les sessions (générez-en une avec : python -c 'import secrets; print(secrets.token_hex())')
SECRET_KEY="votre_clé_secrète_très_longue_et_sécurisée"

# Environnement (development/production)
FLASK_ENV="development"
FLASK_DEBUG="True"

# ===== CONFIGURATION AVANCÉE =====

# Email (pour la réinitialisation des mots de passe)
MAIL_SERVER="smtp.gmail.com"
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME="votre@email.com"
MAIL_PASSWORD="votre_mot_de_passe"
MAIL_DEFAULT_SENDER="Keno Analyzer <noreply@keno-analyzer.com>"

# Configuration ML
ML_AUTO_RETRAIN=True
ML_RETRAIN_INTERVAL_HOURS=24
ML_MODEL_PATH="./ml_models"

# Journalisation
LOG_LEVEL="INFO"
LOG_FILE="keno_analyzer.log"

# Sécurité
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
PERMANENT_SESSION_LIFETIME=3600  # 1 heure

# Limites de requêtes
RATELIMIT_DEFAULT="200 per day;50 per hour"
RATELIMIT_STORAGE_URL="memory://"
```

### 5. Initialisation de la Base de Données

#### Création du Schéma
```bash
# Initialiser le schéma de la base de données
python -c "
import os
from dotenv import load_dotenv
from src.database_manager_postgresql import PostgreSQLManager

# Charger les variables d'environnement
load_dotenv()

# Initialiser la base de données
db = PostgreSQLManager()
db.create_schema_if_needed()
print('✅ Schéma de la base de données initialisé avec succès!')
"
```

#### Chargement des Données Initiales
```bash
# Charger les données de base (utilisateurs, paramètres, etc.)
python -c "
import os
from dotenv import load_dotenv
from src.database_manager_postgresql import PostgreSQLManager

load_dotenv()
db = PostgreSQLManager()

# Créer un utilisateur administrateur par défaut
admin_data = {
    'username': 'admin',
    'email': 'admin@keno-analyzer.com',
    'password': 'admin123',  # À changer immédiatement après la première connexion
    'is_admin': True,
    'is_active': True
}

try:
    db.save_user(**admin_data)
    print('✅ Utilisateur administrateur créé avec succès')
    print('🔑 Identifiants par défaut : admin / admin123')
    print('⚠️ CHANGEZ CES IDENTIFIANTS APRÈS LA PREMIÈRE CONNEXION !')
except Exception as e:
    print(f'❌ Erreur lors de la création de l\'administrateur : {e}')
"
```

### 6. Vérification de l'Installation

#### Vérification des Dépendances
```bash
# Vérifier les dépendances installées
pip list

# Vérifier la version de Python
python --version

# Vérifier PostgreSQL
psql --version
```

#### Tests de Base
```bash
# Tester la connexion à la base de données
python -c "
import os
from dotenv import load_dotenv
from src.database_manager_postgresql import PostgreSQLManager

load_dotenv()
try:
    db = PostgreSQLManager()
    user_count = db.get_user_count()
    print(f'✅ Connexion à la base de données réussie! Utilisateurs trouvés : {user_count}')
except Exception as e:
    print(f'❌ Erreur de connexion à la base de données : {e}')
"
```

#### Tests d'API (si le serveur est en cours d'exécution)
```bash
# Vérifier la santé de l'API
curl http://localhost:5000/api/health

# Obtenir la version
curl http://localhost:5000/api/version
```

### 7. Lancement de l'Application

#### Mode Développement
```bash
# Activer l'environnement virtuel
source .venv/bin/activate  # Linux/macOS
.\\.venv\\Scripts\\Activate.ps1  # Windows

# Lancer en mode développement
flask run --debug

# OU directement avec Python
python src/main.py
```

#### Mode Production avec Gunicorn
```bash
# Installer Gunicorn si ce n'est pas déjà fait
pip install gunicorn

# Lancer avec Gunicorn (4 workers, ajustez selon vos besoins CPU)
gunicorn "src.main:create_app()" -w 4 -b 0.0.0.0:5000 --timeout 120 --access-logfile -

# Pour exécuter en arrière-plan avec nohup
nohup gunicorn "src.main:create_app()" -w 4 -b 0.0.0.0:5000 --timeout 120 > keno_analyzer.log 2>&1 &
```

#### Configuration Systemd (Recommandé pour la production)
Créez un fichier `/etc/systemd/system/keno-analyzer.service` :

```ini
[Unit]
Description=Keno Analyzer Pro
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/chemin/vers/keno-analyzer
Environment="PATH=/chemin/vers/keno-analyzer/.venv/bin"
ExecStart=/chemin/vers/keno-analyzer/.venv/bin/gunicorn \
    --workers 4 \
    --bind unix:keno-analyzer.sock \
    --timeout 120 \
    --access-logfile - \
    "src.main:create_app()"
Restart=always

[Install]
WantedBy=multi-user.target
```

Puis activez et démarrez le service :
```bash
sudo systemctl daemon-reload
sudo systemctl enable keno-analyzer
sudo systemctl start keno-analyzer
sudo systemctl status keno-analyzer
```

### 8. Vérification et Dépannage

#### Vérification de l'Application
1. **Interface Web** : http://localhost:5000
   - Vérifiez que la page d'accueil se charge
   - Testez la navigation entre les différentes sections

2. **Espace Administrateur** : http://localhost:5000/admin
   - Connectez-vous avec les identifiants admin
   - Vérifiez le tableau de bord administrateur
   - Testez la gestion des utilisateurs

3. **API** : http://localhost:5000/api/health
   - Doit retourner un statut 200 avec des informations sur le service

#### Journaux et Surveillance
```bash
# Voir les logs de l'application
tail -f keno_analyzer.log

# Voir les erreurs système
journalctl -u keno-analyzer -f

# Vérifier l'utilisation des ressources
top
htop
```

#### Dépannage Courant
1. **Erreur de connexion à la base de données**
   - Vérifiez que PostgreSQL est en cours d'exécution
   - Vérifiez les identifiants dans le fichier .env
   - Testez la connexion avec `psql` directement

2. **Erreurs d'importation**
   - Vérifiez que l'environnement virtuel est activé
   - Exécutez `pip install -r requirements.txt`
   - Vérifiez la variable PYTHONPATH

3. **Problèmes de permissions**
   - Vérifiez les permissions des fichiers et dossiers
   - Assurez-vous que l'utilisateur a les droits nécessaires

4. **Problèmes de port**
   - Vérifiez qu'aucun autre service n'utilise le port 5000
   - Utilisez `netstat -tuln | grep 5000` pour vérifier

## 🔧 Configuration Avancée

### Configuration Nginx (Production)
Créez un fichier de configuration Nginx dans `/etc/nginx/sites-available/keno-analyzer` :

```nginx
upstream keno_analyzer {
    server unix:/chemin/vers/keno-analyzer/keno-analyzer.sock;
}

server {
    listen 80;
    server_name votre-domaine.com www.votre-domaine.com;

    # Redirection HTTP vers HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name votre-domaine.com www.votre-domaine.com;

    # Chemins des certificats SSL (obtenez-les avec Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/votre-domaine.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/votre-domaine.com/privkey.pem;

    # Paramètres SSL recommandés
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_stapling on;
    ssl_stapling_verify on;

    # Paramètres de sécurité supplémentaires
    add_header X-Frame-Options "SAMEORIGIN";
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Referrer-Policy "strict-origin";
    add_header Content-Security-Policy "default-src 'self';";

    # Fichiers statiques
    location /static {
        alias /chemin/vers/keno-analyzer/src/static;
        expires 30d;
        access_log off;
    }

    # Proxy vers Gunicorn
    location / {
        try_files $uri @proxy_to_app;
    }

    location @proxy_to_app {
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Host $http_host;
        proxy_redirect off;
        proxy_pass http://keno_analyzer;
        proxy_read_timeout 300;
    }

    # Désactiver l'accès aux fichiers sensibles
    location ~ /\.(?!well-known).* {
        deny all;
    }

    location ~* \.(ini|py|sh|sql|env|git|htaccess|htpasswd)$ {
        deny all;
    }
}
```

Activez la configuration et redémarrez Nginx :
```bash
sudo ln -s /etc/nginx/sites-available/keno-analyzer /etc/nginx/sites-enabled/
sudo nginx -t  # Tester la configuration
sudo systemctl restart nginx
```
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### Configuration SSL/HTTPS
```bash
# Installer Certbot
sudo apt install certbot python3-certbot-nginx

# Obtenir un certificat SSL
sudo certbot --nginx -d your-domain.com
```

### Configuration de Monitoring
```bash
# Installer des outils de monitoring
pip install prometheus-client
```

## 🐛 Dépannage

### Problèmes Courants

#### Erreur de Connexion à la Base de Données
```bash
## 🔄 Mise à Jour de l'Application

### Mise à jour des Sources
```bash
# Sauvegarder la base de données (important !)
pg_dump keno_analyzer > keno_analyzer_backup_$(date +%Y%m%d).sql

# Mettre à jour les sources
git pull origin main  # Ou la branche appropriée

# Mettre à jour les dépendances
pip install -r requirements.txt

# Appliquer les migrations si nécessaire
python -c "
import os
from dotenv import load_dotenv
from src.database_manager_postgresql import PostgreSQLManager

load_dotenv()
db = PostgreSQLManager()
db.create_schema_if_needed()
print('✅ Schéma de la base de données mis à jour')
"

# Redémarrer le service
sudo systemctl restart keno-analyzer
```

### Vérification Post-Mise à Jour
1. Vérifiez les journaux pour détecter d'éventuelles erreurs
2. Testez les fonctionnalités principales
3. Vérifiez que les tâches planifiées fonctionnent correctement

## 🔒 Sécurité

### Recommandations de Sécurité
1. **Mots de passe** : Changez le mot de passe admin par défaut immédiatement
2. **Certificats SSL** : Utilisez toujours HTTPS en production
3. **Mises à jour** : Maintenez le système et les dépendances à jour
4. **Sauvegardes** : Configurez des sauvegardes régulières
5. **Surveillance** : Mettez en place une surveillance du serveur

### Commandes Utiles
```bash
# Vérifier que PostgreSQL fonctionne
sudo systemctl status postgresql

# Vérifier les connexions actives
sudo -u postgres psql -c "SELECT * FROM pg_stat_activity;"

# Vérifier les permissions des utilisateurs
sudo -u postgres psql -c "\du"

# Vérifier les tables de la base de données
psql -U keno_user -d keno_analyzer -c "\dt"
```

## 📚 Ressources Supplémentaires

### Documentation
- [Documentation Flask](https://flask.palletsprojects.com/)
- [Documentation PostgreSQL](https://www.postgresql.org/docs/)
- [Documentation Gunicorn](https://docs.gunicorn.org/)
- [Documentation Nginx](https://nginx.org/en/docs/)

### Support
Pour toute question ou problème, veuillez consulter :
1. Les [issues GitHub](https://github.com/votre-utilisateur/keno-analyzer/issues)
2. La [documentation officielle](https://keno-analyzer.com/docs)
3. Le [forum de la communauté](https://community.keno-analyzer.com)

---

**Dernière mise à jour :** 31 Juillet 2025  
**Version du document :** 2.0.0  
**Auteur :** Équipe Keno Analyzer Pro
```

#### Erreur d'Import de Modules
```bash
# Vérifier l'environnement virtuel
which python
pip list

# Réinstaller les dépendances
pip install --force-reinstall -r requirements.txt
```

#### Erreur de Permissions S3
```bash
# Vérifier les credentials AWS
aws configure list

# Tester l'accès S3
aws s3 ls s3://your-bucket-name/
```

#### Performance Lente
```bash
# Vérifier les index de la base de données
python -c "
from enhanced_database_manager import EnhancedDatabaseManager
db = EnhancedDatabaseManager()
# Les index sont créés automatiquement
"
```

### Logs et Debugging

#### Activer les Logs Détaillés
```python
# Dans enhanced_web_app.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### Vérifier les Logs
```bash
# Logs de l'application
tail -f app.log

# Logs PostgreSQL
sudo tail -f /var/log/postgresql/postgresql-*.log
```

## 📊 Optimisation des Performances

### Base de Données
```sql
-- Optimisations PostgreSQL
VACUUM ANALYZE;
REINDEX DATABASE kenodb;
```

### Application
```bash
# Utiliser un cache Redis (optionnel)
pip install redis flask-caching
```

### Système
```bash
# Augmenter les limites de fichiers ouverts
ulimit -n 65536
```

## 🔄 Mise à Jour

### Sauvegarde Avant Mise à Jour
```bash
# Sauvegarder la base de données
pg_dump kenodb > backup_$(date +%Y%m%d).sql

# Sauvegarder les modèles ML
cp -r models/ models_backup_$(date +%Y%m%d)/
```

### Procédure de Mise à Jour
```bash
# Arrêter l'application
pkill -f enhanced_web_app.py

# Mettre à jour le code
git pull origin main

# Mettre à jour les dépendances
pip install -r requirements.txt --upgrade

# Relancer l'application
python enhanced_web_app.py
```

## 📞 Support et Maintenance

### Commandes Utiles
```bash
# Statut du système
curl http://localhost:5000/api/stats

# Forcer un réentraînement ML
curl -X POST http://localhost:5000/api/ml/retrain

# Vérifier la santé de l'API
curl http://localhost:5000/api/health
```

### Maintenance Régulière
```bash
# Script de maintenance (à exécuter hebdomadairement)
#!/bin/bash
echo "🔧 Maintenance Keno Analyzer Pro"

# Nettoyage des logs
find logs/ -name "*.log" -mtime +30 -delete

# Optimisation de la base de données
psql kenodb -c "VACUUM ANALYZE;"

# Vérification de l'espace disque
df -h

echo "✅ Maintenance terminée"
```

## 🎯 Prochaines Étapes

Après l'installation réussie :

1. **Configurer les données** : Importer vos tirages historiques
2. **Personnaliser l'interface** : Adapter les couleurs et le branding
3. **Configurer les alertes** : Mettre en place le monitoring
4. **Former les utilisateurs** : Créer des guides d'utilisation
5. **Planifier la maintenance** : Établir un calendrier de mises à jour

---

**🎉 Félicitations ! Votre installation de Keno Analyzer Pro Enhanced est maintenant prête !**

Pour toute question ou problème, consultez la documentation complète dans `README_ENHANCED.md` ou contactez l'équipe de support.

