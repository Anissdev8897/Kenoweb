#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Entraîneur ML amélioré v2 avec analyse des erreurs utilisateurs
Analyse comparative des performances entre modèles ML et utilisateurs
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
import joblib
import logging
from datetime import datetime, timedelta
import os
import json
from enhanced_database_manager import EnhancedDatabaseManagerV2

logger = logging.getLogger(__name__)

# Vérification de la variable d'environnement DATABASE_URL
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    logger.error("La variable d'environnement DATABASE_URL n'est pas définie")
    raise ValueError("La variable d'environnement DATABASE_URL est requise pour se connecter à la base de données")

class EnhancedMLTrainerV2:
    def __init__(self):
        self.db_manager = EnhancedDatabaseManagerV2()
        self.models = {}
        self.scalers = {}
        self.training_history = []
        
        # Configuration des modèles
        self.model_configs = {
            'random_forest': {
                'model': RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1),
                'name': 'Random Forest',
                'type': 'ensemble'
            },
            'gradient_boosting': {
                'model': GradientBoostingRegressor(n_estimators=100, random_state=42),
                'name': 'Gradient Boosting',
                'type': 'ensemble'
            },
            'neural_network': {
                'model': MLPRegressor(hidden_layer_sizes=(100, 50), random_state=42, max_iter=500),
                'name': 'Neural Network',
                'type': 'neural'
            }
        }
    
    @staticmethod
    def prepare_ssh_key():
        import stat
        private_key = os.getenv("SSH_PRIVATE_KEY")
        if not private_key:
            logger.error("La variable d'environnement SSH_PRIVATE_KEY est absente.")
            return False

        KEY_PATH = os.path.expanduser("~/.ssh/id_rsa")
        ssh_dir = os.path.dirname(KEY_PATH)
        if not os.path.exists(ssh_dir):
            os.makedirs(ssh_dir, mode=0o700)
            logger.info(f"Création du dossier SSH : {ssh_dir}")

        with open(KEY_PATH, "w") as f:
            f.write(private_key)

        os.chmod(KEY_PATH, stat.S_IRUSR | stat.S_IWUSR)
        logger.info(f"Clé privée SSH écrite dans {KEY_PATH} avec permissions 600")
        return True
    
    def prepare_features(self, tirages_df):
        """Préparer les features pour l'entraînement ML."""
        features = []
        targets = []
        
        # Convertir les tirages en format numérique
        tirage_numbers = []
        for _, row in tirages_df.iterrows():
            numbers = [row[f'numero_{i}'] for i in range(1, 21)]
            tirage_numbers.append(sorted(numbers))
        
        # Créer des features basées sur l'historique
        for i in range(5, len(tirage_numbers)):  # Utiliser les 5 derniers tirages comme features
            # Features: statistiques des 5 derniers tirages
            recent_tirages = tirage_numbers[i-5:i]
            
            # Fréquences des numéros dans les 5 derniers tirages
            freq_features = np.zeros(70)
            for tirage in recent_tirages:
                for num in tirage:
                    freq_features[num-1] += 1
            
            # Écarts depuis la dernière apparition
            gap_features = np.zeros(70)
            for num in range(1, 71):
                last_seen = -1
                for j, tirage in enumerate(reversed(recent_tirages)):
                    if num in tirage:
                        last_seen = j
                        break
                gap_features[num-1] = last_seen if last_seen != -1 else 5
            
            # Statistiques globales
            all_numbers = [num for tirage in recent_tirages for num in tirage]
            stats_features = [
                np.mean(all_numbers),
                np.std(all_numbers),
                np.min(all_numbers),
                np.max(all_numbers),
                len(set(all_numbers))  # Nombre de numéros uniques
            ]
            
            # Combiner toutes les features
            feature_vector = np.concatenate([freq_features, gap_features, stats_features])
            features.append(feature_vector)
            
            # Target: le prochain tirage
            targets.append(tirage_numbers[i])
        
        return np.array(features), targets

    def train_models(self, start_date=None, end_date=None, retrain_trigger="MANUAL"):
        """Entraîner tous les modèles ML."""
        training_start = datetime.now()
        
        # Récupérer les données d'entraînement
        tirages_df = self.db_manager.get_official_tirages_for_training(start_date, end_date)
        
        if len(tirages_df) < 10:
            raise ValueError("Pas assez de données pour l'entraînement (minimum 10 tirages)")
        
        logger.info(f"Entraînement sur {len(tirages_df)} tirages")
        
        # Préparer les features
        X, y = self.prepare_features(tirages_df)
        
        if len(X) == 0:
            raise ValueError("Aucune feature générée pour l'entraînement")
        
        # Diviser les données
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Normaliser les features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        training_results = {}
        
        # Entraîner chaque modèle
        for model_key, config in self.model_configs.items():
            logger.info(f"Entraînement du modèle {config['name']}")
            
            try:
                # Adapter les targets pour la régression (prédire les positions moyennes)
                y_train_adapted = [np.mean(tirage) for tirage in y_train]
                y_test_adapted = [np.mean(tirage) for tirage in y_test]
                
                # Entraîner le modèle
                model = config['model']
                model.fit(X_train_scaled, y_train_adapted)
                
                # Évaluer le modèle
                train_score = model.score(X_train_scaled, y_train_adapted)
                test_score = model.score(X_test_scaled, y_test_adapted)
                
                # Prédictions pour calcul des métriques
                y_pred = model.predict(X_test_scaled)
                mse = mean_squared_error(y_test_adapted, y_pred)
                mae = mean_absolute_error(y_test_adapted, y_pred)
                r2 = r2_score(y_test_adapted, y_pred)
                
                # Cross-validation
                cv_scores = cross_val_score(model, X_train_scaled, y_train_adapted, cv=5)
                
                # Sauvegarder le modèle et le scaler en binaire
                model_binary = joblib.dumps(model)
                scaler_binary = joblib.dumps(scaler)
                
                # Métriques d'entraînement
                training_metrics = {
                    'train_score': float(train_score),
                    'test_score': float(test_score),
                    'mse': float(mse),
                    'mae': float(mae),
                    'r2_score': float(r2),
                    'cv_mean': float(cv_scores.mean()),
                    'cv_std': float(cv_scores.std()),
                    'training_samples': len(X_train),
                    'test_samples': len(X_test),
                    'features_count': X_train.shape[1]
                }
                
                # Sauvegarder dans la base de données
                with self.db_manager.engine.connect() as conn:
                    conn.execute(self.db_manager.engine.text("""
                        INSERT INTO ml_models (
                            model_name, model_type, method_name, model_binary,
                            training_score, test_score, r2_score, trained_at, is_active, metadata
                        ) VALUES (
                            :model_name, :model_type, :method_name, :model_binary,
                            :training_score, :test_score, :r2_score, :trained_at, :is_active, :metadata
                        )
                    """), {
                        "model_name": model_key,
                        "model_type": config['type'],
                        "method_name": config['name'],
                        "model_binary": model_binary, # MODIFICATION AJOUTÉE
                        "training_score": train_score,
                        "test_score": test_score,
                        "r2_score": r2,
                        "trained_at": training_start,
                        "is_active": True,
                        "metadata": json.dumps({
                            'scaler_binary': scaler_binary.decode('latin1'), # Encodage pour JSONB
                            'training_metrics': training_metrics
                        })
                    })
                    conn.commit()
                
                # Stocker en mémoire pour utilisation immédiate
                self.models[model_key] = model
                self.scalers[model_key] = scaler
                
                training_results[model_key] = training_metrics
                logger.info(f"Modèle {config['name']} entraîné avec succès (R²: {r2:.4f})")
                
            except Exception as e:
                logger.error(f"Erreur lors de l'entraînement du modèle {config['name']}: {str(e)}")
                continue
        
        training_end = datetime.now()
        training_time = (training_end - training_start).total_seconds()
        
        # Enregistrer l'historique d'entraînement
        self.db_manager.save_ml_training_record(
            model_name="ensemble_models",
            training_start=training_start,
            training_end=training_end,
            data_start_date=tirages_df['date_tirage'].min(),
            data_end_date=tirages_df['date_tirage'].max(),
            total_tirages=len(tirages_df),
            training_metrics=training_results,
            retrain_trigger=retrain_trigger
        )
        
        logger.info(f"Entraînement terminé en {training_time:.2f} secondes")
        return training_results

    def predict_next_numbers(self, model_key, num_numbers=8, target_date=None):
        """Générer des prédictions pour le prochain tirage."""
        if model_key not in self.models:
            # Charger le modèle depuis la base de données si nécessaire
            self.load_model_from_db(model_key)
        
        if model_key not in self.models:
            raise ValueError(f"Modèle {model_key} non disponible")
        
        model = self.models[model_key]
        scaler = self.scalers[model_key]
        
        # Récupérer les derniers tirages pour créer les features
        recent_tirages = self.db_manager.get_official_tirages_for_training()
        recent_tirages = recent_tirages.tail(5)  # 5 derniers tirages
        
        if len(recent_tirages) < 5:
            raise ValueError("Pas assez de tirages récents pour la prédiction")
        
        # Préparer les features comme lors de l'entraînement
        tirage_numbers = []
        for _, row in recent_tirages.iterrows():
            numbers = [row[f'numero_{i}'] for i in range(1, 21)]
            tirage_numbers.append(sorted(numbers))
        
        # Créer les features
        freq_features = np.zeros(70)
        for tirage in tirage_numbers:
            for num in tirage:
                freq_features[num-1] += 1
        
        gap_features = np.zeros(70)
        for num in range(1, 71):
            last_seen = -1
            for j, tirage in enumerate(reversed(tirage_numbers)):
                if num in tirage:
                    last_seen = j
                    break
            gap_features[num-1] = last_seen if last_seen != -1 else 5
        
        all_numbers = [num for tirage in tirage_numbers for num in tirage]
        stats_features = [
            np.mean(all_numbers),
            np.std(all_numbers),
            np.min(all_numbers),
            np.max(all_numbers),
            len(set(all_numbers))
        ]
        
        feature_vector = np.concatenate([freq_features, gap_features, stats_features])
        feature_vector = feature_vector.reshape(1, -1)
        
        # Normaliser
        feature_vector_scaled = scaler.transform(feature_vector)
        
        # Prédire
        prediction = model.predict(feature_vector_scaled)[0]
        
        # Convertir la prédiction en numéros (stratégie hybride)
        # Combiner prédiction ML avec analyse statistique
        predicted_numbers = self._convert_prediction_to_numbers(
            prediction, freq_features, gap_features, num_numbers
        )
        
        # Calculer un score de confiance
        confidence_score = self._calculate_confidence_score(model, feature_vector_scaled)
        
        # Sauvegarder la prédiction
        if target_date is None:
            target_date = datetime.now().date() + timedelta(days=1)
        
        method_name = self.model_configs[model_key]['name']
        prediction_id = self.db_manager.save_ml_prediction(
            model_name=model_key,
            method_name=method_name,
            predicted_numbers=predicted_numbers,
            target_date=target_date,
            confidence_score=confidence_score
        )
        
        return {
            'predicted_numbers': predicted_numbers,
            'confidence_score': confidence_score,
            'prediction_id': prediction_id,
            'method_name': method_name,
            'model_key': model_key
        }

    def load_model_from_db(self, model_key):
        """
        Charge un modèle et son scaler depuis la base de données.
        """
        try:
            with self.db_manager.engine.connect() as conn:
                result = conn.execute(self.db_manager.engine.text("""
                    SELECT model_binary, metadata FROM ml_models
                    WHERE model_name = :model_key AND is_active = TRUE
                    ORDER BY trained_at DESC
                    LIMIT 1
                """), {"model_key": model_key})
                
                row = result.fetchone()
                if row:
                    model_binary = row[0]
                    metadata = json.loads(row[1])
                    scaler_binary = metadata.get("scaler_binary").encode("latin1") # Ré-encoder
                    
                    self.models[model_key] = joblib.loads(model_binary)
                    self.scalers[model_key] = joblib.loads(scaler_binary)
                    logger.info(f"Modèle {model_key} et scaler chargés depuis la base de données.")
                else:
                    logger.warning(f"Aucun modèle actif trouvé pour {model_key} dans la base de données.")
        except Exception as e:
            logger.error(f"Erreur lors du chargement du modèle {model_key} depuis la base de données: {str(e)}")

    def _convert_prediction_to_numbers(self, prediction, freq_features, gap_features, num_numbers):
        """Convertir la prédiction numérique en numéros de Keno."""
        # Stratégie hybride : combiner ML avec analyse statistique
        
        # 1. Numéros basés sur les fréquences (favoriser les numéros chauds)
        freq_scores = freq_features / np.sum(freq_features) if np.sum(freq_features) > 0 else np.ones(70) / 70
        
        # 2. Numéros basés sur les écarts (favoriser les numéros dus)
        gap_scores = (5 - gap_features) / 5  # Inverser les écarts
        gap_scores = np.clip(gap_scores, 0, 1)
        
        # 3. Combiner avec la prédiction ML (utiliser comme biais)
        ml_bias = np.ones(70)
        center = int(prediction)
        if 1 <= center <= 70:
            # Créer une distribution gaussienne centrée sur la prédiction
            for i in range(70):
                distance = abs((i + 1) - center)
                ml_bias[i] = np.exp(-distance / 10)  # Décroissance exponentielle
        
        # 4. Score final combiné
        combined_scores = (freq_scores * 0.3 + gap_scores * 0.3 + ml_bias * 0.4)
        
        # 5. Ajouter de la randomisation pour éviter les prédictions trop prévisibles
        noise = np.random.normal(0, 0.1, 70)
        combined_scores += noise
        
        # 6. Sélectionner les meilleurs numéros
        top_indices = np.argsort(combined_scores)[-num_numbers:]
        predicted_numbers = sorted([i + 1 for i in top_indices])
        
        return predicted_numbers

    def _calculate_confidence_score(self, model, feature_vector):
        """Calculer un score de confiance pour la prédiction."""
        try:
            # Pour les modèles qui supportent predict_proba ou decision_function
            if hasattr(model, 'predict_proba'):
                # Pas applicable pour la régression
                pass
            
            # Utiliser la variance des prédictions comme mesure d'incertitude
            if hasattr(model, 'estimators_'):  # Random Forest, Gradient Boosting
                predictions = [estimator.predict(feature_vector)[0] for estimator in model.estimators_[:10]]
                variance = np.var(predictions)
                confidence = 1 / (1 + variance)  # Plus la variance est faible, plus la confiance est élevée
            else:
                # Pour les autres modèles, utiliser une confiance par défaut
                confidence = 0.7
            
            return min(max(confidence, 0.1), 0.95)  # Borner entre 0.1 et 0.95
            
        except Exception:
            return 0.5  # Confiance par défaut

    def load_model_from_s3(self, model_key):
        """Charger un modèle depuis S3."""
        try:
            # Récupérer les informations du modèle depuis la base de données
            with self.db_manager.engine.connect() as conn:
                result = conn.execute(self.db_manager.engine.text("""
                    SELECT s3_path, metadata FROM ml_models 
                    WHERE model_name = :model_name AND is_active = TRUE
                    ORDER BY trained_at DESC LIMIT 1
                """), {"model_name": model_key})
                
                row = result.fetchone()
                if not row:
                    raise ValueError(f"Aucun modèle actif trouvé pour {model_key}")
                
                s3_path, metadata = row
                metadata = json.loads(metadata) if metadata else {}
                scaler_path = metadata.get('scaler_path')
                
                # Télécharger et charger le modèle
                model_local_path = f"/tmp/model_{model_key}.joblib"
                self.s3_manager.download_model(s3_path, model_local_path)
                self.models[model_key] = joblib.load(model_local_path)
                os.remove(model_local_path)
                
                # Télécharger et charger le scaler
                if scaler_path:
                    scaler_local_path = f"/tmp/scaler_{model_key}.joblib"
                    self.s3_manager.download_model(scaler_path, scaler_local_path)
                    self.scalers[model_key] = joblib.load(scaler_local_path)
                    os.remove(scaler_local_path)
                
                logger.info(f"Modèle {model_key} chargé depuis S3")
                
        except Exception as e:
            logger.error(f"Erreur lors du chargement du modèle {model_key}: {str(e)}")
            raise

    def analyze_user_vs_ml_performance(self, days_back=30):
        """Analyser les performances comparatives entre utilisateurs et modèles ML."""
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days_back)
        
        # Récupérer les performances de tous les prédicteurs
        leaderboard = self.db_manager.get_unified_leaderboard(limit=100)
        
        analysis = {
            'ml_models': [],
            'users': [],
            'comparison': {}
        }
        
        # Séparer les modèles ML et les utilisateurs
        for _, row in leaderboard.iterrows():
            predictor_data = {
                'predictor_id': row['predictor_id'],
                'display_name': row['display_name'],
                'total_predictions': row['total_predictions'],
                'total_evaluated': row['total_evaluated'],
                'avg_accuracy': row['avg_accuracy'],
                'best_score': row['best_score'],
                'methods_used': row['methods_used']
            }
            
            if row['predictor_type'] == 'ML_MODEL':
                analysis['ml_models'].append(predictor_data)
            else:
                analysis['users'].append(predictor_data)
        
        # Calculer les statistiques comparatives
        if analysis['ml_models'] and analysis['users']:
            ml_avg_accuracy = np.mean([m['avg_accuracy'] for m in analysis['ml_models']])
            user_avg_accuracy = np.mean([u['avg_accuracy'] for u in analysis['users']])
            
            ml_best_score = max([m['best_score'] for m in analysis['ml_models']])
            user_best_score = max([u['best_score'] for u in analysis['users']])
            
            analysis['comparison'] = {
                'ml_avg_accuracy': ml_avg_accuracy,
                'user_avg_accuracy': user_avg_accuracy,
                'ml_advantage': ml_avg_accuracy - user_avg_accuracy,
                'ml_best_score': ml_best_score,
                'user_best_score': user_best_score,
                'total_ml_predictions': sum([m['total_predictions'] for m in analysis['ml_models']]),
                'total_user_predictions': sum([u['total_predictions'] for u in analysis['users']]),
                'active_users': len(analysis['users']),
                'active_ml_models': len(analysis['ml_models'])
            }
        
        return analysis

    def get_prediction_error_patterns(self, predictor_id=None, predictor_type=None, limit=50):
        """Analyser les patterns d'erreurs de prédiction."""
        query = """
        SELECT 
            pe.predictor_id,
            pe.predictor_type,
            pe.method_name,
            pe.predicted_but_not_drawn,
            pe.drawn_but_not_predicted,
            pe.correct_predictions,
            pe.error_count,
            pe.miss_count,
            pe.tirage_date
        FROM prediction_errors pe
        WHERE 1=1
        """
        params = {"limit": limit}
        
        if predictor_id:
            query += " AND pe.predictor_id = :predictor_id"
            params["predictor_id"] = predictor_id
        
        if predictor_type:
            query += " AND pe.predictor_type = :predictor_type"
            params["predictor_type"] = predictor_type
        
        query += " ORDER BY pe.created_at DESC LIMIT :limit"
        
        return pd.read_sql(query, self.db_manager.engine, params=params)

    def retrain_on_new_data(self):
        """Réentraîner les modèles avec les nouvelles données."""
        logger.info("Démarrage du réentraînement automatique")
        
        try:
            # Vérifier s'il y a de nouvelles données
            with self.db_manager.engine.connect() as conn:
                result = conn.execute(self.db_manager.engine.text("""
                    SELECT COUNT(*) FROM tirages_keno 
                    WHERE created_at > (
                        SELECT MAX(training_end) FROM ml_training_history
                    )
                """))
                new_tirages_count = result.fetchone()[0]
            
            if new_tirages_count > 0:
                logger.info(f"Trouvé {new_tirages_count} nouveaux tirages, réentraînement en cours...")
                training_results = self.train_models(retrain_trigger="NEW_TIRAGE")
                
                # Générer de nouvelles prédictions avec les modèles mis à jour
                for model_key in self.model_configs.keys():
                    try:
                        prediction_result = self.predict_next_numbers(model_key)
                        logger.info(f"Nouvelle prédiction générée pour {model_key}: {prediction_result['predicted_numbers']}")
                    except Exception as e:
                        logger.error(f"Erreur lors de la génération de prédiction pour {model_key}: {str(e)}")
                
                return training_results
            else:
                logger.info("Aucune nouvelle donnée, réentraînement non nécessaire")
                return None
                
        except Exception as e:
            logger.error(f"Erreur lors du réentraînement automatique: {str(e)}")
            raise

    def generate_all_predictions(self, target_date=None, num_numbers=8):
        """Générer des prédictions avec tous les modèles disponibles."""
        predictions = {}
        
        for model_key, config in self.model_configs.items():
            try:
                prediction = self.predict_next_numbers(model_key, num_numbers, target_date)
                predictions[model_key] = prediction
                logger.info(f"Prédiction générée pour {config['name']}: {prediction['predicted_numbers']}")
            except Exception as e:
                logger.error(f"Erreur lors de la génération de prédiction pour {config['name']}: {str(e)}")
                continue
        
        return predictions
