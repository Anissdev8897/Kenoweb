#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test simple pour valider les fonctionnalités de base avec SQLite
"""

import os
import sys
import sqlite3
from datetime import datetime, date

# Vérification de la variable d'environnement DATABASE_URL
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    print("❌ La variable d'environnement DATABASE_URL est requise pour exécuter les tests")
    sys.exit(1)

# Ajout du répertoire src au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_basic_functionality():
    """Test de base des fonctionnalités."""
    print("🧪 Test simple des fonctionnalités utilisateurs v2")
    print("=" * 50)
    
    try:
        from enhanced_database_manager import EnhancedDatabaseManagerV2
        
        # Initialiser le gestionnaire
        db_manager = EnhancedDatabaseManagerV2()
        print("✅ Gestionnaire de base de données initialisé")
        
        # Test 1: Créer un utilisateur
        session_id = "test_session_simple"
        ip_address = "127.0.0.1"
        
        user_id = db_manager.get_or_create_user(session_id, ip_address)
        print(f"✅ Utilisateur créé: {user_id}")
        
        # Vérifier que l'utilisateur n'est pas "undefined"
        assert user_id != "undefined", "L'ID utilisateur ne doit pas être 'undefined'"
        assert user_id.startswith("utilisateur"), "L'ID utilisateur doit commencer par 'utilisateur'"
        
        # Test 2: Sauvegarder une prédiction utilisateur
        predicted_numbers = [1, 5, 10, 15, 20, 25, 30, 35]
        target_date = date(2025, 2, 1)
        
        prediction_id, returned_user_id = db_manager.save_user_prediction(
            session_id=session_id,
            method_name="Test Simple",
            predicted_numbers=predicted_numbers,
            target_date=target_date,
            confidence_score=0.75,
            ip_address=ip_address
        )
        
        print(f"✅ Prédiction sauvegardée: ID={prediction_id}")
        assert prediction_id is not None, "L'ID de prédiction ne doit pas être None"
        assert returned_user_id == user_id, "L'ID utilisateur doit être cohérent"
        
        # Test 3: Récupérer les prédictions
        predictions_df = db_manager.get_all_predictions_for_display(limit=5)
        print(f"✅ Prédictions récupérées: {len(predictions_df)} entrées")
        
        # Vérifier qu'il n'y a pas de "undefined" dans les résultats
        if len(predictions_df) > 0:
            for _, row in predictions_df.iterrows():
                display_method = row['display_method']
                assert "undefined" not in display_method.lower(), f"'undefined' trouvé dans: {display_method}"
                print(f"   - {display_method}")
        
        # Test 4: Créer un deuxième utilisateur
        session_id_2 = "test_session_simple_2"
        user_id_2 = db_manager.get_or_create_user(session_id_2, "127.0.0.2")
        
        assert user_id != user_id_2, "Les utilisateurs doivent avoir des IDs différents"
        print(f"✅ Deuxième utilisateur créé: {user_id_2}")
        
        # Test 5: Sauvegarder une prédiction pour le deuxième utilisateur
        prediction_id_2, _ = db_manager.save_user_prediction(
            session_id=session_id_2,
            method_name="Test Simple 2",
            predicted_numbers=[2, 6, 11, 16, 21, 26, 31, 36],
            target_date=target_date,
            confidence_score=0.68,
            ip_address="127.0.0.2"
        )
        
        print(f"✅ Deuxième prédiction sauvegardée: ID={prediction_id_2}")
        
        # Test 6: Vérifier que les prédictions ne s'écrasent pas
        all_predictions_df = db_manager.get_all_predictions_for_display(limit=10)
        user_predictions = all_predictions_df[all_predictions_df['predictor_type'] == 'USER']
        
        print(f"✅ Total des prédictions utilisateurs: {len(user_predictions)}")
        assert len(user_predictions) >= 2, "Il doit y avoir au moins 2 prédictions utilisateurs"
        
        # Vérifier que chaque prédiction a un nom d'affichage correct
        for _, row in user_predictions.iterrows():
            display_method = row['display_method']
            predictor_id = row['predictor_id']
            
            print(f"   - Prédicteur: {predictor_id}, Affichage: {display_method}")
            
            # Vérifications
            assert "undefined" not in display_method.lower(), f"'undefined' trouvé dans: {display_method}"
            assert predictor_id.startswith("utilisateur"), f"ID prédicteur invalide: {predictor_id}"
        
        # Test 7: Tester le classement unifié
        leaderboard_df = db_manager.get_unified_leaderboard(limit=10)
        print(f"✅ Classement récupéré: {len(leaderboard_df)} entrées")
        
        for _, row in leaderboard_df.iterrows():
            display_name = row['display_name']
            assert "undefined" not in display_name.lower(), f"'undefined' trouvé dans le classement: {display_name}"
        
        print("\n🎉 Tous les tests simples ont réussi !")
        print("✅ Les fonctionnalités de base sont opérationnelles")
        print("✅ Aucun 'undefined' détecté dans les noms d'affichage")
        print("✅ Les prédictions utilisateurs sont correctement persistées")
        print("✅ Plusieurs utilisateurs peuvent coexister sans interférence")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_basic_functionality()
    sys.exit(0 if success else 1)
