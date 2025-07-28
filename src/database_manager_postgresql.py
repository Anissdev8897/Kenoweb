import logging
import os
from datetime import datetime

from sqlalchemy import create_engine, text
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PostgreSQLManager:
    def __init__(self):
        self.database_url = os.environ.get("DATABASE_URL", "postgresql://kenos_user:qYGSudoftPvnoxaT9Seh5IP4itP1kK0a@dpg-d1umeoer433s73eu3d7g-a.frankfurt-postgres.render.com/kenos_vs92")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set and no fallback URL provided.")
        
        self.engine = create_engine(self.database_url)
        self._create_tables()
    
    def _create_tables(self):
        """Crée les tables nécessaires avec le nouveau schéma SQL corrigé"""
        with self.engine.connect() as conn:
            conn.execute(text("""
                -- Extensions nécessaires
                CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
                CREATE EXTENSION IF NOT EXISTS "pgcrypto";
                
                -- Table principale des tirages
                CREATE TABLE IF NOT EXISTS tirages (
                    id SERIAL PRIMARY KEY,
                    date_tirage DATE NOT NULL,
                    numeros INTEGER[] NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Index pour performance
                CREATE INDEX IF NOT EXISTS idx_tirages_date ON tirages(date_tirage);
                CREATE INDEX IF NOT EXISTS idx_tirages_numeros ON tirages USING GIN(numeros);
                
                -- Table des utilisateurs
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    is_admin BOOLEAN DEFAULT FALSE,
                    is_moderator BOOLEAN DEFAULT FALSE,
                    total_predictions INTEGER DEFAULT 0,
                    correct_predictions INTEGER DEFAULT 0,
                    accuracy_rate NUMERIC(5,4) DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Table des prédictions
                CREATE TABLE IF NOT EXISTS predictions (
                    id SERIAL PRIMARY KEY,
                    tirage_id INTEGER REFERENCES tirages(id) ON DELETE CASCADE,
                    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    method VARCHAR(100) NOT NULL,
                    numeros INTEGER[] NOT NULL,
                    confidence NUMERIC(5,4) DEFAULT 0.0,
                    correct_count INTEGER DEFAULT 0,
                    is_validated BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Table des statistiques de méthodes
                CREATE TABLE IF NOT EXISTS method_stats (
                    id SERIAL PRIMARY KEY,
                    method VARCHAR(100) UNIQUE NOT NULL,
                    total_predictions INTEGER DEFAULT 0,
                    successful_predictions INTEGER DEFAULT 0,
                    success_rate DECIMAL(5,2) DEFAULT 0.00,
                    avg_confidence DECIMAL(5,2) DEFAULT 0.00,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Table des résultats d'analyse
                CREATE TABLE IF NOT EXISTS analysis_results (
                    id SERIAL PRIMARY KEY,
                    tirage_id INTEGER REFERENCES tirages(id) ON DELETE CASCADE,
                    analysis_type VARCHAR(50) NOT NULL,
                    result_data JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Table des modèles ML
                CREATE TABLE IF NOT EXISTS ml_models (
                    id SERIAL PRIMARY KEY,
                    model_name VARCHAR(100) NOT NULL,
                    model_type VARCHAR(50) NOT NULL,
                    weights JSONB,
                    training_score NUMERIC(10,8),
                    test_score NUMERIC(10,8),
                    r2_score NUMERIC(10,8),
                    training_time_seconds INTEGER,
                    is_active BOOLEAN DEFAULT FALSE,
                    parameters JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    trained_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Index pour performance
                CREATE INDEX IF NOT EXISTS idx_tirages_date ON tirages(date_tirage DESC);
                CREATE INDEX IF NOT EXISTS idx_tirages_numeros ON tirages USING GIN(numeros);
                CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
                CREATE INDEX IF NOT EXISTS idx_predictions_user ON predictions(user_id);
                CREATE INDEX IF NOT EXISTS idx_predictions_method ON predictions(method);
                CREATE INDEX IF NOT EXISTS idx_predictions_created ON predictions(created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_predictions_tirage ON predictions(tirage_id);
                CREATE INDEX IF NOT EXISTS idx_analysis_tirage ON analysis_results(tirage_id);
                CREATE INDEX IF NOT EXISTS idx_method_stats_method ON method_stats(method);
                
                -- Insertion de données de test
                INSERT INTO tirages (date_tirage, numeros) VALUES 
                ('2024-01-15', ARRAY[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20]),
                ('2024-01-16', ARRAY[21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40])
                ON CONFLICT DO NOTHING;
                
                -- Insertion de statistiques de méthodes
                INSERT INTO method_stats (method, total_predictions, successful_predictions, success_rate, avg_confidence) VALUES 
                ('frequency_analysis', 0, 0, 0.00, 0.00),
                ('monte_carlo', 0, 0, 0.00, 0.00),
                ('ml_prediction', 0, 0, 0.00, 0.00)
                ON CONFLICT (method) DO NOTHING;
                
                -- Insertion d'un administrateur
                INSERT INTO users (username, email, password_hash, is_admin, is_moderator) VALUES 
                ('admin', 'admin@kenoanalyzer.com', '$2b$12$KIXxP3K1Kp5K4K5K6K7K8K9K0K1K2K3K4K5K6K7K8K9K0K1K2', TRUE, TRUE)
                ON CONFLICT DO NOTHING;
            """))
            conn.commit()
            logger.info("✅ Schéma SQL unifié créé avec succès")

    def get_system_predictions(self, limit=50):
        """Récupère les prédictions système (user_id = 'system')"""
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
                predictions = result.fetchall()
                
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
                    for pred in predictions
                ]
        except Exception as e:
            logger.error(f"❌ Erreur récupération prédictions système: {e}")
            return []

    def get_user_predictions(self, session_id=None, limit=20):
        """Récupère les prédictions utilisateur"""
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
                
                predictions = result.fetchall()
                
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
                    for pred in predictions
                ]
        except Exception as e:
            logger.error(f"❌ Erreur récupération prédictions utilisateur: {e}")
            return []

    def save_prediction(self, user_id, method, numeros, confidence=0.0, session_id=None):
        """Sauvegarde une prédiction dans la base de données (SQL pur)"""
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
                logger.info(f"✅ Tirage sauvegardé: {date_tirage} {heure_tirage} (ID: {tirage_id})")
                return tirage_id
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde tirage: {e}")
            return None

    def get_database_info(self):
        """Retourne les informations sur la base de données"""
        try:
            with self.engine.connect() as conn:
                tirages_count = conn.execute(text("SELECT COUNT(*) FROM tirages")).fetchone()[0]
                predictions_count = conn.execute(text("SELECT COUNT(*) FROM predictions")).fetchone()[0]
                users_count = conn.execute(text("SELECT COUNT(*) FROM users")).fetchone()[0]
                
                return {
                    'type': 'postgresql',
                    'tirages_count': tirages_count,
                    'predictions_count': predictions_count,
                    'users_count': users_count,
                    'status': 'connected',
                    'host': self.database_url.split('@')[-1].split('/')[0]
                }
        except Exception as e:
            logger.error(f"❌ Erreur récupération infos base: {e}")
            return {'type': 'postgresql', 'status': 'error', 'error': str(e)}
            
    def test_connection(self):
        """Test la connexion à la base de données"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"❌ Test connexion échoué: {e}")
            return False
    
    def close(self):
        """Ferme la connexion à la base de données"""
        logger.info("🔒 Connexion base de données fermée (SQL pur)")

# Instance globale
pg_manager = None

def get_postgresql_manager():
    global pg_manager
    if pg_manager is None:
        pg_manager = PostgreSQLManager()
    return pg_manager

