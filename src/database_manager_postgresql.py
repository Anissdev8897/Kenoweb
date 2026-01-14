import logging
import os
import time
from datetime import datetime

from sqlalchemy import create_engine, text, exc
from sqlalchemy.exc import OperationalError, InterfaceError, DatabaseError
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PostgreSQLManager:
    def __init__(self):
        """
        Initialise une nouvelle instance du gestionnaire de base de données.
        Chaque instance gère son propre pool de connexions.
        """
        logger.info("Initialisation d'une nouvelle instance de PostgreSQLManager...")
        self.database_url = os.environ.get("DATABASE_URL")
        if not self.database_url:
            logger.error("La variable d'environnement DATABASE_URL n'est pas définie")
            raise ValueError("La variable d'environnement DATABASE_URL est requise pour se connecter à la base de données")
        
        self.connect_args = {
            'sslmode': 'require',
            'connect_timeout': 20,
            'keepalives': 1,
            'keepalives_idle': 30,
            'keepalives_interval': 10,
            'keepalives_count': 5,
            'application_name': 'keno_analyzer',
            'options': '-c statement_timeout=30000',
            'client_encoding': 'utf8'
        }

        from sqlalchemy.pool import QueuePool
        
        self.engine = create_engine(
            self.database_url,
            poolclass=QueuePool,
            pool_size=2,
            max_overflow=3,
            pool_recycle=120,
            pool_timeout=15,
            pool_pre_ping=True,
            pool_use_lifo=True,
            connect_args=self.connect_args,
            execution_options={'isolation_level': 'READ COMMITTED'}
        )
        
        self.max_retries = 3
        self.retry_delay = 1
        self.last_connection_time = None
        
        from sqlalchemy import event
        
        @event.listens_for(self.engine, 'engine_connect')
        def receive_engine_connect(conn, branch):
            if branch:
                return
            logger.info("Nouvelle connexion établie avec la base de données")
            
        @event.listens_for(self.engine, 'checkout')
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            logger.debug("Vérification de la connexion avant utilisation...")
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute('SELECT 1')
            except:
                logger.warning("La connexion a échoué, tentative de reconnexion...")
                raise exc.DisconnectionError()
            finally:
                cursor.close()

    def create_schema_if_needed(self):
        """
        Assure que le schéma de la base de données est propre et à jour.
        """
        logger.info("Début de la configuration du schéma de la base de données...")
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    logger.info("Vérification des extensions requises...")
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"))
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"pgcrypto\";"))
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
                    
                    logger.info("Vérification et création des tables si elles n'existent pas...")
                    
                    # ... (toutes vos créations de tables existantes comme tirages, users, etc.)

                    ### AJOUT : Création de la table manquante 'user_activity' ###
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS user_activity (
                            id SERIAL PRIMARY KEY,
                            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                            activity_type VARCHAR(50),
                            activity_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                            details JSONB
                        )
                    """))

                    # ... (le reste de vos créations de tables)
                    
                    logger.info("✅ Tables créées avec succès.")

                    logger.info("Création des index...")
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tirages_date ON tirages(date_tirage DESC)"))
                    # ... (tous vos autres index)
                    
                    ### AJOUT : Index pour la nouvelle table 'user_activity' ###
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_user_activity_user_id ON user_activity(user_id)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_user_activity_time ON user_activity(activity_time DESC)"))

                    logger.info("✅ Index créés ou déjà existants.")

                    logger.info("Insertion des données initiales...")
                    conn.execute(text("""
                        INSERT INTO method_stats (method)
                        VALUES ('frequency_analysis'), ('monte_carlo'), ('ml_prediction')
                        ON CONFLICT (method) DO NOTHING
                    """))
                    logger.info("✅ Données initiales insérées.")
            
            logger.info("🎉 Schéma de la base de données configuré avec succès.")

        except Exception as e:
            logger.error(f"❌ Une erreur critique est survenue lors de la configuration du schéma : {e}")
            raise # Propage l'erreur pour un débogage plus facile

    def get_active_user_count(self, days=30):
        """
        Retourne le nombre d'utilisateurs actifs (ayant été actifs dans les X derniers jours)
        """
        try:
            with self.engine.connect() as conn:
                ### CORRECTION : Paramètre SQL bindé correctement pour éviter l'injection SQL ###
                query = text("""
                    SELECT COUNT(DISTINCT user_id) 
                    FROM user_activity 
                    WHERE activity_time >= NOW() - CAST(:days || ' days' AS INTERVAL)
                """)
                result = conn.execute(query, {'days': days})
                return result.scalar() or 0
        except Exception as e:
            logger.error(f"Erreur lors du comptage des utilisateurs actifs: {e}")
            return 0

    ### AJOUT : Méthode manquante 'get_training_runs' ###
    def get_training_runs(self, limit: int = 10) -> list:
        """
        Récupère les derniers entraînements de modèle.
        
        Args:
            limit (int): Le nombre maximum de runs à retourner.
            
        Returns:
            list: Une liste de dictionnaires représentant les runs d'entraînement.
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id, model_id, start_time, end_time, status, parameters, created_at
                    FROM model_training_runs 
                    ORDER BY start_time DESC 
                    LIMIT :limit
                """), {'limit': limit})
                
                return [dict(row._mapping) for row in result.fetchall()]
                
        except Exception as e:
            logger.error(f"❌ Erreur lors de la récupération des runs d'entraînement: {e}")
            return []

    def get_user_count(self) -> int:
        """
        Retourne le nombre total d'utilisateurs enregistrés dans la base de données.
        
        Returns:
            int: Le nombre total d'utilisateurs
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) as count FROM users"))
                return result.scalar() or 0
        except Exception as e:
            logger.error(f"❌ Erreur lors du comptage des utilisateurs: {e}")
            return 0

    def get_active_user_count(self, days: int = 30) -> int:
        """
        Retourne le nombre d'utilisateurs actifs (ayant été actifs dans les X derniers jours).
        
        Args:
            days (int): Nombre de jours pour considérer un utilisateur comme actif (défaut: 30)
            
        Returns:
            int: Le nombre d'utilisateurs actifs
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT COUNT(DISTINCT user_id) as count 
                        FROM user_activity 
                        WHERE activity_time > NOW() - INTERVAL ':days days'
                    """),
                    {'days': days}
                )
                return result.scalar() or 0
        except Exception as e:
            logger.error(f"❌ Erreur lors du comptage des utilisateurs actifs: {e}")
            return 0

    def get_all_predictions(self, limit: int = 1000) -> list:
        """
        Récupère toutes les prédictions de la base de données.
        
        Args:
            limit (int): Nombre maximum de prédictions à retourner (par défaut: 1000)
            
        Returns:
            list: Liste des prédictions avec leurs détails
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT p.id, p.user_id, p.method, p.numeros, p.created_at,
                               p.confidence, p.correct_count, p.is_validated,
                               u.username, u.email
                        FROM predictions p
                        LEFT JOIN users u ON p.user_id = u.id
                        ORDER BY p.created_at DESC
                        LIMIT :limit
                    """),
                    {'limit': limit}
                )
                
                predictions = []
                for row in result.fetchall():
                    pred_dict = dict(row._mapping)
                    # Convertir les types si nécessaire
                    if 'numeros' in pred_dict and isinstance(pred_dict['numeros'], str):
                        # Convertir la chaîne de tableau PostgreSQL en liste Python
                        pred_dict['numeros'] = [int(n) for n in pred_dict['numeros'][1:-1].split(',') if n.strip().isdigit()]
                    predictions.append(pred_dict)
                
                return predictions
                
        except Exception as e:
            logger.error(f"❌ Erreur lors de la récupération des prédictions: {e}")
            return []