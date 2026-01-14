import boto3
import joblib
import os
import logging

# Configuration du logger
logger = logging.getLogger(__name__)

class S3StorageManager:
    def __init__(self):
        self.aws_access_key_id = os.environ.get("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
        self.aws_region = os.environ.get("AWS_REGION", "us-east-1")
        self.bucket_name = os.environ.get("S3_BUCKET_NAME")

        if not self.aws_access_key_id or not self.aws_secret_access_key or not self.bucket_name:
            logger.warning("AWS credentials or S3 bucket name not fully set. S3 operations might fail.")
            self.s3_client = None
        else:
            self.s3_client = boto3.client(
                "s3",
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.aws_region
            )

    def _check_s3_client(self):
        if not self.s3_client:
            raise ConnectionError("S3 client not initialized. AWS credentials or S3 bucket name might be missing.")

    def upload_ml_model(self, model, model_name, model_type):
        """Uploader un modèle ML vers S3"""
        self._check_s3_client()
        buffer = io.BytesIO()
        joblib.dump(model, buffer)
        buffer.seek(0)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        s3_key = f"ml_models/{model_type}/{model_name}_{timestamp}.joblib"
        
        self.s3_client.upload_fileobj(
            buffer, 
            self.bucket_name, 
            s3_key,
            ExtraArgs={"ContentType": "application/octet-stream"}
        )
        logger.info(f"Modèle {model_name} uploadé vers S3: s3://{self.bucket_name}/{s3_key}")
        return f"s3://{self.bucket_name}/{s3_key}"

    def download_ml_model(self, s3_path):
        """Télécharger un modèle ML depuis S3"""
        self._check_s3_client()
        s3_key = s3_path.replace(f"s3://{self.bucket_name}/", "")
        
        buffer = io.BytesIO()
        self.s3_client.download_fileobj(self.bucket_name, s3_key, buffer)
        buffer.seek(0)
        
        model = joblib.load(buffer)
        logger.info(f"Modèle téléchargé depuis S3: {s3_path}")
        return model

    def upload_scaler(self, scaler, scaler_name):
        """Uploader un scaler vers S3"""
        self._check_s3_client()
        buffer = io.BytesIO()
        joblib.dump(scaler, buffer)
        buffer.seek(0)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        s3_key = f"scalers/{scaler_name}_{timestamp}.joblib"
        
        self.s3_client.upload_fileobj(buffer, self.bucket_name, s3_key)
        logger.info(f"Scaler {scaler_name} uploadé vers S3: s3://{self.bucket_name}/{s3_key}")
        return f"s3://{self.bucket_name}/{s3_key}"

    def download_scaler(self, s3_path):
        """Télécharger un scaler depuis S3"""
        self._check_s3_client()
        s3_key = s3_path.replace(f"s3://{self.bucket_name}/", "")
        
        buffer = io.BytesIO()
        self.s3_client.download_fileobj(self.bucket_name, s3_key, buffer)
        buffer.seek(0)
        
        scaler = joblib.load(buffer)
        logger.info(f"Scaler téléchargé depuis S3: {s3_path}")
        return scaler

    def list_models(self, model_type=None):
        """Lister les modèles disponibles sur S3"""
        self._check_s3_client()
        prefix = f"ml_models/{model_type}/" if model_type else "ml_models/"
        
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
                "s3_path": f"s3://{self.bucket_name}/{obj["Key"]}"
            })
        logger.info(f"Listé {len(models)} modèles dans S3 sous le préfixe {prefix}")
        return models


