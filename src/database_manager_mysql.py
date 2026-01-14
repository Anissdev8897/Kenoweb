#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestionnaire de Base de Données MySQL pour Keno Analyzer Pro
Adapté pour le format Keno 2025 (16 numéros sur 56)
"""

import os
import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Any
import json

from sqlalchemy import create_engine, text
import pandas as pd

logger = logging.getLogger(__name__)

class MySQLDatabaseManager:
    """Gestionnaire de base de données MySQL pour Keno Analyzer Pro"""
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Initialise le gestionnaire MySQL
        
        Args:
            database_url: URL de connexion MySQL (None = variable d'environnement)
        """
        self.database_url = database_url or os.environ.get("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set.")
        
        # Vérifier que c'est une URL MySQL
        if not self.database_url.startswith('mysql'):
            logger.warning("L'URL ne semble pas être MySQL. Format attendu: mysql+pymysql://user:pass@host/db")
        
        # Configuration de l'engine SQLAlchemy pour MySQL
        self.engine = create_engine(
            self.database_url,
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_size=5,
            max_overflow=10,
            echo=False
        )
        
        # Créer les tables si nécessaire
        self._create_tables()
    
    def _create_tables(self):
        """Crée les tables MySQL si elles n'existent pas."""
        logger.info("Création des tables MySQL pour Keno 2025...")
        
        with self.engine.connect() as conn:
            conn.execute(text("""
                -- Table des tirages Keno 2025 (nouveau format: 16/56)
                CREATE TABLE IF NOT EXISTS tirages_keno_2025 (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    date_tirage DATE NOT NULL,
                    heure_tirage TIME,
                    numero_1 INT NOT NULL CHECK (numero_1 BETWEEN 1 AND 56),
                    numero_2 INT NOT NULL CHECK (numero_2 BETWEEN 1 AND 56),
                    numero_3 INT NOT NULL CHECK (numero_3 BETWEEN 1 AND 56),
                    numero_4 INT NOT NULL CHECK (numero_4 BETWEEN 1 AND 56),
                    numero_5 INT NOT NULL CHECK (numero_5 BETWEEN 1 AND 56),
                    numero_6 INT NOT NULL CHECK (numero_6 BETWEEN 1 AND 56),
                    numero_7 INT NOT NULL CHECK (numero_7 BETWEEN 1 AND 56),
                    numero_8 INT NOT NULL CHECK (numero_8 BETWEEN 1 AND 56),
                    numero_9 INT NOT NULL CHECK (numero_9 BETWEEN 1 AND 56),
                    numero_10 INT NOT NULL CHECK (numero_10 BETWEEN 1 AND 56),
                    numero_11 INT NOT NULL CHECK (numero_11 BETWEEN 1 AND 56),
                    numero_12 INT NOT NULL CHECK (numero_12 BETWEEN 1 AND 56),
                    numero_13 INT NOT NULL CHECK (numero_13 BETWEEN 1 AND 56),
                    numero_14 INT NOT NULL CHECK (numero_14 BETWEEN 1 AND 56),
                    numero_15 INT NOT NULL CHECK (numero_15 BETWEEN 1 AND 56),
                    numero_16 INT NOT NULL CHECK (numero_16 BETWEEN 1 AND 56),
                    multiplicateur INT,
                    joker VARCHAR(20),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    version VARCHAR(20) DEFAULT '2025',
                    UNIQUE KEY unique_tirage_2025 (date_tirage, heure_tirage)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """))
            
            conn.execute(text("""
                -- Table archive des tirages ancien format (20/70)
                CREATE TABLE IF NOT EXISTS tirages_keno_archive (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    date_tirage DATE NOT NULL,
                    heure_tirage TIME,
                    numero_1 INT NOT NULL CHECK (numero_1 BETWEEN 1 AND 70),
                    numero_2 INT NOT NULL CHECK (numero_2 BETWEEN 1 AND 70),
                    numero_3 INT NOT NULL CHECK (numero_3 BETWEEN 1 AND 70),
                    numero_4 INT NOT NULL CHECK (numero_4 BETWEEN 1 AND 70),
                    numero_5 INT NOT NULL CHECK (numero_5 BETWEEN 1 AND 70),
                    numero_6 INT NOT NULL CHECK (numero_6 BETWEEN 1 AND 70),
                    numero_7 INT NOT NULL CHECK (numero_7 BETWEEN 1 AND 70),
                    numero_8 INT NOT NULL CHECK (numero_8 BETWEEN 1 AND 70),
                    numero_9 INT NOT NULL CHECK (numero_9 BETWEEN 1 AND 70),
                    numero_10 INT NOT NULL CHECK (numero_10 BETWEEN 1 AND 70),
                    numero_11 INT NOT NULL CHECK (numero_11 BETWEEN 1 AND 70),
                    numero_12 INT NOT NULL CHECK (numero_12 BETWEEN 1 AND 70),
                    numero_13 INT NOT NULL CHECK (numero_13 BETWEEN 1 AND 70),
                    numero_14 INT NOT NULL CHECK (numero_14 BETWEEN 1 AND 70),
                    numero_15 INT NOT NULL CHECK (numero_15 BETWEEN 1 AND 70),
                    numero_16 INT NOT NULL CHECK (numero_16 BETWEEN 1 AND 70),
                    numero_17 INT NOT NULL CHECK (numero_17 BETWEEN 1 AND 70),
                    numero_18 INT NOT NULL CHECK (numero_18 BETWEEN 1 AND 70),
                    numero_19 INT NOT NULL CHECK (numero_19 BETWEEN 1 AND 70),
                    numero_20 INT NOT NULL CHECK (numero_20 BETWEEN 1 AND 70),
                    multiplicateur INT,
                    joker VARCHAR(20),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    migrated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_tirage_archive (date_tirage, heure_tirage)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """))
            
            conn.execute(text("""
                -- Table des utilisateurs
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id VARCHAR(100) UNIQUE NOT NULL,
                    display_name VARCHAR(100) NOT NULL,
                    session_id VARCHAR(100),
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    first_prediction TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    total_predictions INT DEFAULT 0,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """))
            
            conn.execute(text("""
                -- Table des modèles ML
                CREATE TABLE IF NOT EXISTS ml_models (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    model_name VARCHAR(100) NOT NULL,
                    model_type VARCHAR(50) NOT NULL,
                    method_name VARCHAR(100) NOT NULL,
                    s3_path VARCHAR(500) NOT NULL,
                    training_score DECIMAL(10, 8),
                    test_score DECIMAL(10, 8),
                    r2_score DECIMAL(10, 8),
                    training_time_seconds INT,
                    trained_at TIMESTAMP NOT NULL,
                    is_active BOOLEAN DEFAULT FALSE,
                    metadata JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """))
            
            conn.execute(text("""
                -- Table unifiée des prédictions
                CREATE TABLE IF NOT EXISTS unified_predictions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    predictor_id VARCHAR(100) NOT NULL,
                    predictor_type ENUM('USER', 'ML_MODEL') NOT NULL,
                    session_id VARCHAR(100),
                    prediction_method VARCHAR(100) NOT NULL,
                    predicted_numbers JSON NOT NULL,
                    confidence_score DECIMAL(5, 4),
                    target_tirage_date DATE NOT NULL,
                    target_tirage_time TIME,
                    actual_numbers JSON,
                    correct_count INT DEFAULT 0,
                    accuracy_percentage DECIMAL(5, 2) DEFAULT 0.0,
                    is_evaluated BOOLEAN DEFAULT FALSE,
                    prediction_hash VARCHAR(64),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    evaluated_at TIMESTAMP NULL,
                    UNIQUE KEY unique_prediction (predictor_id, prediction_method, target_tirage_date, prediction_hash)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """))
            
            conn.execute(text("""
                -- Table des performances par méthode
                CREATE TABLE IF NOT EXISTS method_performance (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    predictor_id VARCHAR(100) NOT NULL,
                    method_name VARCHAR(100) NOT NULL,
                    predictor_type ENUM('USER', 'ML_MODEL') NOT NULL,
                    total_predictions INT DEFAULT 0,
                    total_evaluated INT DEFAULT 0,
                    total_correct_numbers INT DEFAULT 0,
                    average_accuracy DECIMAL(5, 2) DEFAULT 0.0,
                    best_score INT DEFAULT 0,
                    worst_score INT DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_performance (predictor_id, method_name, predictor_type)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """))
            
            conn.execute(text("""
                -- Table des erreurs de prédiction
                CREATE TABLE IF NOT EXISTS prediction_errors (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    prediction_id INT,
                    predictor_id VARCHAR(100) NOT NULL,
                    predictor_type ENUM('USER', 'ML_MODEL') NOT NULL,
                    method_name VARCHAR(100) NOT NULL,
                    predicted_but_not_drawn JSON NOT NULL,
                    drawn_but_not_predicted JSON NOT NULL,
                    correct_predictions JSON NOT NULL,
                    error_count INT NOT NULL,
                    miss_count INT NOT NULL,
                    tirage_date DATE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (prediction_id) REFERENCES unified_predictions(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """))
            
            conn.execute(text("""
                -- Table de l'historique d'entraînement ML
                CREATE TABLE IF NOT EXISTS ml_training_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    model_name VARCHAR(100) NOT NULL,
                    training_start TIMESTAMP NOT NULL,
                    training_end TIMESTAMP NOT NULL,
                    data_start_date DATE NOT NULL,
                    data_end_date DATE NOT NULL,
                    total_tirages_used INT NOT NULL,
                    training_metrics JSON,
                    retrain_trigger VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """))
            
            conn.execute(text("""
                -- Table des sessions utilisateur
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    session_id VARCHAR(100) UNIQUE NOT NULL,
                    user_id VARCHAR(100),
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    predictions_count INT DEFAULT 0,
                    is_active BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """))
            
            # Créer les index
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_tirages_2025_date ON tirages_keno_2025(date_tirage DESC)
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_tirages_archive_date ON tirages_keno_archive(date_tirage DESC)
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_unified_predictions_predictor 
                ON unified_predictions(predictor_id, predictor_type)
            """))
            
            conn.commit()
        
        logger.info("✅ Tables MySQL créées avec succès")
    
    def insert_tirage_2025(self, date_tirage: date, heure_tirage: Optional[str], 
                           numbers: List[int], multiplicateur: Optional[int] = None,
                           joker: Optional[str] = None) -> int:
        """
        Insère un nouveau tirage au format 2025 (16/56)
        
        Args:
            date_tirage: Date du tirage
            heure_tirage: Heure du tirage (optionnel)
            numbers: Liste de 16 numéros tirés (1-56)
            multiplicateur: Multiplicateur (optionnel)
            joker: Numéro joker (optionnel)
            
        Returns:
            ID du tirage inséré
        """
        if len(numbers) != 16:
            raise ValueError(f"Le tirage doit contenir exactement 16 numéros, reçu: {len(numbers)}")
        
        if not all(1 <= n <= 56 for n in numbers):
            raise ValueError("Tous les numéros doivent être entre 1 et 56")
        
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                INSERT INTO tirages_keno_2025 (
                    date_tirage, heure_tirage,
                    numero_1, numero_2, numero_3, numero_4, numero_5,
                    numero_6, numero_7, numero_8, numero_9, numero_10,
                    numero_11, numero_12, numero_13, numero_14, numero_15, numero_16,
                    multiplicateur, joker, version
                ) VALUES (
                    :date_tirage, :heure_tirage,
                    :num1, :num2, :num3, :num4, :num5,
                    :num6, :num7, :num8, :num9, :num10,
                    :num11, :num12, :num13, :num14, :num15, :num16,
                    :multiplicateur, :joker, '2025'
                )
            """), {
                'date_tirage': date_tirage,
                'heure_tirage': heure_tirage,
                'num1': numbers[0], 'num2': numbers[1], 'num3': numbers[2], 'num4': numbers[3],
                'num5': numbers[4], 'num6': numbers[5], 'num7': numbers[6], 'num8': numbers[7],
                'num9': numbers[8], 'num10': numbers[9], 'num11': numbers[10], 'num12': numbers[11],
                'num13': numbers[12], 'num14': numbers[13], 'num15': numbers[14], 'num16': numbers[15],
                'multiplicateur': multiplicateur,
                'joker': joker
            })
            conn.commit()
            return result.lastrowid
    
    def get_tirages_2025(self, limit: Optional[int] = None) -> pd.DataFrame:
        """
        Récupère les tirages au format 2025
        
        Args:
            limit: Nombre de tirages à récupérer (None = tous)
            
        Returns:
            DataFrame avec les tirages
        """
        query = """
            SELECT * FROM tirages_keno_2025 
            ORDER BY date_tirage DESC, heure_tirage DESC
        """
        if limit:
            query += f" LIMIT {limit}"
        
        return pd.read_sql(query, self.engine)
    
    def save_prediction(self, predictor_id: str, predictor_type: str,
                       prediction_method: str, predicted_numbers: List[int],
                       target_date: date, confidence_score: Optional[float] = None) -> int:
        """
        Sauvegarde une prédiction
        
        Args:
            predictor_id: ID du prédicteur (utilisateur ou modèle)
            predictor_type: 'USER' ou 'ML_MODEL'
            prediction_method: Nom de la méthode de prédiction
            predicted_numbers: Liste des numéros prédits
            target_date: Date cible du tirage
            confidence_score: Score de confiance (optionnel)
            
        Returns:
            ID de la prédiction
        """
        import hashlib
        prediction_hash = hashlib.md5(
            f"{predictor_id}_{prediction_method}_{target_date}_{predicted_numbers}".encode()
        ).hexdigest()
        
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                INSERT INTO unified_predictions (
                    predictor_id, predictor_type, prediction_method,
                    predicted_numbers, confidence_score, target_tirage_date,
                    prediction_hash
                ) VALUES (
                    :predictor_id, :predictor_type, :prediction_method,
                    :predicted_numbers, :confidence_score, :target_date,
                    :prediction_hash
                )
                ON DUPLICATE KEY UPDATE
                    predicted_numbers = :predicted_numbers,
                    confidence_score = :confidence_score
            """), {
                'predictor_id': predictor_id,
                'predictor_type': predictor_type,
                'prediction_method': prediction_method,
                'predicted_numbers': json.dumps(predicted_numbers),
                'confidence_score': confidence_score,
                'target_date': target_date,
                'prediction_hash': prediction_hash
            })
            conn.commit()
            return result.lastrowid
    
    def evaluate_prediction(self, prediction_id: int, actual_numbers: List[int]) -> Dict[str, Any]:
        """
        Évalue une prédiction avec les numéros réels
        
        Args:
            prediction_id: ID de la prédiction
            actual_numbers: Liste des numéros réellement tirés
            
        Returns:
            Dict avec les résultats de l'évaluation
        """
        with self.engine.connect() as conn:
            # Récupérer la prédiction
            result = conn.execute(text("""
                SELECT predicted_numbers FROM unified_predictions WHERE id = :prediction_id
            """), {'prediction_id': prediction_id})
            
            row = result.fetchone()
            if not row:
                raise ValueError(f"Prédiction {prediction_id} non trouvée")
            
            predicted_numbers = json.loads(row[0])
            
            # Calculer les métriques
            correct = set(predicted_numbers) & set(actual_numbers)
            predicted_but_not_drawn = set(predicted_numbers) - set(actual_numbers)
            drawn_but_not_predicted = set(actual_numbers) - set(predicted_numbers)
            
            correct_count = len(correct)
            error_count = len(predicted_but_not_drawn)
            miss_count = len(drawn_but_not_predicted)
            
            accuracy = (correct_count / len(predicted_numbers) * 100) if predicted_numbers else 0
            
            # Mettre à jour la prédiction
            conn.execute(text("""
                UPDATE unified_predictions
                SET actual_numbers = :actual_numbers,
                    correct_count = :correct_count,
                    accuracy_percentage = :accuracy,
                    is_evaluated = TRUE,
                    evaluated_at = CURRENT_TIMESTAMP
                WHERE id = :prediction_id
            """), {
                'actual_numbers': json.dumps(actual_numbers),
                'correct_count': correct_count,
                'accuracy': accuracy,
                'prediction_id': prediction_id
            })
            
            # Sauvegarder les erreurs détaillées
            predictor_info = conn.execute(text("""
                SELECT predictor_id, predictor_type, prediction_method, target_tirage_date
                FROM unified_predictions WHERE id = :prediction_id
            """), {'prediction_id': prediction_id}).fetchone()
            
            conn.execute(text("""
                INSERT INTO prediction_errors (
                    prediction_id, predictor_id, predictor_type, method_name,
                    predicted_but_not_drawn, drawn_but_not_predicted,
                    correct_predictions, error_count, miss_count, tirage_date
                ) VALUES (
                    :prediction_id, :predictor_id, :predictor_type, :method_name,
                    :predicted_not_drawn, :drawn_not_predicted,
                    :correct, :error_count, :miss_count, :tirage_date
                )
            """), {
                'prediction_id': prediction_id,
                'predictor_id': predictor_info[0],
                'predictor_type': predictor_info[1],
                'method_name': predictor_info[2],
                'predicted_not_drawn': json.dumps(list(predicted_but_not_drawn)),
                'drawn_not_predicted': json.dumps(list(drawn_but_not_predicted)),
                'correct': json.dumps(list(correct)),
                'error_count': error_count,
                'miss_count': miss_count,
                'tirage_date': predictor_info[3]
            })
            
            conn.commit()
            
            return {
                'prediction_id': prediction_id,
                'correct_count': correct_count,
                'error_count': error_count,
                'miss_count': miss_count,
                'accuracy_percentage': accuracy,
                'correct_numbers': list(correct),
                'predicted_but_not_drawn': list(predicted_but_not_drawn),
                'drawn_but_not_predicted': list(drawn_but_not_predicted)
            }

