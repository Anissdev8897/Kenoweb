#!/usr/bin/env python3
"""
Script de nettoyage des fichiers JSON après migration
Supprime les fichiers predictions.json après confirmation
"""

import os
import logging
from datetime import datetime

# Configuration du logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JSONCleaner:
    def __init__(self):
        """Initialise le nettoyeur"""
        pass
    
    def find_json_files(self, search_path="."):
        """Trouve tous les fichiers JSON de prédictions dans le répertoire"""
        json_files = []
        for root, dirs, files in os.walk(search_path):
            for file in files:
                if file == 'predictions.json':
                    json_files.append(os.path.join(root, file))
        return json_files
    
    def clean_json_file(self, json_file_path, move_to_archive=True):
        """Nettoie un fichier JSON (suppression ou archivage)"""
        try:
            if move_to_archive:
                # Créer un répertoire d'archive
                archive_dir = os.path.join(os.path.dirname(json_file_path), 'json_archive')
                os.makedirs(archive_dir, exist_ok=True)
                
                # Déplacer le fichier vers l'archive avec timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                archive_name = f"predictions_{timestamp}.json"
                archive_path = os.path.join(archive_dir, archive_name)
                
                import shutil
                shutil.move(json_file_path, archive_path)
                logger.info(f"Fichier archivé: {json_file_path} -> {archive_path}")
                return archive_path
            else:
                # Supprimer le fichier
                os.remove(json_file_path)
                logger.info(f"Fichier supprimé: {json_file_path}")
                return None
                
        except Exception as e:
            logger.error(f"Erreur nettoyage fichier {json_file_path}: {e}")
            return None
    
    def clean_all(self, search_path=".", move_to_archive=True, confirm=True):
        """Nettoie tous les fichiers JSON trouvés"""
        json_files = self.find_json_files(search_path)
        
        if not json_files:
            logger.info("Aucun fichier predictions.json trouvé à nettoyer")
            return 0
        
        logger.info(f"Fichiers JSON trouvés: {len(json_files)}")
        for file in json_files:
            logger.info(f"  - {file}")
        
        if confirm:
            action = "archivés" if move_to_archive else "supprimés"
            response = input(f"Voulez-vous que ces {len(json_files)} fichiers soient {action}? (oui/non): ")
            if response.lower() not in ['oui', 'o', 'yes', 'y']:
                logger.info("Nettoyage annulé par l'utilisateur")
                return 0
        
        cleaned_count = 0
        
        for json_file in json_files:
            result = self.clean_json_file(json_file, move_to_archive)
            if result is not None or not move_to_archive:
                cleaned_count += 1
        
        action = "archivés" if move_to_archive else "supprimés"
        logger.info(f"Nettoyage terminé: {cleaned_count} fichiers {action}")
        return cleaned_count

def main():
    """Fonction principale du script de nettoyage"""
    logger.info("=== Début du nettoyage des fichiers JSON ===")
    
    cleaner = JSONCleaner()
    
    # Nettoyer tous les fichiers JSON (archivage par défaut)
    cleaned_count = cleaner.clean_all(
        search_path=".",  # Rechercher dans le répertoire courant
        move_to_archive=True,  # Archiver au lieu de supprimer
        confirm=True  # Demander confirmation
    )
    
    if cleaned_count > 0:
        logger.info(f"✅ Nettoyage réussi: {cleaned_count} fichiers traités")
    else:
        logger.info("ℹ️ Aucun fichier à nettoyer")
    
    logger.info("=== Fin du nettoyage ===")

if __name__ == "__main__":
    main()

