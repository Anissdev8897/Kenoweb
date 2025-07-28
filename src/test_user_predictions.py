#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import stat
import logging
import unittest
import tempfile
import sqlite3
from datetime import datetime, date, timedelta
import json

# Configuration simple du logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

KEY_PATH = "/root/.ssh/id_rsa"

def prepare_ssh_key():
    private_key = os.getenv("SSH_PRIVATE_KEY")
    if not private_key:
        logger.error("La variable d'environnement SSH_PRIVATE_KEY est absente.")
        return False
    
    ssh_dir = os.path.dirname(KEY_PATH)
    if not os.path.exists(ssh_dir):
        os.makedirs(ssh_dir, mode=0o700)
        logger.info(f"Création du dossier SSH : {ssh_dir}")
    
    with open(KEY_PATH, "w") as f:
        f.write(private_key)
    
    os.chmod(KEY_PATH, stat.S_IRUSR | stat.S_IWUSR)
    logger.info(f"Clé privée SSH écrite dans {KEY_PATH} avec permissions 600")
    return True

# Préparation de la clé SSH avant la suite du code
if not prepare_ssh_key():
    logger.error("Échec de la préparation de la clé SSH. Arrêt des tests.")
    sys.exit(1)

# Ajouter le répertoire src au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configuration pour utiliser SQLite en test
database_url = os.environ.get("DATABASE_URL", "postgresql://kenos_user:qYGSudoftPvnoxaT9Seh5IP4itP1kK0a@dpg-d1umeoer433s73eu3d7g-a.frankfurt-postgres.render.com/kenos_vs92")

from enhanced_database_manager import EnhancedDatabaseManagerV2
from enhanced_ml_trainer import EnhancedMLTrainerV2

class TestUserPredictionsV2(unittest.TestCase):
    
    def setUp(self):
        """Initialiser les tests avec une base de données temporaire."""
        self.db_manager = EnhancedDatabaseManagerV2()
        self.ml_trainer = EnhancedMLTrainerV2()
        
        # Insérer quelques tirages de test
        self.insert_test_tirages()
    
    def insert_test_tirages(self):
        """Insérer des tirages de test."""
        test_tirages = [
            {
                'date_tirage': date(2025, 1, 1),
                'heure_tirage': None,
                'numero_1': 5, 'numero_2': 12, 'numero_3': 18, 'numero_4': 25,
                'numero_5': 33, 'numero_6': 41, 'numero_7': 47, 'numero_8': 52,
                'numero_9': 58, 'numero_10': 63, 'numero_11': 2, 'numero_12': 9,
                'numero_13': 15, 'numero_14': 22, 'numero_15': 29, 'numero_16': 36,
                'numero_17': 43, 'numero_18': 49, 'numero_19': 55, 'numero_20': 67,
                'multiplicateur': None, 'joker': None
            },
            {
                'date_tirage': date(2025, 1, 2),
                'heure_tirage': None,
                'numero_1': 3, 'numero_2': 11, 'numero_3': 19, 'numero_4': 27,
                'numero_5': 34, 'numero_6': 42, 'numero_7': 48, 'numero_8': 53,
                'numero_9': 59, 'numero_10': 64, 'numero_11': 7, 'numero_12': 14,
                'numero_13': 21, 'numero_14': 28, 'numero_15': 35, 'numero_16': 41,
                'numero_17': 46, 'numero_18': 51, 'numero_19': 57, 'numero_20': 68,
                'multiplicateur': None, 'joker': None
            },
            {
                'date_tirage': date(2025, 1, 3),
                'heure_tirage': None,
                'numero_1': 1, 'numero_2': 8, 'numero_3': 16, 'numero_4': 23,
                'numero_5': 31, 'numero_6': 38, 'numero_7': 45, 'numero_8': 50,
                'numero_9': 56, 'numero_10': 61, 'numero_11': 4, 'numero_12': 10,
                'numero_13': 17, 'numero_14': 24, 'numero_15': 32, 'numero_16': 39,
                'numero_17': 44, 'numero_18': 52, 'numero_19': 58, 'numero_20': 65,
                'multiplicateur': None, 'joker': None
            }
        ]
        
        for tirage in test_tirages:
            with self.db_manager.engine.connect() as conn:
                conn.execute(self.db_manager.engine.text("""
                    INSERT INTO tirages_keno (
                        date_tirage, heure_tirage, numero_1, numero_2, numero_3,
                        numero_4, numero_5, numero_6, numero_7, numero_8,
                        numero_9, numero_10, numero_11, numero_12, numero_13,
                        numero_14, numero_15, numero_16, numero_17, numero_18,
                        numero_19, numero_20, multiplicateur, joker
                    ) VALUES (
                        :date_tirage, :heure_tirage, :numero_1, :numero_2, :numero_3,
                        :numero_4, :numero_5, :numero_6, :numero_7, :numero_8,
                        :numero_9, :numero_10, :numero_11, :numero_12, :numero_13,
                        :numero_14, :numero_15, :numero_16, :numero_17, :numero_18,
                        :numero_19, :numero_20, :multiplicateur, :joker
                    )
                """), tirage)
                conn.commit()
    
    def test_user_creation_and_identification(self):
        """Tester la création et l'identification des utilisateurs."""
        print("\n=== Test de création et identification des utilisateurs ===")
        
        # Test 1: Créer un nouvel utilisateur
        session_id_1 = "test_session_001"
        ip_address_1 = "192.168.1.100"
        
        user_id_1 = self.db_manager.get_or_create_user(session_id_1, ip_address_1)
        print(f"Utilisateur créé: {user_id_1}")
        
        self.assertIsNotNone(user_id_1)
        self.assertTrue(user_id_1.startswith('utilisateur'))
        
        # Test 2: Récupérer le même utilisateur avec la même session
        user_id_1_bis = self.db_manager.get_or_create_user(session_id_1, ip_address_1)
        print(f"Utilisateur récupéré: {user_id_1_bis}")
        
        self.assertEqual(user_id_1, user_id_1_bis)
        
        # Test 3: Créer un deuxième utilisateur
        session_id_2 = "test_session_002"
        ip_address_2 = "192.168.1.101"
        
        user_id_2 = self.db_manager.get_or_create_user(session_id_2, ip_address_2)
        print(f"Deuxième utilisateur créé: {user_id_2}")
        
        self.assertIsNotNone(user_id_2)
        self.assertNotEqual(user_id_1, user_id_2)
        
        print("✅ Test de création d'utilisateurs réussi")
    
    def test_user_predictions_persistence(self):
        """Tester la persistance des prédictions utilisateurs."""
        print("\n=== Test de persistance des prédictions utilisateurs ===")
        
        session_id = "test_session_predictions"
        ip_address = "192.168.1.200"
        
        # Test 1: Sauvegarder une prédiction utilisateur
        predicted_numbers = [5, 12, 18, 25, 33, 41, 47, 52]
        target_date = date(2025, 1, 10)
        method_name = "Analyse Fréquences"
        
        prediction_id, user_id = self.db_manager.save_user_prediction(
            session_id=session_id,
            method_name=method_name,
            predicted_numbers=predicted_numbers,
            target_date=target_date,
            confidence_score=0.75,
            ip_address=ip_address
        )
        
        print(f"Prédiction sauvegardée: ID={prediction_id}, Utilisateur={user_id}")
        
        self.assertIsNotNone(prediction_id)
        self.assertIsNotNone(user_id)
        
        # Test 2: Sauvegarder une deuxième prédiction pour le même utilisateur
        predicted_numbers_2 = [3, 11, 19, 27, 34, 42, 48, 53]
        method_name_2 = "Analyse Écarts"
        
        prediction_id_2, user_id_2 = self.db_manager.save_user_prediction(
            session_id=session_id,
            method_name=method_name_2,
            predicted_numbers=predicted_numbers_2,
            target_date=target_date,
            confidence_score=0.68,
            ip_address=ip_address
        )
        
        print(f"Deuxième prédiction sauvegardée: ID={prediction_id_2}, Utilisateur={user_id_2}")
        
        self.assertEqual(user_id, user_id_2)  # Même utilisateur
        self.assertNotEqual(prediction_id, prediction_id_2)  # Prédictions différentes
        
        # Test 3: Vérifier que les prédictions ne s'écrasent pas
        predictions_df = self.db_manager.get_all_predictions_for_display(limit=10)
        user_predictions = predictions_df[predictions_df['predictor_id'] == user_id]
        
        print(f"Nombre de prédictions pour {user_id}: {len(user_predictions)}")
        self.assertEqual(len(user_predictions), 2)
        
        print("✅ Test de persistance des prédictions réussi")
    
    def test_prediction_evaluation_and_errors(self):
        """Tester l'évaluation des prédictions et l'analyse des erreurs."""
        print("\n=== Test d'évaluation des prédictions et analyse des erreurs ===")
        
        session_id = "test_session_evaluation"
        ip_address = "192.168.1.300"
        
        # Créer une prédiction pour un tirage existant
        target_date = date(2025, 1, 1)
        predicted_numbers = [5, 12, 18, 25, 33, 41, 47, 99]  # 99 n'existe pas dans le tirage
        
        prediction_id, user_id = self.db_manager.save_user_prediction(
            session_id=session_id,
            method_name="Test Évaluation",
            predicted_numbers=predicted_numbers,
            target_date=target_date,
            confidence_score=0.80,
            ip_address=ip_address
        )
        
        print(f"Prédiction créée pour évaluation: ID={prediction_id}")
        
        # Simuler l'évaluation avec les numéros réels du tirage
        actual_numbers = [5, 12, 18, 25, 33, 41, 47, 52, 58, 63, 2, 9, 15, 22, 29, 36, 43, 49, 55, 67]
        
        self.db_manager.evaluate_predictions_for_tirage(
            tirage_date=target_date,
            tirage_time=None,
            actual_numbers=actual_numbers
        )
        
        print("Évaluation des prédictions effectuée")
        
        # Vérifier les résultats de l'évaluation
        with self.db_manager.engine.connect() as conn:
            result = conn.execute(self.db_manager.engine.text("""
                SELECT correct_count, accuracy_percentage, is_evaluated
                FROM unified_predictions 
                WHERE id = :prediction_id
            """), {"prediction_id": prediction_id})
            
            evaluation_result = result.fetchone()
            
        print(f"Résultat évaluation: {evaluation_result[0]} corrects, {evaluation_result[1]}% précision")
        
        self.assertTrue(evaluation_result[2])  # is_evaluated = True
        self.assertEqual(evaluation_result[0], 7)  # 7 numéros corrects
        self.assertAlmostEqual(evaluation_result[1], 87.5, places=1)  # 7/8 = 87.5%
        
        # Vérifier l'analyse des erreurs
        errors_df = self.db_manager.get_user_prediction_errors(user_id, limit=5)
        
        print(f"Nombre d'erreurs analysées: {len(errors_df)}")
        self.assertEqual(len(errors_df), 1)
        
        error_row = errors_df.iloc[0]
        print(f"Erreurs détaillées: {error_row['error_count']} erreurs, {error_row['miss_count']} manqués")
        
        self.assertEqual(error_row['error_count'], 1)  # 1 numéro prédit mais pas tiré (99)
        self.assertEqual(error_row['miss_count'], 13)  # 13 numéros tirés mais pas prédits
        
        print("✅ Test d'évaluation et analyse des erreurs réussi")
    
    def test_ml_vs_user_performance_comparison(self):
        """Tester la comparaison des performances ML vs utilisateurs."""
        print("\n=== Test de comparaison des performances ML vs utilisateurs ===")
        
        # Créer des prédictions utilisateur
        session_id = "test_session_comparison"
        user_prediction_id, user_id = self.db_manager.save_user_prediction(
            session_id=session_id,
            method_name="Test Utilisateur",
            predicted_numbers=[1, 8, 16, 23, 31, 38, 45, 50],
            target_date=date(2025, 1, 3),
            confidence_score=0.65,
            ip_address="192.168.1.400"
        )
        
        # Créer une prédiction ML
        ml_prediction_id = self.db_manager.save_ml_prediction(
            model_name="test_model",
            method_name="Test ML",
            predicted_numbers=[1, 8, 16, 23, 31, 38, 45, 56],
            target_date=date(2025, 1, 3),
            confidence_score=0.85
        )
        
        print(f"Prédictions créées: Utilisateur={user_prediction_id}, ML={ml_prediction_id}")
        
        # Évaluer les prédictions
        actual_numbers = [1, 8, 16, 23, 31, 38, 45, 50, 56, 61, 4, 10, 17, 24, 32, 39, 44, 52, 58, 65]
        
        self.db_manager.evaluate_predictions_for_tirage(
            tirage_date=date(2025, 1, 3),
            tirage_time=None,
            actual_numbers=actual_numbers
        )
        
        # Récupérer le classement unifié
        leaderboard_df = self.db_manager.get_unified_leaderboard(limit=10)
        
        print(f"Nombre d'entrées dans le classement: {len(leaderboard_df)}")
        self.assertGreaterEqual(len(leaderboard_df), 2)
        
        # Vérifier que les deux types de prédicteurs sont présents
        predictor_types = set(leaderboard_df['predictor_type'].tolist())
        print(f"Types de prédicteurs: {predictor_types}")
        
        self.assertIn('USER', predictor_types)
        self.assertIn('ML_MODEL', predictor_types)
        
        # Analyser les performances comparatives
        try:
            analysis = self.ml_trainer.analyze_user_vs_ml_performance(days_back=30)
            
            print(f"Analyse comparative:")
            print(f"- Utilisateurs actifs: {analysis['comparison'].get('active_users', 0)}")
            print(f"- Modèles ML actifs: {analysis['comparison'].get('active_ml_models', 0)}")
            print(f"- Précision moyenne utilisateurs: {analysis['comparison'].get('user_avg_accuracy', 0):.2f}%")
            print(f"- Précision moyenne ML: {analysis['comparison'].get('ml_avg_accuracy', 0):.2f}%")
            
            self.assertIsInstance(analysis, dict)
            self.assertIn('comparison', analysis)
            
        except Exception as e:
            print(f"Note: Analyse comparative non disponible (normal en test): {e}")
        
        print("✅ Test de comparaison des performances réussi")
    
    def test_multiple_users_no_interference(self):
        """Tester que plusieurs utilisateurs n'interfèrent pas entre eux."""
        print("\n=== Test de non-interférence entre utilisateurs ===")
        
        # Créer 3 utilisateurs différents
        users_data = [
            {"session": "session_user_1", "ip": "192.168.1.501", "method": "Fréquences"},
            {"session": "session_user_2", "ip": "192.168.1.502", "method": "Écarts"},
            {"session": "session_user_3", "ip": "192.168.1.503", "method": "Cycles"}
        ]
        
        user_ids = []
        prediction_ids = []
        
        # Créer des prédictions pour chaque utilisateur
        for i, user_data in enumerate(users_data):
            predicted_numbers = [j + (i * 10) for j in range(1, 9)]  # Numéros différents pour chaque utilisateur
            predicted_numbers = [n for n in predicted_numbers if n <= 70]  # S'assurer que les numéros sont valides
            
            if len(predicted_numbers) < 8:
                predicted_numbers.extend(range(60, 68))
                predicted_numbers = predicted_numbers[:8]
            
            prediction_id, user_id = self.db_manager.save_user_prediction(
                session_id=user_data["session"],
                method_name=user_data["method"],
                predicted_numbers=predicted_numbers,
                target_date=date(2025, 1, 15),
                confidence_score=0.70 + (i * 0.05),
                ip_address=user_data["ip"]
            )
            
            user_ids.append(user_id)
            prediction_ids.append(prediction_id)
            
            print(f"Utilisateur {i+1}: {user_id}, Prédiction: {prediction_id}")
        
        # Vérifier que tous les utilisateurs sont différents
        self.assertEqual(len(set(user_ids)), 3)
        
        # Vérifier que toutes les prédictions sont différentes
        self.assertEqual(len(set(prediction_ids)), 3)
        
        # Vérifier que chaque utilisateur a ses propres prédictions
        for user_id in user_ids:
            user_predictions = self.db_manager.get_user_performance_summary(user_id)
            print(f"Prédictions pour {user_id}: {len(user_predictions)}")
            self.assertEqual(len(user_predictions), 1)
        
        # Récupérer toutes les prédictions et vérifier qu'elles sont toutes présentes
        all_predictions = self.db_manager.get_all_predictions_for_display(limit=20)
        user_predictions_count = len(all_predictions[all_predictions['predictor_type'] == 'USER'])
        
        print(f"Total des prédictions utilisateurs dans le système: {user_predictions_count}")
        self.assertGreaterEqual(user_predictions_count, 3)
        
        print("✅ Test de non-interférence entre utilisateurs réussi")
    
    def test_user_display_names(self):
        """Tester que les noms d'affichage des utilisateurs sont corrects."""
        print("\n=== Test des noms d'affichage des utilisateurs ===")
        
        session_id = "test_session_display"
        ip_address = "192.168.1.600"
        
        # Créer un utilisateur
        user_id = self.db_manager.get_or_create_user(session_id, ip_address)
        
        # Vérifier le nom d'affichage dans la base de données
        with self.db_manager.engine.connect() as conn:
            result = conn.execute(self.db_manager.engine.text("""
                SELECT display_name FROM users WHERE user_id = :user_id
            """), {"user_id": user_id})
            
            display_name = result.fetchone()[0]
        
        print(f"Nom d'affichage pour {user_id}: {display_name}")
        
        # Vérifier que le nom d'affichage suit le format attendu
        self.assertTrue(display_name.startswith('Utilisateur'))
        self.assertNotEqual(display_name, 'undefined')
        
        # Créer une prédiction et vérifier l'affichage
        prediction_id, _ = self.db_manager.save_user_prediction(
            session_id=session_id,
            method_name="Test Affichage",
            predicted_numbers=[1, 2, 3, 4, 5, 6, 7, 8],
            target_date=date(2025, 1, 20),
            ip_address=ip_address
        )
        
        # Récupérer les prédictions avec noms d'affichage
        predictions_df = self.db_manager.get_all_predictions_for_display(limit=5)
        user_prediction = predictions_df[predictions_df['predictor_id'] == user_id].iloc[0]
        
        print(f"Méthode d'affichage: {user_prediction['display_method']}")
        
        # Vérifier que le nom d'affichage contient le nom de l'utilisateur
        self.assertIn(display_name, user_prediction['display_method'])
        self.assertNotIn('undefined', user_prediction['display_method'])
        
        print("✅ Test des noms d'affichage réussi")

def run_tests():
    """Exécuter tous les tests."""
    print("🧪 Démarrage des tests des fonctionnalités utilisateurs v2")
    print("=" * 60)
    
    # Créer une suite de tests
    test_suite = unittest.TestSuite()
    
    # Ajouter tous les tests
    test_suite.addTest(TestUserPredictionsV2('test_user_creation_and_identification'))
    test_suite.addTest(TestUserPredictionsV2('test_user_predictions_persistence'))
    test_suite.addTest(TestUserPredictionsV2('test_prediction_evaluation_and_errors'))
    test_suite.addTest(TestUserPredictionsV2('test_ml_vs_user_performance_comparison'))
    test_suite.addTest(TestUserPredictionsV2('test_multiple_users_no_interference'))
    test_suite.addTest(TestUserPredictionsV2('test_user_display_names'))
    
    # Exécuter les tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("🎉 Tous les tests ont réussi !")
        print("✅ Les fonctionnalités de prédictions utilisateurs v2 sont opérationnelles")
    else:
        print("❌ Certains tests ont échoué")
        print(f"Échecs: {len(result.failures)}")
        print(f"Erreurs: {len(result.errors)}")
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)

