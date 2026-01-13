import logging
import os
import json
from datetime import datetime
from sqlalchemy import create_engine, text, event
from sqlalchemy.engine import Engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Enable foreign key support for SQLite
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

class SQLiteManager:
    def __init__(self, db_path="keno.db"):
        logger.info(f"Initialisation de SQLiteManager avec {db_path}...")
        self.database_url = f"sqlite:///{db_path}"
        self.engine = create_engine(self.database_url)

    def create_schema_if_needed(self):
        logger.info("Configuration du schéma de la base de données SQLite...")
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    # Users table
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS users (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            username TEXT UNIQUE,
                            email TEXT UNIQUE,
                            password_hash TEXT,
                            is_admin BOOLEAN DEFAULT 0,
                            is_moderator BOOLEAN DEFAULT 0,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            last_login TIMESTAMP
                        )
                    """))

                    # User Activity table
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS user_activity (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                            activity_type VARCHAR(50),
                            activity_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            details TEXT
                        )
                    """))

                    # Tirages table
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS tirages (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            date_tirage DATE,
                            periode VARCHAR(20),
                            numeros TEXT, -- Stored as JSON or comma separated
                            multiplicateur INTEGER,
                            joker VARCHAR(20),
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(date_tirage, periode)
                        )
                    """))

                    # Predictions table
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS predictions (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id TEXT, -- Can be 'system' or user ID/username
                            method VARCHAR(100),
                            numeros TEXT, -- Stored as JSON
                            confidence FLOAT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            correct_count INTEGER DEFAULT 0,
                            is_validated BOOLEAN DEFAULT 0,
                            tirage_id INTEGER REFERENCES tirages(id),
                            session_id TEXT
                        )
                    """))

                    # Model Training Runs table
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS model_training_runs (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            model_id VARCHAR(100),
                            model_type VARCHAR(50),
                            start_time TIMESTAMP,
                            end_time TIMESTAMP,
                            status VARCHAR(20),
                            parameters TEXT, -- JSON
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            created_by INTEGER REFERENCES users(id)
                        )
                    """))

                    # Method Stats table (if needed)
                    conn.execute(text("""
                         CREATE TABLE IF NOT EXISTS method_stats (
                            method VARCHAR(100) PRIMARY KEY
                         )
                    """))

                    # Insert initial data
                    conn.execute(text("""
                        INSERT OR IGNORE INTO method_stats (method)
                        VALUES ('frequency_analysis'), ('monte_carlo'), ('ml_prediction')
                    """))

            logger.info("✅ Schéma SQLite configuré avec succès.")

        except Exception as e:
            logger.error(f"❌ Erreur lors de la configuration du schéma : {e}")
            raise

    def get_active_user_count(self, days=30):
        try:
            with self.engine.connect() as conn:
                query = text(f"""
                    SELECT COUNT(DISTINCT user_id)
                    FROM user_activity
                    WHERE activity_time >= datetime('now', '-{days} days')
                """)
                result = conn.execute(query)
                return result.scalar() or 0
        except Exception as e:
            logger.error(f"Erreur lors du comptage des utilisateurs actifs: {e}")
            return 0

    def get_training_runs(self, limit: int = 10) -> list:
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id, model_id, start_time, end_time, status, parameters, created_at
                    FROM model_training_runs
                    ORDER BY start_time DESC
                    LIMIT :limit
                """), {'limit': limit})

                runs = []
                for row in result.fetchall():
                    run = dict(row._mapping)
                    # Convert strings to appropriate types if needed (e.g., parameters from JSON)
                    if run.get('parameters') and isinstance(run['parameters'], str):
                         try:
                             run['parameters'] = json.loads(run['parameters'])
                         except:
                             pass
                    runs.append(run)
                return runs
        except Exception as e:
            logger.error(f"❌ Erreur lors de la récupération des runs d'entraînement: {e}")
            return []

    def get_user_count(self) -> int:
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) as count FROM users"))
                return result.scalar() or 0
        except Exception as e:
            logger.error(f"❌ Erreur lors du comptage des utilisateurs: {e}")
            return 0

    def get_all_predictions(self, limit: int = 1000) -> list:
        try:
            with self.engine.connect() as conn:
                # We need to handle the join carefully if user_id is text in predictions but int ID in users
                # Assuming predictions.user_id might store username or ID as string.
                # In SQLite simplified schema, let's just select from predictions.
                result = conn.execute(
                    text("""
                        SELECT p.id, p.user_id, p.method, p.numeros, p.created_at,
                               p.confidence, p.correct_count, p.is_validated
                        FROM predictions p
                        ORDER BY p.created_at DESC
                        LIMIT :limit
                    """),
                    {'limit': limit}
                )

                predictions = []
                for row in result.fetchall():
                    pred_dict = dict(row._mapping)
                    if 'numeros' in pred_dict and isinstance(pred_dict['numeros'], str):
                        try:
                            pred_dict['numeros'] = json.loads(pred_dict['numeros'])
                        except:
                            # Try parsing if it's like postgres array string
                            if pred_dict['numeros'].startswith('{'):
                                pred_dict['numeros'] = [int(n) for n in pred_dict['numeros'][1:-1].split(',') if n.strip().isdigit()]
                            pass
                    predictions.append(pred_dict)

                return predictions
        except Exception as e:
            logger.error(f"❌ Erreur lors de la récupération des prédictions: {e}")
            return []

    def save_prediction(self, user_id, method, numeros, confidence, session_id=None, tirage_id=None):
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    query = text("""
                        INSERT INTO predictions (user_id, method, numeros, confidence, session_id, tirage_id)
                        VALUES (:user_id, :method, :numeros, :confidence, :session_id, :tirage_id)
                    """)

                    # Convert list to JSON string for storage
                    numeros_json = json.dumps(numeros) if isinstance(numeros, list) else numeros

                    result = conn.execute(query, {
                        "user_id": str(user_id),
                        "method": method,
                        "numeros": numeros_json,
                        "confidence": confidence,
                        "session_id": session_id,
                        "tirage_id": tirage_id
                    })

                    # Get the last inserted ID
                    # In SQLAlchemy with SQLite, result.lastrowid should work
                    return result.lastrowid
        except Exception as e:
            logger.error(f"Erreur sauvegarde prédiction: {e}")
            return None

    def get_user_predictions(self, session_id=None, limit=20):
        try:
            with self.engine.connect() as conn:
                params = {'limit': limit}
                where_clause = ""
                if session_id:
                    where_clause = "WHERE session_id = :session_id"
                    params['session_id'] = session_id

                query = text(f"""
                    SELECT * FROM predictions
                    {where_clause}
                    ORDER BY created_at DESC
                    LIMIT :limit
                """)

                result = conn.execute(query, params)
                predictions = []
                for row in result.fetchall():
                    pred = dict(row._mapping)
                    if isinstance(pred.get('numeros'), str):
                        try:
                            pred['numeros'] = json.loads(pred['numeros'])
                        except:
                            pass
                    predictions.append(pred)
                return predictions
        except Exception as e:
            logger.error(f"Erreur get_user_predictions: {e}")
            return []

    def get_system_predictions(self, limit=50):
        try:
            with self.engine.connect() as conn:
                query = text("""
                    SELECT * FROM predictions
                    WHERE user_id = 'system'
                    ORDER BY created_at DESC
                    LIMIT :limit
                """)

                result = conn.execute(query, {'limit': limit})
                predictions = []
                for row in result.fetchall():
                    pred = dict(row._mapping)
                    if isinstance(pred.get('numeros'), str):
                        try:
                            pred['numeros'] = json.loads(pred['numeros'])
                        except:
                            pass
                    predictions.append(pred)
                return predictions
        except Exception as e:
            logger.error(f"Erreur get_system_predictions: {e}")
            return []

    def save_tirage(self, date_tirage, periode, numeros, multiplicateur, joker):
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    query = text("""
                        INSERT OR IGNORE INTO tirages (date_tirage, periode, numeros, multiplicateur, joker)
                        VALUES (:date_tirage, :periode, :numeros, :multiplicateur, :joker)
                    """)

                    numeros_json = json.dumps(numeros) if isinstance(numeros, list) else numeros

                    result = conn.execute(query, {
                        "date_tirage": date_tirage,
                        "periode": periode,
                        "numeros": numeros_json,
                        "multiplicateur": multiplicateur,
                        "joker": joker
                    })
                    # Use a select to get ID if it was ignored
                    if result.rowcount == 0:
                         id_res = conn.execute(text("SELECT id FROM tirages WHERE date_tirage=:d AND periode=:p"), {"d": date_tirage, "p": periode})
                         row = id_res.fetchone()
                         return row[0] if row else None
                    return result.lastrowid
        except Exception as e:
            logger.error(f"Erreur sauvegarde tirage: {e}")
            return None

    def backup_full_database(self):
        # Implement backup if needed, or just log
        logger.info("Backup database called (not implemented for SQLite)")
        pass

    def start_training_run(self, model_type, parameters, created_by, model_name=""):
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    query = text("""
                        INSERT INTO model_training_runs (model_type, parameters, created_by, status, start_time, model_id)
                        VALUES (:model_type, :parameters, :created_by, 'in_progress', CURRENT_TIMESTAMP, :model_name)
                    """)
                    result = conn.execute(query, {
                        "model_type": model_type,
                        "parameters": json.dumps(parameters),
                        "created_by": created_by,
                        "model_name": model_name
                    })
                    return result.lastrowid
        except Exception as e:
            logger.error(f"Erreur start_training_run: {e}")
            return None

    def update_training_run_status(self, run_id, status, error_message=None):
         try:
            with self.engine.connect() as conn:
                with conn.begin():
                    query = text("""
                        UPDATE model_training_runs
                        SET status = :status
                        WHERE id = :run_id
                    """)
                    conn.execute(query, {"status": status, "run_id": run_id})
         except Exception as e:
            logger.error(f"Erreur update_training_run_status: {e}")

    def complete_training_run(self, run_id, model_id, metrics):
         try:
            with self.engine.connect() as conn:
                with conn.begin():
                    query = text("""
                        UPDATE model_training_runs
                        SET status = 'completed', end_time = CURRENT_TIMESTAMP, model_id = :model_id
                        WHERE id = :run_id
                    """)
                    conn.execute(query, {"model_id": str(model_id), "run_id": run_id})
         except Exception as e:
            logger.error(f"Erreur complete_training_run: {e}")

    def get_training_run_by_status(self, status):
         try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT * FROM model_training_runs WHERE status = :status LIMIT 1"), {"status": status})
                row = result.fetchone()
                if row:
                     return dict(row._mapping)
                return None
         except Exception as e:
            logger.error(f"Erreur get_training_run_by_status: {e}")
            return None
