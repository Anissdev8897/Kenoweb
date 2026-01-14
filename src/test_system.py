#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test et validation du système Keno intégré
Tests unitaires et d'intégration pour tous les composants
"""

import unittest
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
import tempfile
import shutil
import logging

# Vérification de la variable d'environnement DATABASE_URL
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    raise ValueError("La variable d'environnement DATABASE_URL est requise pour exécuter les tests")

# Ajouter le répertoire src au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import des modules à tester
from enhanced_database_manager import EnhancedDatabaseManager
from enhanced_s3_manager import EnhancedS3StorageManager
from enhanced_ml_trainer import EnhancedKenoMLTrainer
from integration_manager import KenoIntegrationManager

# Configuration du logging pour les tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestEnhancedDatabaseManager(unittest.TestCase):
    """Tests pour le gestionnaire de base de données amélioré"""
    
    def setUp(self):
        """Configuration avant chaque test"""
        # Utiliser une base de données de test en mémoire
        os.environ['DATABASE_URL'] = 'sqlite:///test_keno.db'
        self.db_manager = EnhancedDatabaseManager()
    
    def tearDown(self):
        """Nettoyage après chaque test"""
        # Supprimer la base de données de test
        if os.path.exists('test_keno.db'):
            os.remove('test_keno.db')
    
    def test_database_initialization(self):
        """Test de l'initialisation de la base de données"""
        self.assertIsNotNone(self.db_manager)
        self.assertIsNotNone(self.db_manager.engine)
    
    def test_save_user_prediction(self):
        """Test de sauvegarde des prédictions utilisateur"""
        prediction_id = self.db_manager.save_user_prediction(
            user_id="test_user",
            session_id="test_session",
            method_name="Test Method",
            predicted_numbers=[1, 2, 3, 4, 5, 6, 7, 8],
            target_date=date.today()
        )
        
        self.assertIsNotNone(prediction_id)
        self.assertIsInstance(prediction_id, int)
    
    def test_save_ml_prediction(self):
        """Test de sauvegarde des prédictions ML"""
        prediction_id = self.db_manager.save_ml_prediction(
            model_name="test_model",
            method_name="Test ML Method",
            predicted_numbers=[10, 20, 30, 40, 50, 60, 70, 8],
            target_date=date.today(),
            confidence_score=0.75
        )
        
        self.assertIsNotNone(prediction_id)
        self.assertIsInstance(prediction_id, int)
    
    def test_evaluate_predictions(self):
        """Test d'évaluation des prédictions"""
        # Créer une prédiction de test
        prediction_id = self.db_manager.save_user_prediction(
            user_id="test_user",
            session_id="test_session",
            method_name="Test Method",
            predicted_numbers=[1, 2, 3, 4, 5, 6, 7, 8],
            target_date=date.today()
        )
        
        # Évaluer avec des résultats simulés
        actual_numbers = [1, 2, 3, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31]
        
        self.db_manager.evaluate_predictions_for_tirage(
            tirage_date=date.today(),
            tirage_time=None,
            actual_numbers=actual_numbers
        )
        
        # Vérifier que l'évaluation a été effectuée
        leaderboard = self.db_manager.get_unified_predictions_leaderboard()
        self.assertGreater(len(leaderboard), 0)

class TestEnhancedS3Manager(unittest.TestCase):
    """Tests pour le gestionnaire S3 amélioré"""
    
    def setUp(self):
        """Configuration avant chaque test"""
        # Forcer l'utilisation du stockage local pour les tests
        self.s3_manager = EnhancedS3StorageManager()
        self.s3_manager.use_local_storage = True
        self.s3_manager.local_storage_path = tempfile.mkdtemp()
    
    def tearDown(self):
        """Nettoyage après chaque test"""
        # Supprimer le répertoire de test
        if os.path.exists(self.s3_manager.local_storage_path):
            shutil.rmtree(self.s3_manager.local_storage_path)
    
    def test_save_and_load_object(self):
        """Test de sauvegarde et chargement d'objets"""
        test_data = {"test": "data", "numbers": [1, 2, 3]}
        
        # Sauvegarder
        path = self.s3_manager.save_object(test_data, "test_object.pickle")
        self.assertIsNotNone(path)
        
        # Charger
        loaded_data = self.s3_manager.load_object("test_object.pickle")
        self.assertEqual(test_data, loaded_data)
    
    def test_save_and_load_model(self):
        """Test de sauvegarde et chargement de modèles"""
        # Créer un modèle simple pour le test
        from sklearn.linear_model import LinearRegression
        model = LinearRegression()
        
        # Sauvegarder
        path = self.s3_manager.save_model(model, "test_model.joblib")
        self.assertIsNotNone(path)
        
        # Charger
        loaded_model = self.s3_manager.load_model("test_model.joblib")
        self.assertIsNotNone(loaded_model)
        self.assertEqual(type(model), type(loaded_model))
    
    def test_list_models(self):
        """Test de listage des modèles"""
        # Sauvegarder quelques modèles de test
        from sklearn.linear_model import LinearRegression
        model = LinearRegression()
        
        self.s3_manager.save_model(model, "model1.joblib")
        self.s3_manager.save_model(model, "model2.joblib")
        
        # Lister les modèles
        models = self.s3_manager.list_models()
        self.assertGreaterEqual(len(models), 2)

class TestMLTrainer(unittest.TestCase):
    """Tests pour l'entraîneur ML amélioré"""
    
    def setUp(self):
        """Configuration avant chaque test"""
        # Créer des gestionnaires de test
        os.environ['DATABASE_URL'] = 'sqlite:///test_ml_keno.db'
        self.db_manager = EnhancedDatabaseManager()
        
        self.s3_manager = EnhancedS3StorageManager()
        self.s3_manager.use_local_storage = True
        self.s3_manager.local_storage_path = tempfile.mkdtemp()
        
        # Créer des données de test
        self._create_test_data()
        
        self.ml_trainer = EnhancedKenoMLTrainer(self.db_manager, self.s3_manager)
    
    def tearDown(self):
        """Nettoyage après chaque test"""
        if os.path.exists('test_ml_keno.db'):
            os.remove('test_ml_keno.db')
        if os.path.exists(self.s3_manager.local_storage_path):
            shutil.rmtree(self.s3_manager.local_storage_path)
    
    def _create_test_data(self):
        """Créer des données de test dans la base de données"""
        # Générer des tirages de test
        np.random.seed(42)  # Pour la reproductibilité
        
        for i in range(100):  # 100 tirages de test
            # Générer 20 numéros aléatoires entre 1 et 70
            numbers = np.random.choice(range(1, 71), size=20, replace=False)
            numbers.sort()
            
            tirage_data = {
                'date_tirage': date.today() - timedelta(days=100-i),
                'heure_tirage': '20:00:00'
            }
            
            # Ajouter les numéros
            for j, num in enumerate(numbers, 1):
                tirage_data[f'numero_{j}'] = int(num)
            
            # Ajouter des champs optionnels
            tirage_data['multiplicateur'] = np.random.randint(2, 11)
            tirage_data['joker'] = f"J{np.random.randint(100000, 999999)}"
            
            self.db_manager.insert_new_tirage(tirage_data)
    
    def test_load_training_data(self):
        """Test de chargement des données d'entraînement"""
        data = self.ml_trainer.load_official_training_data()
        
        self.assertIsNotNone(data)
        self.assertIn('numbers_matrix', data)
        self.assertIn('dates', data)
        self.assertIn('dataframe', data)
        
        # Vérifier que nous avons bien nos 100 tirages de test
        self.assertEqual(len(data['dataframe']), 100)
        self.assertEqual(data['numbers_matrix'].shape, (100, 20))
    
    def test_create_training_features(self):
        """Test de création des features d'entraînement"""
        data = self.ml_trainer.load_official_training_data()
        features, targets = self.ml_trainer.create_training_features(
            data['numbers_matrix'], 
            data['dates']
        )
        
        self.assertIsNotNone(features)
        self.assertIsNotNone(targets)
        
        # Vérifier les dimensions
        self.assertEqual(features.shape[0], targets.shape[0])
        self.assertEqual(targets.shape[1], 70)  # 70 numéros possibles
    
    def test_training_summary(self):
        """Test du résumé d'entraînement"""
        summary = self.ml_trainer.get_training_summary()
        
        self.assertIsInstance(summary, dict)
        self.assertIn('status', summary)

class TestIntegrationManager(unittest.TestCase):
    """Tests pour le gestionnaire d'intégration"""
    
    def setUp(self):
        """Configuration avant chaque test"""
        # Désactiver les processus automatiques pour les tests
        os.environ['DATABASE_URL'] = 'sqlite:///test_integration_keno.db'
        self.integration_manager = KenoIntegrationManager()
        self.integration_manager.auto_update_enabled = False
    
    def tearDown(self):
        """Nettoyage après chaque test"""
        self.integration_manager.stop_automatic_processes()
        if os.path.exists('test_integration_keno.db'):
            os.remove('test_integration_keno.db')
    
    def test_system_initialization(self):
        """Test de l'initialisation du système"""
        self.assertIsNotNone(self.integration_manager.db_manager)
        self.assertIsNotNone(self.integration_manager.s3_manager)
    
    def test_system_status(self):
        """Test de récupération du statut système"""
        status = self.integration_manager.get_system_status()
        
        self.assertIsInstance(status, dict)
        self.assertIn('system_initialized', status)
        self.assertIn('database_status', status)
        self.assertIn('storage_info', status)

class TestSystemIntegration(unittest.TestCase):
    """Tests d'intégration complète du système"""
    
    def setUp(self):
        """Configuration avant chaque test"""
        os.environ['DATABASE_URL'] = 'sqlite:///test_full_integration.db'
        
        # Créer tous les composants
        self.db_manager = EnhancedDatabaseManager()
        
        self.s3_manager = EnhancedS3StorageManager()
        self.s3_manager.use_local_storage = True
        self.s3_manager.local_storage_path = tempfile.mkdtemp()
        
        # Créer des données de test
        self._create_comprehensive_test_data()
    
    def tearDown(self):
        """Nettoyage après chaque test"""
        if os.path.exists('test_full_integration.db'):
            os.remove('test_full_integration.db')
        if os.path.exists(self.s3_manager.local_storage_path):
            shutil.rmtree(self.s3_manager.local_storage_path)
    
    def _create_comprehensive_test_data(self):
        """Créer un jeu de données complet pour les tests"""
        np.random.seed(42)
        
        # Créer 50 tirages de test
        for i in range(50):
            numbers = np.random.choice(range(1, 71), size=20, replace=False)
            numbers.sort()
            
            tirage_data = {
                'date_tirage': date.today() - timedelta(days=50-i),
                'heure_tirage': '20:00:00'
            }
            
            for j, num in enumerate(numbers, 1):
                tirage_data[f'numero_{j}'] = int(num)
            
            tirage_data['multiplicateur'] = np.random.randint(2, 11)
            tirage_data['joker'] = f"J{np.random.randint(100000, 999999)}"
            
            self.db_manager.insert_new_tirage(tirage_data)
        
        # Créer quelques prédictions de test
        for i in range(10):
            # Prédiction utilisateur
            self.db_manager.save_user_prediction(
                user_id=f"test_user_{i}",
                session_id=f"session_{i}",
                method_name="Test Method",
                predicted_numbers=list(np.random.choice(range(1, 71), size=8, replace=False)),
                target_date=date.today() + timedelta(days=1)
            )
            
            # Prédiction ML
            self.db_manager.save_ml_prediction(
                model_name=f"test_model_{i}",
                method_name="Test ML Method",
                predicted_numbers=list(np.random.choice(range(1, 71), size=8, replace=False)),
                target_date=date.today() + timedelta(days=1),
                confidence_score=np.random.random()
            )
    
    def test_full_workflow(self):
        """Test du workflow complet du système"""
        # 1. Vérifier que les données sont bien chargées
        tirages = self.db_manager.get_official_tirages_for_training()
        self.assertEqual(len(tirages), 50)
        
        # 2. Vérifier le leaderboard
        leaderboard = self.db_manager.get_unified_predictions_leaderboard()
        self.assertGreater(len(leaderboard), 0)
        
        # 3. Vérifier les statistiques de performance
        stats = self.db_manager.get_method_performance_comparison()
        self.assertIsInstance(stats, pd.DataFrame)
        
        # 4. Tester l'ajout d'un nouveau tirage
        new_tirage = {
            'date_tirage': date.today(),
            'heure_tirage': '20:00:00',
            'multiplicateur': 5,
            'joker': 'J123456'
        }
        
        # Ajouter les numéros
        numbers = np.random.choice(range(1, 71), size=20, replace=False)
        for i, num in enumerate(numbers, 1):
            new_tirage[f'numero_{i}'] = int(num)
        
        # Insérer le tirage (cela devrait évaluer les prédictions)
        self.db_manager.insert_new_tirage(new_tirage)
        
        # Vérifier que les prédictions ont été évaluées
        recent_predictions = self.db_manager.get_recent_predictions_for_display()
        evaluated_predictions = [p for p in recent_predictions.to_dict('records') if p.get('is_evaluated')]
        self.assertGreater(len(evaluated_predictions), 0)

def run_performance_tests():
    """Exécuter des tests de performance"""
    logger.info("🚀 Début des tests de performance...")
    
    # Test de performance de la base de données
    start_time = datetime.now()
    
    os.environ['DATABASE_URL'] = 'sqlite:///test_performance.db'
    db_manager = EnhancedDatabaseManager()
    
    # Insérer 1000 tirages
    np.random.seed(42)
    for i in range(1000):
        numbers = np.random.choice(range(1, 71), size=20, replace=False)
        tirage_data = {
            'date_tirage': date.today() - timedelta(days=1000-i),
            'heure_tirage': '20:00:00'
        }
        
        for j, num in enumerate(numbers, 1):
            tirage_data[f'numero_{j}'] = int(num)
        
        tirage_data['multiplicateur'] = np.random.randint(2, 11)
        tirage_data['joker'] = f"J{np.random.randint(100000, 999999)}"
        
        db_manager.insert_new_tirage(tirage_data)
    
    insert_time = (datetime.now() - start_time).total_seconds()
    logger.info(f"⏱️ Insertion de 1000 tirages: {insert_time:.2f} secondes")
    
    # Test de performance de lecture
    start_time = datetime.now()
    tirages = db_manager.get_official_tirages_for_training()
    read_time = (datetime.now() - start_time).total_seconds()
    logger.info(f"⏱️ Lecture de {len(tirages)} tirages: {read_time:.2f} secondes")
    
    # Nettoyage
    if os.path.exists('test_performance.db'):
        os.remove('test_performance.db')
    
    logger.info("✅ Tests de performance terminés")

def main():
    """Fonction principale pour exécuter tous les tests"""
    logger.info("🧪 Début des tests du système Keno intégré...")
    
    # Créer une suite de tests
    test_suite = unittest.TestSuite()
    
    # Ajouter les tests
    test_suite.addTest(unittest.makeSuite(TestEnhancedDatabaseManager))
    test_suite.addTest(unittest.makeSuite(TestEnhancedS3Manager))
    test_suite.addTest(unittest.makeSuite(TestMLTrainer))
    test_suite.addTest(unittest.makeSuite(TestIntegrationManager))
    test_suite.addTest(unittest.makeSuite(TestSystemIntegration))
    
    # Exécuter les tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Afficher les résultats
    logger.info(f"\n📊 Résultats des tests:")
    logger.info(f"   Tests exécutés: {result.testsRun}")
    logger.info(f"   Échecs: {len(result.failures)}")
    logger.info(f"   Erreurs: {len(result.errors)}")
    
    if result.failures:
        logger.error("❌ Échecs détectés:")
        for test, traceback in result.failures:
            logger.error(f"   {test}: {traceback}")
    
    if result.errors:
        logger.error("❌ Erreurs détectées:")
        for test, traceback in result.errors:
            logger.error(f"   {test}: {traceback}")
    
    # Tests de performance
    run_performance_tests()
    
    # Résultat final
    if result.wasSuccessful():
        logger.info("✅ Tous les tests ont réussi!")
        return True
    else:
        logger.error("❌ Certains tests ont échoué!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

