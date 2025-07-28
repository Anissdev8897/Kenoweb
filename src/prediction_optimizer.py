#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Keno Analyzer Pro - Système d'Optimisation des Prédictions
Ce module permet d'évaluer et d'ajuster les méthodes de prédiction
sans réentraîner le modèle principal
"""

import json
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
import os

class PredictionOptimizer:
    """Système d'optimisation des prédictions basé sur l'évaluation des erreurs"""
    
    def __init__(self, base_path=None):
        self.base_path = base_path or os.path.dirname(os.path.abspath(__file__))
        self.performance_data = defaultdict(dict)
        self.method_weights = self._load_method_weights()
        self.error_history = self._load_error_history()
        self.adjustment_log = []
        
    def _load_method_weights(self):
        """Charge les poids actuels des méthodes"""
        weights_file = os.path.join(self.base_path, 'method_weights.json')
        if os.path.exists(weights_file):
            with open(weights_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'frequencies': 1.0,
            'ecarts': 1.0,
            'cycles': 1.0,
            'mixed': 1.0,
            'ml': 1.0,
            'fibonacci': 1.0,
            'sums': 1.0,
            'complete': 1.0
        }
    
    def _load_error_history(self):
        """Charge l'historique des erreurs"""
        history_file = os.path.join(self.base_path, 'error_history.json')
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def evaluate_predictions(self, predictions, actual_results):
        """
        Évalue les prédictions par rapport aux résultats réels
        Retourne un score d'erreur par méthode
        """
        errors = {}
        
        for method, pred_numbers in predictions.items():
            if method in actual_results:
                actual = actual_results[method]
                
                # Calcul de l'erreur
                correct_predictions = len(set(pred_numbers) & set(actual))
                total_predictions = len(pred_numbers)
                
                # Score d'erreur (plus bas = mieux)
                error_score = 1 - (correct_predictions / total_predictions)
                errors[method] = {
                    'error_score': error_score,
                    'correct_predictions': correct_predictions,
                    'total_predictions': total_predictions,
                    'accuracy': correct_predictions / total_predictions,
                    'timestamp': datetime.now().isoformat()
                }
        
        return errors
    
    def adjust_method_weights(self, errors):
        """
        Ajuste les poids des méthodes basés sur les erreurs
        Sans réentraîner le modèle principal
        """
        adjustments = {}
        
        for method, error_data in errors.items():
            current_weight = self.method_weights.get(method, 1.0)
            accuracy = error_data['accuracy']
            
            # Ajustement basé sur la performance
            if accuracy > 0.3:  # Performance acceptable
                new_weight = current_weight * 1.1
            elif accuracy < 0.1:  # Performance faible
                new_weight = current_weight * 0.8
            else:
                new_weight = current_weight * 0.95  # Légère réduction
            
            # Limitation des poids
            new_weight = max(0.1, min(2.0, new_weight))
            
            adjustments[method] = {
                'old_weight': current_weight,
                'new_weight': new_weight,
                'accuracy': accuracy,
                'adjustment_reason': f"Performance: {accuracy:.2f}"
            }
            
            self.method_weights[method] = new_weight
        
        # Enregistrement de l'ajustement
        self.adjustment_log.append({
            'timestamp': datetime.now().isoformat(),
            'adjustments': adjustments,
            'errors': errors
        })
        
        self._save_adjustments()
        return adjustments
    
    def get_weighted_predictions(self, raw_predictions):
        """
        Applique les poids ajustés aux prédictions
        """
        weighted_predictions = {}
        
        for method, predictions in raw_predictions.items():
            weight = self.method_weights.get(method, 1.0)
            
            # Application du poids aux prédictions
            if isinstance(predictions, list):
                # Pour les listes de numéros, on multiplie la confiance
                weighted_predictions[method] = {
                    'numbers': predictions,
                    'confidence': weight,
                    'weight': weight
                }
            else:
                # Pour les prédictions structurées
                predictions['weight'] = weight
                predictions['confidence'] = predictions.get('confidence', 1.0) * weight
                weighted_predictions[method] = predictions
        
        return weighted_predictions
    
    def generate_combined_prediction(self, all_predictions):
        """
        Génère une prédiction combinée basée sur les poids ajustés
        """
        weighted = self.get_weighted_predictions(all_predictions)
        
        # Combinaison des prédictions pondérées
        combined_scores = defaultdict(float)
        method_contributions = defaultdict(list)
        
        for method, pred_data in weighted.items():
            if isinstance(pred_data, dict) and 'numbers' in pred_data:
                numbers = pred_data['numbers']
                confidence = pred_data.get('confidence', 1.0)
                
                for num in numbers:
                    combined_scores[num] += confidence
                    method_contributions[num].append({
                        'method': method,
                        'confidence': confidence
                    })
        
        # Tri par score combiné
        top_numbers = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)[:20]
        
        return {
            'predictions': [num for num, score in top_numbers],
            'scores': dict(top_numbers),
            'method_contributions': dict(method_contributions),
            'weights_used': self.method_weights.copy(),
            'generated_at': datetime.now().isoformat()
        }
    
    def _save_adjustments(self):
        """Sauvegarde les ajustements"""
        weights_file = os.path.join(self.base_path, 'method_weights.json')
        with open(weights_file, 'w', encoding='utf-8') as f:
            json.dump(self.method_weights, f, indent=2, ensure_ascii=False)
        
        history_file = os.path.join(self.base_path, 'adjustment_history.json')
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(self.adjustment_log, f, indent=2, ensure_ascii=False)
    
    def get_performance_summary(self):
        """Retourne un résumé des performances"""
        if not self.adjustment_log:
            return {"message": "Aucune donnée de performance disponible"}
        
        latest_adjustment = self.adjustment_log[-1]
        
        return {
            'latest_adjustment': latest_adjustment,
            'current_weights': self.method_weights,
            'total_adjustments': len(self.adjustment_log),
            'average_accuracy': self._calculate_average_accuracy()
        }
    
    def _calculate_average_accuracy(self):
        """Calcule la précision moyenne"""
        if not self.adjustment_log:
            return 0.0
        
        accuracies = []
        for adjustment in self.adjustment_log:
            if 'errors' in adjustment:
                for method, data in adjustment['errors'].items():
                    accuracies.append(data.get('accuracy', 0.0))
        
        return sum(accuracies) / len(accuracies) if accuracies else 0.0
    
    def reset_weights(self):
        """Réinitialise tous les poids à 1.0"""
        self.method_weights = {method: 1.0 for method in self.method_weights}
        self._save_adjustments()
        return {"message": "Poids réinitialisés avec succès"}

# Instance globale
optimizer = PredictionOptimizer()

if __name__ == "__main__":
    # Test du système
    print("🎯 Test du système d'optimisation des prédictions")
    
    # Exemple de données
    test_predictions = {
        'frequencies': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        'ecarts': [11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
        'cycles': [21, 22, 23, 24, 25, 26, 27, 28, 29, 30]
    }
    
    test_results = {
        'frequencies': [1, 2, 3, 5, 7, 9, 11, 13, 15, 17],
        'ecarts': [12, 14, 16, 18, 20, 22, 24, 26, 28, 30],
        'cycles': [21, 23, 25, 27, 29, 31, 33, 35, 37, 39]
    }
    
    errors = optimizer.evaluate_predictions(test_predictions, test_results)
    adjustments = optimizer.adjust_method_weights(errors)
    combined = optimizer.generate_combined_prediction(test_predictions)
    
    print("\n📊 Résultats de l'évaluation:")
    print(json.dumps(errors, indent=2, ensure_ascii=False))
    print("\n⚖️ Ajustements:")
    print(json.dumps(adjustments, indent=2, ensure_ascii=False))
    print("\n🎯 Prédiction combinée:")
    print(json.dumps(combined, indent=2, ensure_ascii=False))
