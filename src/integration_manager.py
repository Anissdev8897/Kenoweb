#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestionnaire d'intégration pour fusionner les prédictions ML et utilisateurs
Coordination entre tous les composants du système
"""

import logging
import threading
import time
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np
import os
from enhanced_database_manager import EnhancedDatabaseManagerV2, get_enhanced_database_manager
from enhanced_s3_manager import EnhancedS3StorageManager
from enhanced_ml_trainer import EnhancedMLTrainerV2

# Configuration du logger
logger = logging.getLogger(__name__)

# Vérification de la variable d'environnement DATABASE_URL
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    logger.error("La variable d'environnement DATABASE_URL est requise")
    raise ValueError("La variable d'environnement DATABASE_URL est requise pour se connecter à la base de données")

class KenoIntegrationManager:
    """Gestionnaire principal pour l'intégration complète du système Keno"""
    
    def __init__(self):
        # Composants principaux
        self.db_manager = get_enhanced_database_manager()
        self.s3_manager = EnhancedS3StorageManager()
        self.ml_trainer = None
        
        # État du système
        self.is_initialized = False
        self.auto_update_enabled = True
        self.update_thread = None
        
        # Configuration
        self.config = {
            'auto_retrain_interval_hours': 24,  # Réentraîner toutes les 24h
            'prediction_update_interval_minutes': 60,  # Nouvelles prédictions toutes les heures
            'performance_check_interval_minutes': 30,  # Vérifier les performances toutes les 30min
        }
        
        # Initialiser le système
        self._initialize_system()
    
    def _initialize_system(self):
        """Initialiser complètement le système intégré."""
        try:
            logger.info("🚀 Initialisation du système Keno intégré...")
            
            # Vérifier la base de données
            self._check_database_health()
            
            # Initialiser l'entraîneur ML
            self._initialize_ml_trainer()
            
            # Démarrer les processus automatiques
            self._start_automatic_processes()
            
            self.is_initialized = True
            logger.info("✅ Système Keno intégré initialisé avec succès!")
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'initialisation du système: {e}")
            self.is_initialized = False
    
    def _check_database_health(self):
        """Vérifier l'état de la base de données."""
        try:
            # Vérifier la connectivité
            tirages_count = len(self.db_manager.get_official_tirages_for_training())
            logger.info(f"📊 Base de données: {tirages_count} tirages disponibles")
            
            # Vérifier les tables
            leaderboard = self.db_manager.get_unified_predictions_leaderboard(limit=1)
            logger.info(f"🏆 Système de prédictions: {len(leaderboard)} entrées dans le leaderboard")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Problème avec la base de données: {e}")
            return False
    
    def _initialize_ml_trainer(self):
        """Initialiser l'entraîneur ML."""
        try:
            logger.info("🤖 Initialisation de l'entraîneur ML...")
            
            self.ml_trainer = EnhancedMLTrainerV2()
            
            # Essayer de charger des modèles existants
            if not self.ml_trainer.load_trained_models():
                logger.info("🔄 Aucun modèle existant, lancement de l'entraînement initial...")
                success = self.ml_trainer.train_enhanced_models()
                if not success:
                    logger.error("❌ Échec de l'entraînement initial")
                    return False
            
            # Générer des prédictions initiales
            self.ml_trainer.generate_predictions_for_next_tirage()
            
            logger.info("✅ Entraîneur ML initialisé")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'initialisation ML: {e}")
            return False
    
    def _start_automatic_processes(self):
        """Démarrer les processus automatiques."""
        if self.update_thread is None or not self.update_thread.is_alive():
            self.update_thread = threading.Thread(target=self._automatic_update_worker, daemon=True)
            self.update_thread.start()
            logger.info("🔄 Processus automatiques démarrés")
    
    def _automatic_update_worker(self):
        """Worker pour les mises à jour automatiques."""
        last_retrain = datetime.now()
        last_prediction_update = datetime.now()
        last_performance_check = datetime.now()
        
        while self.auto_update_enabled:
            try:
                current_time = datetime.now()
                
                # Vérification des performances
                if (current_time - last_performance_check).total_seconds() >= self.config['performance_check_interval_minutes'] * 60:
                    self._check_system_performance()
                    last_performance_check = current_time
                
                # Mise à jour des prédictions
                if (current_time - last_prediction_update).total_seconds() >= self.config['prediction_update_interval_minutes'] * 60:
                    self._update_predictions()
                    last_prediction_update = current_time
                
                # Réentraînement périodique
                if (current_time - last_retrain).total_seconds() >= self.config['auto_retrain_interval_hours'] * 3600:
                    self._periodic_retrain()
                    last_retrain = current_time
                
                # Attendre 5 minutes avant la prochaine vérification
                time.sleep(300)
                
            except Exception as e:
                logger.error(f"❌ Erreur dans le worker automatique: {e}")
                time.sleep(300)  # Attendre avant de réessayer
    
    def _check_system_performance(self):
        """Vérifier les performances du système."""
        try:
            if not self.ml_trainer:
                return
            
            # Évaluer les performances des modèles ML
            performance = self.ml_trainer.evaluate_model_performance()
            
            if performance:
                ml_perf = performance.get('ml_performance', [])
                user_perf = performance.get('user_performance', [])
                
                logger.info(f"📊 Performance ML: {len(ml_perf)} modèles actifs")
                logger.info(f"📊 Performance utilisateurs: {len(user_perf)} méthodes actives")
                
                # Vérifier si un réentraînement est nécessaire
                if ml_perf:
                    avg_ml_accuracy = np.mean([p['average_accuracy'] for p in ml_perf])
                    if avg_ml_accuracy < 30:  # Seuil de performance minimum
                        logger.warning("⚠️ Performance ML faible, réentraînement recommandé")
                        self._trigger_retrain("PERFORMANCE_LOW")
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la vérification des performances: {e}")
    
    def _update_predictions(self):
        """Mettre à jour les prédictions ML."""
        try:
            if self.ml_trainer and self.ml_trainer.is_trained:
                success = self.ml_trainer.generate_predictions_for_next_tirage()
                if success:
                    logger.info("🔮 Prédictions ML mises à jour")
                else:
                    logger.warning("⚠️ Échec de la mise à jour des prédictions ML")
        except Exception as e:
            logger.error(f"❌ Erreur lors de la mise à jour des prédictions: {e}")
    
    def _periodic_retrain(self):
        """Réentraînement périodique des modèles."""
        try:
            logger.info("🔄 Réentraînement périodique des modèles ML...")
            
            if self.ml_trainer:
                success = self.ml_trainer.train_enhanced_models(force_retrain=True)
                if success:
                    logger.info("✅ Réentraînement périodique terminé")
                else:
                    logger.error("❌ Échec du réentraînement périodique")
        except Exception as e:
            logger.error(f"❌ Erreur lors du réentraînement périodique: {e}")
    
    def _trigger_retrain(self, trigger_reason):
        """Déclencher un réentraînement pour une raison spécifique."""
        try:
            logger.info(f"🔄 Réentraînement déclenché: {trigger_reason}")
            
            if self.ml_trainer:
                # Lancer le réentraînement en arrière-plan
                def retrain():
                    self.ml_trainer.train_enhanced_models(force_retrain=True)
                
                retrain_thread = threading.Thread(target=retrain, daemon=True)
                retrain_thread.start()
        except Exception as e:
            logger.error(f"❌ Erreur lors du déclenchement du réentraînement: {e}")
    
    def add_new_tirage(self, tirage_data):
        """Ajouter un nouveau tirage et déclencher les mises à jour."""
        try:
            logger.info(f"📥 Nouveau tirage reçu: {tirage_data.get('date_tirage')}")
            
            # Insérer le tirage (cela évalue automatiquement les prédictions)
            self.db_manager.insert_new_tirage(tirage_data)
            
            # Générer de nouvelles prédictions ML
            if self.ml_trainer:
                self.ml_trainer.generate_predictions_for_next_tirage()
            
            # Vérifier si un réentraînement est nécessaire
            # (par exemple, tous les 50 nouveaux tirages)
            tirages_count = len(self.db_manager.get_official_tirages_for_training())
            if tirages_count % 50 == 0:
                self._trigger_retrain("NEW_TIRAGE_MILESTONE")
            
            logger.info("✅ Nouveau tirage traité avec succès")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'ajout du nouveau tirage: {e}")
            return False
    
    def get_system_status(self):
        """Obtenir le statut complet du système."""
        try:
            status = {
                'system_initialized': self.is_initialized,
                'auto_update_enabled': self.auto_update_enabled,
                'database_status': 'connected',
                'ml_trainer_status': 'not_initialized',
                'storage_info': self.s3_manager.get_storage_info(),
                'last_update': datetime.now().isoformat()
            }
            
            # Statut de la base de données
            try:
                tirages_count = len(self.db_manager.get_official_tirages_for_training())
                status['database_tirages_count'] = tirages_count
            except:
                status['database_status'] = 'error'
            
            # Statut ML
            if self.ml_trainer:
                if self.ml_trainer.is_trained:
                    status['ml_trainer_status'] = 'trained'
                    status['ml_summary'] = self.ml_trainer.get_training_summary()
                else:
                    status['ml_trainer_status'] = 'not_trained'
            
            # Performances récentes
            try:
                leaderboard = self.db_manager.get_unified_predictions_leaderboard(limit=10)
                status['active_predictors'] = len(leaderboard)
                
                performance_stats = self.db_manager.get_method_performance_comparison()
                ml_methods = performance_stats[performance_stats['predictor_type'] == 'ML_MODEL']
                user_methods = performance_stats[performance_stats['predictor_type'] == 'USER']
                
                status['ml_methods_count'] = len(ml_methods)
                status['user_methods_count'] = len(user_methods)
                
                if len(ml_methods) > 0:
                    status['avg_ml_accuracy'] = float(ml_methods['average_accuracy'].mean())
                if len(user_methods) > 0:
                    status['avg_user_accuracy'] = float(user_methods['average_accuracy'].mean())
                    
            except Exception as e:
                logger.error(f"Erreur lors de la récupération des performances: {e}")
            
            return status
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la récupération du statut: {e}")
            return {'error': str(e)}
    
    def force_full_retrain(self):
        """Forcer un réentraînement complet du système."""
        try:
            logger.info("🔄 Réentraînement complet forcé...")
            
            if self.ml_trainer:
                success = self.ml_trainer.train_enhanced_models(force_retrain=True)
                if success:
                    logger.info("✅ Réentraînement complet terminé")
                    return True
                else:
                    logger.error("❌ Échec du réentraînement complet")
                    return False
            else:
                logger.error("❌ Entraîneur ML non disponible")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erreur lors du réentraînement complet: {e}")
            return False
    
    def get_unified_dashboard_data(self):
        """Récupérer toutes les données pour le tableau de bord unifié."""
        try:
            dashboard_data = {
                'system_status': self.get_system_status(),
                'leaderboard': [],
                'recent_predictions': [],
                'performance_stats': {'ml_methods': [], 'user_methods': []},
                'ml_summary': {}
            }
            
            # Leaderboard unifié
            leaderboard_df = self.db_manager.get_unified_predictions_leaderboard()
            dashboard_data['leaderboard'] = leaderboard_df.to_dict('records') if not leaderboard_df.empty else []
            
            # Prédictions récentes
            predictions_df = self.db_manager.get_recent_predictions_for_display()
            dashboard_data['recent_predictions'] = predictions_df.to_dict('records') if not predictions_df.empty else []
            
            # Statistiques de performance
            performance_df = self.db_manager.get_method_performance_comparison()
            if not performance_df.empty:
                ml_methods = performance_df[performance_df['predictor_type'] == 'ML_MODEL']
                user_methods = performance_df[performance_df['predictor_type'] == 'USER']
                
                dashboard_data['performance_stats'] = {
                    'ml_methods': ml_methods.to_dict('records'),
                    'user_methods': user_methods.to_dict('records')
                }
            
            # Résumé ML
            if self.ml_trainer:
                dashboard_data['ml_summary'] = self.ml_trainer.get_training_summary()
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la récupération des données du tableau de bord: {e}")
            return {
                'system_status': {'error': str(e)},
                'leaderboard': [],
                'recent_predictions': [],
                'performance_stats': {'ml_methods': [], 'user_methods': []},
                'ml_summary': {}
            }
    
    def stop_automatic_processes(self):
        """Arrêter tous les processus automatiques."""
        self.auto_update_enabled = False
        if self.ml_trainer:
            self.ml_trainer.stop_auto_retrain()
        logger.info("⏹️ Processus automatiques arrêtés")
    
    def __del__(self):
        """Nettoyage lors de la destruction de l'objet."""
        self.stop_automatic_processes()

# Instance globale du gestionnaire d'intégration
integration_manager = None

def get_integration_manager():
    """Obtenir l'instance globale du gestionnaire d'intégration."""
    global integration_manager
    if integration_manager is None:
        integration_manager = KenoIntegrationManager()
    return integration_manager

if __name__ == "__main__":
    # Test du gestionnaire d'intégration
    manager = KenoIntegrationManager()
    
    print("Statut du système:")
    status = manager.get_system_status()
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    print("\nDonnées du tableau de bord:")
    dashboard = manager.get_unified_dashboard_data()
    print(f"  Leaderboard: {len(dashboard['leaderboard'])} entrées")
    print(f"  Prédictions récentes: {len(dashboard['recent_predictions'])} entrées")
    print(f"  Méthodes ML: {len(dashboard['performance_stats']['ml_methods'])}")
    print(f"  Méthodes utilisateur: {len(dashboard['performance_stats']['user_methods'])}")
    
    # Garder le programme en vie pour tester les processus automatiques
    try:
        print("\nProcessus automatiques en cours... (Ctrl+C pour arrêter)")
        while True:
            time.sleep(60)
            print(f"Système actif - {datetime.now()}")
    except KeyboardInterrupt:
        print("\nArrêt du système...")
        manager.stop_automatic_processes()

