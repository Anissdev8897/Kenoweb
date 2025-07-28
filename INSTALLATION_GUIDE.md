# 🚀 Guide d'Installation - Keno Analyzer Pro Enhanced

## 📋 Prérequis Système

### Système d'Exploitation
- **Linux** : Ubuntu 20.04+ (recommandé)
- **Windows** : Windows 10+ avec WSL2
- **macOS** : macOS 10.15+

### Logiciels Requis
- **Python** : 3.8+ (3.11 recommandé)
- **Base de données** : PostgreSQL 12+ ou SQLite 3.35+
- **Git** : Pour le versioning (optionnel)

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

### 2. Configuration de la Base de Données

#### PostgreSQL
```bash
# Démarrer le service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Créer un utilisateur et une base de données
sudo -u postgres psql
```

```sql
-- Dans psql
CREATE USER keno_user WITH PASSWORD 'secure_password';
CREATE DATABASE kenodb OWNER keno_user;
GRANT ALL PRIVILEGES ON DATABASE kenodb TO keno_user;
\q
```

#### SQLite (Alternative pour les tests)
```bash
# Aucune installation requise, SQLite est inclus avec Python
```

### 3. Installation du Projet

#### Extraction de l'Archive
```bash
# Extraire l'archive
tar -xzf Kenoweb-Enhanced-Complete.tar.gz
cd Kenoweb-main/
```

#### Création de l'Environnement Virtuel
```bash
# Créer l'environnement virtuel
python3 -m venv venv

# Activer l'environnement
source venv/bin/activate  # Linux/macOS
# ou
venv\Scripts\activate     # Windows
```

#### Installation des Dépendances
```bash
# Installer toutes les dépendances
pip install -r requirements.txt

# Ou installation manuelle
pip install psycopg2-binary sqlalchemy scikit-learn flask flask-cors boto3 pandas numpy matplotlib seaborn joblib
```

### 4. Configuration des Variables d'Environnement

#### Créer le fichier .env
```bash
# Dans le répertoire src/
cd src/
touch .env
```

#### Contenu du fichier .env
```bash
# Base de données PostgreSQL
DATABASE_URL="postgresql://keno_user:secure_password@localhost/kenodb"

# Ou SQLite pour les tests
# DATABASE_URL="sqlite:///keno.db"

# Configuration AWS S3 (optionnel)
AWS_ACCESS_KEY_ID="your_access_key_id"
AWS_SECRET_ACCESS_KEY="your_secret_access_key"
AWS_REGION="us-east-1"
S3_BUCKET_NAME="keno-ml-models"

# Configuration Flask
FLASK_ENV="development"
FLASK_DEBUG="True"
SECRET_KEY="your_secret_key_here"

# Configuration ML
ML_AUTO_RETRAIN="True"
ML_RETRAIN_INTERVAL_HOURS="24"
```

### 5. Initialisation de la Base de Données

#### Test de Connexion
```bash
# Tester la connexion à la base de données
python -c "
import os
os.environ['DATABASE_URL'] = 'postgresql://keno_user:secure_password@localhost/kenodb'
from enhanced_database_manager import EnhancedDatabaseManager
db = EnhancedDatabaseManager()
print('✅ Connexion à la base de données réussie!')
"
```

#### Chargement des Données Initiales (Optionnel)
```bash
# Si vous avez des données de tirages existantes
python load_initial_data.py
```

### 6. Tests de Validation

#### Tests Basiques
```bash
# Exécuter les tests simples
python simple_test.py
```

#### Tests Complets (Optionnel)
```bash
# Exécuter tous les tests
python test_system.py
```

### 7. Lancement de l'Application

#### Mode Développement
```bash
# Lancer l'application
python enhanced_web_app.py
```

#### Mode Production
```bash
# Installer Gunicorn
pip install gunicorn

# Lancer avec Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 enhanced_web_app:app
```

### 8. Vérification de l'Installation

#### Accès à l'Interface Web
```
http://localhost:5000
```

#### Vérifications à Effectuer
1. ✅ Page d'accueil se charge correctement
2. ✅ Grille Keno interactive fonctionne
3. ✅ Génération de prédictions utilisateur
4. ✅ Statut ML affiché (peut être "en cours d'initialisation")
5. ✅ Tableau de bord unifié accessible

## 🔧 Configuration Avancée

### Configuration Nginx (Production)
```nginx
server {
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
# Vérifier que PostgreSQL fonctionne
sudo systemctl status postgresql

# Vérifier les permissions
sudo -u postgres psql -c "\du"
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

