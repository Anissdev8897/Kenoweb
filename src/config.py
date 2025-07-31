import os

# Configuration de la base de données
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("La variable d'environnement DATABASE_URL est requise pour se connecter à la base de données")

DATABASE_CONFIG = {
    'postgresql_url': DATABASE_URL,
    'fallback_json_path': os.path.join(os.path.dirname(__file__), 'data', 'users.json'),
    'backup_json_path': os.path.join(os.path.dirname(__file__), 'data', 'users_backup.json')
}

# Configuration OpenAI
OPENAI_API_KEY = "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"

# Configuration de l'application
APP_CONFIG = {
    'SECRET_KEY': os.environ.get('SECRET_KEY', 'keno-secret-key-change-in-production'),
    'SESSION_TYPE': 'filesystem',
    'SESSION_FILE_DIR': os.path.join(os.path.dirname(__file__), 'sessions'),
    'SESSION_PERMANENT': False,
    'PERMANENT_SESSION_LIFETIME': 3600  # 1 heure
}

# Configuration des chemins
PATHS = {
    'static': os.path.join(os.path.dirname(__file__), 'static'),
    'templates': os.path.join(os.path.dirname(__file__), 'templates'),
    'data': os.path.join(os.path.dirname(__file__), 'data'),
    'logs': os.path.join(os.path.dirname(__file__), 'logs')
}

# Créer les répertoires nécessaires
for path in PATHS.values():
    os.makedirs(path, exist_ok=True)
