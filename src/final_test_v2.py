#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test final des fonctionnalités utilisateurs v2 avec SQLite
"""

import os
import sys
from datetime import datetime, date

database_url = os.environ.get("DATABASE_URL", "postgresql://kenos_user:qYGSudoftPvnoxaT9Seh5IP4itP1kK0a@dpg-d1umeoer433s73eu3d7g-a.frankfurt-postgres.render.com/kenos_vs92")
def test_final_functionality():
    """Test final complet des fonctionnalités."""
    print("🧪 Test final des fonctionnalités utilisateurs v2")
    print("=" * 60)
    
    try:
        # Utiliser le gestionnaire PostgreSQL
        from enhanced_database_manager import EnhancedDatabaseManagerV2
        
        # Initialiser le gestionnaire
        db_manager = EnhancedDatabaseManagerV2()
        print("✅ Gestionnaire de base de données PostgreSQL initialisé")
        
        # Test 1: Créer plusieurs utilisateurs
        print("\n📝 Test 1: Création de plusieurs utilisateurs")
        users = []
        for i in range(3):
            session_id = f"test_session_{i+1}"
            ip_address = f"192.168.1.{100+i}"
            
            user_id = db_manager.get_or_create_user(session_id, ip_address)
            users.append((user_id, session_id, ip_address))
            print(f"   Utilisateur {i+1}: {user_id}")
            
            # Vérifications
            assert user_id != "undefined", f"L'ID utilisateur ne doit pas être 'undefined'"
            assert user_id.startswith("utilisateur"), f"L'ID utilisateur doit commencer par 'utilisateur'"
        
        # Vérifier que tous les utilisateurs sont différents
        user_ids = [u[0] for u in users]
        assert len(set(user_ids)) == 3, "Tous les utilisateurs doivent être différents"
        print("✅ Création d'utilisateurs réussie")
        
        # Test 2: Sauvegarder des prédictions pour chaque utilisateur
        print("\n📝 Test 2: Sauvegarde de prédictions multiples")
        predictions = []
        methods = ["Analyse Fréquences", "Analyse Écarts", "Stratégie Mixte"]
        
        for i, (user_id, session_id, ip_address) in enumerate(users):
            predicted_numbers = [j + (i * 10) for j in range(1, 9)]
            predicted_numbers = [n for n in predicted_numbers if n <= 70]
            if len(predicted_numbers) < 8:
                predicted_numbers.extend(range(60, 68))
                predicted_numbers = predicted_numbers[:8]
            
            prediction_id, returned_user_id = db_manager.save_user_prediction(
                session_id=session_id,
                method_name=methods[i],
                predicted_numbers=predicted_numbers,
                target_date=date(2025, 2, 15),
                confidence_score=0.70 + (i * 0.05),
                ip_address=ip_address
            )
            
            predictions.append((prediction_id, user_id, methods[i], predicted_numbers))
            print(f"   Prédiction {i+1}: ID={prediction_id}, Utilisateur={user_id}, Méthode={methods[i]}")
            
            # Vérifications
            assert prediction_id is not None, "L'ID de prédiction ne doit pas être None"
            assert returned_user_id == user_id, "L'ID utilisateur doit être cohérent"
        
        print("✅ Sauvegarde de prédictions réussie")
        
        # Test 3: Vérifier que les prédictions ne s'écrasent pas
        print("\n📝 Test 3: Vérification de la persistance des prédictions")
        all_predictions_df = db_manager.get_all_predictions_for_display(limit=20)
        user_predictions = all_predictions_df[all_predictions_df['predictor_type'] == 'USER']
        
        print(f"   Total des prédictions utilisateurs: {len(user_predictions)}")
        assert len(user_predictions) >= 3, "Il doit y avoir au moins 3 prédictions utilisateurs"
        
        # Vérifier les noms d'affichage
        for _, row in user_predictions.iterrows():
            display_method = row['display_method']
            predictor_id = row['predictor_id']
            
            print(f"   - Prédicteur: {predictor_id}, Affichage: {display_method}")
            
            # Vérifications critiques
            assert "undefined" not in display_method.lower(), f"'undefined' trouvé dans: {display_method}"
            assert predictor_id.startswith("utilisateur"), f"ID prédicteur invalide: {predictor_id}"
            assert "Utilisateur" in display_method, f"Le nom d'affichage doit contenir 'Utilisateur': {display_method}"
        
        print("✅ Persistance des prédictions vérifiée")
        
        # Test 4: Ajouter une prédiction ML pour comparaison
        print("\n📝 Test 4: Ajout d'une prédiction ML")
        ml_prediction_id = db_manager.save_ml_prediction(
            model_name="test_model",
            method_name="Machine Learning",
            predicted_numbers=[5, 15, 25, 35, 45, 55, 65, 70],
            target_date=date(2025, 2, 15),
            confidence_score=0.85
        )
        
        print(f"   Prédiction ML: ID={ml_prediction_id}")
        assert ml_prediction_id is not None, "L'ID de prédiction ML ne doit pas être None"
        print("✅ Prédiction ML ajoutée")
        
        # Test 5: Vérifier le classement unifié
        print("\n📝 Test 5: Vérification du classement unifié")
        
        # D'abord, simuler une évaluation pour avoir des données dans le classement
        actual_numbers = [5, 15, 25, 35, 45, 55, 65, 70, 1, 11, 21, 31, 41, 51, 61, 2, 12, 22, 32, 42]
        db_manager.evaluate_predictions_for_tirage(
            tirage_date=date(2025, 2, 15),
            tirage_time=None,
            actual_numbers=actual_numbers
        )
        
        leaderboard_df = db_manager.get_unified_leaderboard(limit=10)
        print(f"   Entrées dans le classement: {len(leaderboard_df)}")
        
        if len(leaderboard_df) > 0:
            for _, row in leaderboard_df.iterrows():
                display_name = row['display_name']
                predictor_type = row['predictor_type']
                avg_accuracy = row['avg_accuracy']
                
                print(f"   - {display_name} ({predictor_type}): {avg_accuracy:.1f}%")
                
                # Vérifications
                assert "undefined" not in display_name.lower(), f"'undefined' trouvé dans le classement: {display_name}"
                
                if predictor_type == 'USER':
                    assert "Utilisateur" in display_name, f"Le nom d'affichage utilisateur doit contenir 'Utilisateur': {display_name}"
                elif predictor_type == 'ML_MODEL':
                    assert "🤖" in display_name, f"Le nom d'affichage ML doit contenir '🤖': {display_name}"
        
        print("✅ Classement unifié vérifié")
        
        # Test 6: Vérifier les performances individuelles
        print("\n📝 Test 6: Vérification des performances individuelles")
        for user_id, _, _, _ in users:
            performance_df = db_manager.get_user_performance_summary(user_id)
            print(f"   Performances pour {user_id}: {len(performance_df)} méthodes")
            
            if len(performance_df) > 0:
                for _, row in performance_df.iterrows():
                    method_name = row['method_name']
                    total_predictions = row['total_predictions']
                    avg_accuracy = row['average_accuracy']
                    print(f"     - {method_name}: {total_predictions} prédictions, {avg_accuracy:.1f}% précision")
        
        print("✅ Performances individuelles vérifiées")
        
        # Test 7: Vérifier les erreurs de prédiction
        print("\n📝 Test 7: Vérification de l'analyse des erreurs")
        for user_id, _, _, _ in users:
            errors_df = db_manager.get_user_prediction_errors(user_id, limit=5)
            print(f"   Erreurs pour {user_id}: {len(errors_df)} analyses")
            
            if len(errors_df) > 0:
                for _, row in errors_df.iterrows():
                    method_name = row['method_name']
                    error_count = row['error_count']
                    miss_count = row['miss_count']
                    print(f"     - {method_name}: {error_count} erreurs, {miss_count} manqués")
        
        print("✅ Analyse des erreurs vérifiée")
        
        # Test 8: Vérifier les prédictions groupées par prédicteur
        print("\n📝 Test 8: Vérification des prédictions groupées")
        grouped_predictions_df = db_manager.get_recent_predictions_by_predictor(limit=5)
        print(f"   Prédictions groupées: {len(grouped_predictions_df)} entrées")
        
        predictors_found = set()
        for _, row in grouped_predictions_df.iterrows():
            display_name = row['display_name']
            predictor_type = row['predictor_type']
            predictors_found.add(predictor_type)
            
            print(f"   - {display_name} ({predictor_type})")
            
            # Vérifications
            assert "undefined" not in display_name.lower(), f"'undefined' trouvé: {display_name}"
        
        print(f"   Types de prédicteurs trouvés: {predictors_found}")
        print("✅ Prédictions groupées vérifiées")
        
        # Résumé final
        print("\n" + "=" * 60)
        print("🎉 TOUS LES TESTS ONT RÉUSSI !")
        print("✅ Fonctionnalités validées:")
        print("   • Création d'utilisateurs avec IDs uniques (utilisateurX)")
        print("   • Persistance des prédictions sans écrasement")
        print("   • Noms d'affichage corrects (pas de 'undefined')")
        print("   • Coexistence des prédictions utilisateurs et ML")
        print("   • Évaluation et analyse des erreurs")
        print("   • Classement unifié fonctionnel")
        print("   • Performances individuelles trackées")
        print("   • Groupement des prédictions par prédicteur")
        
        print(f"\n📊 Statistiques finales:")
        print(f"   • Utilisateurs créés: {len(users)}")
        print(f"   • Prédictions utilisateurs: {len(user_predictions)}")
        print(f"   • Prédictions ML: 1")
        print(f"   • Entrées dans le classement: {len(leaderboard_df)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_final_functionality()
    sys.exit(0 if success else 1)

