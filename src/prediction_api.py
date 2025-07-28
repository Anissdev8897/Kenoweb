#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Keno Analyzer Pro - API pour l'optimisation des prédictions
Endpoints pour évaluer et ajuster les méthodes sans réentraînement
"""

from flask import Flask, request, jsonify
import json
import os
import sys
from datetime import datetime
from prediction_optimizer import PredictionOptimizer

# Ajouter le chemin du système
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class PredictionAPI:
    def __init__(self):
        self.optimizer = PredictionOptimizer()
        self.chat_messages = []
        self.load_chat_history()
    
    def load_chat_history(self):
        """Charge l'historique des messages de chat"""
        chat_file = os.path.join(os.path.dirname(__file__), 'chat_history.json')
        if os.path.exists(chat_file):
            with open(chat_file, 'r', encoding='utf-8') as f:
                self.chat_messages = json.load(f)
    
    def save_chat_history(self):
        """Sauvegarde l'historique des messages"""
        chat_file = os.path.join(os.path.dirname(__file__), 'chat_history.json')
        with open(chat_file, 'w', encoding='utf-8') as f:
            json.dump(self.chat_messages, f, indent=2, ensure_ascii=False)
    
    def get_performance_summary(self):
        """Retourne un résumé des performances des méthodes"""
        try:
            summary = self.optimizer.get_performance_summary()
            
            # Ajouter des informations supplémentaires
            summary['current_weights'] = self.optimizer.method_weights
            summary['total_predictions'] = len(self.optimizer.adjustment_log) * 8  # 8 méthodes
            summary['method_accuracy'] = self.calculate_method_accuracy()
            summary['best_method'] = self.get_best_method()
            
            return summary
        except Exception as e:
            return {"error": str(e)}
    
    def calculate_method_accuracy(self):
        """Calcule la précision par méthode"""
        method_accuracy = {}
        
        for adjustment in self.optimizer.adjustment_log:
            if 'errors' in adjustment:
                for method, data in adjustment['errors'].items():
                    if method not in method_accuracy:
                        method_accuracy[method] = []
                    method_accuracy[method].append(data.get('accuracy', 0.0))
        
        # Moyenne des précisions
        for method in method_accuracy:
            accuracies = method_accuracy[method]
            method_accuracy[method] = sum(accuracies) / len(accuracies) if accuracies else 0.0
        
        return method_accuracy
    
    def get_best_method(self):
        """Retourne la meilleure méthode basée sur la précision"""
        method_accuracy = self.calculate_method_accuracy()
        if not method_accuracy:
            return None
        
        return max(method_accuracy.items(), key=lambda x: x[1])[0]
    
    def add_chat_message(self, username, message):
        """Ajoute un message de chat"""
        chat_message = {
            'username': username,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        
        self.chat_messages.append(chat_message)
        
        # Garder seulement les 100 derniers messages
        if len(self.chat_messages) > 100:
            self.chat_messages = self.chat_messages[-100:]
        
        self.save_chat_history()
        return chat_message
    
    def get_chat_messages(self):
        """Retourne les messages de chat"""
        return self.chat_messages
    
    def evaluate_prediction_accuracy(self, predictions, actual_results):
        """Évalue la précision des prédictions"""
        errors = self.optimizer.evaluate_predictions(predictions, actual_results)
        adjustments = self.optimizer.adjust_method_weights(errors)
        
        return {
            'errors': errors,
            'adjustments': adjustments,
            'new_weights': self.optimizer.method_weights,
            'timestamp': datetime.now().isoformat()
        }
    
    def reset_all_weights(self):
        """Réinitialise tous les poids"""
        result = self.optimizer.reset_weights()
        return result

# Instance globale
prediction_api = PredictionAPI()

def create_prediction_routes(app):
    """Crée les routes API pour l'optimisation des prédictions"""
    
    @app.route('/api/prediction/performance', methods=['GET'])
    def get_performance():
        """Retourne les données de performance"""
        return jsonify(prediction_api.get_performance_summary())
    
    @app.route('/api/prediction/evaluate', methods=['POST'])
    def evaluate_predictions():
        """Évalue les prédictions et ajuste les poids"""
        try:
            data = request.get_json()
            predictions = data.get('predictions', {})
            actual_results = data.get('actual_results', {})
            
            result = prediction_api.evaluate_prediction_accuracy(predictions, actual_results)
            return jsonify(result)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/prediction/reset-weights', methods=['POST'])
    def reset_weights():
        """Réinitialise les poids des méthodes"""
        try:
            result = prediction_api.reset_all_weights()
            return jsonify(result)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/chat/messages', methods=['GET'])
    def get_chat_messages():
        """Retourne les messages de chat"""
        return jsonify({'messages': prediction_api.get_chat_messages()})
    
    @app.route('/api/chat/save', methods=['POST'])
    def save_chat_message():
        """Sauvegarde un message de chat"""
        try:
            data = request.get_json()
            username = data.get('username', 'Anonyme')
            message = data.get('message', '')
            
            if not message.strip():
                return jsonify({'error': 'Message vide'}), 400
            
            saved_message = prediction_api.add_chat_message(username, message)
            return jsonify({'success': True, 'message': saved_message})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/prediction/combined', methods=['POST'])
    def get_combined_prediction():
        """Retourne une prédiction combinée basée sur les poids ajustés"""
        try:
            data = request.get_json()
            all_predictions = data.get('predictions', {})
            
            combined = prediction_api.optimizer.generate_combined_prediction(all_predictions)
            return jsonify(combined)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    # Test du système
    print("🎯 Test du système API de prédiction")
    
    # Créer une application Flask de test
    from flask import Flask
    app = Flask(__name__)
    
    create_prediction_routes(app)
    
    @app.route('/test')
    def test():
        return jsonify({"message": "API de prédiction fonctionnelle"})
    
    print("✅ Routes créées avec succès")
    print("📊 /api/prediction/performance - Données de performance")
    print("🎯 /api/prediction/evaluate - Évaluation des prédictions")
    print("🔄 /api/prediction/reset-weights - Réinitialisation des poids")
    print("💬 /api/chat/messages - Messages de chat")
    print("💾 /api/chat/save - Sauvegarde des messages")
