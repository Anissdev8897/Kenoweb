#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestionnaire de base de données amélioré v2 compatible SQLite
Version simplifiée pour les tests et le développement local
"""

import sqlite3
from sqlalchemy import create_engine, text
import pandas as pd
import os
import json
import logging
from datetime import datetime, date, time as dt_time
import numpy as np
import uuid
import hashlib

logger = logging.getLogger(__name__)

# Configuration de la base de données par défaut pour SQLite
DEFAULT_SQLITE_URL = "sqlite:///kenoweb_v2.db"

# Récupération de l'URL de la base de données depuis les variables d'environnement
database_url = os.environ.get("DATABASE_URL", DEFAULT_SQLITE_URL)

# Chemin de la clé SSH (à adapter selon l'environnement)
KEY_PATH = os.environ.get("SSH_KEY_PATH", "/root/.ssh/id_rsa")

class EnhancedDatabaseManagerV2SQLite:
    def __init__(self):
        self.database_url = os.environ.get("DATABASE_URL", "sqlite:///kenoweb_v2.db")
        self.engine = create_engine(self.database_url)
        self._create_enhanced_tables()

    def prepare_ssh_key():
        private_key = os.getenv("SSH_PRIVATE_KEY")
        if not private_key:
            logger.error("La variable d'environnement SSH_PRIVATE_KEY est absente.")
            return False
        
        ssh_dir = os.path.dirname(KEY_PATH)
        if not os.path.exists(ssh_dir):
            os.makedirs(ssh_dir, mode=0o700)
            logger.info(f"Création du dossier SSH : {ssh_dir}")
        
        with open(KEY_PATH, "w") as f:
            f.write(private_key)
        
        os.chmod(KEY_PATH, stat.S_IRUSR | stat.S_IWUSR)
        logger.info(f"Clé privée SSH écrite dans {KEY_PATH} avec permissions 600")
        return True
    
    # Prépare la clé SSH avant toute connexion à la DB
    if not prepare_ssh_key():
        logger.error("Impossible de préparer la clé SSH. Arrêt du script.")
        exit(1)

    def _create_enhanced_tables(self):
        """Crée les tables améliorées compatibles SQLite."""
        with self.engine.connect() as conn:
            conn.execute(text("""
                -- Table des tirages officiels
                CREATE TABLE IF NOT EXISTS tirages_keno (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date_tirage DATE NOT NULL,
                    heure_tirage TIME,
                    numero_1 INTEGER NOT NULL CHECK (numero_1 BETWEEN 1 AND 70),
                    numero_2 INTEGER NOT NULL CHECK (numero_2 BETWEEN 1 AND 70),
                    numero_3 INTEGER NOT NULL CHECK (numero_3 BETWEEN 1 AND 70),
                    numero_4 INTEGER NOT NULL CHECK (numero_4 BETWEEN 1 AND 70),
                    numero_5 INTEGER NOT NULL CHECK (numero_5 BETWEEN 1 AND 70),
                    numero_6 INTEGER NOT NULL CHECK (numero_6 BETWEEN 1 AND 70),
                    numero_7 INTEGER NOT NULL CHECK (numero_7 BETWEEN 1 AND 70),
                    numero_8 INTEGER NOT NULL CHECK (numero_8 BETWEEN 1 AND 70),
                    numero_9 INTEGER NOT NULL CHECK (numero_9 BETWEEN 1 AND 70),
                    numero_10 INTEGER NOT NULL CHECK (numero_10 BETWEEN 1 AND 70),
                    numero_11 INTEGER NOT NULL CHECK (numero_11 BETWEEN 1 AND 70),
                    numero_12 INTEGER NOT NULL CHECK (numero_12 BETWEEN 1 AND 70),
                    numero_13 INTEGER NOT NULL CHECK (numero_13 BETWEEN 1 AND 70),
                    numero_14 INTEGER NOT NULL CHECK (numero_14 BETWEEN 1 AND 70),
                    numero_15 INTEGER NOT NULL CHECK (numero_15 BETWEEN 1 AND 70),
                    numero_16 INTEGER NOT NULL CHECK (numero_16 BETWEEN 1 AND 70),
                    numero_17 INTEGER NOT NULL CHECK (numero_17 BETWEEN 1 AND 70),
                    numero_18 INTEGER NOT NULL CHECK (numero_18 BETWEEN 1 AND 70),
                    numero_19 INTEGER NOT NULL CHECK (numero_19 BETWEEN 1 AND 70),
                    numero_20 INTEGER NOT NULL CHECK (numero_20 BETWEEN 1 AND 70),
                    multiplicateur INTEGER,
                    joker TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date_tirage, heure_tirage)
                );

                -- Table des utilisateurs
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT UNIQUE NOT NULL,
                    display_name TEXT NOT NULL,
                    session_id TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    first_prediction TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_predictions INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Table des modèles ML
                CREATE TABLE IF NOT EXISTS ml_models (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name TEXT NOT NULL,
                    model_type TEXT NOT NULL,
                    method_name TEXT NOT NULL,
                    s3_path TEXT NOT NULL,
                    training_score REAL,
                    test_score REAL,
                    r2_score REAL,
                    training_time_seconds INTEGER,
                    trained_at TIMESTAMP NOT NULL,
                    is_active BOOLEAN DEFAULT FALSE,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Table unifiée des prédictions
                CREATE TABLE IF NOT EXISTS unified_predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    predictor_id TEXT NOT NULL,
                    predictor_type TEXT NOT NULL CHECK (predictor_type IN ('USER', 'ML_MODEL')),
                    session_id TEXT,
                    prediction_method TEXT NOT NULL,
                    predicted_numbers TEXT NOT NULL, -- JSON array
                    confidence_score REAL,
                    target_tirage_date DATE NOT NULL,
                    target_tirage_time TIME,
                    actual_numbers TEXT, -- JSON array
                    correct_count INTEGER DEFAULT 0,
                    accuracy_percentage REAL DEFAULT 0.0,
                    is_evaluated BOOLEAN DEFAULT FALSE,
                    prediction_hash TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    evaluated_at TIMESTAMP,
                    UNIQUE(predictor_id, prediction_method, target_tirage_date, prediction_hash)
                );

                -- Table des performances par méthode et utilisateur
                CREATE TABLE IF NOT EXISTS method_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    predictor_id TEXT NOT NULL,
                    method_name TEXT NOT NULL,
                    predictor_type TEXT NOT NULL CHECK (predictor_type IN ('USER', 'ML_MODEL')),
                    total_predictions INTEGER DEFAULT 0,
                    total_evaluated INTEGER DEFAULT 0,
                    total_correct_numbers INTEGER DEFAULT 0,
                    average_accuracy REAL DEFAULT 0.0,
                    best_score INTEGER DEFAULT 0,
                    worst_score INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(predictor_id, method_name, predictor_type)
                );

                -- Table des erreurs détaillées
                CREATE TABLE IF NOT EXISTS prediction_errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prediction_id INTEGER REFERENCES unified_predictions(id),
                    predictor_id TEXT NOT NULL,
                    predictor_type TEXT NOT NULL,
                    method_name TEXT NOT NULL,
                    predicted_but_not_drawn TEXT NOT NULL, -- JSON array
                    drawn_but_not_predicted TEXT NOT NULL, -- JSON array
                    correct_predictions TEXT NOT NULL, -- JSON array
                    error_count INTEGER NOT NULL,
                    miss_count INTEGER NOT NULL,
                    tirage_date DATE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Table de l'historique d'entraînement ML
                CREATE TABLE IF NOT EXISTS ml_training_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name TEXT NOT NULL,
                    training_start TIMESTAMP NOT NULL,
                    training_end TIMESTAMP NOT NULL,
                    data_start_date DATE NOT NULL,
                    data_end_date DATE NOT NULL,
                    total_tirages_used INTEGER NOT NULL,
                    training_metrics TEXT, -- JSON
                    retrain_trigger TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Table des sessions utilisateur
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    user_id TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    predictions_count INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT TRUE
                );
            """))
            conn.commit()

    def generate_user_id(self, session_id, ip_address=None):
        """Générer un ID utilisateur unique basé sur la session."""
        # Vérifier s'il existe déjà un utilisateur pour cette session
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT user_id FROM users WHERE session_id = :session_id
            """), {"session_id": session_id})
            
            existing_user = result.fetchone()
            if existing_user:
                return existing_user[0]
            
            # Générer un nouvel ID utilisateur
            result = conn.execute(text("""
                SELECT COUNT(*) + 1 FROM users WHERE user_id LIKE 'utilisateur%'
            """))
            user_counter = result.fetchone()[0]
            
            user_id = f"utilisateur{user_counter}"
            display_name = f"Utilisateur {user_counter}"
            
            # Créer le nouvel utilisateur
            conn.execute(text("""
                INSERT OR IGNORE INTO users (user_id, display_name, session_id, ip_address)
                VALUES (:user_id, :display_name, :session_id, :ip_address)
            """), {
                "user_id": user_id,
                "display_name": display_name,
                "session_id": session_id,
                "ip_address": ip_address
            })
            
            # Créer la session
            conn.execute(text("""
                INSERT OR REPLACE INTO user_sessions (session_id, user_id, ip_address)
                VALUES (:session_id, :user_id, :ip_address)
            """), {
                "session_id": session_id,
                "user_id": user_id,
                "ip_address": ip_address
            })
            
            conn.commit()
            return user_id

    def save_ml_model(self, model_name, model_type, method_name, s3_path, training_score, test_score, r2_score, training_time_seconds, trained_at, is_active, metadata):
        """Enregistre ou met à jour un modèle ML dans la table ml_models."""
        with self.engine.connect() as conn:
            # Désactiver l'ancien modèle actif du même type
            conn.execute(text("""
                UPDATE ml_models
                SET is_active = FALSE
                WHERE model_type = :model_type AND is_active = TRUE
            """), {"model_type": model_type})

            # Insérer le nouveau modèle
            conn.execute(text("""
                INSERT INTO ml_models (
                    model_name, model_type, method_name, s3_path, training_score,
                    test_score, r2_score, training_time_seconds,
                    trained_at, is_active, metadata
                ) VALUES (
                    :model_name, :model_type, :method_name, :s3_path, :training_score,
                    :test_score, :r2_score, :training_time_seconds,
                    :trained_at, :is_active, :metadata
                )
            """), {
                "model_name": model_name,
                "model_type": model_type,
                "method_name": method_name,
                "s3_path": s3_path,
                "training_score": training_score,
                "test_score": test_score,
                "r2_score": r2_score,
                "training_time_seconds": training_time_seconds,
                "trained_at": trained_at,
                "is_active": is_active,
                "metadata": json.dumps(metadata) if isinstance(metadata, dict) else metadata
            })
            conn.commit()

        """Récupérer ou créer un utilisateur basé sur la session."""
        return self.generate_user_id(session_id, ip_address)

    def save_user_prediction(self, session_id, method_name, predicted_numbers, 
                           target_date, target_time=None, confidence_score=None, 
                           ip_address=None, user_agent=None):
        """Sauvegarder une prédiction utilisateur."""
        user_id = self.get_or_create_user(session_id, ip_address, user_agent)
        
        # Créer un hash pour éviter les doublons
        prediction_data = f"{user_id}_{method_name}_{target_date}_{sorted(predicted_numbers)}"
        prediction_hash = hashlib.md5(prediction_data.encode()).hexdigest()
        
        with self.engine.connect() as conn:
            try:
                result = conn.execute(text("""
                    INSERT INTO unified_predictions (
                        predictor_id, predictor_type, session_id, prediction_method, 
                        predicted_numbers, confidence_score, target_tirage_date, 
                        target_tirage_time, prediction_hash
                    ) VALUES (
                        :user_id, 'USER', :session_id, :method_name, :predicted_numbers,
                        :confidence_score, :target_date, :target_time, :prediction_hash
                    )
                """), {
                    "user_id": user_id,
                    "session_id": session_id,
                    "method_name": method_name,
                    "predicted_numbers": json.dumps(predicted_numbers),
                    "confidence_score": confidence_score,
                    "target_date": target_date,
                    "target_time": target_time,
                    "prediction_hash": prediction_hash
                })
                
                prediction_id = result.lastrowid
                
                # Mettre à jour le compteur de prédictions de l'utilisateur
                conn.execute(text("""
                    UPDATE users SET 
                        total_predictions = total_predictions + 1,
                        last_activity = CURRENT_TIMESTAMP
                    WHERE user_id = :user_id
                """), {"user_id": user_id})
                
                # Mettre à jour la session
                conn.execute(text("""
                    UPDATE user_sessions SET 
                        predictions_count = predictions_count + 1,
                        last_activity = CURRENT_TIMESTAMP
                    WHERE session_id = :session_id
                """), {"session_id": session_id})
                
                conn.commit()
                return prediction_id, user_id
                
            except Exception as e:
                if "unique constraint" in str(e).lower():
                    # Prédiction déjà existante
                    result = conn.execute(text("""
                        SELECT id FROM unified_predictions 
                        WHERE prediction_hash = :prediction_hash
                    """), {"prediction_hash": prediction_hash})
                    existing_id = result.fetchone()[0]
                    return existing_id, user_id
                else:
                    raise e

    def save_ml_prediction(self, model_name, method_name, predicted_numbers, 
                          target_date, target_time=None, confidence_score=None):
        """Sauvegarder une prédiction ML."""
        predictor_id = f"ML_{model_name}"
        
        # Créer un hash pour éviter les doublons
        prediction_data = f"{predictor_id}_{method_name}_{target_date}_{sorted(predicted_numbers)}"
        prediction_hash = hashlib.md5(prediction_data.encode()).hexdigest()
        
        with self.engine.connect() as conn:
            try:
                result = conn.execute(text("""
                    INSERT INTO unified_predictions (
                        predictor_id, predictor_type, prediction_method, predicted_numbers,
                        confidence_score, target_tirage_date, target_tirage_time, prediction_hash
                    ) VALUES (
                        :predictor_id, 'ML_MODEL', :method_name, :predicted_numbers,
                        :confidence_score, :target_date, :target_time, :prediction_hash
                    )
                """), {
                    "predictor_id": predictor_id,
                    "method_name": method_name,
                    "predicted_numbers": json.dumps(predicted_numbers),
                    "confidence_score": confidence_score,
                    "target_date": target_date,
                    "target_time": target_time,
                    "prediction_hash": prediction_hash
                })
                conn.commit()
                return result.lastrowid
            except Exception as e:
                if "unique constraint" in str(e).lower():
                    # Prédiction déjà existante
                    result = conn.execute(text("""
                        SELECT id FROM unified_predictions 
                        WHERE prediction_hash = :prediction_hash
                    """), {"prediction_hash": prediction_hash})
                    return result.fetchone()[0]
                else:
                    raise e

    def get_all_predictions_for_display(self, limit=50):
        """Récupérer toutes les prédictions pour l'affichage."""
        query = """
        SELECT 
            up.predictor_id,
            CASE 
                WHEN up.predictor_type = 'ML_MODEL' THEN '🤖 ' || up.prediction_method
                WHEN up.predictor_type = 'USER' THEN 
                    COALESCE(u.display_name, up.predictor_id) || ' - ' || up.prediction_method
                ELSE up.predictor_id || ' - ' || up.prediction_method
            END as display_method,
            up.predicted_numbers,
            up.actual_numbers,
            up.correct_count,
            up.accuracy_percentage,
            up.target_tirage_date,
            up.is_evaluated,
            up.created_at,
            up.predictor_type
        FROM unified_predictions up
        LEFT JOIN users u ON up.predictor_id = u.user_id AND up.predictor_type = 'USER'
        ORDER BY up.created_at DESC 
        LIMIT :limit
        """
        df = pd.read_sql(query, self.engine, params={"limit": limit})
        
        # Convertir les JSON strings en listes
        if not df.empty:
            df['predicted_numbers'] = df['predicted_numbers'].apply(
                lambda x: json.loads(x) if x else []
            )
            df['actual_numbers'] = df['actual_numbers'].apply(
                lambda x: json.loads(x) if x else None
            )
        
        return df

    def get_unified_leaderboard(self, limit=20):
        """Récupérer le classement unifié de tous les prédicteurs."""
        query = """
        SELECT 
            mp.predictor_id,
            CASE 
                WHEN mp.predictor_type = 'ML_MODEL' THEN '🤖 ' || mp.predictor_id
                WHEN mp.predictor_type = 'USER' THEN 
                    COALESCE(u.display_name, mp.predictor_id)
                ELSE mp.predictor_id
            END as display_name,
            mp.predictor_type,
            SUM(mp.total_predictions) as total_predictions,
            SUM(mp.total_evaluated) as total_evaluated,
            AVG(mp.average_accuracy) as avg_accuracy,
            MAX(mp.best_score) as best_score,
            COUNT(mp.method_name) as methods_used
        FROM method_performance mp
        LEFT JOIN users u ON mp.predictor_id = u.user_id AND mp.predictor_type = 'USER'
        WHERE mp.total_evaluated > 0
        GROUP BY mp.predictor_id, mp.predictor_type, u.display_name
        ORDER BY avg_accuracy DESC, total_evaluated DESC
        LIMIT :limit
        """
        return pd.read_sql(query, self.engine, params={"limit": limit})

    def get_user_performance_summary(self, user_id):
        """Récupérer un résumé des performances d'un utilisateur."""
        query = """
        SELECT 
            mp.method_name,
            mp.total_predictions,
            mp.total_evaluated,
            mp.average_accuracy,
            mp.best_score,
            mp.worst_score,
            mp.last_updated
        FROM method_performance mp
        WHERE mp.predictor_id = :user_id AND mp.predictor_type = 'USER'
        ORDER BY mp.average_accuracy DESC
        """
        return pd.read_sql(query, self.engine, params={"user_id": user_id})

    def get_active_users_count(self):
        """Récupérer le nombre d'utilisateurs actifs."""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(DISTINCT predictor_id) as active_users
                FROM unified_predictions 
                WHERE predictor_type = 'USER' 
                AND created_at >= date('now', '-7 days')
            """))
            return result.fetchone()[0]

    def get_official_tirages_for_training(self, start_date=None, end_date=None):
        """Récupérer uniquement les tirages officiels pour l'entraînement ML."""
        query = """
        SELECT * FROM tirages_keno 
        WHERE 1=1
        """
        params = {}
        
        if start_date:
            query += " AND date_tirage >= :start_date"
            params["start_date"] = start_date
        
        if end_date:
            query += " AND date_tirage <= :end_date"
            params["end_date"] = end_date
        
        query += " ORDER BY date_tirage ASC, heure_tirage ASC"
        
        return pd.read_sql(query, self.engine, params=params)

    def evaluate_predictions_for_tirage(self, tirage_date, tirage_time, actual_numbers):
        """Évaluer toutes les prédictions pour un tirage donné."""
        with self.engine.connect() as conn:
            # Récupérer toutes les prédictions non évaluées pour ce tirage
            result = conn.execute(text("""
                SELECT id, predictor_id, predictor_type, prediction_method, predicted_numbers
                FROM unified_predictions 
                WHERE target_tirage_date = :tirage_date 
                AND (target_tirage_time IS NULL OR target_tirage_time = :tirage_time)
                AND is_evaluated = 0
            """), {
                "tirage_date": tirage_date,
                "tirage_time": tirage_time
            })
            
            predictions = result.fetchall()
            
            for prediction in predictions:
                pred_id, predictor_id, predictor_type, method_name, predicted_numbers_json = prediction
                
                # Convertir JSON en liste
                predicted_numbers = json.loads(predicted_numbers_json)
                
                # Calculer les métriques
                correct_numbers = list(set(predicted_numbers) & set(actual_numbers))
                correct_count = len(correct_numbers)
                accuracy_percentage = (correct_count / len(predicted_numbers)) * 100 if predicted_numbers else 0
                
                # Mettre à jour la prédiction
                conn.execute(text("""
                    UPDATE unified_predictions 
                    SET actual_numbers = :actual_numbers,
                        correct_count = :correct_count,
                        accuracy_percentage = :accuracy_percentage,
                        is_evaluated = 1,
                        evaluated_at = CURRENT_TIMESTAMP
                    WHERE id = :pred_id
                """), {
                    "pred_id": pred_id,
                    "actual_numbers": json.dumps(actual_numbers),
                    "correct_count": correct_count,
                    "accuracy_percentage": accuracy_percentage
                })
                
                # Sauvegarder les erreurs détaillées
                self._save_prediction_error(conn, pred_id, predictor_id, predictor_type, 
                                          method_name, predicted_numbers, actual_numbers, tirage_date)
                
                # Mettre à jour les performances de la méthode
                self._update_method_performance(conn, predictor_id, method_name, predictor_type)
            
            conn.commit()
            logger.info(f"Évalué {len(predictions)} prédictions pour le tirage du {tirage_date}")

    def _save_prediction_error(self, conn, prediction_id, predictor_id, predictor_type, 
                              method_name, predicted_numbers, actual_numbers, tirage_date):
        """Sauvegarder les détails des erreurs de prédiction."""
        predicted_set = set(predicted_numbers)
        actual_set = set(actual_numbers)
        
        predicted_but_not_drawn = list(predicted_set - actual_set)
        drawn_but_not_predicted = list(actual_set - predicted_set)
        correct_predictions = list(predicted_set & actual_set)
        error_count = len(predicted_but_not_drawn)
        miss_count = len(drawn_but_not_predicted)
        
        conn.execute(text("""
            INSERT INTO prediction_errors (
                prediction_id, predictor_id, predictor_type, method_name,
                predicted_but_not_drawn, drawn_but_not_predicted, correct_predictions,
                error_count, miss_count, tirage_date
            ) VALUES (
                :prediction_id, :predictor_id, :predictor_type, :method_name,
                :predicted_but_not_drawn, :drawn_but_not_predicted, :correct_predictions,
                :error_count, :miss_count, :tirage_date
            )
        """), {
            "prediction_id": prediction_id,
            "predictor_id": predictor_id,
            "predictor_type": predictor_type,
            "method_name": method_name,
            "predicted_but_not_drawn": json.dumps(predicted_but_not_drawn),
            "drawn_but_not_predicted": json.dumps(drawn_but_not_predicted),
            "correct_predictions": json.dumps(correct_predictions),
            "error_count": error_count,
            "miss_count": miss_count,
            "tirage_date": tirage_date
        })

    def _update_method_performance(self, conn, predictor_id, method_name, predictor_type):
        """Mettre à jour les statistiques de performance d'une méthode."""
        # Calculer les nouvelles statistiques
        result = conn.execute(text("""
            SELECT 
                COUNT(*) as total_predictions,
                COUNT(CASE WHEN is_evaluated = 1 THEN 1 END) as total_evaluated,
                SUM(CASE WHEN is_evaluated = 1 THEN correct_count ELSE 0 END) as total_correct,
                AVG(CASE WHEN is_evaluated = 1 THEN accuracy_percentage ELSE NULL END) as avg_accuracy,
                MAX(CASE WHEN is_evaluated = 1 THEN correct_count ELSE 0 END) as best_score,
                MIN(CASE WHEN is_evaluated = 1 THEN correct_count ELSE 999 END) as worst_score
            FROM unified_predictions 
            WHERE predictor_id = :predictor_id 
            AND prediction_method = :method_name 
            AND predictor_type = :predictor_type
        """), {
            "predictor_id": predictor_id,
            "method_name": method_name,
            "predictor_type": predictor_type
        })
        
        stats = result.fetchone()
        
        # Mettre à jour ou insérer les performances
        conn.execute(text("""
            INSERT OR REPLACE INTO method_performance (
                predictor_id, method_name, predictor_type, total_predictions, total_evaluated,
                total_correct_numbers, average_accuracy, best_score, worst_score, last_updated
            ) VALUES (
                :predictor_id, :method_name, :predictor_type, :total_predictions, :total_evaluated,
                :total_correct, :avg_accuracy, :best_score, :worst_score, CURRENT_TIMESTAMP
            )
        """), {
            "predictor_id": predictor_id,
            "method_name": method_name,
            "predictor_type": predictor_type,
            "total_predictions": stats[0],
            "total_evaluated": stats[1],
            "total_correct": stats[2] or 0,
            "avg_accuracy": float(stats[3]) if stats[3] else 0.0,
            "best_score": stats[4] or 0,
            "worst_score": stats[5] if stats[5] != 999 else 0
        })

    def get_user_prediction_errors(self, user_id, limit=20):
        """Récupérer les erreurs de prédiction d'un utilisateur."""
        query = """
        SELECT 
            pe.method_name,
            pe.predicted_but_not_drawn,
            pe.drawn_but_not_predicted,
            pe.correct_predictions,
            pe.error_count,
            pe.miss_count,
            pe.tirage_date,
            pe.created_at
        FROM prediction_errors pe
        WHERE pe.predictor_id = :user_id AND pe.predictor_type = 'USER'
        ORDER BY pe.created_at DESC
        LIMIT :limit
        """
        df = pd.read_sql(query, self.engine, params={"user_id": user_id, "limit": limit})
        
        # Convertir les JSON strings en listes
        if not df.empty:
            for col in ['predicted_but_not_drawn', 'drawn_but_not_predicted', 'correct_predictions']:
                df[col] = df[col].apply(lambda x: json.loads(x) if x else [])
        
        return df

    def get_recent_predictions_by_predictor(self, limit=10):
        """Récupérer les prédictions récentes groupées par prédicteur."""
        query = """
        WITH recent_predictions AS (
            SELECT 
                up.*,
                CASE 
                    WHEN up.predictor_type = 'ML_MODEL' THEN '🤖 ' || up.predictor_id
                    WHEN up.predictor_type = 'USER' THEN 
                        COALESCE(u.display_name, up.predictor_id)
                    ELSE up.predictor_id
                END as display_name,
                ROW_NUMBER() OVER (PARTITION BY up.predictor_id ORDER BY up.created_at DESC) as rn
            FROM unified_predictions up
            LEFT JOIN users u ON up.predictor_id = u.user_id AND up.predictor_type = 'USER'
        )
        SELECT 
            predictor_id,
            display_name,
            predictor_type,
            prediction_method,
            predicted_numbers,
            actual_numbers,
            correct_count,
            accuracy_percentage,
            target_tirage_date,
            is_evaluated,
            created_at
        FROM recent_predictions 
        WHERE rn <= :limit
        ORDER BY created_at DESC
        """
        df = pd.read_sql(query, self.engine, params={"limit": limit})
        
        # Convertir les JSON strings en listes
        if not df.empty:
            df['predicted_numbers'] = df['predicted_numbers'].apply(
                lambda x: json.loads(x) if x else []
            )
            df['actual_numbers'] = df['actual_numbers'].apply(
                lambda x: json.loads(x) if x else None
            )
        
        return df

