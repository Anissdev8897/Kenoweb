import logging
import os
import time
from datetime import datetime

from sqlalchemy import create_engine, text, exc
from sqlalchemy.exc import OperationalError, InterfaceError, DatabaseError
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
        # Utiliser uniquement la variable d'environnement, sans valeur par défaut
        self.database_url = os.environ.get("DATABASE_URL")
        if not self.database_url:
            logger.error("La variable d'environnement DATABASE_URL n'est pas définie")
            raise ValueError("La variable d'environnement DATABASE_URL est requise pour se connecter à la base de données")
        
        # Configuration SSL avancée pour Render avec reconnexion
        self.connect_args = {
            'sslmode': 'require',
            'sslrootcert': None,
            'sslcert': None,
            'sslkey': None,
            'ssl_min_protocol_version': 'TLSv1.2',
            'ssl_max_protocol_version': 'TLSv1.3',
            'connect_timeout': 20,
            'keepalives': 1,
            'keepalives_idle': 30,
            'keepalives_interval': 10,
            'keepalives_count': 5,
            'application_name': 'keno_analyzer',
            'options': '-c statement_timeout=30000',  # Timeout de 30 secondes par requête
            'client_encoding': 'utf8'
        }

        from sqlalchemy.pool import QueuePool
        
        # Configurer le moteur avec des paramètres optimisés pour Render
        self.engine = create_engine(
            self.database_url,
            poolclass=QueuePool,
            pool_size=2,            # Réduit pour éviter la surcharge
            max_overflow=3,         # Réduit pour éviter la surcharge
            pool_recycle=120,       # Recycle plus fréquemment (2 minutes)
            pool_timeout=15,        # Timeout plus court pour obtenir une connexion
            pool_pre_ping=True,     # Vérifie la connexion avant utilisation
            pool_use_lifo=True,     # Réutilise les connexions récentes
            connect_args=self.connect_args,
            execution_options={
                'isolation_level': 'READ COMMITTED',
                'compiled_cache': None
            }
        )
        
        # Configuration des tentatives de reconnexion
        self.max_retries = 3
        self.retry_delay = 1
        self.last_connection_time = None
        
        # Configurer le gestionnaire d'événements pour gérer les erreurs de connexion
        from sqlalchemy import event
        
        def reconnect_engine():
            """Réinitialise le moteur de base de données et établit une nouvelle connexion"""
            logger.warning("Tentative de reconnexion à la base de données...")
            self.engine.dispose()  # Ferme toutes les connexions existantes
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
                execution_options={
                    'isolation_level': 'READ COMMITTED',
                    'compiled_cache': None
                }
            )
            self.last_connection_time = datetime.now()
            logger.info("Nouvelle connexion à la base de données établie")
            
        self.reconnect_engine = reconnect_engine
        
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
        Cette méthode doit être appelée une seule fois par le processus principal au démarrage.
        """
        logger.info("Début de la configuration du schéma de la base de données...")
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    # --- ÉTAPE 1: CRÉATION DES EXTENSIONS ---
                    logger.info("Vérification des extensions requises...")
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"))
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"pgcrypto\";"))
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
                    
                    # --- ÉTAPE 2: CRÉATION DES TABLES ---
                    logger.info("Vérification et création des tables si elles n'existent pas...")
                    
                    # Table tirages
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
                    
                    # Table users
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS users (
                            id SERIAL PRIMARY KEY,
                            username VARCHAR(50) UNIQUE NOT NULL,
                            email VARCHAR(255) UNIQUE,
                            password VARCHAR(255) NOT NULL,
                            is_admin BOOLEAN DEFAULT FALSE,
                            is_moderator BOOLEAN DEFAULT FALSE,
                            is_active BOOLEAN DEFAULT TRUE,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                            last_login TIMESTAMP WITH TIME ZONE,
                            last_active TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        )
                    """))
                    
                    # Table model_training_runs
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS model_training_runs (
                            id SERIAL PRIMARY KEY,
                            model_id INTEGER REFERENCES ml_models(id) ON DELETE CASCADE,
                            start_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                            end_time TIMESTAMP WITH TIME ZONE,
                            status VARCHAR(50) NOT NULL,
                            metrics JSONB,
                            parameters JSONB,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        )
                    """))
                    
                    # Table predictions
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
                    
                    # Table method_stats (avec 'correct_predictions' et 'accuracy')
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS method_stats (
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
                        CREATE TABLE IF NOT EXISTS analysis_results (
                            id SERIAL PRIMARY KEY,
                            tirage_id INTEGER REFERENCES tirages(id) ON DELETE CASCADE,
                            analysis_type VARCHAR(50) NOT NULL,
                            result_data JSONB,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(tirage_id, analysis_type)
                        )
                    """))
                    
                    # Table ml_models avec métadonnées
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS ml_models (
                            id SERIAL PRIMARY KEY,
                            model_name VARCHAR(100) NOT NULL,
                            model_type VARCHAR(50) NOT NULL,
                            model_binary BYTEA,
                            training_score NUMERIC(10,8),
                            test_score NUMERIC(10,8),
                            r2_score NUMERIC(10,8),
                            training_time_seconds INTEGER,
                            metadata JSONB,  -- Ajout de la colonne metadata
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                            trained_at TIMESTAMP WITH TIME ZONE,
                            version VARCHAR(50)  -- Ajout d'un champ version
                        )
                    """))
                    
                    # Table model_metrics avec clé étrangère vers ml_models
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS model_metrics (
                            id SERIAL PRIMARY KEY,
                            model_id INTEGER REFERENCES ml_models(id) ON DELETE CASCADE,
                            metric_name VARCHAR(100) NOT NULL,
                            metric_value NUMERIC(10,8) NOT NULL,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(model_id, metric_name)
                        )
                    """))
                    logger.info("✅ Tables créées avec succès.")

                    # --- ÉTAPE 2: CRÉATION DES INDEX ---
                    logger.info("Création des index...")
                    # Utilisation de IF NOT EXISTS pour éviter les erreurs de doublons
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tirages_date ON tirages(date_tirage DESC)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tirages_numeros ON tirages USING GIN(numeros)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_predictions_user ON predictions(user_id)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_predictions_method ON predictions(method)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_predictions_created ON predictions(created_at DESC)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_analysis_tirage ON analysis_results(tirage_id)"))
                    logger.info("✅ Index créés ou déjà existants.")

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

    def save_prediction(self, user_id, method, numeros, confidence=0.0, session_id=None, tirage_id=None):
        """Sauvegarde une prédiction dans la table predictions selon le schéma réel"""
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    result = conn.execute(text("""
                        INSERT INTO predictions (user_id, method, numeros, confidence, session_id, tirage_id)
                        VALUES (:user_id, :method, :numeros, :confidence, :session_id, :tirage_id)
                        RETURNING id
                    """), {
                        "user_id": user_id,
                        "method": method,
                        "numeros": numeros,
                        "confidence": confidence or 0.0,
                        "session_id": session_id,
                        "tirage_id": tirage_id
                    })
                    prediction_id = result.fetchone()[0]
                    logger.info(f"✅ Prédiction sauvegardée: {user_id} - {method} (ID: {prediction_id})")
                    return prediction_id

        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde prédiction: {e}")
            return None

    def save_user_prediction(self, user_id, tirage_id, predicted_numbers, confidence_score, prediction_method):
        """Sauvegarde une prédiction dans la table user_predictions selon le schéma réel"""
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    result = conn.execute(text("""
                        INSERT INTO user_predictions (user_id, tirage_id, predicted_numbers, confidence_score, prediction_method)
                        VALUES (:user_id, :tirage_id, :predicted_numbers, :confidence_score, :prediction_method)
                        RETURNING id
                    """), {
                        "user_id": user_id,
                        "tirage_id": tirage_id,
                        "predicted_numbers": predicted_numbers,
                        "confidence_score": confidence_score,
                        "prediction_method": prediction_method
                    })
                    prediction_id = result.fetchone()[0]
                    logger.info(f"✅ Prédiction utilisateur sauvegardée: {user_id} - {prediction_method} (ID: {prediction_id})")
                    return prediction_id

        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde prédiction utilisateur: {e}")
            return None

    def save_analysis_result(self, tirage_id, analysis_type, result_data):
        """Sauvegarde un résultat d'analyse dans la table analysis_results"""
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    result = conn.execute(text("""
                        INSERT INTO analysis_results (tirage_id, analysis_type, result_data)
                        VALUES (:tirage_id, :analysis_type, :result_data)
                        ON CONFLICT (tirage_id, analysis_type) DO UPDATE
                        SET result_data = EXCLUDED.result_data,
                            created_at = CURRENT_TIMESTAMP
                        RETURNING id
                    """), {
                        "tirage_id": tirage_id,
                        "analysis_type": analysis_type,
                        "result_data": result_data
                    })
                    analysis_id = result.fetchone()[0]
                    logger.info(f"✅ Résultat d'analyse sauvegardé: {analysis_type} pour tirage {tirage_id} (ID: {analysis_id})")
                    return analysis_id

        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde résultat d'analyse: {e}")
            return None

    def update_method_stats(self, method, total_predictions=None, correct_predictions=None, accuracy=None):
        """Met à jour les statistiques d'une méthode dans la table method_stats"""
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    # Vérifier si la méthode existe
                    existing = conn.execute(text("""
                        SELECT id FROM method_stats WHERE method = :method
                    """), {"method": method}).fetchone()
                    
                    if existing:
                        # Mettre à jour
                        update_fields = []
                        params = {"method": method}
                        
                        if total_predictions is not None:
                            update_fields.append("total_predictions = :total_predictions")
                            params["total_predictions"] = total_predictions
                        
                        if correct_predictions is not None:
                            update_fields.append("correct_predictions = :correct_predictions")
                            params["correct_predictions"] = correct_predictions
                        
                        if accuracy is not None:
                            update_fields.append("accuracy = :accuracy")
                            params["accuracy"] = accuracy
                        
                        if update_fields:
                            update_fields.append("last_updated = CURRENT_TIMESTAMP")
                            query = f"UPDATE method_stats SET {', '.join(update_fields)} WHERE method = :method RETURNING id"
                            result = conn.execute(text(query), params)
                            stats_id = result.fetchone()[0]
                            logger.info(f"✅ Statistiques mises à jour pour {method} (ID: {stats_id})")
                            return stats_id
                    else:
                        # Créer nouvelle entrée
                        result = conn.execute(text("""
                            INSERT INTO method_stats (method, total_predictions, correct_predictions, accuracy)
                            VALUES (:method, :total_predictions, :correct_predictions, :accuracy)
                            RETURNING id
                        """), {
                            "method": method,
                            "total_predictions": total_predictions or 0,
                            "correct_predictions": correct_predictions or 0,
                            "accuracy": accuracy or 0.0
                        })
                        stats_id = result.fetchone()[0]
                        logger.info(f"✅ Nouvelles statistiques créées pour {method} (ID: {stats_id})")
                        return stats_id

        except Exception as e:
            logger.error(f"❌ Erreur mise à jour statistiques méthode: {e}")
            return None

    def save_tirage(self, date_tirage, numeros, heure_tirage=None, multiplicateur=None, joker=None, **kwargs):
        """Sauvegarde un tirage dans la base de données, en gérant plusieurs formats de date.
        
        Args:
            date_tirage (str ou date): Date du tirage (format 'DD/MM/YYYY' ou 'YYYY-MM-DD' ou objet date)
            numeros (list): Liste des numéros tirés
            heure_tirage (str, optional): Heure du tirage. Par défaut None.
            multiplicateur (int, optional): Multiplicateur de gains. Par défaut None.
            joker (str, optional): Numéro joker. Par défaut None.
            
        Returns:
            int: ID du tirage sauvegardé ou None en cas d'échec
        """
        last_exception = None
        
        # Gérer plusieurs formats de date de manière robuste
        if isinstance(date_tirage, str):
            try:
                date_obj = datetime.strptime(date_tirage, '%d/%m/%Y').date()
            except ValueError:
                try:
                    date_obj = datetime.strptime(date_tirage, '%Y-%m-%d').date()
                except ValueError as ve:
                    logger.error(f"Format de date non reconnu pour '{date_tirage}'. Utilisez 'DD/MM/YYYY' ou 'YYYY-MM-DD'.")
                    return None
        else:
            date_obj = date_tirage
        
        for attempt in range(self.max_retries):
            try:
                # Vérifier si une reconnexion est nécessaire
                if self.last_connection_time is None or (datetime.now() - self.last_connection_time).total_seconds() > 3600:  # 1 heure
                    logger.info("Nouvelle connexion nécessaire (délai écoulé)")
                    self.reconnect_engine()
                
                with self.engine.connect() as conn:
                    # Début de la transaction
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
                            "date_tirage": date_obj, 
                            "heure_tirage": heure_tirage, 
                            "numeros": numeros,
                            "multiplicateur": multiplicateur, 
                            "joker": joker
                        })
                        
                        tirage_id = result.fetchone()[0]
                        logger.info(f"✅ Tirage du {date_obj.strftime('%d/%m/%Y')} sauvegardé (ID: {tirage_id})")
                        return tirage_id
                        
            except Exception as e:
                last_exception = e
                if attempt == self.max_retries - 1:  # Dernière tentative
                    logger.error(f"❌ Échec après {self.max_retries} tentatives de sauvegarde du tirage du {date_obj}")
                    logger.error(f"Dernière erreur: {str(e)}")
                    return None
                
                # Tenter une reconnexion en cas d'erreur de connexion
                if isinstance(e, (exc.OperationalError, exc.InterfaceError, exc.DatabaseError)):
                    logger.warning(f"⚠️ Erreur de connexion détectée: {str(e)}")
                    try:
                        self.reconnect_engine()
                    except Exception as reconnect_error:
                        logger.error(f"❌ Échec de la reconnexion: {str(reconnect_error)}")
                
                # Attente exponentielle avant une nouvelle tentative
                wait_time = (2 ** attempt) * self.retry_delay
                logger.warning(f"⚠️ Tentative {attempt + 1}/{self.max_retries} échouée. Nouvelle tentative dans {wait_time:.1f}s...")
                time.sleep(wait_time)
        
        logger.error(f"❌ Échec critique de sauvegarde du tirage après {self.max_retries} tentatives")
        if last_exception:
            logger.error(f"Dernière erreur: {str(last_exception)}")
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
            
    def save_ml_model(self, model_name: str, model_type: str, model_binary: bytes, 
                     training_score: float = None, test_score: float = None, 
                     r2_score: float = None, training_time_seconds: int = None,
                     metadata: dict = None, version: str = '1.0') -> int:
        """
        Sauvegarde un modèle ML dans la base de données.
        
        Args:
            model_name (str): Nom du modèle
            model_type (str): Type de modèle (ex: 'random_forest', 'neural_network')
            model_binary (bytes): Données binaires du modèle sérialisé
            training_score (float, optional): Score sur l'ensemble d'entraînement
            test_score (float, optional): Score sur l'ensemble de test
            r2_score (float, optional): Score R² du modèle
            training_time_seconds (int, optional): Temps d'entraînement en secondes
            metadata (dict, optional): Métadonnées supplémentaires du modèle
            version (str, optional): Version du modèle (défaut: '1.0')
            
        Returns:
            int: L'ID du modèle sauvegardé ou None en cas d'erreur
        """
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    result = conn.execute(text("""
                        INSERT INTO ml_models (
                            model_name, model_type, model_binary, training_score,
                            test_score, r2_score, training_time_seconds,
                            metadata, version, trained_at
                        ) VALUES (
                            :model_name, :model_type, :model_binary, :training_score,
                            :test_score, :r2_score, :training_time_seconds,
                            :metadata, :version, CURRENT_TIMESTAMP
                        )
                        RETURNING id
                    """), {
                        'model_name': model_name,
                        'model_type': model_type,
                        'model_binary': model_binary,
                        'training_score': training_score,
                        'test_score': test_score,
                        'r2_score': r2_score,
                        'training_time_seconds': training_time_seconds,
                        'metadata': metadata,
                        'version': version
                    })
                    
                    model_id = result.scalar()
                    logger.info(f"✅ Modèle ML '{model_name}' sauvegardé avec l'ID: {model_id}")
                    return model_id
                    
        except Exception as e:
            logger.error(f"❌ Erreur lors de la sauvegarde du modèle ML: {e}")
            return None

    def get_ml_model(self, model_id: int):
        """
        Récupère un modèle ML par son ID.
        
        Args:
            model_id (int): ID du modèle à récupérer
            
        Returns:
            dict: Les données du modèle ou None si non trouvé
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT * FROM ml_models WHERE id = :model_id
                """), {'model_id': model_id})
                
                row = result.fetchone()
                if row:
                    return dict(row._mapping)
                return None
                
        except Exception as e:
            logger.error(f"❌ Erreur lors de la récupération du modèle ML: {e}")
            return None

    def get_latest_ml_model(self, model_type: str = None):
        """
        Récupère le dernier modèle ML entraîné.
        
        Args:
            model_type (str, optional): Type de modèle à filtrer
            
        Returns:
            dict: Les données du modèle ou None si non trouvé
        """
        try:
            with self.engine.connect() as conn:
                query = """
                    SELECT * FROM ml_models 
                    WHERE trained_at IS NOT NULL
                """
                params = {}
                
                if model_type:
                    query += " AND model_type = :model_type"
                    params['model_type'] = model_type
                    
                query += " ORDER BY trained_at DESC LIMIT 1"
                
                result = conn.execute(text(query), params)
                row = result.fetchone()
                
                if row:
                    return dict(row._mapping)
                return None
                
        except Exception as e:
            logger.error(f"❌ Erreur lors de la récupération du dernier modèle ML: {e}")
            return None

    def start_training_run(self, model_type: str, parameters: dict, created_by: int = None) -> int:
        """
        Démarre un nouvel entraînement de modèle.
        
        Args:
            model_type (str): Type de modèle à entraîner
            parameters (dict): Paramètres d'entraînement
            created_by (int, optional): ID de l'utilisateur qui a démarré l'entraînement
            
        Returns:
            int: L'ID du run d'entraînement ou None en cas d'erreur
        """
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    result = conn.execute(text("""
                        INSERT INTO model_training_runs (
                            model_type, parameters, status, created_by, start_time
                        ) VALUES (
                            :model_type, :parameters, 'pending', :created_by, CURRENT_TIMESTAMP
                        )
                        RETURNING id
                    """), {
                        'model_type': model_type,
                        'parameters': parameters,
                        'created_by': created_by
                    })
                    
                    run_id = result.scalar()
                    logger.info(f"✅ Démarrage de l'entraînement du modèle {model_type} (ID: {run_id})")
                    return run_id
                    
        except Exception as e:
            logger.error(f"❌ Erreur lors du démarrage de l'entraînement: {e}")
            return None

    def complete_training_run(self, run_id: int, model_id: int, metrics: dict) -> bool:
        """
        Finalise un entraînement de modèle avec succès.
        
        Args:
            run_id (int): ID du run d'entraînement
            model_id (int): ID du modèle entraîné
            metrics (dict): Métriques d'évaluation
            
        Returns:
            bool: True si la mise à jour a réussi, False sinon
        """
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    # Mettre à jour le statut du run
                    conn.execute(text("""
                        UPDATE model_training_runs 
                        SET status = 'completed', 
                            end_time = CURRENT_TIMESTAMP,
                            model_id = :model_id
                        WHERE id = :run_id
                    """), {
                        'run_id': run_id,
                        'model_id': model_id
                    })
                    
                    # Sauvegarder les métriques
                    if metrics:
                        for metric_name, metric_value in metrics.items():
                            conn.execute(text("""
                                INSERT INTO model_metrics (
                                    model_id, metric_name, metric_value
                                ) VALUES (
                                    :model_id, :metric_name, :metric_value
                                )
                                ON CONFLICT (model_id, metric_name) 
                                DO UPDATE SET 
                                    metric_value = EXCLUDED.metric_value,
                                    created_at = CURRENT_TIMESTAMP
                            """), {
                                'model_id': model_id,
                                'metric_name': metric_name,
                                'metric_value': float(metric_value)
                            })
                    
                    logger.info(f"✅ Entraînement {run_id} complété avec succès")
                    return True
                    
        except Exception as e:
            logger.error(f"❌ Erreur lors de la finalisation de l'entraînement: {e}")
            return False

    def get_training_run(self, run_id: int) -> dict:
        """
        Récupère les détails d'un run d'entraînement.
        
        Args:
            run_id (int): ID du run à récupérer
            
        Returns:
            dict: Les détails du run ou None si non trouvé
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT * FROM model_training_runs WHERE id = :run_id
                """), {'run_id': run_id})
                
                row = result.fetchone()
                if row:
                    return dict(row._mapping)
                return None
                
        except Exception as e:
            logger.error(f"❌ Erreur lors de la récupération du run {run_id}: {e}")
            return None

    def get_model_metrics(self, model_id: int) -> list:
        """
        Récupère toutes les métriques d'un modèle.
        
        Args:
            model_id (int): ID du modèle
            
        Returns:
            list: Liste des métriques du modèle
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT metric_name, metric_value, created_at 
                    FROM model_metrics 
                    WHERE model_id = :model_id
                    ORDER BY created_at DESC
                """), {'model_id': model_id})
                
                return [dict(row._mapping) for row in result.fetchall()]
                
        except Exception as e:
            logger.error(f"❌ Erreur lors de la récupération des métriques: {e}")
            return []

    def get_user_by_email(self, email: str) -> dict:
        """
        Récupère un utilisateur par son adresse email.
        
        Args:
            email (str): L'email de l'utilisateur à rechercher
            
        Returns:
            dict: Les informations de l'utilisateur ou None si non trouvé
        """
        try:
            with self.engine.connect() as connection:
                result = connection.execute(
                    text("""
                        SELECT id, username, email, password, is_active, is_admin, is_moderator,
                               created_at, updated_at
                        FROM users 
                        WHERE email = :email
                    """),
                    {'email': email}
                ).fetchone()
                
                if result:
                    return dict(result._mapping)
                return None
                
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'utilisateur par email: {e}")
            raise

