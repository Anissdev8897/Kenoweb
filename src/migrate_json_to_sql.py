#!/usr/bin/env python3
"""
Script de migration des données JSON vers PostgreSQL
Migre les fichiers predictions.json vers la base de données
"""

import os
import json
import logging
from datetime import datetime
from database_manager_postgresql import PostgreSQLManager

# Configuration du logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JSONToSQLMigrator:
    def __init__(self):
        """Initialise le migrateur avec le gestionnaire de base de données"""
        self.db_manager = PostgreSQLManager()
        
    def find_json_files(self, search_path="."):
        """Trouve tous les fichiers JSON de prédictions dans le répertoire"""
        json_files = []
        for root, dirs, files in os.walk(search_path):
            for file in files:
                if file == 'predictions.json':
                    json_files.append(os.path.join(root, file))
        return json_files
    
    def migrate_predictions_file(self, json_file_path):
        """Migre un fichier predictions.json vers la base de données"""
        try:
            logger.info(f"Migration du fichier: {json_file_path}")
            
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            predictions = data.get('predictions', [])
            migrated_count = 0
            
            for prediction in predictions:
                try:
                    # Extraire les données de la prédiction
                    user_id = prediction.get('username', 'anonymous')
                    method = prediction.get('method', 'unknown')
                    numbers = prediction.get('numbers', [])
                    confidence = prediction.get('confidence', 0.0)
                    
                    # Sauvegarder dans la table predictions
                    prediction_id = self.db_manager.save_prediction(
                        user_id=user_id,
                        method=method,
                        numeros=numbers,
                        confidence=confidence
                    )
                    
                    if prediction_id:
                        migrated_count += 1
                        logger.info(f"Prédiction migrée: {user_id} - {method} (ID: {prediction_id})")
                    
                    # Si on a un tirage_id, sauvegarder aussi dans user_predictions
                    if 'tirage_id' in prediction:
                        user_pred_id = self.db_manager.save_user_prediction(
                            user_id=user_id,
                            tirage_id=prediction['tirage_id'],
                            predicted_numbers=numbers,
                            confidence_score=confidence,
                            prediction_method=method
                        )
                        if user_pred_id:
                            logger.info(f"Prédiction utilisateur migrée (ID: {user_pred_id})")
                    
                except Exception as e:
                    logger.error(f"Erreur migration prédiction: {e}")
                    continue
            
            logger.info(f"Migration terminée: {migrated_count}/{len(predictions)} prédictions migrées")
            return migrated_count
            
        except Exception as e:
            logger.error(f"Erreur migration fichier {json_file_path}: {e}")
            return 0
    
    def backup_json_file(self, json_file_path):
        """Crée une sauvegarde du fichier JSON avant migration"""
        try:
            backup_path = f"{json_file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            import shutil
            shutil.copy2(json_file_path, backup_path)
            logger.info(f"Sauvegarde créée: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Erreur création sauvegarde: {e}")
            return None
    
    def migrate_all(self, search_path=".", create_backup=True):
        """Migre tous les fichiers JSON trouvés"""
        json_files = self.find_json_files(search_path)
        
        if not json_files:
            logger.info("Aucun fichier predictions.json trouvé")
            return 0
        
        total_migrated = 0
        
        for json_file in json_files:
            logger.info(f"Traitement du fichier: {json_file}")
            
            # Créer une sauvegarde si demandé
            if create_backup:
                self.backup_json_file(json_file)
            
            # Migrer le fichier
            migrated = self.migrate_predictions_file(json_file)
            total_migrated += migrated
        
        logger.info(f"Migration globale terminée: {total_migrated} prédictions migrées au total")
        return total_migrated

def main():
    """Fonction principale du script de migration"""
    logger.info("=== Début de la migration JSON vers SQL ===")
    
    migrator = JSONToSQLMigrator()
    
    # Rechercher et migrer tous les fichiers JSON
    total_migrated = migrator.migrate_all(
        search_path=".",  # Rechercher dans le répertoire courant
        create_backup=True  # Créer des sauvegardes
    )
    
    if total_migrated > 0:
        logger.info(f"✅ Migration réussie: {total_migrated} prédictions migrées")
    else:
        logger.info("ℹ️ Aucune donnée à migrer ou migration échouée")
    
    logger.info("=== Fin de la migration ===")

if __name__ == "__main__":
    main()

