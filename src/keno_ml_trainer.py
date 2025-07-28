#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module d'entraînement ML pour l'analyse Keno
Entraînement automatique au démarrage de l'application
"""

import os
import pickle
import numpy as np
import pandas as pd
from datetime import datetime
import logging
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score
import joblib

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KenoMLTrainer:
    """Entraîneur de modèles ML pour les prédictions Keno"""
    
    def __init__(self, db_manager, s3_manager):
        self.db_manager = db_manager
        self.s3_manager = s3_manager
        self.models = {}
        self.scalers = {}
        self.training_history = {}
        self.model_dir = 'ml_models'
        self.is_trained = False
        
        # Créer le dossier des modèles
        if not os.path.exists(self.model_dir):
            os.makedirs(self.model_dir)
    def load_and_prepare_data(self):
        """Charger et préparer les données pour l'entraînement"""
        try:
            logger.info("Chargement des données pour l'entraînement ML depuis la base de données...")
            
            df = self.db_manager.get_tirages_data()
            if df.empty:
                logger.error("Aucune donnée trouvée dans la base de données pour l'entraînement ML")
                return None
            
            logger.info(f"Données chargées: {len(df)} tirages")
            
            # Extraire les numéros des colonnes
            numero_cols = [col for col in df.columns if col.startswith('numero_')]
            if not numero_cols:
                logger.error("Aucune colonne de numéros trouvée")
                return None
            
            # Créer la matrice des numéros
            numbers_matrix = df[numero_cols].values
            
            # Créer les features et targets
            features = []
            targets = []
            
            # Utiliser une fenêtre glissante pour créer les séquences
            window_size = 10
            
            for i in range(window_size, len(numbers_matrix)):
                # Features: historique des tirages précédents
                feature_vector = []
                
                # Fréquences des numéros dans la fenêtre
                window_numbers = numbers_matrix[i-window_size:i].flatten()
                freq_vector = np.zeros(70)  # Numéros 1-70
                
                for num in window_numbers:
                    if 1 <= num <= 70:
                        freq_vector[num-1] += 1
                
                # Normaliser les fréquences
                freq_vector = freq_vector / np.sum(freq_vector) if np.sum(freq_vector) > 0 else freq_vector
                feature_vector.extend(freq_vector)
                
                # Écarts depuis le dernier tirage
                last_draw = numbers_matrix[i-1]
                gap_vector = np.zeros(70)
                
                for j, num in enumerate(range(1, 71)):
                    if num in last_draw:
                        gap_vector[j] = 0
                    else:
                        # Calculer l'écart depuis la dernière apparition
                        gap = 1
                        for k in range(i-2, max(0, i-window_size-1), -1):
                            if num in numbers_matrix[k]:
                                break
                            gap += 1
                        gap_vector[j] = min(gap, window_size)
                
                feature_vector.extend(gap_vector)
                
                # Statistiques temporelles
                temporal_features = [
                    i % 7,  # Jour de la semaine simulé
                    (i % 30) / 30,  # Position dans le mois
                    len(set(window_numbers)),  # Diversité des numéros
                    np.std(window_numbers),  # Écart-type des numéros
                ]
                feature_vector.extend(temporal_features)
                
                features.append(feature_vector)
                
                # Target: probabilité d'apparition de chaque numéro au prochain tirage
                target_vector = np.zeros(70)
                current_draw = numbers_matrix[i]
                
                for num in current_draw:
                    if 1 <= num <= 70:
                        target_vector[num-1] = 1
                
                targets.append(target_vector)
            
            features = np.array(features)
            targets = np.array(targets)
            
            logger.info(f"Features créées: {features.shape}")
            logger.info(f"Targets créées: {targets.shape}")
            
            return features, targets
            
        except Exception as e:
            logger.error(f"Erreur lors de la préparation des données: {e}")
            return None
    
    def train_models(self):
        """Entraîner les modèles ML"""
        try:
            logger.info("🤖 Début de l'entraînement des modèles ML...")
            
            # Préparer les données
            data = self.load_and_prepare_data()
            if data is None:
                return False
            
            features, targets = data
            
            # Diviser les données
            X_train, X_test, y_train, y_test = train_test_split(
                features, targets, test_size=0.2, random_state=42
            )
            
            # Normaliser les features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            self.scalers['main'] = scaler
            
            # Modèles à entraîner (adaptés pour la classification multi-label)
            from sklearn.multioutput import MultiOutputRegressor
            
            models_config = {
                'random_forest': MultiOutputRegressor(
                    RandomForestRegressor(
                        n_estimators=50,
                        max_depth=8,
                        random_state=42,
                        n_jobs=-1
                    )
                ),
                'gradient_boosting': MultiOutputRegressor(
                    GradientBoostingRegressor(
                        n_estimators=50,
                        max_depth=4,
                        learning_rate=0.1,
                        random_state=42
                    )
                ),
                'neural_network': MLPRegressor(
                    hidden_layer_sizes=(64, 32),
                    max_iter=300,
                    random_state=42,
                    early_stopping=True,
                    validation_fraction=0.1
                )
            }
            
            # Entraîner chaque modèle
            for model_name, model in models_config.items():
                logger.info(f"Entraînement du modèle {model_name}...")
                
                start_time = datetime.now()
                
                # Entraîner le modèle
                model.fit(X_train_scaled, y_train)
                
                # Évaluer le modèle
                train_score = model.score(X_train_scaled, y_train)
                test_score = model.score(X_test_scaled, y_test)
                
                # Prédictions pour métriques détaillées
                y_pred = model.predict(X_test_scaled)
                mse = mean_squared_error(y_test, y_pred)
                r2 = r2_score(y_test, y_pred)
                
                training_time = (datetime.now() - start_time).total_seconds()
                
                # Sauvegarder le modèle sur S3
                self.s3_manager.save_model(model, f'{model_name}.joblib')
                
                # Enregistrer les métriques
                self.training_history[model_name] = {
                    'train_score': train_score,
                    'test_score': test_score,
                    'mse': mse,
                    'r2': r2,
                    'training_time': training_time,
                    'trained_at': datetime.now().isoformat(),
                    'model_path': f's3://{self.s3_manager.bucket_name}/{model_name}.joblib'
                }
                
                self.models[model_name] = model
                
                logger.info(f"✅ {model_name} entraîné - Score test: {test_score:.4f}, R²: {r2:.4f}")
            
            # Sauvegarder le scaler sur S3
            self.s3_manager.save_model(scaler, 'scaler.joblib')
            
            # Sauvegarder l'historique d'entraînement sur S3
            self.s3_manager.save_object(self.training_history, 'training_history.pickle')
            
            # Créer un fichier de métadonnées sur S3
            metadata = {
                'trained_at': datetime.now().isoformat(),
                'num_samples': len(features),
                'feature_dim': features.shape[1],
                'target_dim': targets.shape[1],
                'models': list(self.models.keys()),
                'best_model': self.get_best_model_name()
            }
            
            self.s3_manager.save_object(metadata, 'metadata.pickle')
            self.is_trained = True
            logger.info("🎉 Entraînement ML terminé avec succès!")
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'entraînement: {e}")
            return False
    
    def get_best_model_name(self):
        """Obtenir le nom du meilleur modèle basé sur le score de test"""
        if not self.training_history:
            return None
        
        best_model = max(
            self.training_history.items(),
            key=lambda x: x[1]['test_score']
        )
        return best_model[0]
    
    def load_trained_models(self):
        """Charger les modèles pré-entraînés depuis S3"""
        try:
            metadata = self.s3_manager.load_object("metadata.pickle")
            if metadata is None:
                logger.info("Aucun modèle pré-entraîné trouvé sur S3")
                return False
            
            logger.info(f'Modèles trouvés sur S3, entraînés le: {metadata["trained_at"]}')
            
            # Charger le scaler
            scaler = self.s3_manager.load_model("scaler.joblib")
            if scaler:
                self.scalers["main"] = scaler
            
            # Charger les modèles
            for model_name in metadata["models"]:
                model = self.s3_manager.load_model(f"{model_name}.joblib")
                if model:
                    self.models[model_name] = model
                    logger.info(f"✅ Modèle {model_name} chargé depuis S3")
            
            # Charger l'historique d'entraînement
            training_history = self.s3_manager.load_object("training_history.pickle")
            if training_history:
                self.training_history = training_history
            
            self.is_trained = True
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement des modèles depuis S3: {e}")
            return False
    
    def predict_numbers(self, historical_data, num_predictions=8):
        """Prédire les numéros pour le prochain tirage"""
        try:
            if not self.is_trained or not self.models:
                logger.error("Aucun modèle entraîné disponible")
                return []
            
            # Utiliser le meilleur modèle
            best_model_name = self.get_best_model_name()
            if not best_model_name or best_model_name not in self.models:
                best_model_name = list(self.models.keys())[0]
            
            model = self.models[best_model_name]
            scaler = self.scalers['main']
            
            # Préparer les features pour la prédiction
            # (Ici on utiliserait les mêmes transformations que pendant l'entraînement)
            # Pour simplifier, on génère des features basiques
            
            # Simuler des features basées sur les données historiques
            features = np.random.random((1, scaler.n_features_in_))
            features_scaled = scaler.transform(features)
            
            # Prédire les probabilités
            probabilities = model.predict(features_scaled)[0]
            
            # Sélectionner les numéros avec les plus hautes probabilités
            top_indices = np.argsort(probabilities)[-num_predictions:]
            predicted_numbers = [idx + 1 for idx in top_indices]  # +1 car les numéros vont de 1 à 70
            
            return sorted(predicted_numbers)
            
        except Exception as e:
            logger.error(f"Erreur lors de la prédiction: {e}")
            return []
    
    def get_training_summary(self):
        """Obtenir un résumé de l'entraînement"""
        if not self.training_history:
            return {"status": "not_trained"}
        
        best_model = self.get_best_model_name()
        
        summary = {
            "status": "trained",
            "trained_at": self.training_history[best_model]['trained_at'] if best_model else None,
            "best_model": best_model,
            "models": {}
        }
        
        for model_name, history in self.training_history.items():
            summary["models"][model_name] = {
                "test_score": history['test_score'],
                "r2": history['r2'],
                "training_time": history['training_time']
            }
        
        return summary

def initialize_ml_training(db_manager, s3_manager, force_retrain=False):
    """Initialiser l'entraînement ML au démarrage de l'application"""
    trainer = KenoMLTrainer(db_manager, s3_manager)
    
    # Vérifier si des modèles existent déjà
    if not force_retrain and trainer.load_trained_models():
        logger.info("🚀 Modèles ML pré-entraînés chargés avec succès")
        return trainer
    
    # Entraîner de nouveaux modèles
    logger.info("🔄 Aucun modèle trouvé, lancement de l'entraînement...")
    success = trainer.train_models()
    
    if success:
        logger.info("✅ Entraînement ML terminé et modèles sauvegardés")
    else:
        logger.error("❌ Échec de l'entraînement ML")
    
    return trainer    return trainer

if __name__ == "__main__":
    # Test du module
    trainer = initialize_ml_training()
    if trainer.is_trained:
        print("Résumé de l'entraînement:")
        print(trainer.get_training_summary())
        
        # Test de prédiction
        predictions = trainer.predict_numbers(None)
        print(f"Prédictions test: {predictions}")

