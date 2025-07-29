import logging
import os
from datetime import datetime

from sqlalchemy import create_engine, text
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Instance globale du gestionnaire de base de données
_postgresql_manager_instance = None

def get_postgresql_manager():
    """
    Retourne une instance unique du gestionnaire de base de données PostgreSQL.
    Implémente le pattern Singleton pour éviter les connexions multiples.
    """
    global _postgresql_manager_instance
    if _postgresql_manager_instance is None:
        _postgresql_manager_instance = PostgreSQLManager()
    return _postgresql_manager_instance

class PostgreSQLManager:
    def __init__(self):
        self.database_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://kenos_user:qYGSudoftPvnoxaT9Seh5IP4itP1kK0a@dpg-d1umeoer433s73eu3d7g-a.frankfurt-postgres.render.com/kenos_vs92"
        )
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set and no fallback URL provided.")
        
        # SOLUTION N°1 : Forcer la connexion SSL
        # On ajoute "?sslmode=require" si ce n'est pas déjà présent
        if "?sslmode" not in self.database_url:
            self.database_url += "?sslmode=require"
            
        self.engine = create_engine(self.database_url)
        self._create_schema()

    def _create_schema(self):
        """Crée les tables et les index en s'assurant de partir d'un état propre."""
        try:
            # --- ÉTAPE 1: CRÉATION DES TABLES ---
            with self.engine.connect() as conn:
                with conn.begin():
                    logger.info("Vérification et création des tables si elles n'existent pas...")
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\""))
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"pgcrypto\""))
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))

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
                    conn.execute(text("DROP INDEX IF EXISTS idx_tirages_date;"))
                    conn.execute(text("DROP INDEX IF EXISTS idx_tirages_numeros;"))
                    conn.execute(text("DROP INDEX IF EXISTS idx_users_username;"))
                    conn.execute(text("DROP INDEX IF EXISTS idx_users_email;"))
                    conn.execute(text("DROP INDEX IF EXISTS idx_predictions_user;"))
                    conn.execute(text("DROP INDEX IF EXISTS idx_predictions_method;"))
                    conn.execute(text("DROP INDEX IF EXISTS idx_predictions_created;"))
                    conn.execute(text("DROP INDEX IF EXISTS idx_analysis_tirage;"))

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

    # ... (Le reste de vos fonctions) ...
    
    # SOLUTION N°3 : Accepter des arguments supplémentaires pour ne pas planter
    def save_tirage(self, date_tirage, heure_tirage, numeros, multiplicateur=None, joker=None, **kwargs):
        """Sauvegarde un tirage dans la base de données"""
        try:
            with self.engine.connect() as conn:
                # La transaction est gérée par le with...begin()
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
                        "date_tirage": date_tirage,
                        "heure_tirage": heure_tirage,
                        "numeros": numeros,
                        "multiplicateur": multiplicateur,
                        "joker": joker
                    })
                    tirage_id = result.fetchone()[0]
                    logger.info(f"✅ Tirage sauvegardé (ID: {tirage_id})")
                    return tirage_id
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde tirage: {e}")
            return None
            
    # Collez ici le reste de vos fonctions (save_user, get_user_by_username, etc.)
    # ...

