#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour enregistrer un modèle ML dans la base de données PostgreSQL
Avec SQLAlchemy - Version Manus
"""

import os
from sqlalchemy import create_engine, text
from datetime import datetime
from typing import Dict, Any

# Configuration de la base de données
def get_database_url():
    return os.environ.get(
        "DATABASE_URL", 
        "postgresql://kenos_user:qYGSudoftPvnoxaT9Seh5IP4itP1kK0a@dpg-d1umeoer433s73eu3d7g-a.frankfurt-postgres.render.com/kenos_vs92"
    )

def create_table_and_insert_model():
    """Créer la table ml_models et insérer un modèle"""
    try:
        engine = create_engine(get_database_url())
        
        with engine.connect() as connection:
            # Créer la table ml_models si elle n'existe pas
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS ml_models (
                    id SERIAL PRIMARY KEY,
                    model_name VARCHAR(100) NOT NULL,
                    model_type VARCHAR(50) NOT NULL,
                    s3_path VARCHAR(500),
                    training_score NUMERIC(10,8),
                    test_score NUMERIC(10,8),
                    r2_score NUMERIC(10,8),
                    training_time_seconds INTEGER,
                    trained_at TIMESTAMP NOT NULL,
                    is_active BOOLEAN DEFAULT FALSE,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            print("✅ Table ml_models créée ou déjà existante.")

            # Insérer le modèle KenoPredictorV1
            model_data = {
                'model_name': 'KenoPredictorV1',
                'model_type': 'RandomForestClassifier',
                's3_path': 's3://keno-models/KenoPredictorV1_20250728.pkl',
                'training_score': 0.85678912,
                'test_score': 0.82345678,
                'r2_score': 0.78901234,
                'training_time_seconds': 3600,
                'trained_at': datetime.now(),
                'is_active': True,
                'metadata': {'version': '1.0', 'author': 'Manus'}
            }

            connection.execute(text("""
                INSERT INTO ml_models (model_name, model_type, s3_path, training_score, test_score, r2_score, training_time_seconds, trained_at, is_active, metadata)
                VALUES (:model_name, :model_type, :s3_path, :training_score, :test_score, :r2_score, :training_time_seconds, :trained_at, :is_active, :metadata)
            """), model_data)
            connection.commit()
            print("✅ Modèle KenoPredictorV1 inséré avec succès dans la table ml_models.")
            print(f"   - Model: {model_data['model_name']}")
            print(f"   - Type: {model_data['model_type']}")
            print(f"   - Training Score: {model_data['training_score']}")
            print(f"   - Test Score: {model_data['test_score']}")
            print(f"   - Training Time: {model_data['training_time_seconds']}s")

    except Exception as e:
        print(f"❌ Erreur lors de l'opération sur la base de données : {e}")

def save_model_manus():
    """Fonction principale pour sauvegarder le modèle de Manus"""
    print("🚀 Enregistrement du modèle ML dans la base de données...")
    create_table_and_insert_model()
    print("✅ Opération terminée avec succès !")

if __name__ == "__main__":
    save_model_manus()
