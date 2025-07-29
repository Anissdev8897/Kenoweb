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
        
        self.engine = create_engine(self.database_url)
        self._create_tables()
    
    def _create_tables(self):
        """Crée les tables nécessaires pour correspondre au schéma de la base de données existante."""
        with self.engine.connect() as conn:
            try:
                # Activer les extensions nécessaires
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\""))
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"pgcrypto\""))
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
                
                # --- Table tirages ---
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS tirages (
                        id SERIAL PRIMARY KEY,
                        date_tirage DATE NOT NULL UNIQUE,
                        heure_tirage TIME,
                        numeros INTEGER[] NOT NULL DEFAULT '{}'::INTEGER[],
                        multiplicateur INTEGER,
                        joker VARCHAR(20),
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tirages_date ON tirages(date_tirage DESC)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tirages_numeros ON tirages USING GIN(numeros)"))

                # --- Table users (INCHANGÉE COMME DEMANDÉ) ---
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        username VARCHAR(50) UNIQUE NOT NULL,
                        email VARCHAR(255) UNIQUE,
                        password_hash VARCHAR(255) NOT NULL,
                        is_admin BOOLEAN DEFAULT FALSE,
                        is_moderator BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        last_active TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)"))

                # --- Table predictions ---
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS predictions (
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
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_predictions_user ON predictions(user_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_predictions_method ON predictions(method)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_predictions_created ON predictions(created_at DESC)"))

                # --- Table method_stats (MISE À JOUR) ---
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS method_stats (
                        id SERIAL PRIMARY KEY,
                        method VARCHAR(100) UNIQUE NOT NULL,
                        total_predictions INTEGER DEFAULT 0,
                        correct_predictions INTEGER DEFAULT 0,
                        accuracy FLOAT8 DEFAULT 0.0,
                        last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    )
                """))

                # --- Table analysis_results ---
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS analysis_results (
                        id SERIAL PRIMARY KEY,
                        tirage_id INTEGER REFERENCES tirages(id) ON DELETE CASCADE,
                        analysis_type VARCHAR(50) NOT NULL,
                        result_data JSONB,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(tirage_id, analysis_type)
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_analysis_tirage ON analysis_results(tirage_id)"))

                # --- Table ml_models (MISE À JOUR SELON L'IMAGE) ---
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS ml_models (
                        id SERIAL PRIMARY KEY,
                        model_name VARCHAR(100) NOT NULL,
                        model_type VARCHAR(50) NOT NULL,
                        s3_path VARCHAR(500),
                        training_score NUMERIC(10,8),
                        test_score NUMERIC(10,8),
                        r2_score NUMERIC(10,8),
                        training_time_seconds INTEGER,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        trained_at TIMESTAMP WITH TIME ZONE
                    )
                """))

                # Insertion des méthodes par défaut dans method_stats
                conn.execute(text("""
                    INSERT INTO method_stats (method)
                    VALUES ('frequency_analysis'), ('monte_carlo'), ('ml_prediction')
                    ON CONFLICT (method) DO NOTHING
                """))
                
                conn.commit()
                logger.info("✅ Les tables et les index ont été vérifiés et créés avec succès.")
            except Exception as e:
                logger.error(f"❌ Erreur lors de la création des tables : {e}")
                conn.rollback()

    # Le reste des fonctions (get_system_predictions, save_prediction, etc.) reste inchangé
    # ... (collez ici le reste de vos fonctions de la classe)
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

