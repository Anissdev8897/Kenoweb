#!/usr/bin/env python3
"""
Script de re-entraînement du modèle Keno Analyzer Pro
Supporte l'entraînement complet et incrémental
"""

import os
import sys
import logging
import argparse
from datetime import datetime
import json
import pickle
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('model_training.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ModelTrainer:
    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(__file__), 'data')
        self.models_dir = os.path.join(os.path.dirname(__file__), 'models')
        self.ensure_directories()
        
    def ensure_directories(self):
        """S'assurer que les répertoires existent"""
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.models_dir, exist_ok=True)
    
    def load_data(self):
        """Charger les données d'entraînement"""
        try:
            # Charger les données historiques
            csv_path = os.path.join(self.data_dir, 'keno_data.csv')
            if not os.path.exists(csv_path):
                logger.error(f"Fichier CSV non trouvé: {csv_path}")
                return None
            
            df = pd.read_csv(csv_path)
            logger.info(f"Données chargées: {len(df)} lignes")
            return df
            
        except Exception as e:
            logger.error(f"Erreur chargement données: {e}")
            return None
    
    def prepare_features(self, df):
        """Préparer les features pour l'entraînement"""
        try:
            # Extraire les numéros des tirages
            numbers = []
            for _, row in df.iterrows():
                nums = []
                for i in range(1, 21):
                    col_name = f'numero_{i}'
                    if col_name in row and pd.notna(row[col_name]):
                        nums.append(int(row[col_name]))
                numbers.append(nums)
            
            # Créer les features
            features = []
            targets = []
            
            for i in range(10, len(numbers)):
                # Features: statistiques des 10 derniers tirages
                recent_numbers = numbers[i-10:i]
                
                # Fréquence de chaque numéro
                freq_features = [0] * 70
                for draw in recent_numbers:
                    for num in draw:
                        if 1 <= num <= 70:
                            freq_features[num-1] += 1
                
                # Moyennes et écarts types
                all_recent = [num for draw in recent_numbers for num in draw]
                if all_recent:
                    mean_num = np.mean(all_recent)
                    std_num = np.std(all_recent)
                    min_num = np.min(all_recent)
                    max_num = np.max(all_recent)
                else:
                    mean_num = std_num = min_num = max_num = 0
                
                # Features combinées
                feature_vector = freq_features + [mean_num, std_num, min_num, max_num]
                features.append(feature_vector)
                
                # Target: prédire si un numéro apparaîtra (simplifié)
                next_draw = numbers[i]
                target = [1 if j+1 in next_draw else 0 for j in range(70)]
                targets.append(target)
            
            return np.array(features), np.array(targets)
            
        except Exception as e:
            logger.error(f"Erreur préparation features: {e}")
            return None, None
    
    def train_model(self, X, y, model_type='full'):
        """Entraîner le modèle"""
        try:
            logger.info(f"Début entraînement {model_type}")
            
            # Séparer les données
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Créer et entraîner le modèle
            model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
            
            model.fit(X_train, y_train)
            
            # Évaluer le modèle
            y_pred = model.predict(X_test)
            accuracy = accuracy_score(y_test.flatten(), y_pred.flatten())
            
            logger.info(f"Précision du modèle: {accuracy:.4f}")
            
            # Sauvegarder le modèle
            model_path = os.path.join(self.models_dir, 'keno_model.pkl')
            with open(model_path, 'wb') as f:
                pickle.dump(model, f)
            
            logger.info(f"Modèle sauvegardé: {model_path}")
            
            # Sauvegarder les métriques
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'model_type': model_type,
                'accuracy': accuracy,
                'samples': len(X_train),
                'features': X_train.shape[1]
            }
            
            metrics_path = os.path.join(self.models_dir, 'training_metrics.json')
            with open(metrics_path, 'w') as f:
                json.dump(metrics, f, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur entraînement modèle: {e}")
            return False
    
    def incremental_training(self):
        """Entraînement incrémental avec nouvelles données"""
        try:
            logger.info("Début entraînement incrémental")
            
            # Charger le modèle existant
            model_path = os.path.join(self.models_dir, 'keno_model.pkl')
            if not os.path.exists(model_path):
                logger.info("Aucun modèle existant, passage en entraînement complet")
                return self.full_training()
            
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
            
            # Charger les nouvelles données
            df = self.load_data()
            if df is None:
                return False
            
            # Préparer les features
            X, y = self.prepare_features(df)
            if X is None or y is None:
                return False
            
            # Entraînement incrémental (ré-entraînement complet pour simplifier)
            return self.train_model(X, y, 'incremental')
            
        except Exception as e:
            logger.error(f"Erreur entraînement incrémental: {e}")
            return False
    
    def full_training(self):
        """Entraînement complet du modèle"""
        try:
            logger.info("Début entraînement complet")
            
            # Charger les données
            df = self.load_data()
            if df is None:
                return False
            
            # Préparer les features
            X, y = self.prepare_features(df)
            if X is None or y is None:
                return False
            
            # Entraîner le modèle
            return self.train_model(X, y, 'full')
            
        except Exception as e:
            logger.error(f"Erreur entraînement complet: {e}")
            return False

def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(description='Script de re-entraînement Keno')
    parser.add_argument('--full', action='store_true', help='Entraînement complet')
    parser.add_argument('--incremental', action='store_true', help='Entraînement incrémental')
    
    args = parser.parse_args()
    
    trainer = ModelTrainer()
    
    if args.full:
        success = trainer.full_training()
    elif args.incremental:
        success = trainer.incremental_training()
    else:
        # Par défaut: entraînement complet
        success = trainer.full_training()
    
    if success:
        logger.info("Entraînement terminé avec succès")
        sys.exit(0)
    else:
        logger.error("Échec de l'entraînement")
        sys.exit(1)

if __name__ == '__main__':
    main()
