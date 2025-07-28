#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Application web améliorée v2 avec gestion des prédictions utilisateurs
Interface pour afficher toutes les prédictions sans écrasement
"""

from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
import logging
import os
import json
from datetime import datetime, timedelta
import uuid
import threading
import time
from enhanced_database_manager import EnhancedDatabaseManagerV2
from enhanced_ml_trainer import EnhancedMLTrainerV2

database_url = os.environ.get("DATABASE_URL", "postgresql://kenos_user:qYGSudoftPvnoxaT9Seh5IP4itP1kK0a@dpg-d1umeoer433s73eu3d7g-a.frankfurt-postgres.render.com/kenos_vs92")


# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'keno-secret-key-2025')
CORS(app)

# Initialisation des gestionnaires
db_manager = EnhancedDatabaseManagerV2()
ml_trainer = EnhancedMLTrainerV2()

# Variables globales pour le statut
ml_status = {
    'is_training': False,
    'last_training': None,
    'models_available': [],
    'last_predictions': {}
}

@app.route('/')
def index():
    """Page principale avec interface améliorée."""
    return render_template('enhanced_index_v2.html')

@app.route('/api/status')
def get_status():
    """Récupérer le statut du système."""
    try:
        # Compter les tirages disponibles
        with db_manager.engine.connect() as conn:
            result = conn.execute(db_manager.engine.text("SELECT COUNT(*) FROM tirages_keno"))
            total_tirages = result.fetchone()[0]
            
            # Compter les utilisateurs actifs
            active_users = db_manager.get_active_users_count()
            
            # Récupérer les dernières prédictions
            recent_predictions = db_manager.get_recent_predictions_by_predictor(limit=5)
        
        return jsonify({
            'status': 'connected',
            'total_tirages': total_tirages,
            'active_users': active_users,
            'ml_status': ml_status,
            'recent_predictions_count': len(recent_predictions),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du statut: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/predict/<method>')
def predict(method):
    """Générer une prédiction avec la méthode spécifiée."""
    try:
        # Générer un ID de session si nécessaire
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
        
        session_id = session['session_id']
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')
        
        # Récupérer les paramètres
        num_numbers = int(request.args.get('numbers', 8))
        target_date = datetime.now().date() + timedelta(days=1)
        
        predicted_numbers = []
        confidence_score = None
        prediction_id = None
        user_id = None
        
        # Générer la prédiction selon la méthode
        if method == 'ml' or method == 'machine_learning':
            # Prédiction ML
            try:
                prediction_result = ml_trainer.predict_next_numbers(
                    'random_forest', num_numbers, target_date
                )
                predicted_numbers = prediction_result['predicted_numbers']
                confidence_score = prediction_result['confidence_score']
                prediction_id = prediction_result['prediction_id']
                method_name = "Machine Learning"
            except Exception as e:
                logger.error(f"Erreur ML: {str(e)}")
                return jsonify({'error': f'Erreur ML: {str(e)}'}), 500
        
        else:
            # Prédictions utilisateur (méthodes traditionnelles)
            method_names = {
                'frequency': 'Analyse Fréquences',
                'gaps': 'Analyse Écarts',
                'cycles': 'Analyse Cycles',
                'mixed': 'Stratégie Mixte',
                'fibonacci': 'Pondération Fibonacci',
                'sums': 'Analyse Sommes',
                'complete': 'Analyse Complète'
            }
            
            method_name = method_names.get(method, method.title())
            
            # Générer la prédiction avec la méthode traditionnelle
            predicted_numbers = generate_traditional_prediction(method, num_numbers)
            confidence_score = calculate_traditional_confidence(method)
            
            # Sauvegarder la prédiction utilisateur
            prediction_id, user_id = db_manager.save_user_prediction(
                session_id=session_id,
                method_name=method_name,
                predicted_numbers=predicted_numbers,
                target_date=target_date,
                confidence_score=confidence_score,
                ip_address=ip_address,
                user_agent=user_agent
            )
        
        return jsonify({
            'success': True,
            'method': method_name,
            'predicted_numbers': predicted_numbers,
            'confidence_score': confidence_score,
            'prediction_id': prediction_id,
            'user_id': user_id,
            'target_date': target_date.isoformat(),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la prédiction {method}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/predictions/all')
def get_all_predictions():
    """Récupérer toutes les prédictions pour l'affichage."""
    try:
        limit = int(request.args.get('limit', 20))
        predictions_df = db_manager.get_all_predictions_for_display(limit)
        
        predictions = []
        for _, row in predictions_df.iterrows():
            predictions.append({
                'predictor_id': row['predictor_id'],
                'display_method': row['display_method'],
                'predicted_numbers': row['predicted_numbers'],
                'actual_numbers': row['actual_numbers'] if row['actual_numbers'] else None,
                'correct_count': row['correct_count'],
                'accuracy_percentage': float(row['accuracy_percentage']) if row['accuracy_percentage'] else 0.0,
                'target_date': row['target_tirage_date'].isoformat() if row['target_tirage_date'] else None,
                'is_evaluated': row['is_evaluated'],
                'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                'predictor_type': row['predictor_type']
            })
        
        return jsonify({
            'success': True,
            'predictions': predictions,
            'total_count': len(predictions)
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des prédictions: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/predictions/by-predictor')
def get_predictions_by_predictor():
    """Récupérer les prédictions groupées par prédicteur."""
    try:
        limit = int(request.args.get('limit', 10))
        predictions_df = db_manager.get_recent_predictions_by_predictor(limit)
        
        # Grouper par prédicteur
        grouped_predictions = {}
        for _, row in predictions_df.iterrows():
            predictor_id = row['predictor_id']
            if predictor_id not in grouped_predictions:
                grouped_predictions[predictor_id] = {
                    'predictor_id': predictor_id,
                    'display_name': row['display_name'],
                    'predictor_type': row['predictor_type'],
                    'predictions': []
                }
            
            grouped_predictions[predictor_id]['predictions'].append({
                'prediction_method': row['prediction_method'],
                'predicted_numbers': row['predicted_numbers'],
                'actual_numbers': row['actual_numbers'] if row['actual_numbers'] else None,
                'correct_count': row['correct_count'],
                'accuracy_percentage': float(row['accuracy_percentage']) if row['accuracy_percentage'] else 0.0,
                'target_date': row['target_tirage_date'].isoformat() if row['target_tirage_date'] else None,
                'is_evaluated': row['is_evaluated'],
                'created_at': row['created_at'].isoformat() if row['created_at'] else None
            })
        
        return jsonify({
            'success': True,
            'predictors': list(grouped_predictions.values()),
            'total_predictors': len(grouped_predictions)
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des prédictions par prédicteur: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/leaderboard')
def get_leaderboard():
    """Récupérer le classement unifié."""
    try:
        limit = int(request.args.get('limit', 20))
        leaderboard_df = db_manager.get_unified_leaderboard(limit)
        
        leaderboard = []
        for _, row in leaderboard_df.iterrows():
            leaderboard.append({
                'predictor_id': row['predictor_id'],
                'display_name': row['display_name'],
                'predictor_type': row['predictor_type'],
                'total_predictions': row['total_predictions'],
                'total_evaluated': row['total_evaluated'],
                'avg_accuracy': float(row['avg_accuracy']) if row['avg_accuracy'] else 0.0,
                'best_score': row['best_score'],
                'methods_used': row['methods_used']
            })
        
        return jsonify({
            'success': True,
            'leaderboard': leaderboard,
            'total_entries': len(leaderboard)
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du classement: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/performance')
def get_user_performance():
    """Récupérer les performances de l'utilisateur actuel."""
    try:
        if 'session_id' not in session:
            return jsonify({'error': 'Session non trouvée'}), 400
        
        session_id = session['session_id']
        user_id = db_manager.get_or_create_user(session_id, request.remote_addr)
        
        # Récupérer les performances
        performance_df = db_manager.get_user_performance_summary(user_id)
        errors_df = db_manager.get_user_prediction_errors(user_id, limit=10)
        
        performance = []
        for _, row in performance_df.iterrows():
            performance.append({
                'method_name': row['method_name'],
                'total_predictions': row['total_predictions'],
                'total_evaluated': row['total_evaluated'],
                'average_accuracy': float(row['average_accuracy']) if row['average_accuracy'] else 0.0,
                'best_score': row['best_score'],
                'worst_score': row['worst_score'],
                'last_updated': row['last_updated'].isoformat() if row['last_updated'] else None
            })
        
        errors = []
        for _, row in errors_df.iterrows():
            errors.append({
                'method_name': row['method_name'],
                'predicted_but_not_drawn': row['predicted_but_not_drawn'],
                'drawn_but_not_predicted': row['drawn_but_not_predicted'],
                'correct_predictions': row['correct_predictions'],
                'error_count': row['error_count'],
                'miss_count': row['miss_count'],
                'tirage_date': row['tirage_date'].isoformat() if row['tirage_date'] else None
            })
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'performance': performance,
            'recent_errors': errors
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des performances utilisateur: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ml/retrain', methods=['POST'])
def retrain_ml_models():
    """Réentraîner les modèles ML."""
    try:
        if ml_status['is_training']:
            return jsonify({'error': 'Entraînement déjà en cours'}), 400
        
        # Lancer l'entraînement en arrière-plan
        def background_training():
            try:
                ml_status['is_training'] = True
                ml_status['last_training'] = datetime.now().isoformat()
                
                training_results = ml_trainer.train_models(retrain_trigger="MANUAL")
                
                ml_status['models_available'] = list(training_results.keys())
                ml_status['is_training'] = False
                
                logger.info("Réentraînement terminé avec succès")
                
            except Exception as e:
                ml_status['is_training'] = False
                logger.error(f"Erreur lors du réentraînement: {str(e)}")
        
        training_thread = threading.Thread(target=background_training)
        training_thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Réentraînement ML lancé en arrière-plan!',
            'status': 'training_started'
        })
        
    except Exception as e:
        logger.error(f"Erreur lors du lancement du réentraînement: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ml/predict-all', methods=['POST'])
def generate_all_ml_predictions():
    """Générer des prédictions avec tous les modèles ML."""
    try:
        num_numbers = int(request.json.get('numbers', 8))
        target_date = datetime.now().date() + timedelta(days=1)
        
        predictions = ml_trainer.generate_all_predictions(target_date, num_numbers)
        
        ml_status['last_predictions'] = {
            model_key: {
                'numbers': result['predicted_numbers'],
                'confidence': result['confidence_score'],
                'timestamp': datetime.now().isoformat()
            }
            for model_key, result in predictions.items()
        }
        
        return jsonify({
            'success': True,
            'predictions': predictions,
            'message': f'Généré {len(predictions)} prédictions ML'
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération des prédictions ML: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analysis/user-vs-ml')
def analyze_user_vs_ml():
    """Analyser les performances utilisateurs vs ML."""
    try:
        days_back = int(request.args.get('days', 30))
        analysis = ml_trainer.analyze_user_vs_ml_performance(days_back)
        
        return jsonify({
            'success': True,
            'analysis': analysis,
            'period_days': days_back
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse comparative: {str(e)}")
        return jsonify({'error': str(e)}), 500

def generate_traditional_prediction(method, num_numbers):
    """Générer une prédiction avec les méthodes traditionnelles."""
    try:
        # Récupérer les derniers tirages
        recent_tirages = db_manager.get_official_tirages_for_training()
        recent_tirages = recent_tirages.tail(50)  # 50 derniers tirages
        
        if len(recent_tirages) < 10:
            # Prédiction aléatoire si pas assez de données
            import random
            return sorted(random.sample(range(1, 71), num_numbers))
        
        # Extraire tous les numéros
        all_numbers = []
        for _, row in recent_tirages.iterrows():
            numbers = [row[f'numero_{i}'] for i in range(1, 21)]
            all_numbers.extend(numbers)
        
        # Calculer les fréquences
        frequencies = {}
        for num in range(1, 71):
            frequencies[num] = all_numbers.count(num)
        
        # Calculer les écarts
        gaps = {}
        for num in range(1, 71):
            last_seen = -1
            for i, row in enumerate(reversed(recent_tirages.itertuples())):
                tirage_numbers = [getattr(row, f'numero_{j}') for j in range(1, 21)]
                if num in tirage_numbers:
                    last_seen = i
                    break
            gaps[num] = last_seen if last_seen != -1 else len(recent_tirages)
        
        # Sélectionner les numéros selon la méthode
        if method == 'frequency':
            # Favoriser les numéros fréquents
            sorted_by_freq = sorted(frequencies.items(), key=lambda x: x[1], reverse=True)
            predicted_numbers = [num for num, _ in sorted_by_freq[:num_numbers]]
        
        elif method == 'gaps':
            # Favoriser les numéros avec le plus grand écart
            sorted_by_gap = sorted(gaps.items(), key=lambda x: x[1], reverse=True)
            predicted_numbers = [num for num, _ in sorted_by_gap[:num_numbers]]
        
        elif method == 'cycles':
            # Analyse cyclique simple
            cycle_scores = {}
            for num in range(1, 71):
                cycle_scores[num] = (frequencies[num] * 0.6) + (gaps[num] * 0.4)
            sorted_by_cycle = sorted(cycle_scores.items(), key=lambda x: x[1], reverse=True)
            predicted_numbers = [num for num, _ in sorted_by_cycle[:num_numbers]]
        
        elif method == 'mixed':
            # Stratégie mixte
            mixed_scores = {}
            for num in range(1, 71):
                freq_score = frequencies[num] / max(frequencies.values()) if max(frequencies.values()) > 0 else 0
                gap_score = gaps[num] / max(gaps.values()) if max(gaps.values()) > 0 else 0
                mixed_scores[num] = (freq_score * 0.5) + (gap_score * 0.5)
            sorted_by_mixed = sorted(mixed_scores.items(), key=lambda x: x[1], reverse=True)
            predicted_numbers = [num for num, _ in sorted_by_mixed[:num_numbers]]
        
        elif method == 'fibonacci':
            # Pondération Fibonacci
            fib_weights = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55]
            fib_scores = {}
            for num in range(1, 71):
                score = 0
                for i, weight in enumerate(fib_weights[:min(len(recent_tirages), 10)]):
                    if i < len(recent_tirages):
                        row = recent_tirages.iloc[-(i+1)]
                        tirage_numbers = [row[f'numero_{j}'] for j in range(1, 21)]
                        if num in tirage_numbers:
                            score += weight
                fib_scores[num] = score
            sorted_by_fib = sorted(fib_scores.items(), key=lambda x: x[1], reverse=True)
            predicted_numbers = [num for num, _ in sorted_by_fib[:num_numbers]]
        
        elif method == 'sums':
            # Analyse des sommes
            recent_sums = []
            for _, row in recent_tirages.iterrows():
                numbers = [row[f'numero_{i}'] for i in range(1, 21)]
                recent_sums.append(sum(numbers))
            
            avg_sum = sum(recent_sums) / len(recent_sums)
            target_avg = avg_sum / 20  # Moyenne par numéro
            
            # Sélectionner des numéros autour de cette moyenne
            import random
            center = int(target_avg)
            predicted_numbers = []
            for i in range(num_numbers):
                offset = random.randint(-15, 15)
                num = max(1, min(70, center + offset))
                while num in predicted_numbers:
                    num = random.randint(1, 70)
                predicted_numbers.append(num)
        
        else:  # complete ou méthode inconnue
            # Analyse complète combinant toutes les méthodes
            complete_scores = {}
            for num in range(1, 71):
                freq_norm = frequencies[num] / max(frequencies.values()) if max(frequencies.values()) > 0 else 0
                gap_norm = gaps[num] / max(gaps.values()) if max(gaps.values()) > 0 else 0
                complete_scores[num] = (freq_norm * 0.4) + (gap_norm * 0.4) + (random.random() * 0.2)
            
            sorted_by_complete = sorted(complete_scores.items(), key=lambda x: x[1], reverse=True)
            predicted_numbers = [num for num, _ in sorted_by_complete[:num_numbers]]
        
        return sorted(predicted_numbers)
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération de prédiction traditionnelle: {str(e)}")
        # Prédiction aléatoire en cas d'erreur
        import random
        return sorted(random.sample(range(1, 71), num_numbers))

def calculate_traditional_confidence(method):
    """Calculer un score de confiance pour les méthodes traditionnelles."""
    confidence_map = {
        'frequency': 0.65,
        'gaps': 0.60,
        'cycles': 0.70,
        'mixed': 0.75,
        'fibonacci': 0.55,
        'sums': 0.50,
        'complete': 0.80
    }
    return confidence_map.get(method, 0.60)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

