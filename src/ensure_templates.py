import os
import shutil
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def ensure_templates():
    """
    Copie les fichiers de templates du dossier racine vers le dossier templates de l'application
    si nécessaire pour le déploiement sur Render.
    """
    try:
        # Chemins source et destination
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        src_templates = os.path.join(base_dir, 'templates')
        dest_templates = os.path.join(os.path.dirname(__file__), 'templates')
        
        # Si le dossier source n'existe pas, on ne fait rien
        if not os.path.exists(src_templates):
            logger.warning(f"Le dossier source des templates n'existe pas: {src_templates}")
            return False
            
        # Créer le dossier de destination s'il n'existe pas
        os.makedirs(dest_templates, exist_ok=True)
        
        # Copier les fichiers
        for filename in os.listdir(src_templates):
            src_path = os.path.join(src_templates, filename)
            dest_path = os.path.join(dest_templates, filename)
            
            # Ne copier que si nécessaire (fichier manquant ou modifié)
            if not os.path.exists(dest_path) or \
               os.path.getmtime(src_path) > os.path.getmtime(dest_path):
                shutil.copy2(src_path, dest_path)
                logger.info(f"Fichier copié: {src_path} -> {dest_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"Erreur lors de la copie des templates: {e}")
        return False

if __name__ == "__main__":
    ensure_templates()
