import logging
import os
from datetime import datetime

from sqlalchemy import create_engine, text
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# NOTE IMPORTANTE : Le pattern Singleton (get_postgresql_manager) a été supprimé.
# Chaque processus (ou thread) doit créer sa propre instance de PostgreSQLManager.
# Cela résout les problèmes de connexion SSL inattendue dans les environnements multi-processus (ex: Flask en mode debug).

class PostgreSQLManager:
    def __init__(self):
        """
        Initialise une nouvelle instance du gestionnaire de base de données.
        Chaque instance gère son propre pool de connexions.
        """
        logger.info("Initialisation d'une nouvelle instance de PostgreSQLManager...")
        self.database_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://kenos_user:qYGSudoftPvnoxaT9Seh5IP4itP1kK0a@dpg-d1umeoer433s73eu3d7g-a.frankfurt-postgres.render.com/kenos_vs92"
        )
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set and no fallback URL provided.")
        
        # S'assurer que le mode SSL est requis pour Render
        if "sslmode" not in self.database_url:
            self.database_url += "?sslmode=require"
            
        # Configurer le moteur avec le recyclage des connexions pour gérer les timeouts
        self.engine = create_engine(
            self.database_url,
            pool_recycle=300,  # Recycle les connexions inactives depuis plus de 5 minutes (300s)
            pool_pre_ping=True # Vérifie la connexion avant de l'utiliser
        )

    def create_schema_if_needed(self):
        """
        Assure que le schéma de la base de données est propre et à jour.
        Cette méthode doit être appelée une seule fois par le processus principal au démarrage.
        """
        logger.info("Début de la configuration du schéma de la base de données...")
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    # Nettoyage complet des anciennes structures pour garantir un état propre
                    logger.info("Nettoyage des anciennes tables et index pour garantir un état propre...")
                    conn.execute(text("DROP TABLE IF EXISTS ml_models CASCADE;"))
                    conn.execute(text("DROP TABLE IF EXISTS analysis_results CASCADE;"))
                    conn.execute(text("DROP TABLE IF EXISTS predictions CASCADE;"))
                    conn.execute(text("DROP TABLE IF EXISTS tirages CASCADE;"))
                    conn.execute(text("DROP TABLE IF EXISTS users CASCADE;"))
                    conn.execute(text("DROP TABLE IF EXISTS method_stats CASCADE;"))
                    logger.info("Nettoyage terminé.")

                    # --- ÉTAPE 1: CRÉATION DES TABLES ---
                    logger.info("Création des tables...")
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"; CREATE EXTENSION IF NOT EXISTS \"pgcrypto\"; CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
                    
                    # Table tirages
                    conn.execute(text("""
                        CREATE TABLE tirages (
                            id SERIAL PRIMARY KEY,
                            date_tirage DATE NOT NULL UNIQUE,
                            heure_tirage TIME,
                            numeros INTEGER[] NOT NULL DEFAULT \'{}\':INTEGER[],
                            multiplicateur INTEGER,
                            joker VARCHAR(20),
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        )
                    """))
                    
                    # Table users (avec 'password' au lieu de 'password_hash')
                    conn.execute(text("""
                        CREATE TABLE users (
                            id SERIAL PRIMARY KEY,
                            username VARCHAR(50) UNIQUE NOT NULL,
                            email VARCHAR(255) UNIQUE,
                            password VARCHAR(255) NOT NULL, -- Changement ici: password au lieu de password_hash
                            is_admin BOOLEAN DEFAULT FALSE,
                            is_moderator BOOLEAN DEFAULT FALSE,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                            last_active TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        )
                    """))
                    
                    # Table predictions
                    conn.execute(text("""
                        CREATE TABLE predictions (
                            id SERIAL PRIMARY KEY,
                            tirage_id INTEGER REFERENCES tirages(id) ON DELETE CASCADE,
                            user_id VARCHAR(50) NOT NULL,
                            method VARCHAR(100) NOT NULL,
                            numeros INTEGER[] NOT NULL,
                            session_id VARCHAR(255),
                            confidence NUMERIC(5,4) DEFAULT 0.0,
                            correct_count INTEGER DEFAULT 0,
                            is_validated BOOLEAN DEFAULT FALSE,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        )
                    """))
                    
                    # Table method_stats (avec 'correct_predictions' et 'accuracy')
                    conn.execute(text("""
                        CREATE TABLE method_stats (
                            id SERIAL PRIMARY KEY,
                            method VARCHAR(100) UNIQUE NOT NULL,
                            total_predictions INTEGER DEFAULT 0,
                            correct_predictions INTEGER DEFAULT 0, -- Changement ici: correct_predictions
                            accuracy FLOAT8 DEFAULT 0.0, -- Changement ici: accuracy
                            last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        )
                    """))
                    
                    # Table analysis_results
                    conn.execute(text("""
                        CREATE TABLE analysis_results (
                            id SERIAL PRIMARY KEY,
                            tirage_id INTEGER REFERENCES tirages(id) ON DELETE CASCADE,
                            analysis_type VARCHAR(50) NOT NULL,
                            result_data JSONB,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(tirage_id, analysis_type)
                        )
                    """))
                    
                    # Table ml_models (avec 's3_path' au lieu de 'weights', et sans 'is_active', 'parameters')
                    conn.execute(text("""
                        CREATE TABLE ml_models (
                            id SERIAL PRIMARY KEY,
                            model_name VARCHAR(100) NOT NULL,
                            model_type VARCHAR(50) NOT NULL,
                            s3_path VARCHAR(500), -- Changement ici: s3_path au lieu de weights
                            training_score NUMERIC(10,8),
                            test_score NUMERIC(10,8),
                            r2_score NUMERIC(10,8),
                            training_time_seconds INTEGER,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                            trained_at TIMESTAMP WITH TIME ZONE
                        )
                    """))
                    logger.info("✅ Tables créées avec succès.")

                    # --- ÉTAPE 2: CRÉATION DES INDEX ---
                    logger.info("Création des index...")
                    conn.execute(text("CREATE INDEX idx_tirages_date ON tirages(date_tirage DESC)"))
                    conn.execute(text("CREATE INDEX idx_tirages_numeros ON tirages USING GIN(numeros)"))
                    conn.execute(text("CREATE INDEX idx_users_username ON users(username)"))
                    conn.execute(text("CREATE INDEX idx_users_email ON users(email)"))
                    conn.execute(text("CREATE INDEX idx_predictions_user ON predictions(user_id)"))
                    conn.execute(text("CREATE INDEX idx_predictions_method ON predictions(method)"))
                    conn.execute(text("CREATE INDEX idx_predictions_created ON predictions(created_at DESC)"))
                    conn.execute(text("CREATE INDEX idx_analysis_tirage ON analysis_results(tirage_id)"))
                    logger.info("✅ Index créés avec succès.")

                    # --- ÉTAPE 3: INSERTION DES DONNÉES INITIALES ---
                    conn.execute(text("""
                        INSERT INTO method_stats (method)
                        VALUES (\'frequency_analysis\'), (\'monte_carlo\'), (\'ml_prediction\')
                        ON CONFLICT (method) DO NOTHING
                    """))
                    logger.info("✅ Données initiales insérées.")
            
            logger.info("🎉 Schéma de la base de données configuré avec succès.")

        except Exception as e:
            logger.error(f"❌ Une erreur critique est survenue lors de la configuration du schéma : {e}")

    def save_user(self, username, password, email=None):
        """Sauvegarde un nouvel utilisateur avec un mot de passe en clair."""
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    result = conn.execute(text("""
                        INSERT INTO users (username, password, email)
                        VALUES (:username, :password, :email)
                        RETURNING id
                    """), {
                        "username": username,
                        "password": password,
                        "email": email
                    })
                    user_id = result.fetchone()[0]
                    logger.info(f"✅ Utilisateur \'{username}\' sauvegardé avec succès (ID: {user_id}).")
                    return user_id
        except Exception as e:
            logger.error(f"❌ Erreur lors de la sauvegarde de l\'utilisateur \'{username}\': {e}")
            return None

    def get_user_by_username(self, username):
        """Récupère un utilisateur par son nom d\'utilisateur."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id, username, password, email, is_admin, is_moderator, created_at, last_active 
                    FROM users 
                    WHERE username = :username
                """), {"username": username})
                user = result.fetchone()
                return dict(user._mapping) if user else None
        except Exception as e:
            logger.error(f"❌ Erreur lors de la récupération de l\'utilisateur \'{username}\': {e}")
            return None

    def save_prediction(self, user_id, method, numeros, confidence=0.0, session_id=None):
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    result = conn.execute(text("""
                        INSERT INTO predictions (user_id, method, numeros, confidence, session_id)
                        VALUES (:user_id, :method, :numeros, :confidence, :session_id)
                        RETURNING id
                    """), {
                        "user_id": user_id, "method": method, "numeros": numeros,
                        "confidence": confidence, "session_id": session_id
                    })
                    prediction_id = result.fetchone()[0]
                    logger.info(f"✅ Prédiction sauvegardée: {user_id} - {method} (ID: {prediction_id})")
                    return prediction_id
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde prédiction: {e}")
            return None

    def save_tirage(self, date_tirage, numeros, heure_tirage=None, multiplicateur=None, joker=None, **kwargs):
        """Sauvegarde un tirage dans la base de données, en gérant plusieurs formats de date."""
        try:
            # Gérer plusieurs formats de date de manière robuste
            if isinstance(date_tirage, str):
                try:
                    date_obj = datetime.strptime(date_tirage, \'%d/%m/%Y\').date()
                except ValueError:
                    try:
                        date_obj = datetime.strptime(date_tirage, \'%Y-%m-%d\').date()
                    except ValueError:
                        logger.error(f"Format de date non reconnu pour \'{date_tirage}\'. Utilisez \'DD/MM/YYYY\' ou \'YYYY-MM-DD\'.")
                        return None
            else:
                date_obj = date_tirage

            with self.engine.connect() as conn:
                with conn.begin():
                    result = conn.execute(text("""
                        INSERT INTO tirages (date_tirage, heure_tirage, numeros, multiplicateur, joker)
                        VALUES (:date_tirage, :heure_tirage, :numeros, :multiplicateur, :joker)
                        ON CONFLICT (date_tirage) DO UPDATE
                        SET numeros = EXCLUDED.numeros,
                            heure_tirage = EXCLUDED.heure_tirage,
                            multiplicateur = EXCLUDED.multiplicateur,
                            joker = EXCLUDED.joker,
                            updated_at = CURRENT_TIMESTAMP
                        RETURNING id
                    """), {
                        "date_tirage": date_obj, "heure_tirage": heure_tirage, "numeros": numeros,
                        "multiplicateur": multiplicateur, "joker": joker
                    })
                    tirage_id = result.fetchone()[0]
                    logger.info(f"✅ Tirage du {date_obj.strftime(\'%d/%m/%Y\')} sauvegardé (ID: {tirage_id})")
                    return tirage_id
        except Exception as e:
            logger.error(f"❌ Erreur lors de la sauvegarde du tirage pour la date \'{date_tirage}\': {e}")
            return None

    def get_all_tirages(self, limit=100):
        """Récupère la liste des tirages"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id, date_tirage, heure_tirage, numeros, multiplicateur, joker, created_at, updated_at
                    FROM tirages ORDER BY date_tirage DESC LIMIT :limit
                """), {"limit": limit})
                return [dict(row._mapping) for row in result.fetchall()]
        except Exception as e:
            logger.error(f"❌ Erreur récupération tirages: {e}")
            return []
            
    def get_system_predictions(self, limit=50):
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id, user_id, method, numeros, confidence, created_at, correct_count, is_validated
                    FROM predictions WHERE user_id = \'system\' ORDER BY created_at DESC LIMIT :limit
                """), {"limit": limit})
                return [dict(row._mapping) for row in result.fetchall()]
        except Exception as e:
            logger.error(f"❌ Erreur récupération prédictions système: {e}")
            return []

    def get_user_predictions(self, session_id=None, limit=20):
        try:
            with self.engine.connect() as conn:
                if session_id:
                    query = text("""
                        SELECT id, user_id, method, numeros, confidence, created_at, correct_count, is_validated
                        FROM predictions WHERE user_id != \'system\' AND (session_id = :session_id OR user_id = :session_id)
                        ORDER BY created_at DESC LIMIT :limit
                    """)
                    params = {"session_id": session_id, "limit": limit}
                else:
                    query = text("""
                        SELECT id, user_id, method, numeros, confidence, created_at, correct_count, is_validated
                        FROM predictions WHERE user_id != \'system\' ORDER BY created_at DESC LIMIT :limit
                    """)
                    params = {"limit": limit}
                result = conn.execute(query, params)
                return [dict(row._mapping) for row in result.fetchall()]
        except Exception as e:
            logger.error(f"❌ Erreur récupération prédictions utilisateur: {e}")
            return []


