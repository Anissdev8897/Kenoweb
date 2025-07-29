import logging
import os
from datetime import datetime

from sqlalchemy import create_engine, text
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PostgreSQLManager:
    def __init__(self):
        """
        Initialise une nouvelle instance du gestionnaire de base de données.
        Cette méthode doit être appelée une fois par processus.
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
            
        # Configurer le moteur avec le recyclage des connexions pour la stabilité
        self.engine = create_engine(
            self.database_url,
            pool_recycle=300,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            connect_args={
                'connect_timeout': 10,
                'keepalives': 1,
                'keepalives_idle': 30,
                'keepalives_interval': 10,
                'keepalives_count': 5
            },
            echo=False  # Mettre à True pour le débogage
        )
        
        # Création d'une session factory
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        self._create_schema()

    def _create_schema(self):
        """
        Crée le schéma de la base de données.
        Cette méthode est conservée pour la rétrocompatibilité.
        """
        logger.warning("_create_schema() est dépréciée. Utilisez create_schema_if_needed() à la place.")
        self.create_schema_if_needed()

    def create_schema_if_needed(self):
        """
        Crée les tables et les index. Doit être appelée explicitement
        par le processus principal au démarrage, et non par les workers.
        """
        logger.info("Début de la configuration du schéma de la base de données...")
        try:
            # --- ÉTAPE 1: CRÉATION DES TABLES ---
            with self.engine.connect() as conn:
                with conn.begin():
                    logger.info("Vérification et création des tables si elles n'existent pas...")
                    # Création des extensions nécessaires
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\""))
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"pgcrypto\""))
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))

                    # Création des tables
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS tirages (
                            id SERIAL PRIMARY KEY, date_tirage DATE NOT NULL UNIQUE, heure_tirage TIME,
                            numeros INTEGER[] NOT NULL DEFAULT '{}'::INTEGER[], multiplicateur INTEGER, joker VARCHAR(20),
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        )"""))
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS users (
                            id SERIAL PRIMARY KEY, username VARCHAR(50) UNIQUE NOT NULL, email VARCHAR(255) UNIQUE,
                            password VARCHAR(255) NOT NULL, is_admin BOOLEAN DEFAULT FALSE, is_moderator BOOLEAN DEFAULT FALSE,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, last_active TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        )"""))
                    # ... (les autres créations de tables restent identiques)
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS predictions (
                            id SERIAL PRIMARY KEY, tirage_id INTEGER REFERENCES tirages(id) ON DELETE CASCADE, user_id VARCHAR(50) NOT NULL,
                            method VARCHAR(100) NOT NULL, numeros INTEGER[] NOT NULL, session_id VARCHAR(255),
                            confidence NUMERIC(5,4) DEFAULT 0.0, correct_count INTEGER DEFAULT 0, is_validated BOOLEAN DEFAULT FALSE,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        )"""))
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS method_stats (
                            id SERIAL PRIMARY KEY, method VARCHAR(100) UNIQUE NOT NULL, total_predictions INTEGER DEFAULT 0,
                            correct_predictions INTEGER DEFAULT 0, accuracy FLOAT8 DEFAULT 0.0,
                            last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        )"""))
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS analysis_results (
                            id SERIAL PRIMARY KEY, tirage_id INTEGER REFERENCES tirages(id) ON DELETE CASCADE,
                            analysis_type VARCHAR(50) NOT NULL, result_data JSONB, created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(tirage_id, analysis_type)
                        )"""))
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS ml_models (
                            id SERIAL PRIMARY KEY, model_name VARCHAR(100) NOT NULL, model_type VARCHAR(50) NOT NULL,
                            s3_path VARCHAR(500), training_score NUMERIC(10,8), test_score NUMERIC(10,8),
                            r2_score NUMERIC(10,8), training_time_seconds INTEGER,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, trained_at TIMESTAMP WITH TIME ZONE
                        )"""))
                    logger.info("✅ Vérification des tables terminée.")

            # --- ÉTAPE 2: CRÉATION DES INDEX (AVEC NETTOYAGE PRÉALABLE) ---
            with self.engine.connect() as conn:
                with conn.begin():
                    logger.info("Nettoyage et re-création des index...")
                    # LA SOLUTION : On supprime les index s'ils existent avant de les recréer.
                    conn.execute(text("DROP INDEX IF EXISTS idx_tirages_date;"))
                    conn.execute(text("DROP INDEX IF EXISTS idx_tirages_numeros;"))
                    conn.execute(text("DROP INDEX IF EXISTS idx_users_username;"))
                    conn.execute(text("DROP INDEX IF EXISTS idx_users_email;"))
                    conn.execute(text("DROP INDEX IF EXISTS idx_predictions_user;"))
                    conn.execute(text("DROP INDEX IF EXISTS idx_predictions_method;"))
                    conn.execute(text("DROP INDEX IF EXISTS idx_predictions_created;"))
                    conn.execute(text("DROP INDEX IF EXISTS idx_analysis_tirage;"))

                    # Maintenant, on crée les index sur une base propre
                    conn.execute(text("CREATE INDEX idx_tirages_date ON tirages(date_tirage DESC)"))
                    conn.execute(text("CREATE INDEX idx_tirages_numeros ON tirages USING GIN(numeros)"))
                    conn.execute(text("CREATE INDEX idx_users_username ON users(username)"))
                    conn.execute(text("CREATE INDEX idx_users_email ON users(email)"))
                    conn.execute(text("CREATE INDEX idx_predictions_user ON predictions(user_id)"))
                    conn.execute(text("CREATE INDEX idx_predictions_method ON predictions(method)"))
                    conn.execute(text("CREATE INDEX idx_predictions_created ON predictions(created_at DESC)"))
                    conn.execute(text("CREATE INDEX idx_analysis_tirage ON analysis_results(tirage_id)"))
                    logger.info("✅ Création des index terminée.")

            # --- ÉTAPE 3: INSERTION DES DONNÉES INITIALES ---
            with self.engine.connect() as conn:
                with conn.begin():
                    conn.execute(text("""
                        INSERT INTO method_stats (method)
                        VALUES ('frequency_analysis'), ('monte_carlo'), ('ml_prediction')
                        ON CONFLICT (method) DO NOTHING
                    """))
                    logger.info("✅ Données initiales insérées.")
            
            logger.info("🎉 Schéma de la base de données configuré avec succès.")

        except Exception as e:
            logger.error(f"❌ Une erreur critique est survenue lors de la configuration du schéma : {e}")

    # ... (Le reste de vos fonctions reste ici, inchangé) ...
    def save_user(self, username, password, email=None):
        """Sauvegarde un nouvel utilisateur avec un mot de passe en clair."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    INSERT INTO users (username, password, email)
                    VALUES (:username, :password, :email)
                    RETURNING id
                """), {
                    "username": username,
                    "password": password, # Stockage direct
                    "email": email
                })
                conn.commit()
                user_id = result.fetchone()[0]
                logger.info(f"✅ Utilisateur '{username}' sauvegardé avec succès (ID: {user_id}).")
                return user_id
        except Exception as e:
            logger.error(f"❌ Erreur lors de la sauvegarde de l'utilisateur '{username}': {e}")
            return None

    def get_user_by_username(self, username):
        """Récupère un utilisateur par son nom d'utilisateur."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id, username, password, email, is_admin, is_moderator, created_at, last_active 
                    FROM users 
                    WHERE username = :username
                """), {"username": username})
                user = result.fetchone()
                if user:
                    # Retourne un dictionnaire pour un accès facile aux colonnes
                    return dict(user._mapping)
                return None
        except Exception as e:
            logger.error(f"❌ Erreur lors de la récupération de l'utilisateur '{username}': {e}")
            return None
    def get_system_predictions(self, limit=50):
        try:
            with self.engine.connect() as conn:
                query = text("""
                    SELECT id, user_id, method, numeros, confidence, created_at, correct_count, is_validated
                    FROM predictions 
                    WHERE user_id = 'system'
                    ORDER BY created_at DESC 
                    LIMIT :limit
                """)
                result = conn.execute(query, {"limit": limit})
                return [
                    {
                        'id': pred[0],
                        'user_id': pred[1],
                        'method': pred[2],
                        'numbers': pred[3],
                        'confidence': float(pred[4]) if pred[4] else 0.0,
                        'timestamp': pred[5].isoformat() if pred[5] else None,
                        'correct_count': pred[6] or 0,
                        'is_validated': pred[7] or False
                    }
                    for pred in result.fetchall()
                ]
        except Exception as e:
            logger.error(f"❌ Erreur récupération prédictions système: {e}")
            return []

    def get_user_predictions(self, session_id=None, limit=20):
        try:
            with self.engine.connect() as conn:
                if session_id:
                    query = text("""
                        SELECT id, user_id, method, numeros, confidence, created_at, correct_count, is_validated
                        FROM predictions 
                        WHERE user_id != 'system' AND (session_id = :session_id OR user_id = :session_id)
                        ORDER BY created_at DESC 
                        LIMIT :limit
                    """)
                    result = conn.execute(query, {"session_id": session_id, "limit": limit})
                else:
                    query = text("""
                        SELECT id, user_id, method, numeros, confidence, created_at, correct_count, is_validated
                        FROM predictions 
                        WHERE user_id != 'system'
                        ORDER BY created_at DESC 
                        LIMIT :limit
                    """)
                    result = conn.execute(query, {"limit": limit})
                return [
                    {
                        'id': pred[0],
                        'user_id': pred[1],
                        'method': pred[2],
                        'numbers': pred[3],
                        'confidence': float(pred[4]) if pred[4] else 0.0,
                        'timestamp': pred[5].isoformat() if pred[5] else None,
                        'correct_count': pred[6] or 0,
                        'is_validated': pred[7] or False
                    }
                    for pred in result.fetchall()
                ]
        except Exception as e:
            logger.error(f"❌ Erreur récupération prédictions utilisateur: {e}")
            return []

    def save_prediction(self, user_id, method, numeros, confidence=0.0, session_id=None):
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    INSERT INTO predictions (user_id, method, numeros, confidence, session_id)
                    VALUES (:user_id, :method, :numeros, :confidence, :session_id)
                    RETURNING id
                """), {
                    "user_id": user_id,
                    "method": method,
                    "numeros": numeros,
                    "confidence": confidence,
                    "session_id": session_id
                })
                conn.commit()
                prediction_id = result.fetchone()[0]
                logger.info(f"✅ Prédiction sauvegardée: {user_id} - {method} (ID: {prediction_id})")
                return prediction_id
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde prédiction: {e}")
            return None

    def save_tirage(self, date_tirage, heure_tirage, numeros, multiplicateur=None, joker=None):
        """Sauvegarde un tirage dans la base de données"""
        try:
            with self.engine.connect() as conn:
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
                    "date_tirage": date_tirage,
                    "heure_tirage": heure_tirage,
                    "numeros": numeros,
                    "multiplicateur": multiplicateur,
                    "joker": joker
                })
                conn.commit()
                tirage_id = result.fetchone()[0]
                logger.info(f"✅ Tirage sauvegardé (ID: {tirage_id})")
                return tirage_id
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde tirage: {e}")
            return None

    def get_all_tirages(self, limit=100):
        """Récupère la liste des tirages"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id, date_tirage, heure_tirage, numeros, multiplicateur, joker, created_at, updated_at
                    FROM tirages
                    ORDER BY date_tirage DESC
                    LIMIT :limit
                """), {"limit": limit})
                return [
                    {
                        'id': row[0],
                        'date_tirage': row[1].isoformat() if row[1] else None,
                        'heure_tirage': str(row[2]) if row[2] else None,
                        'numeros': row[3],
                        'multiplicateur': row[4],
                        'joker': row[5],
                        'created_at': row[6].isoformat() if row[6] else None,
                        'updated_at': row[7].isoformat() if row[7] else None
                    }
                    for row in result.fetchall()
                ]
        except Exception as e:
            logger.error(f"❌ Erreur récupération tirages: {e}")
            return []
