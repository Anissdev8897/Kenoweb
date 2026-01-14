#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestionnaire de base de données amélioré v2 pour la gestion des prédictions utilisateurs
Persistance des prédictions individuelles et analyse des erreurs par utilisateur
"""

import psycopg2
from sqlalchemy import create_engine, text
import pandas as pd
import os
import json
import logging
from datetime import datetime, date, time as dt_time
import numpy as np
import uuid
import hashlib
import stat  # Ajout nécessaire

# Configuration du logger
logger = logging.getLogger(__name__)

# Vérification de la variable d'environnement DATABASE_URL
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    logger.error("La variable d'environnement DATABASE_URL n'est pas définie")
    raise ValueError("La variable d'environnement DATABASE_URL est requise pour se connecter à la base de données")

class EnhancedDatabaseManagerV2:
    def __init__(self):
        self.database_url = os.environ.get("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set.")
        self.engine = create_engine(self.database_url)
        self._create_enhanced_tables()

    def _create_enhanced_tables(self):
        """Crée les tables améliorées pour l'intégration ML et la gestion des utilisateurs."""
        with self.engine.connect() as conn:
            conn.execute(text("""
                -- Table des tirages officiels (inchangée)
                CREATE TABLE IF NOT EXISTS tirages_keno (
                    id SERIAL PRIMARY KEY,
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
                    joker VARCHAR(20),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date_tirage, heure_tirage)
                );

                -- Table des utilisateurs pour gérer les identifiants
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(100) UNIQUE NOT NULL,
                    display_name VARCHAR(100) NOT NULL,
                    session_id VARCHAR(100),
                    ip_address INET,
                    user_agent TEXT,
                    first_prediction TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_predictions INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Table des modèles ML améliorée
                CREATE TABLE IF NOT EXISTS ml_models (
                    id SERIAL PRIMARY KEY,
                    model_name VARCHAR(100) NOT NULL,
                    model_type VARCHAR(50) NOT NULL,
                    method_name VARCHAR(100) NOT NULL,
                    s3_path VARCHAR(500) NOT NULL,
                    training_score DECIMAL(10, 8),
                    test_score DECIMAL(10, 8),
                    r2_score DECIMAL(10, 8),
                    training_time_seconds INTEGER,
                    trained_at TIMESTAMP NOT NULL,
                    is_active BOOLEAN DEFAULT FALSE,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Table unifiée des prédictions (utilisateurs + modèles ML) - améliorée
                CREATE TABLE IF NOT EXISTS unified_predictions (
                    id SERIAL PRIMARY KEY,
                    predictor_id VARCHAR(100) NOT NULL,
                    predictor_type VARCHAR(20) NOT NULL CHECK (predictor_type IN ('USER', 'ML_MODEL')),
                    session_id VARCHAR(100),
                    prediction_method VARCHAR(100) NOT NULL,
                    predicted_numbers INTEGER[] NOT NULL,
                    confidence_score DECIMAL(5, 4),
                    target_tirage_date DATE NOT NULL,
                    target_tirage_time TIME,
                    actual_numbers INTEGER[],
                    correct_count INTEGER DEFAULT 0,
                    accuracy_percentage DECIMAL(5, 2) DEFAULT 0.0,
                    is_evaluated BOOLEAN DEFAULT FALSE,
                    prediction_hash VARCHAR(64), -- Hash pour éviter les doublons
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    evaluated_at TIMESTAMP,
                    UNIQUE(predictor_id, prediction_method, target_tirage_date, prediction_hash)
                );

                -- Table des performances par méthode et utilisateur
                CREATE TABLE IF NOT EXISTS method_performance (
                    id SERIAL PRIMARY KEY,
                    predictor_id VARCHAR(100) NOT NULL,
                    method_name VARCHAR(100) NOT NULL,
                    predictor_type VARCHAR(20) NOT NULL CHECK (predictor_type IN ('USER', 'ML_MODEL')),
                    total_predictions INTEGER DEFAULT 0,
                    total_evaluated INTEGER DEFAULT 0,
                    total_correct_numbers INTEGER DEFAULT 0,
                    average_accuracy DECIMAL(5, 2) DEFAULT 0.0,
                    best_score INTEGER DEFAULT 0,
                    worst_score INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(predictor_id, method_name, predictor_type)
                );

                -- Table des erreurs détaillées par prédiction
                CREATE TABLE IF NOT EXISTS prediction_errors (
                    id SERIAL PRIMARY KEY,
                    prediction_id INTEGER REFERENCES unified_predictions(id),
                    predictor_id VARCHAR(100) NOT NULL,
                    predictor_type VARCHAR(20) NOT NULL,
                    method_name VARCHAR(100) NOT NULL,
                    predicted_but_not_drawn INTEGER[] NOT NULL,
                    drawn_but_not_predicted INTEGER[] NOT NULL,
                    correct_predictions INTEGER[] NOT NULL,
                    error_count INTEGER NOT NULL,
                    miss_count INTEGER NOT NULL, -- Numéros manqués
                    tirage_date DATE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Table de l'historique d'entraînement ML
                CREATE TABLE IF NOT EXISTS ml_training_history (
                    id SERIAL PRIMARY KEY,
                    model_name VARCHAR(100) NOT NULL,
                    training_start TIMESTAMP NOT NULL,
                    training_end TIMESTAMP NOT NULL,
                    data_start_date DATE NOT NULL,
                    data_end_date DATE NOT NULL,
                    total_tirages_used INTEGER NOT NULL,
                    training_metrics JSONB,
                    retrain_trigger VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Table des sessions utilisateur pour le suivi
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(100) UNIQUE NOT NULL,
                    user_id VARCHAR(100) REFERENCES users(user_id),
                    ip_address INET,
                    user_agent TEXT,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    predictions_count INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT TRUE
                );

                -- Index pour optimiser les performances
                CREATE INDEX IF NOT EXISTS idx_tirages_date ON tirages_keno(date_tirage DESC);
                CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);
                CREATE INDEX IF NOT EXISTS idx_users_session_id ON users(session_id);
                CREATE INDEX IF NOT EXISTS idx_unified_predictions_predictor ON unified_predictions(predictor_id, predictor_type);
                CREATE INDEX IF NOT EXISTS idx_unified_predictions_method ON unified_predictions(prediction_method);
                CREATE INDEX IF NOT EXISTS idx_unified_predictions_target_date ON unified_predictions(target_tirage_date DESC);
                CREATE INDEX IF NOT EXISTS idx_method_performance_predictor ON method_performance(predictor_id, method_name);
                CREATE INDEX IF NOT EXISTS idx_prediction_errors_predictor ON prediction_errors(predictor_id, method_name);
                CREATE INDEX IF NOT EXISTS idx_user_sessions_session_id ON user_sessions(session_id);
                CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
            """))
            conn.commit()

    def generate_user_id(self, session_id, ip_address=None):
        """Générer un ID utilisateur unique basé sur la session."""
        # Créer un hash basé sur la session et l'IP pour un ID stable
        hash_input = f"{session_id}_{ip_address or 'unknown'}"
        user_hash = hashlib.md5(hash_input.encode()).hexdigest()[:8]
        
        # Vérifier s'il existe déjà un utilisateur pour cette session
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT user_id FROM users WHERE session_id = :session_id
            """), {"session_id": session_id})
            
            existing_user = result.fetchone()
            if existing_user:
                return existing_user[0]
            
            # Générer un nouvel ID utilisateur
            user_counter = conn.execute(text("""
                SELECT COUNT(*) + 1 FROM users WHERE user_id LIKE 'utilisateur%'
            """)).fetchone()[0]
            
            user_id = f"utilisateur{user_counter}"
            display_name = f"Utilisateur {user_counter}"
            
            # Créer le nouvel utilisateur
            conn.execute(text("""
                INSERT INTO users (user_id, display_name, session_id, ip_address)
                VALUES (:user_id, :display_name, :session_id, :ip_address)
                ON CONFLICT (user_id) DO NOTHING
            """), {
                "user_id": user_id,
                "display_name": display_name,
                "session_id": session_id,
                "ip_address": ip_address
            })
            
            # Créer la session
            conn.execute(text("""
                INSERT INTO user_sessions (session_id, user_id, ip_address)
                VALUES (:session_id, :user_id, :ip_address)
                ON CONFLICT (session_id) DO UPDATE SET
                    last_activity = CURRENT_TIMESTAMP
            """), {
                "session_id": session_id,
                "user_id": user_id,
                "ip_address": ip_address
            })
            
            conn.commit()
            return user_id

    def get_or_create_user(self, session_id, ip_address=None, user_agent=None):
        """Récupérer ou créer un utilisateur basé sur la session."""
        return self.generate_user_id(session_id, ip_address)

    def save_user_prediction(self, session_id, method_name, predicted_numbers, 
                           target_date, target_time=None, confidence_score=None, 
                           ip_address=None, user_agent=None):
        """Sauvegarder une prédiction utilisateur avec gestion automatique de l'ID."""
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
                    ) RETURNING id
                """), {
                    "user_id": user_id,
                    "session_id": session_id,
                    "method_name": method_name,
                    "predicted_numbers": predicted_numbers,
                    "confidence_score": confidence_score,
                    "target_date": target_date,
                    "target_time": target_time,
                    "prediction_hash": prediction_hash
                })
                
                prediction_id = result.fetchone()[0]
                
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
                    ) RETURNING id
                """), {
                    "predictor_id": predictor_id,
                    "method_name": method_name,
                    "predicted_numbers": predicted_numbers,
                    "confidence_score": confidence_score,
                    "target_date": target_date,
                    "target_time": target_time,
                    "prediction_hash": prediction_hash
                })
                conn.commit()
                return result.fetchone()[0]
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

    def evaluate_predictions_for_tirage(self, tirage_date, tirage_time, actual_numbers):
        """Évaluer toutes les prédictions pour un tirage donné."""
        with self.engine.connect() as conn:
            # Récupérer toutes les prédictions non évaluées pour ce tirage
            result = conn.execute(text("""
                SELECT id, predictor_id, predictor_type, prediction_method, predicted_numbers
                FROM unified_predictions 
                WHERE target_tirage_date = :tirage_date 
                AND (target_tirage_time IS NULL OR target_tirage_time = :tirage_time)
                AND is_evaluated = FALSE
            """), {
                "tirage_date": tirage_date,
                "tirage_time": tirage_time
            })
            
            predictions = result.fetchall()
            
            for prediction in predictions:
                pred_id, predictor_id, predictor_type, method_name, predicted_numbers = prediction
                
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
                        is_evaluated = TRUE,
                        evaluated_at = CURRENT_TIMESTAMP
                    WHERE id = :pred_id
                """), {
                    "pred_id": pred_id,
                    "actual_numbers": actual_numbers,
                    "correct_count": correct_count,
                    "accuracy_percentage": accuracy_percentage
                })
                
                # Sauvegarder les erreurs détaillées
                self._save_prediction_error(conn, pred_id, predictor_id, predictor_type, 
                                          method_name, predicted_numbers, actual_numbers, tirage_date)
                
                # Mettre à jour les performances de la méthode pour ce prédicteur
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
            "predicted_but_not_drawn": predicted_but_not_drawn,
            "drawn_but_not_predicted": drawn_but_not_predicted,
            "correct_predictions": correct_predictions,
            "error_count": error_count,
            "miss_count": miss_count,
            "tirage_date": tirage_date
        })

    def _update_method_performance(self, conn, predictor_id, method_name, predictor_type):
        """Mettre à jour les statistiques de performance d'une méthode pour un prédicteur spécifique."""
        # Calculer les nouvelles statistiques
        result = conn.execute(text("""
            SELECT 
                COUNT(*) as total_predictions,
                COUNT(CASE WHEN is_evaluated = TRUE THEN 1 END) as total_evaluated,
                SUM(CASE WHEN is_evaluated = TRUE THEN correct_count ELSE 0 END) as total_correct,
                AVG(CASE WHEN is_evaluated = TRUE THEN accuracy_percentage ELSE NULL END) as avg_accuracy,
                MAX(CASE WHEN is_evaluated = TRUE THEN correct_count ELSE 0 END) as best_score,
                MIN(CASE WHEN is_evaluated = TRUE THEN correct_count ELSE 999 END) as worst_score
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
            INSERT INTO method_performance (
                predictor_id, method_name, predictor_type, total_predictions, total_evaluated,
                total_correct_numbers, average_accuracy, best_score, worst_score
            ) VALUES (
                :predictor_id, :method_name, :predictor_type, :total_predictions, :total_evaluated,
                :total_correct, :avg_accuracy, :best_score, :worst_score
            ) ON CONFLICT (predictor_id, method_name, predictor_type) 
            DO UPDATE SET
                total_predictions = EXCLUDED.total_predictions,
                total_evaluated = EXCLUDED.total_evaluated,
                total_correct_numbers = EXCLUDED.total_correct_numbers,
                average_accuracy = EXCLUDED.average_accuracy,
                best_score = EXCLUDED.best_score,
                worst_score = EXCLUDED.worst_score,
                last_updated = CURRENT_TIMESTAMP
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

    def get_all_predictions_for_display(self, limit=50):
        """Récupérer toutes les prédictions pour l'affichage, groupées par prédicteur."""
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
        return pd.read_sql(query, self.engine, params={"user_id": user_id, "limit": limit})

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
        return pd.read_sql(query, self.engine, params={"limit": limit})

    def get_active_users_count(self):
        """Récupérer le nombre d'utilisateurs actifs."""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(DISTINCT predictor_id) as active_users
                FROM unified_predictions 
                WHERE predictor_type = 'USER' 
                AND created_at >= CURRENT_DATE - INTERVAL '7 days'
            """))
            return result.fetchone()[0]

    def cleanup_old_sessions(self, days_old=30):
        """Nettoyer les anciennes sessions inactives."""
        with self.engine.connect() as conn:
            conn.execute(text("""
                UPDATE user_sessions 
                SET is_active = FALSE 
                WHERE last_activity < CURRENT_DATE - INTERVAL ':days days'
                AND is_active = TRUE
            """), {"days": days_old})
            conn.commit()

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

    def insert_new_tirage(self, tirage_data):
        """Insérer un nouveau tirage et déclencher l'évaluation des prédictions."""
        with self.engine.connect() as conn:
            # Insérer le tirage
            conn.execute(text("""
                INSERT INTO tirages_keno (
                    date_tirage, heure_tirage, numero_1, numero_2, numero_3,
                    numero_4, numero_5, numero_6, numero_7, numero_8,
                    numero_9, numero_10, numero_11, numero_12, numero_13,
                    numero_14, numero_15, numero_16, numero_17, numero_18,
                    numero_19, numero_20, multiplicateur, joker
                ) VALUES (
                    :date_tirage, :heure_tirage, :numero_1, :numero_2, :numero_3,
                    :numero_4, :numero_5, :numero_6, :numero_7, :numero_8,
                    :numero_9, :numero_10, :numero_11, :numero_12, :numero_13,
                    :numero_14, :numero_15, :numero_16, :numero_17, :numero_18,
                    :numero_19, :numero_20, :multiplicateur, :joker
                ) ON CONFLICT (date_tirage, heure_tirage) DO NOTHING
            """), tirage_data)
            conn.commit()
            
            # Extraire les numéros pour l'évaluation
            actual_numbers = [
                tirage_data[f"numero_{i}"] for i in range(1, 21)
            ]
            
            # Évaluer les prédictions pour ce tirage
            self.evaluate_predictions_for_tirage(
                tirage_data["date_tirage"], 
                tirage_data.get("heure_tirage"), 
                actual_numbers
            )
            
            logger.info(f"Nouveau tirage inséré et prédictions évaluées pour {tirage_data['date_tirage']}")

    def save_ml_training_record(self, model_name, training_start, training_end, 
                               data_start_date, data_end_date, total_tirages, 
                               training_metrics, retrain_trigger="MANUAL"):
        """Enregistrer l'historique d'entraînement ML."""
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO ml_training_history (
                    model_name, training_start, training_end, data_start_date,
                    data_end_date, total_tirages_used, training_metrics, retrain_trigger
                ) VALUES (
                    :model_name, :training_start, :training_end, :data_start_date,
                    :data_end_date, :total_tirages, :training_metrics, :retrain_trigger
                )
            """), {
                "model_name": model_name,
                "training_start": training_start,
                "training_end": training_end,
                "data_start_date": data_start_date,
                "data_end_date": data_end_date,
                "total_tirages": total_tirages,
                "training_metrics": json.dumps(training_metrics),
                "retrain_trigger": retrain_trigger
            })
            conn.commit()

# Remplace :
# from enhanced_database_manager import EnhancedDatabaseManager
# par :
from enhanced_database_manager import EnhancedDatabaseManagerV2

db_manager = None

def get_enhanced_database_manager() -> EnhancedDatabaseManagerV2:
    """Récupère l'instance globale du gestionnaire de base de données amélioré V2"""
    global db_manager
    if db_manager is None:
        db_manager = EnhancedDatabaseManagerV2()
    return db_manager

