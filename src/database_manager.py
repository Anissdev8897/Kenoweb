#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestionnaire de Base de Données pour Keno Analyzer Pro
Gère la sauvegarde et la synchronisation des données.
VERSION CORRIGÉE - Conversion des dates DD/MM/YYYY vers ISO YYYY-MM-DD
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import re

import psycopg2
from sqlalchemy import create_engine, text
import pandas as pd

# Récupération de l'URL de la base de données depuis les variables d'environnement
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    logger.error("La variable d'environnement DATABASE_URL n'est pas définie")
    raise ValueError("La variable d'environnement DATABASE_URL est requise pour se connecter à la base de données")

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set.")
        self.engine = create_engine(self.database_url)
        self._create_tables()

    def _create_tables(self):
        """Crée les tables si elles n'existent pas."""
        with self.engine.connect() as conn:
            conn.execute(text("""
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

                CREATE INDEX IF NOT EXISTS idx_tirages_date ON tirages_keno(date_tirage DESC);
                CREATE INDEX IF NOT EXISTS idx_tirages_created_at ON tirages_keno(created_at DESC);

                CREATE TABLE IF NOT EXISTS ml_models (
                    id SERIAL PRIMARY KEY,
                    model_name VARCHAR(100) NOT NULL,
                    model_type VARCHAR(50) NOT NULL,
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

                CREATE TABLE IF NOT EXISTS user_predictions (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(100) NOT NULL,
                    session_id VARCHAR(100),
                    prediction_method VARCHAR(50) NOT NULL,
                    predicted_numbers INTEGER[] NOT NULL,
                    confidence_score DECIMAL(5, 4),
                    actual_numbers INTEGER[],
                    correct_count INTEGER DEFAULT 0,
                    is_evaluated BOOLEAN DEFAULT FALSE,
                    tirage_date DATE,
                    tirage_time TIME,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_user_predictions_user_id ON user_predictions(user_id);
                CREATE INDEX IF NOT EXISTS idx_user_predictions_date ON user_predictions(tirage_date DESC);

                CREATE TABLE IF NOT EXISTS model_errors (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(100) NOT NULL,
                    prediction_id INTEGER REFERENCES user_predictions(id),
                    model_name VARCHAR(100) NOT NULL,
                    predicted_numbers INTEGER[] NOT NULL,
                    actual_numbers INTEGER[] NOT NULL,
                    error_count INTEGER NOT NULL,
                    accuracy_rate DECIMAL(5, 4) NOT NULL,
                    error_details JSONB,
                    tirage_date DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_model_errors_user_id ON model_errors(user_id);
                CREATE INDEX IF NOT EXISTS idx_model_errors_date ON model_errors(tirage_date DESC);

                CREATE TABLE IF NOT EXISTS analysis_results (
                    id SERIAL PRIMARY KEY,
                    analysis_type VARCHAR(50) NOT NULL,
                    parameters JSONB,
                    results JSONB NOT NULL,
                    execution_time_ms INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            conn.commit()

    def convert_date_format(self, date_input):
        """
        Convertit une date du format DD/MM/YYYY vers le format ISO YYYY-MM-DD.
        
        Args:
            date_input: Date sous forme de string DD/MM/YYYY, objet datetime, ou déjà au format ISO
            
        Returns:
            String au format YYYY-MM-DD ou objet date Python
        """
        if date_input is None:
            return None
            
        # Si c'est déjà un objet date ou datetime
        if isinstance(date_input, (datetime, type(datetime.now().date()))):
            return date_input
            
        # Si c'est une string
        if isinstance(date_input, str):
            date_input = date_input.strip()
            
            # Si c'est déjà au format ISO (YYYY-MM-DD)
            if re.match(r'^\d{4}-\d{2}-\d{2}$', date_input):
                try:
                    # Valider que c'est une date valide
                    datetime.strptime(date_input, '%Y-%m-%d')
                    return date_input
                except ValueError:
                    logger.error(f"Date ISO invalide: {date_input}")
                    return None
            
            # Si c'est au format DD/MM/YYYY
            if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', date_input):
                try:
                    # Parser la date DD/MM/YYYY
                    date_obj = datetime.strptime(date_input, '%d/%m/%Y')
                    # Retourner au format ISO
                    return date_obj.strftime('%Y-%m-%d')
                except ValueError as e:
                    logger.error(f"❌ Erreur conversion date {date_input}: {e}")
                    return None
            
            # Autres formats possibles
            for fmt in ['%d-%m-%Y', '%Y/%m/%d', '%d.%m.%Y']:
                try:
                    date_obj = datetime.strptime(date_input, fmt)
                    return date_obj.strftime('%Y-%m-%d')
                except ValueError:
                    continue
            
            logger.error(f"❌ Format de date non reconnu: {date_input}")
            return None
        
        logger.error(f"❌ Type de date non supporté: {type(date_input)} - {date_input}")
        return None

    def get_tirages_data(self, limit=None, start_date=None, end_date=None):
        """Récupérer les tirages depuis PostgreSQL"""
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
        
        query += " ORDER BY date_tirage DESC, heure_tirage DESC"
        
        if limit:
            query += " LIMIT :limit"
            params["limit"] = limit
        
        return pd.read_sql(query, self.engine, params=params)

    def insert_new_tirage(self, tirage_data):
        """Insérer un nouveau tirage avec conversion de date automatique"""
        try:
            # Convertir la date au format ISO si nécessaire
            if 'date_tirage' in tirage_data:
                tirage_data['date_tirage'] = self.convert_date_format(tirage_data['date_tirage'])
                
                if tirage_data['date_tirage'] is None:
                    logger.error("❌ Impossible de convertir la date, tirage ignoré")
                    return
            
            with self.engine.connect() as conn:
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
                logger.info(f"✅ Tirage inséré avec succès pour la date {tirage_data['date_tirage']}")
                
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'insertion du tirage: {e}")
            raise

    def save_ml_model_metadata(self, model_info):
        """Sauvegarder les métadonnées d'un modèle ML"""
        with self.engine.connect() as conn:
            # Désactiver l'ancien modèle actif du même type
            conn.execute(text("""
                UPDATE ml_models 
                SET is_active = FALSE 
                WHERE model_type = :model_type AND is_active = TRUE
            """), {"model_type": model_info["model_type"]})
            
            # Insérer le nouveau modèle
            conn.execute(text("""
                INSERT INTO ml_models (
                    model_name, model_type, s3_path, training_score,
                    test_score, r2_score, training_time_seconds,
                    trained_at, is_active, metadata
                ) VALUES (
                    :model_name, :model_type, :s3_path, :training_score,
                    :test_score, :r2_score, :training_time_seconds,
                    :trained_at, TRUE, :metadata
                )
            """), model_info)
            conn.commit()

    def get_active_ml_models_metadata(self):
        """Récupérer les métadonnées des modèles ML actifs."""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT * FROM ml_models 
                WHERE is_active = TRUE 
                ORDER BY trained_at DESC
            """))
            return result.fetchall()

    def save_analysis_result(self, analysis_type, parameters, results, execution_time_ms):
        """Sauvegarder les résultats d'analyse."""
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO analysis_results (
                    analysis_type, parameters, results, execution_time_ms
                ) VALUES (
                    :analysis_type, :parameters, :results, :execution_time_ms
                )
            """), {
                "analysis_type": analysis_type,
                "parameters": parameters,
                "results": results,
                "execution_time_ms": execution_time_ms
            })
            conn.commit()

    def save_user_prediction(self, user_id, session_id, prediction_method, predicted_numbers, confidence_score, tirage_date=None, tirage_time=None):
        """Sauvegarder les prédictions utilisateur."""
        # Convertir la date si nécessaire
        if tirage_date:
            tirage_date = self.convert_date_format(tirage_date)
        
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                INSERT INTO user_predictions (
                    user_id, session_id, prediction_method, predicted_numbers, confidence_score, tirage_date, tirage_time
                ) VALUES (
                    :user_id, :session_id, :prediction_method, :predicted_numbers, :confidence_score, :tirage_date, :tirage_time
                ) RETURNING id
            """), {
                "user_id": user_id,
                "session_id": session_id,
                "prediction_method": prediction_method,
                "predicted_numbers": predicted_numbers,
                "confidence_score": confidence_score,
                "tirage_date": tirage_date,
                "tirage_time": tirage_time
            })
            conn.commit()
            return result.fetchone()[0]  # Retourner l'ID de la prédiction

    def save_tirage(self, date, numeros, multiplicateur, joker):
        """Sauvegarder un tirage dans la base de données avec conversion de date automatique."""
        try:
            # Convertir la date au format ISO
            date_converted = self.convert_date_format(date)
            
            if date_converted is None:
                logger.error(f"❌ Impossible de convertir la date: {date}")
                return None

            # Les numéros doivent être passés comme une liste de 20 éléments
            tirage_data = {
                'date_tirage': date_converted,
                'heure_tirage': datetime.now().time(), # Ou une heure spécifique si disponible
                'multiplicateur': multiplicateur,
                'joker': joker
            }
            
            for i, num in enumerate(numeros):
                tirage_data[f'numero_{i+1}'] = num

            self.insert_new_tirage(tirage_data)
            logger.info(f"✅ Tirage sauvegardé avec succès pour la date {date_converted}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde tirage: {e}")
            return None

    def save_tirages_data(self, tirages_df):
        """Sauvegarder un DataFrame de tirages dans la base de données avec conversion de date"""
        if tirages_df is None or tirages_df.empty:
            logger.warning("Aucune donnée à sauvegarder")
            return
        
        success_count = 0
        error_count = 0
        
        # Convertir le DataFrame en format compatible avec la base de données
        for index, row in tirages_df.iterrows():
            try:
                # Récupérer la date et la convertir
                date_raw = row.get("Date", row.get("date_tirage", row.get("date")))
                date_converted = self.convert_date_format(date_raw)
                
                if date_converted is None:
                    logger.error(f"❌ Erreur conversion date ligne {index}: {date_raw}")
                    error_count += 1
                    continue
                
                tirage_data = {
                    "date_tirage": date_converted,
                    "heure_tirage": row.get("Heure", row.get("heure_tirage")),
                    "numero_1": row.get("N1", row.get("numero_1")),
                    "numero_2": row.get("N2", row.get("numero_2")),
                    "numero_3": row.get("N3", row.get("numero_3")),
                    "numero_4": row.get("N4", row.get("numero_4")),
                    "numero_5": row.get("N5", row.get("numero_5")),
                    "numero_6": row.get("N6", row.get("numero_6")),
                    "numero_7": row.get("N7", row.get("numero_7")),
                    "numero_8": row.get("N8", row.get("numero_8")),
                    "numero_9": row.get("N9", row.get("numero_9")),
                    "numero_10": row.get("N10", row.get("numero_10")),
                    "numero_11": row.get("N11", row.get("numero_11")),
                    "numero_12": row.get("N12", row.get("numero_12")),
                    "numero_13": row.get("N13", row.get("numero_13")),
                    "numero_14": row.get("N14", row.get("numero_14")),
                    "numero_15": row.get("N15", row.get("numero_15")),
                    "numero_16": row.get("N16", row.get("numero_16")),
                    "numero_17": row.get("N17", row.get("numero_17")),
                    "numero_18": row.get("N18", row.get("numero_18")),
                    "numero_19": row.get("N19", row.get("numero_19")),
                    "numero_20": row.get("N20", row.get("numero_20")),
                    "multiplicateur": row.get("Multiplicateur", row.get("multiplicateur")),
                    "joker": row.get("Joker", row.get("joker"))
                }
                
                self.insert_new_tirage(tirage_data)
                success_count += 1
                
            except Exception as e:
                logger.error(f"❌ Erreur sauvegarde tirage ligne {index}: {e}")
                error_count += 1
        
        logger.info(f"✅ Sauvegarde terminée: {success_count} succès, {error_count} erreurs")

    def save_model_error(self, user_id, prediction_id, model_name, predicted_numbers, actual_numbers, tirage_date):
        """Sauvegarder les erreurs du modèle pour un utilisateur."""
        # Convertir la date si nécessaire
        if tirage_date:
            tirage_date = self.convert_date_format(tirage_date)
        
        error_count = len(set(predicted_numbers) - set(actual_numbers))
        accuracy_rate = (len(predicted_numbers) - error_count) / len(predicted_numbers) if predicted_numbers else 0
        
        error_details = {
            "predicted_but_not_drawn": list(set(predicted_numbers) - set(actual_numbers)),
            "drawn_but_not_predicted": list(set(actual_numbers) - set(predicted_numbers)),
            "correct_predictions": list(set(predicted_numbers) & set(actual_numbers))
        }
        
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO model_errors (
                    user_id, prediction_id, model_name, predicted_numbers, actual_numbers,
                    error_count, accuracy_rate, error_details, tirage_date
                ) VALUES (
                    :user_id, :prediction_id, :model_name, :predicted_numbers, :actual_numbers,
                    :error_count, :accuracy_rate, :error_details, :tirage_date
                )
            """), {
                "user_id": user_id,
                "prediction_id": prediction_id,
                "model_name": model_name,
                "predicted_numbers": predicted_numbers,
                "actual_numbers": actual_numbers,
                "error_count": error_count,
                "accuracy_rate": accuracy_rate,
                "error_details": json.dumps(error_details),
                "tirage_date": tirage_date
            })
            conn.commit()

    def update_prediction_evaluation(self, prediction_id, actual_numbers):
        """Mettre à jour une prédiction avec les résultats réels."""
        with self.engine.connect() as conn:
            # Récupérer la prédiction
            result = conn.execute(text("""
                SELECT predicted_numbers FROM user_predictions WHERE id = :prediction_id
            """), {"prediction_id": prediction_id})
            
            row = result.fetchone()
            if not row:
                return False
            
            predicted_numbers = row[0]
            correct_count = len(set(predicted_numbers) & set(actual_numbers))
            
            # Mettre à jour la prédiction
            conn.execute(text("""
                UPDATE user_predictions 
                SET actual_numbers = :actual_numbers, 
                    correct_count = :correct_count, 
                    is_evaluated = TRUE
                WHERE id = :prediction_id
            """), {
                "prediction_id": prediction_id,
                "actual_numbers": actual_numbers,
                "correct_count": correct_count
            })
            conn.commit()
            return True

    def get_user_predictions(self, user_id, limit=50):
        """Récupérer les prédictions d'un utilisateur."""
        query = """
        SELECT * FROM user_predictions 
        WHERE user_id = :user_id 
        ORDER BY created_at DESC 
        LIMIT :limit
        """
        return pd.read_sql(query, self.engine, params={"user_id": user_id, "limit": limit})

    def get_user_model_errors(self, user_id, limit=50):
        """Récupérer les erreurs du modèle pour un utilisateur."""
        query = """
        SELECT * FROM model_errors 
        WHERE user_id = :user_id 
        ORDER BY created_at DESC 
        LIMIT :limit
        """
        return pd.read_sql(query, self.engine, params={"user_id": user_id, "limit": limit})

    def get_user_statistics(self, user_id):
        """Récupérer les statistiques d'un utilisateur."""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    COUNT(*) as total_predictions,
                    COUNT(CASE WHEN is_evaluated = TRUE THEN 1 END) as evaluated_predictions,
                    AVG(CASE WHEN is_evaluated = TRUE THEN correct_count END) as avg_correct,
                    MAX(correct_count) as best_score,
                    COUNT(CASE WHEN correct_count >= 5 THEN 1 END) as good_predictions
                FROM user_predictions 
                WHERE user_id = :user_id
            """), {"user_id": user_id})
            
            return result.fetchone()

    def get_model_performance_for_user(self, user_id, model_name=None):
        """Récupérer les performances du modèle pour un utilisateur."""
        query = """
        SELECT 
            model_name,
            COUNT(*) as total_errors,
            AVG(accuracy_rate) as avg_accuracy,
            AVG(error_count) as avg_errors
        FROM model_errors 
        WHERE user_id = :user_id
        """
        params = {"user_id": user_id}
        
        if model_name:
            query += " AND model_name = :model_name"
            params["model_name"] = model_name
        
        query += " GROUP BY model_name ORDER BY avg_accuracy DESC"
        
        return pd.read_sql(query, self.engine, params=params)


# Instance globale du gestionnaire de base de données
db_manager = None

def get_database_manager() -> DatabaseManager:
    """Récupère l'instance globale du gestionnaire de base de données"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
    return db_manager

def initialize_database():
    """Initialise la base de données au démarrage de l'application"""
    try:
        manager = get_database_manager()
        logger.info("Gestionnaire de base de données initialisé")
        return manager
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de la base de données: {e}")
        return None

if __name__ == "__main__":
    # Test du gestionnaire de base de données avec les dates problématiques
    manager = initialize_database()
    
    if manager:
        # Test avec les dates qui causaient des erreurs
        test_dates = [
            "27/11/2018", "25/11/2018", "23/11/2018", "22/11/2018", 
            "20/11/2018", "19/11/2018", "17/11/2018", "15/11/2018", "14/11/2018"
        ]
        
        print("🧪 Test de conversion des dates problématiques:")
        for date_str in test_dates:
            converted = manager.convert_date_format(date_str)
            print(f"  {date_str} → {converted}")
        
        # Test de sauvegarde d'un tirage avec date problématique
        print("\n🧪 Test de sauvegarde avec date problématique:")
        try:
            success = manager.save_tirage(
                date="27/11/2018",  # Date qui causait l'erreur
                numeros=[3, 5, 13, 16, 19, 25, 33, 34, 35, 46, 47, 48, 49, 60, 61, 62, 63, 65, 67, 68],
                multiplicateur=2,
                joker="JOKER"
            )
            print(f"  Résultat: {'✅ Succès' if success else '❌ Échec'}")
        except Exception as e:
            print(f"  ❌ Erreur: {e}")
        
        print("\n✅ Tests terminés")

