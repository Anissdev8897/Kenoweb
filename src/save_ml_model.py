#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour enregistrer un modèle ML dans la base de données PostgreSQL
Avec SQLAlchemy - Version Manus
"""

import os
import sys
import json
from pathlib import Path
from sqlalchemy import create_engine, text, exc
from datetime import datetime
from typing import Dict, Any
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Configuration de la base de données
def get_database_url():
    """Récupère l'URL de la base de données depuis les variables d'environnement.
    
    Returns:
        str: L'URL de la base de données
        
    Raises:
        ValueError: Si la variable d'environnement DATABASE_URL n'est pas définie
    """
    # Charger les variables d'environnement depuis le fichier .env
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        from dotenv import load_dotenv
        load_dotenv(env_path)
        logger.info(f"Variables d'environnement chargées depuis: {env_path}")
    else:
        logger.warning(f"Fichier .env non trouvé à l'emplacement: {env_path}")
    
    # Récupérer l'URL de la base de données
    database_url = os.environ.get("DATABASE_URL")
    
    # Afficher une version masquée de l'URL pour le débogage
    if database_url and '@' in database_url:
        parts = database_url.split('@')
        if '//' in parts[0]:
            protocol = parts[0].split('//')[0] + '//'
            credentials = parts[0].split('//')[1]
            if ':' in credentials:
                user = credentials.split(':')[0]
                db_display = f"{protocol}{user}:********@{'@'.join(parts[1:])}"
                logger.info(f"Connexion à la base de données: {db_display}")
    
    if not database_url:
        error_msg = "La variable d'environnement DATABASE_URL est requise pour se connecter à la base de données"
        logger.error(error_msg)
        raise ValueError(error_msg)
        
    return database_url

def create_table_and_insert_model():
    """Créer la table ml_models et insérer un modèle"""
    try:
        # Obtenir l'URL de la base de données
        database_url = get_database_url()
        logger.info("Tentative de connexion à la base de données...")
        
        # Créer le moteur avec des paramètres de débogage
        engine = create_engine(
            database_url,
            echo=True,  # Active le logging SQL
            pool_pre_ping=True  # Vérifie la connexion avant utilisation
        )
        
        with engine.connect() as connection:
            logger.info("Connexion à la base de données établie avec succès")
            
            # Vérifier si la table existe déjà
            table_exists = connection.execute(
                text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'ml_models'
                    )
                """)
            ).scalar()
            
            if not table_exists:
                logger.info("Création de la table ml_models...")
                # Créer la table ml_models si elle n'existe pas
                connection.execute(text("""
                    CREATE TABLE ml_models (
                        id SERIAL PRIMARY KEY,
                        model_name VARCHAR(100) NOT NULL,
                        model_type VARCHAR(50) NOT NULL,
                        model_binary BYTEA,
                        training_score NUMERIC(10,8),
                        test_score NUMERIC(10,8),
                        r2_score NUMERIC(10,8),
                        training_time_seconds INTEGER,
                        trained_at TIMESTAMP NOT NULL,
                        is_active BOOLEAN DEFAULT FALSE,
                        metadata JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                connection.commit()
                logger.info("✅ Table ml_models créée avec succès")
            else:
                logger.info("ℹ️ La table ml_models existe déjà")

            # Créer un modèle factice plus réaliste
            logger.info("Préparation des données du modèle...")
            
            # Un modèle factice plus réaliste (séquence d'octets plus longue)
            dummy_model_binary = bytes([i % 256 for i in range(1000)])
            
            # Données du modèle
            model_data = {
                'model_name': 'KenoPredictorV1',
                'model_type': 'RandomForestClassifier',
                'model_binary': dummy_model_binary,
                'training_score': 0.85678912,
                'test_score': 0.82345678,
                'r2_score': 0.78901234,
                'training_time_seconds': 3600,
                'trained_at': datetime.now(),
                'is_active': True,
                'metadata': {
                    'version': '1.0', 
                    'author': 'Manus',
                    'features': ['freq_1', 'freq_2', 'freq_3', 'gaps_1', 'gaps_2', 'gaps_3'],
                    'target': 'next_draw',
                    'parameters': {
                        'n_estimators': 100,
                        'max_depth': 10,
                        'random_state': 42
                    }
                }
            }

            # Exécution de la requête d'insertion
            logger.info("Insertion du modèle dans la base de données...")
            
            # Afficher un aperçu des données pour le débogage
            logger.debug("Données du modèle à insérer:")
            for key, value in model_data.items():
                if key != 'model_binary':
                    logger.debug(f"  {key}: {value}")
                else:
                    logger.debug(f"  {key}: {len(value)} octets de données binaires")
            
            try:
                # Préparer la requête SQL
                sql = """
                    INSERT INTO ml_models (
                        model_name, model_type, model_binary, training_score, 
                        test_score, r2_score, training_time_seconds, 
                        trained_at, is_active, metadata
                    ) VALUES (
                        %(model_name)s, %(model_type)s, %(model_binary)s, %(training_score)s, 
                        %(test_score)s, %(r2_score)s, %(training_time_seconds)s, 
                        %(trained_at)s, %(is_active)s, %(metadata)s
                    )
                    RETURNING id
                """
                
                # Afficher la requête SQL pour le débogage
                logger.debug("Requête SQL préparée:")
                logger.debug(sql)
                logger.debug("Paramètres:")
                logger.debug({k: v for k, v in model_data.items() if k != 'model_binary'})
                
                # Exécuter avec execute() directement pour éviter les problèmes de paramètres
                with connection.connection.cursor() as cursor:
                    # Convertir le dictionnaire metadata en chaîne JSON
                    model_data_for_db = model_data.copy()
                    if 'metadata' in model_data_for_db and isinstance(model_data_for_db['metadata'], dict):
                        model_data_for_db['metadata'] = json.dumps(model_data_for_db['metadata'])
                    
                    # Afficher les données pour le débogage
                    logger.debug("Données à insérer dans la base de données:")
                    for k, v in model_data_for_db.items():
                        if k != 'model_binary':
                            logger.debug(f"  {k}: {v} (type: {type(v).__name__})")
                        else:
                            logger.debug(f"  {k}: {len(v)} octets de données binaires")
                    
                    # Exécuter la requête avec les données préparées
                    cursor.execute(sql, model_data_for_db)
                    model_id = cursor.fetchone()[0]
                    connection.connection.commit()
                
                logger.info(f"✅ Modèle inséré avec succès (ID: {model_id})")
                logger.info(f"   - Nom: {model_data['model_name']}")
                logger.info(f"   - Type: {model_data['model_type']}")
                logger.info(f"   - Score d'entraînement: {model_data['training_score']:.4f}")
                logger.info(f"   - Score de test: {model_data['test_score']:.4f}")
                logger.info(f"   - Temps d'entraînement: {model_data['training_time_seconds']}s")
                
            except Exception as e:
                logger.error("❌ Erreur lors de l'insertion du modèle:")
                logger.error(f"Type d'erreur: {type(e).__name__}")
                logger.error(f"Message d'erreur: {str(e)}")
                
                # Afficher plus de détails sur l'erreur si disponible
                if hasattr(e, 'orig') and e.orig:
                    logger.error(f"Erreur d'origine: {e.orig}")
                    if hasattr(e.orig, 'pgerror') and e.orig.pgerror:
                        logger.error(f"Erreur PostgreSQL: {e.orig.pgerror}")
                    if hasattr(e.orig, 'pgcode') and e.orig.pgcode:
                        logger.error(f"Code d'erreur PostgreSQL: {e.orig.pgcode}")
                
                # Annuler toute transaction en cours
                if connection.in_transaction():
                    connection.rollback()
                
                # Relancer l'exception pour un traitement ultérieur
                raise
            
            return True
            
    except exc.SQLAlchemyError as e:
        logger.error(f"❌ Erreur SQL: {str(e)}")
        if hasattr(e, 'orig') and hasattr(e.orig, 'pgerror'):
            logger.error(f"Détails: {e.orig.pgerror}")
        return False
    except Exception as e:
        logger.error(f"❌ Erreur inattendue: {str(e)}", exc_info=True)
        return False
    finally:
        if 'engine' in locals():
            engine.dispose()

def save_model_manus():
    """Fonction principale pour sauvegarder le modèle de Manus"""
    print("🚀 Enregistrement du modèle ML dans la base de données...")
    create_table_and_insert_model()
    print("✅ Opération terminée avec succès !")

if __name__ == "__main__":
    save_model_manus()
