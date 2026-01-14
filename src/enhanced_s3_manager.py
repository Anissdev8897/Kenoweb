#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestionnaire S3 amélioré pour les modèles ML
Support complet pour la sauvegarde et le chargement des modèles
"""

import boto3
import joblib
import pickle
import io
import os
from datetime import datetime
import logging
import json

# KEY_PATH = "/root/.ssh/id_rsa"
# def prepare_ssh_key():
#     private_key = os.getenv("SSH_PRIVATE_KEY")
#     if not private_key:
#         logger.error("La variable d'environnement SSH_PRIVATE_KEY est absente.")
#         return False
#     
#     ssh_dir = os.path.dirname(KEY_PATH)
#     if not os.path.exists(ssh_dir):
#         os.makedirs(ssh_dir, mode=0o700)
#         logger.info(f"Création du dossier SSH : {ssh_dir}")
#     
#     with open(KEY_PATH, "w") as f:
#         f.write(private_key)
#     
#     os.chmod(KEY_PATH, stat.S_IRUSR | stat.S_IWUSR)
#     logger.info(f"Clé privée SSH écrite dans {KEY_PATH} avec permissions 600")
#     return True
# 
# if n# if not prepare_ssh_key():
#     logger.error("Impossible de préparer la clé SSH. Arrêt du script.")
#    # exit(1)(1)
logger = logging.getLogger(__name__)

class EnhancedS3StorageManager:
    def __init__(self):
        self.aws_access_key_id = os.environ.get("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
        self.aws_region = os.environ.get("AWS_REGION", "us-east-1")
        self.bucket_name = os.environ.get("S3_BUCKET_NAME")

        if not self.aws_access_key_id or not self.aws_secret_access_key or not self.bucket_name:
            logger.warning("⚠️ AWS credentials or S3 bucket name not fully set. Using local storage fallback.")
            self.s3_client = None
            self.use_local_storage = True
            self.local_storage_path = "local_ml_storage"
            os.makedirs(self.local_storage_path, exist_ok=True)
        else:
            try:
                self.s3_client = boto3.client(
                    "s3",
                    aws_access_key_id=self.aws_access_key_id,
                    aws_secret_access_key=self.aws_secret_access_key,
                    region_name=self.aws_region
                )
                self.use_local_storage = False
                logger.info("✅ S3 client initialized successfully")
            except Exception as e:
                logger.error(f"❌ Failed to initialize S3 client: {e}")
                self.s3_client = None
                self.use_local_storage = True
                self.local_storage_path = "local_ml_storage"
                os.makedirs(self.local_storage_path, exist_ok=True)

    def _get_local_path(self, key):
        """Obtenir le chemin local pour un fichier."""
        return os.path.join(self.local_storage_path, key.replace('/', '_'))

    def save_model(self, model, filename):
        """Sauvegarder un modèle (S3 ou local)."""
        try:
            if self.use_local_storage:
                return self._save_model_local(model, filename)
            else:
                return self._save_model_s3(model, filename)
        except Exception as e:
            logger.error(f"❌ Erreur lors de la sauvegarde du modèle {filename}: {e}")
            # Fallback vers le stockage local
            return self._save_model_local(model, filename)

    def _save_model_local(self, model, filename):
        """Sauvegarder un modèle localement."""
        local_path = self._get_local_path(filename)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        joblib.dump(model, local_path)
        logger.info(f"💾 Modèle sauvegardé localement: {local_path}")
        return f"local://{local_path}"

    def _save_model_s3(self, model, filename):
        """Sauvegarder un modèle sur S3."""
        buffer = io.BytesIO()
        joblib.dump(model, buffer)
        buffer.seek(0)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        s3_key = f"enhanced_ml_models/{filename}_{timestamp}.joblib"
        
        self.s3_client.upload_fileobj(
            buffer, 
            self.bucket_name, 
            s3_key,
            ExtraArgs={"ContentType": "application/octet-stream"}
        )
        logger.info(f"☁️ Modèle uploadé vers S3: s3://{self.bucket_name}/{s3_key}")
        return f"s3://{self.bucket_name}/{s3_key}"

    def load_model(self, path_or_filename):
        """Charger un modèle (S3 ou local)."""
        try:
            if path_or_filename.startswith("s3://"):
                return self._load_model_s3(path_or_filename)
            elif path_or_filename.startswith("local://"):
                return self._load_model_local(path_or_filename.replace("local://", ""))
            else:
                # Essayer de charger depuis le stockage par défaut
                if self.use_local_storage:
                    return self._load_model_local(self._get_local_path(path_or_filename))
                else:
                    return self._load_model_s3(f"s3://{self.bucket_name}/enhanced_ml_models/{path_or_filename}")
        except Exception as e:
            logger.error(f"❌ Erreur lors du chargement du modèle {path_or_filename}: {e}")
            return None

    def _load_model_local(self, local_path):
        """Charger un modèle depuis le stockage local."""
        if os.path.exists(local_path):
            model = joblib.load(local_path)
            logger.info(f"📂 Modèle chargé localement: {local_path}")
            return model
        else:
            logger.error(f"❌ Fichier local non trouvé: {local_path}")
            return None

    def _load_model_s3(self, s3_path):
        """Charger un modèle depuis S3."""
        s3_key = s3_path.replace(f"s3://{self.bucket_name}/", "")
        
        buffer = io.BytesIO()
        self.s3_client.download_fileobj(self.bucket_name, s3_key, buffer)
        buffer.seek(0)
        
        model = joblib.load(buffer)
        logger.info(f"☁️ Modèle téléchargé depuis S3: {s3_path}")
        return model

    def save_object(self, obj, filename):
        """Sauvegarder un objet Python (pickle)."""
        try:
            if self.use_local_storage:
                return self._save_object_local(obj, filename)
            else:
                return self._save_object_s3(obj, filename)
        except Exception as e:
            logger.error(f"❌ Erreur lors de la sauvegarde de l'objet {filename}: {e}")
            return self._save_object_local(obj, filename)

    def _save_object_local(self, obj, filename):
        """Sauvegarder un objet localement."""
        local_path = self._get_local_path(filename)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        with open(local_path, 'wb') as f:
            pickle.dump(obj, f)
        logger.info(f"💾 Objet sauvegardé localement: {local_path}")
        return f"local://{local_path}"

    def _save_object_s3(self, obj, filename):
        """Sauvegarder un objet sur S3."""
        buffer = io.BytesIO()
        pickle.dump(obj, buffer)
        buffer.seek(0)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        s3_key = f"enhanced_ml_objects/{filename}_{timestamp}.pickle"
        
        self.s3_client.upload_fileobj(buffer, self.bucket_name, s3_key)
        logger.info(f"☁️ Objet uploadé vers S3: s3://{self.bucket_name}/{s3_key}")
        return f"s3://{self.bucket_name}/{s3_key}"

    def load_object(self, path_or_filename):
        """Charger un objet Python."""
        try:
            if path_or_filename.startswith("s3://"):
                return self._load_object_s3(path_or_filename)
            elif path_or_filename.startswith("local://"):
                return self._load_object_local(path_or_filename.replace("local://", ""))
            else:
                # Essayer de charger depuis le stockage par défaut
                if self.use_local_storage:
                    return self._load_object_local(self._get_local_path(path_or_filename))
                else:
                    return self._load_object_s3(f"s3://{self.bucket_name}/enhanced_ml_objects/{path_or_filename}")
        except Exception as e:
            logger.error(f"❌ Erreur lors du chargement de l'objet {path_or_filename}: {e}")
            return None

    def _load_object_local(self, local_path):
        """Charger un objet depuis le stockage local."""
        if os.path.exists(local_path):
            with open(local_path, 'rb') as f:
                obj = pickle.load(f)
            logger.info(f"📂 Objet chargé localement: {local_path}")
            return obj
        else:
            logger.error(f"❌ Fichier local non trouvé: {local_path}")
            return None

    def _load_object_s3(self, s3_path):
        """Charger un objet depuis S3."""
        s3_key = s3_path.replace(f"s3://{self.bucket_name}/", "")
        
        buffer = io.BytesIO()
        self.s3_client.download_fileobj(self.bucket_name, s3_key, buffer)
        buffer.seek(0)
        
        obj = pickle.load(buffer)
        logger.info(f"☁️ Objet téléchargé depuis S3: {s3_path}")
        return obj

    def upload_ml_model(self, model, model_name, model_type):
        """Uploader un modèle ML avec métadonnées."""
        filename = f"{model_type}/{model_name}.joblib"
        return self.save_model(model, filename)

    def download_ml_model(self, s3_path):
        """Télécharger un modèle ML."""
        return self.load_model(s3_path)

    def upload_scaler(self, scaler, scaler_name):
        """Uploader un scaler."""
        filename = f"scalers/{scaler_name}.joblib"
        return self.save_model(scaler, filename)

    def download_scaler(self, s3_path):
        """Télécharger un scaler."""
        return self.load_model(s3_path)

    def list_models(self, model_type=None):
        """Lister les modèles disponibles."""
        try:
            if self.use_local_storage:
                return self._list_models_local(model_type)
            else:
                return self._list_models_s3(model_type)
        except Exception as e:
            logger.error(f"❌ Erreur lors du listage des modèles: {e}")
            return []

    def _list_models_local(self, model_type=None):
        """Lister les modèles locaux."""
        models = []
        search_path = self.local_storage_path
        
        if model_type:
            search_path = os.path.join(search_path, f"enhanced_ml_models_{model_type}")
        
        if os.path.exists(search_path):
            for root, dirs, files in os.walk(search_path):
                for file in files:
                    if file.endswith('.joblib'):
                        full_path = os.path.join(root, file)
                        stat = os.stat(full_path)
                        models.append({
                            "key": os.path.relpath(full_path, self.local_storage_path),
                            "size": stat.st_size,
                            "last_modified": datetime.fromtimestamp(stat.st_mtime),
                            "s3_path": f"local://{full_path}"
                        })
        
        logger.info(f"📂 Listé {len(models)} modèles locaux")
        return models

    def _list_models_s3(self, model_type=None):
        """Lister les modèles S3."""
        prefix = f"enhanced_ml_models/{model_type}/" if model_type else "enhanced_ml_models/"
        
        response = self.s3_client.list_objects_v2(
            Bucket=self.bucket_name,
            Prefix=prefix
        )
        
        models = []
        for obj in response.get("Contents", []):
            models.append({
                "key": obj["Key"],
                "size": obj["Size"],
                "last_modified": obj["LastModified"],
                "s3_path": f"s3://{self.bucket_name}/{obj['Key']}"
            })
        
        logger.info(f"☁️ Listé {len(models)} modèles dans S3 sous le préfixe {prefix}")
        return models

    def cleanup_old_models(self, keep_latest=5):
        """Nettoyer les anciens modèles (garder seulement les plus récents)."""
        try:
            models = self.list_models()
            if len(models) <= keep_latest:
                return
            
            # Trier par date de modification (plus récent en premier)
            models.sort(key=lambda x: x['last_modified'], reverse=True)
            
            # Supprimer les anciens modèles
            models_to_delete = models[keep_latest:]
            
            for model in models_to_delete:
                try:
                    if self.use_local_storage:
                        local_path = model['s3_path'].replace('local://', '')
                        if os.path.exists(local_path):
                            os.remove(local_path)
                            logger.info(f"🗑️ Modèle local supprimé: {local_path}")
                    else:
                        s3_key = model['key']
                        self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
                        logger.info(f"🗑️ Modèle S3 supprimé: {s3_key}")
                except Exception as e:
                    logger.error(f"❌ Erreur lors de la suppression de {model['key']}: {e}")
            
            logger.info(f"🧹 Nettoyage terminé: {len(models_to_delete)} anciens modèles supprimés")
            
        except Exception as e:
            logger.error(f"❌ Erreur lors du nettoyage: {e}")

    def get_storage_info(self):
        """Obtenir des informations sur le stockage utilisé."""
        info = {
            "storage_type": "local" if self.use_local_storage else "s3",
            "bucket_name": self.bucket_name if not self.use_local_storage else None,
            "local_path": self.local_storage_path if self.use_local_storage else None,
            "models_count": len(self.list_models()),
            "status": "active"
        }
        
        if self.use_local_storage:
            # Calculer la taille du stockage local
            total_size = 0
            if os.path.exists(self.local_storage_path):
                for root, dirs, files in os.walk(self.local_storage_path):
                    for file in files:
                        total_size += os.path.getsize(os.path.join(root, file))
            info["storage_size_mb"] = total_size / (1024 * 1024)
        
        return info

if __name__ == "__main__":
    # Test du gestionnaire S3 amélioré
    manager = EnhancedS3StorageManager()
    
    print("Informations de stockage:")
    info = manager.get_storage_info()
    for key, value in info.items():
        print(f"  {key}: {value}")
    
    # Test de sauvegarde/chargement
    test_data = {"test": "data", "timestamp": datetime.now().isoformat()}
    
    # Sauvegarder
    path = manager.save_object(test_data, "test_object.pickle")
    print(f"Objet sauvegardé: {path}")
    
    # Charger
    loaded_data = manager.load_object("test_object.pickle")
    print(f"Objet chargé: {loaded_data}")
    
    # Lister les modèles
    models = manager.list_models()
    print(f"Modèles trouvés: {len(models)}")

