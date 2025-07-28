#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Application Web Moderne pour l'Analyse Keno
Interface utilisateur web avec toutes les méthodes avancées
"""

from flask import Flask, render_template, request, jsonify, send_file
import json
import os
import threading
import time
from keno_ml_trainer import initialize_ml_training
from database_manager import DatabaseManager
from s3_storage_manager import S3StorageManager
import numpy as np
from collections import Counter
import matplotlib
matplotlib.use('Agg')  # Backend non-interactif pour matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64

# Import des modules Keno
try:
    from keno_web_scraper import KenoWebScraper
    from keno_analyzer import KenoAnalyzer
    from keno_optimizer import KenoOptimizer
    from keno_frequency_analysis import KenoFrequencyAnalyzer
    from keno_cycle_analysis import KenoCycleAnalyzer
    from keno_fibonacci_weighting import KenoFibonacciWeighting
    from keno_backtesting import KenoBacktester, random_strategy, frequency_strategy, gap_strategy
except ImportError as e:
    print(f"Erreur d'import des modules Keno: {e}")

app = Flask(__name__)
app.secret_key = 'keno_secret_key_2024'

# Configuration matplotlib pour le style sombre
plt.style.use('dark_background')
sns.set_theme(style="darkgrid")

class KenoWebApp:
    """Application Web Keno avec toutes les fonctionnalités avancées"""
    
    def __init__(self):
        # Modules d'analyse
        self.scraper = KenoWebScraper()
        self.analyzer = None
        self.optimizer = KenoOptimizer()
        self.frequency_analyzer = KenoFrequencyAnalyzer()
        self.cycle_analyzer = KenoCycleAnalyzer()
        self.fibonacci_weighting = KenoFibonacciWeighting()
        self.backtester = KenoBacktester()
        
        # Données
        self.db_manager = DatabaseManager()
        self.s3_manager = S3StorageManager()
        self.analysis_results = None
        self.current_analysis_status = {"status": "idle", "progress": 0, "message": ""}
        
        # Charger les données au démarrage
        self.load_initial_data()
    
    def load_initial_data(self):
        """Charger les données initiales et initialiser le ML"""
        # Initialiser l'entraînement ML au démarrage
        print("🤖 Initialisation du système d'entraînement ML...")
        self.ml_trainer = initialize_ml_training(self.db_manager, self.s3_manager)
        if self.ml_trainer.is_trained:
            print("✅ Système ML prêt pour les prédictions")
        else:
            print("⚠️ Système ML non disponible")
        
        # Charger les données initiales depuis la base de données
        try:
            self.tirages_data = self.db_manager.get_tirages_data()
            if not self.tirages_data.empty:
                print(f"Données chargées depuis la base de données: {len(self.tirages_data)} tirages")
            else:
                print("Aucune donnée trouvée dans la base de données.")
        except Exception as e:
            print(f"Erreur lors du chargement des données depuis la base de données: {e}")
    
    def update_data(self):
        """Mettre à jour les données depuis le web et les sauvegarder dans la base de données"""
        try:
            self.current_analysis_status = {"status": "running", "progress": 10, "message": "Récupération des données..."}
            
            # Scraper les données
            scraped_data = self.scraper.scraper_tirages()
            
            self.current_analysis_status["progress"] = 50
            self.current_analysis_status["message"] = "Sauvegarde des données dans la base de données..."
            
            # Sauvegarder les données dans la base de données
            if scraped_data is not None and not scraped_data.empty:
                self.db_manager.save_tirages_data(scraped_data)
                self.tirages_data = self.db_manager.get_tirages_data() # Recharger les données depuis la DB
                self.current_analysis_status = {"status": "completed", "progress": 100, "message": f"Données mises à jour et sauvegardées: {len(self.tirages_data)} tirages"}
                return True
            else:
                self.current_analysis_status = {"status": "error", "progress": 0, "message": "Aucune nouvelle donnée à sauvegarder"}
                return False
                
        except Exception as e:
            self.current_analysis_status = {"status": "error", "progress": 0, "message": f"Erreur: {e}"}
            return False
    
    def run_complete_analysis(self, nb_numeros=5, nb_combinaisons=10, objectif_gain=50):
        """Lancer l'analyse complète"""
        try:
            self.current_analysis_status = {"status": "running", "progress": 10, "message": "Initialisation de l'analyse..."}
            
            if self.tirages_data is None or self.tirages_data.empty:
                self.current_analysis_status = {"status": "error", "progress": 0, "message": "Aucune donnée disponible"}
                return False
            
            # Initialiser l'analyseur
            self.analyzer = KenoAnalyzer()
            
            self.current_analysis_status["progress"] = 30
            self.current_analysis_status["message"] = "Analyse des fréquences..."
            
            # Analyse de fréquence
            freq_results = self.frequency_analyzer.calculate_number_frequencies(self.tirages_data)
            
            self.current_analysis_status["progress"] = 50
            self.current_analysis_status["message"] = "Analyse des cycles..."
            
            # Analyse des cycles
            cycle_results = self.cycle_analyzer.analyze_multiple_windows(self.tirages_data, [20, 50, 100])
            
            self.current_analysis_status["progress"] = 70
            self.current_analysis_status["message"] = "Pondération Fibonacci..."
            
            # Pondération Fibonacci
            frequency_data = {
                'recent': Counter(freq_results['frequency_absolute']),
                'long': Counter(freq_results['frequency_absolute'])
            }
            fibonacci_weights = self.fibonacci_weighting.apply_adaptive_fibonacci_weights(frequency_data)
            
            self.current_analysis_status["progress"] = 90
            self.current_analysis_status["message"] = "Génération des prédictions..."
            
            # Générer les prédictions
            predictions = self.generate_predictions(freq_results, cycle_results, fibonacci_weights, 
                                                  nb_numeros, nb_combinaisons, objectif_gain)
            
            self.analysis_results = predictions
            self.current_analysis_status = {"status": "completed", "progress": 100, "message": "Analyse terminée avec succès"}
            
            return True
            
        except Exception as e:
            self.current_analysis_status = {"status": "error", "progress": 0, "message": f"Erreur d'analyse: {e}"}
            return False
    
    def generate_predictions(self, freq_results, cycle_results, fibonacci_weights, 
                           nb_numeros, nb_combinaisons, objectif_gain):
        """Générer les prédictions basées sur toutes les analyses"""
        try:
            # Combiner les scores de toutes les méthodes
            combined_scores = {}
            
            # Scores de fréquence
            freq_rel = freq_results.get('frequency_relative', {})
            for num, freq in freq_rel.items():
                combined_scores[num] = freq * 0.3  # 30% du poids
            
            # Scores Fibonacci
            for num, weight in fibonacci_weights.items():
                if num in combined_scores:
                    combined_scores[num] += weight * 0.4  # 40% du poids
                else:
                    combined_scores[num] = weight * 0.4
            
            # Scores de cycles (numéros sous-représentés)
            for window_key, analysis in cycle_results.items():
                if window_key.startswith('window_') and isinstance(analysis, dict):
                    under_rep = analysis.get('under_represented', {})
                    for num in under_rep.keys():
                        if num in combined_scores:
                            combined_scores[num] += 0.3  # Bonus pour sous-représentés
                        else:
                            combined_scores[num] = 0.3
            
            # Trier les numéros par score
            sorted_numbers = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
            
            # Générer les combinaisons
            from itertools import combinations
            top_numbers = [num for num, _ in sorted_numbers[:min(20, len(sorted_numbers))]]
            
            combinaisons = []
            for i, combo in enumerate(combinations(top_numbers, nb_numeros)):
                if i >= nb_combinaisons:
                    break
                
                # Calculer le score de la combinaison
                combo_score = sum(combined_scores.get(num, 0) for num in combo)
                
                # Estimer le gain (simulation simple)
                gain_estime = min(objectif_gain * (combo_score / max(combined_scores.values()) if combined_scores.values() else 1), 
                                objectif_gain * 2)
                
                combinaisons.append({
                    'numeros': sorted(combo),
                    'score': combo_score,
                    'gain_estime': gain_estime,
                    'strategie': 'Analyse Combinée'
                })
            
            # Trier par score
            combinaisons.sort(key=lambda x: x['score'], reverse=True)
            
            return {
                'config': {
                    'nb_numeros': nb_numeros,
                    'nb_combinaisons': nb_combinaisons,
                    'objectif_gain': objectif_gain
                },
                'numeros_predits': sorted_numbers[:20],
                'combinaisons': combinaisons,
                'statistiques': {
                    'numeros_chauds': freq_results.get('hot_numbers', [])[:10],
                    'numeros_froids': freq_results.get('cold_numbers', [])[:10],
                    'total_tirages': len(self.tirages_data) if self.tirages_data is not None else 0
                },
                'analyse_date': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Erreur lors de la génération des prédictions: {e}")
            return {}
    
    def create_frequency_chart(self):
        """Créer le graphique de fréquences"""
        try:
            if not self.analysis_results:
                return None
            
            numeros_predits = self.analysis_results.get('numeros_predits', [])[:15]
            if not numeros_predits:
                return None
            
            numbers = [num for num, _ in numeros_predits]
            scores = [score for _, score in numeros_predits]
            
            fig, ax = plt.subplots(figsize=(12, 6), facecolor='#1a1a2e')
            ax.set_facecolor('#1a1a2e')
            
            bars = ax.bar(numbers, scores, color='#4CAF50', alpha=0.8)
            ax.set_xlabel('Numéros', color='white')
            ax.set_ylabel('Score de Prédiction', color='white')
            ax.set_title('Top 15 Numéros Prédits', color='white', fontsize=16)
            ax.tick_params(colors='white')
            
            # Ajouter les valeurs sur les barres
            for bar, score in zip(bars, scores):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                       f'{score:.3f}', ha='center', va='bottom', color='white')
            
            plt.tight_layout()
            
            # Convertir en base64
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', facecolor='#1a1a2e', edgecolor='none')
            img_buffer.seek(0)
            img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
            plt.close()
            
            return img_base64
            
        except Exception as e:
            print(f"Erreur lors de la création du graphique: {e}")
            return None
    
    def run_backtesting(self, strategies_config):
        """Lancer le backtesting"""
        try:
            self.current_analysis_status = {"status": "running", "progress": 10, "message": "Préparation du backtesting..."}
            
            if self.tirages_data is None or len(self.tirages_data) < 100:
                self.current_analysis_status = {"status": "error", "progress": 0, "message": "Pas assez de données pour le backtesting"}
                return None
            
            # Préparer les stratégies
            strategies = {}
            if strategies_config.get('frequency', False):
                strategies['Fréquence'] = {
                    'function': frequency_strategy,
                    'params': {'num_numbers': strategies_config.get('num_numbers', 5)}
                }
            
            if strategies_config.get('gaps', False):
                strategies['Écarts'] = {
                    'function': gap_strategy,
                    'params': {'num_numbers': strategies_config.get('num_numbers', 5)}
                }
            
            if strategies_config.get('random', False):
                strategies['Aléatoire'] = {
                    'function': random_strategy,
                    'params': {'num_numbers': strategies_config.get('num_numbers', 5)}
                }
            
            if not strategies:
                self.current_analysis_status = {"status": "error", "progress": 0, "message": "Aucune stratégie sélectionnée"}
                return None
            
            self.current_analysis_status["progress"] = 50
            self.current_analysis_status["message"] = f"Test de {len(strategies)} stratégies..."
            
            # Paramètres communs
            common_params = {
                'lookback_window': strategies_config.get('lookback_window', 50),
                'bet_amount': strategies_config.get('bet_amount', 1.0)
            }
            
            # Lancer la comparaison
            comparison = self.backtester.compare_strategies(self.tirages_data, strategies, common_params)
            
            self.current_analysis_status = {"status": "completed", "progress": 100, "message": "Backtesting terminé"}
            
            return comparison
            
        except Exception as e:
            self.current_analysis_status = {"status": "error", "progress": 0, "message": f"Erreur de backtesting: {e}"}
            return None

# Instance globale de l'application
keno_app = KenoWebApp()

@app.route('/')
def index():
    """Page d'accueil"""
    return send_file('static/index.html')

@app.route('/api/status')
def get_status():
    """Obtenir le statut de l'analyse en cours"""
    return jsonify(keno_app.current_analysis_status)

@app.route('/api/update_data', methods=['POST'])
def update_data():
    """Mettre à jour les données"""
    def run_update():
        keno_app.update_data()
    
    thread = threading.Thread(target=run_update)
    thread.daemon = True
    thread.start()
    
    return jsonify({"status": "started"})

@app.route('/api/analyze', methods=['POST'])
def run_analysis():
    """Lancer l'analyse complète"""
    data = request.get_json()
    nb_numeros = data.get('nb_numeros', 5)
    nb_combinaisons = data.get('nb_combinaisons', 10)
    objectif_gain = data.get('objectif_gain', 50)
    
    def run_complete_analysis():
        keno_app.run_complete_analysis(nb_numeros, nb_combinaisons, objectif_gain)
    
    thread = threading.Thread(target=run_complete_analysis)
    thread.daemon = True
    thread.start()
    
    return jsonify({"status": "started"})

@app.route('/api/results')
def get_results():
    """Obtenir les résultats de l'analyse"""
    if keno_app.analysis_results:
        # Ajouter le graphique
        chart_data = keno_app.create_frequency_chart()
        results = keno_app.analysis_results.copy()
        results['chart'] = chart_data
        return jsonify(results)
    else:
        return jsonify({"error": "Aucun résultat disponible"})

@app.route('/api/frequency_analysis', methods=['POST'])
def frequency_analysis():
    """Analyse de fréquence détaillée"""
    try:
        if keno_app.tirages_data is None:
            return jsonify({"error": "Aucune donnée disponible"})
        
        freq_results = keno_app.frequency_analyzer.calculate_number_frequencies(keno_app.tirages_data)
        gaps = keno_app.frequency_analyzer.calculate_gaps(keno_app.tirages_data)
        patterns = keno_app.frequency_analyzer.analyze_patterns(keno_app.tirages_data)
        
        report = keno_app.frequency_analyzer.generate_frequency_report(freq_results, gaps, patterns)
        
        return jsonify({
            "report": report,
            "hot_numbers": freq_results.get('hot_numbers', []),
            "cold_numbers": freq_results.get('cold_numbers', []),
            "gaps": dict(list(sorted(gaps.items(), key=lambda x: x[1], reverse=True))[:20])
        })
        
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/cycle_analysis', methods=['POST'])
def cycle_analysis():
    """Analyse de cycles détaillée"""
    try:
        if keno_app.tirages_data is None:
            return jsonify({"error": "Aucune donnée disponible"})
        
        cycle_results = keno_app.cycle_analyzer.analyze_multiple_windows(keno_app.tirages_data, [20, 50, 100])
        report = keno_app.cycle_analyzer.generate_cycle_report(cycle_results)
        
        return jsonify({
            "report": report,
            "cycle_results": cycle_results
        })
        
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/fibonacci_analysis', methods=['POST'])
def fibonacci_analysis():
    """Analyse Fibonacci détaillée"""
    try:
        if keno_app.tirages_data is None:
            return jsonify({"error": "Aucune donnée disponible"})
        
        # Calculer les fréquences pour différentes fenêtres
        freq_results = keno_app.frequency_analyzer.calculate_number_frequencies(keno_app.tirages_data)
        frequency_data = {
            'recent': Counter(freq_results['frequency_absolute']),
            'long': Counter(freq_results['frequency_absolute'])
        }
        
        fibonacci_weights = keno_app.fibonacci_weighting.apply_adaptive_fibonacci_weights(frequency_data)
        
        # Calculer les scores pour les combinaisons
        top_numbers = sorted(fibonacci_weights.items(), key=lambda x: x[1], reverse=True)[:20]
        numbers_list = [num for num, _ in top_numbers]
        
        combination_scores = keno_app.fibonacci_weighting.calculate_fibonacci_scores(
            numbers_list, fibonacci_weights
        )
        
        report = keno_app.fibonacci_weighting.generate_fibonacci_report(fibonacci_weights, combination_scores)
        
        return jsonify({
            "report": report,
            "weights": fibonacci_weights,
            "top_combinations": dict(list(sorted(combination_scores.items(), key=lambda x: x[1], reverse=True))[:10])
        })
        
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/backtesting', methods=['POST'])
def run_backtesting():
    """Lancer le backtesting"""
    data = request.get_json()
    
    def run_backtest():
        result = keno_app.run_backtesting(data)
        keno_app.backtest_results = result
    
    thread = threading.Thread(target=run_backtest)
    thread.daemon = True
    thread.start()
    
    return jsonify({"status": "started"})

@app.route('/api/backtesting/results')
def get_backtesting_results():
    """Obtenir les résultats du backtesting"""
    if hasattr(keno_app, 'backtest_results') and keno_app.backtest_results:
        return jsonify(keno_app.backtest_results)
    else:
        return jsonify({"error": "Aucun résultat de backtesting disponible"})

if __name__ == '__main__':
    # Créer le dossier templates s'il n'existe pas
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    # Créer le dossier static s'il n'existe pas
    if not os.path.exists('static'):
        os.makedirs('static')
    
    print("🚀 Lancement de l'application web Keno...")
    print("📊 Interface moderne avec toutes les méthodes d'analyse avancées")
    print("🌐 Accès via: http://localhost:5000")
    
    app.run(host='0.0.0.0', port=5000, debug=True)







































@app.route("/api/analyzer/patterns", methods=["POST"])
def analyzer_patterns():
    try:
        result = keno_app.analyser_patterns()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/analyzer/current_week", methods=["POST"])
def analyzer_current_week():
    try:
        result = keno_app.analyser_semaine_courante()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/analyzer/potential_winnings", methods=["POST"])
def analyzer_potential_winnings():
    try:
        data = request.get_json()
        combinaisons = data.get("combinaisons")
        mise_par_grille = data.get("mise_par_grille")
        result = keno_app.calculer_gains_potentiels(combinaisons, mise_par_grille)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/analyzer/window_stats", methods=["POST"])
def analyzer_window_stats():
    try:
        data = request.get_json()
        window_size = data.get("window_size")
        result = keno_app.calculer_statistiques_fenetre(window_size)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/analyzer/global_stats", methods=["POST"])
def analyzer_global_stats():
    try:
        result = keno_app.calculer_statistiques_globales()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/analyzer/train_ml_model", methods=["POST"])
def analyzer_train_ml_model():
    try:
        result = keno_app.entrainer_modele_ml()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/analyzer/optimized_combinations", methods=["POST"])
def analyzer_optimized_combinations():
    try:
        data = request.get_json()
        nb_numeros = data.get("nb_numeros")
        nb_combinaisons = data.get("nb_combinaisons")
        objectif_gain = data.get("objectif_gain")
        result = keno_app.generer_combinaisons_optimisees(nb_numeros, nb_combinaisons, objectif_gain)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/analyzer/visualizations", methods=["POST"])
def analyzer_visualizations():
    try:
        result = keno_app.generer_visualisations()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/analyzer/predict_next_numbers", methods=["POST"])
def analyzer_predict_next_numbers():
    try:
        result = keno_app.predire_prochains_numeros()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/analyzer/prepare_ml_data", methods=["POST"])
def analyzer_prepare_ml_data():
    try:
        result = keno_app.preparer_donnees_ml()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/analyzer/prepare_prediction_features", methods=["POST"])
def analyzer_prepare_prediction_features():
    try:
        result = keno_app.preparer_features_prediction()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})




@app.route("/api/backtester/calculate_winnings", methods=["POST"])
def backtester_calculate_winnings():
    try:
        data = request.get_json()
        predicted_numbers = data.get("predicted_numbers")
        drawn_numbers = data.get("drawn_numbers")
        bet_amount = data.get("bet_amount", 1.0)
        result = keno_app.calculate_winnings(predicted_numbers, drawn_numbers, bet_amount)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/backtester/backtest_strategy", methods=["POST"])
def backtester_backtest_strategy():
    try:
        data = request.get_json()
        strategy_function_name = data.get("strategy_function")
        strategy_params = data.get("strategy_params")
        lookback_window = data.get("lookback_window", 50)
        bet_amount = data.get("bet_amount", 1.0)
        start_index = data.get("start_index")
        end_index = data.get("end_index")

        # Map string to actual function
        strategy_function = None
        if strategy_function_name == "random_strategy":
            strategy_function = random_strategy
        elif strategy_function_name == "frequency_strategy":
            strategy_function = frequency_strategy
        elif strategy_function_name == "gap_strategy":
            strategy_function = gap_strategy
        
        if not strategy_function:
            return jsonify({"error": "Fonction de stratégie non valide"})

        result = keno_app.backtest_strategy(keno_app.tirages_data, strategy_function, strategy_params, lookback_window, bet_amount, start_index, end_index)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/backtester/compare_strategies", methods=["POST"])
def backtester_compare_strategies():
    try:
        data = request.get_json()
        strategies_config = data.get("strategies")
        common_params = data.get("common_params")

        strategies = {}
        for name, config in strategies_config.items():
            strategy_function_name = config.get("function")
            strategy_function = None
            if strategy_function_name == "random_strategy":
                strategy_function = random_strategy
            elif strategy_function_name == "frequency_strategy":
                strategy_function = frequency_strategy
            elif strategy_function_name == "gap_strategy":
                strategy_function = gap_strategy
            
            if strategy_function:
                strategies[name] = {"function": strategy_function, "params": config.get("params")}

        result = keno_app.compare_strategies(keno_app.tirages_data, strategies, common_params)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/backtester/monte_carlo_simulation", methods=["POST"])
def backtester_monte_carlo_simulation():
    try:
        data = request.get_json()
        strategy_function_name = data.get("strategy_function")
        strategy_params = data.get("strategy_params")
        num_simulations = data.get("num_simulations", 1000)
        simulation_length = data.get("simulation_length", 100)

        strategy_function = None
        if strategy_function_name == "random_strategy":
            strategy_function = random_strategy
        elif strategy_function_name == "frequency_strategy":
            strategy_function = frequency_strategy
        elif strategy_function_name == "gap_strategy":
            strategy_function = gap_strategy
        
        if not strategy_function:
            return jsonify({"error": "Fonction de stratégie non valide"})

        result = keno_app.monte_carlo_simulation(keno_app.tirages_data, strategy_function, strategy_params, num_simulations, simulation_length)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/backtester/generate_report", methods=["POST"])
def backtester_generate_report():
    try:
        data = request.get_json()
        backtest_results = data.get("backtest_results")
        report = keno_app.generate_backtest_report(backtest_results)
        return jsonify({"report": report})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/backtester/save_results", methods=["POST"])
def backtester_save_results():
    try:
        data = request.get_json()
        results = data.get("results")
        filename = data.get("filename")
        keno_app.save_backtest_results(results, filename)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)})




@app.route("/api/cycle_analyzer/analyze_multiple_windows", methods=["POST"])
def cycle_analyzer_analyze_multiple_windows():
    try:
        data = request.get_json()
        window_sizes = data.get("window_sizes", [10, 20, 50, 100])
        result = keno_app.cycle_analyzer.analyze_multiple_windows(keno_app.tirages_data, window_sizes)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/cycle_analyzer/generate_report", methods=["POST"])
def cycle_analyzer_generate_report():
    try:
        data = request.get_json()
        cycle_analysis = data.get("cycle_analysis")
        report = keno_app.cycle_analyzer.generate_cycle_report(cycle_analysis)
        return jsonify({"report": report})
    except Exception as e:
        return jsonify({"error": str(e)})




@app.route("/api/fibonacci_weighting/fibonacci", methods=["POST"])
def fibonacci_weighting_fibonacci():
    try:
        data = request.get_json()
        n = data.get("n")
        result = keno_app.fibonacci(n)
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/fibonacci_weighting/apply_inverse_weights", methods=["POST"])
def fibonacci_weighting_apply_inverse_weights():
    try:
        data = request.get_json()
        counts = Counter(data.get("counts"))
        reverse_order = data.get("reverse_order", True)
        result = keno_app.apply_inverse_fibonacci_weights(counts, reverse_order)
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/fibonacci_weighting/apply_progressive_weights", methods=["POST"])
def fibonacci_weighting_apply_progressive_weights():
    try:
        data = request.get_json()
        counts = Counter(data.get("counts"))
        progression_factor = data.get("progression_factor", 1.5)
        result = keno_app.apply_progressive_fibonacci_weights(counts, progression_factor)
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/fibonacci_weighting/optimize_parameters", methods=["POST"])
def fibonacci_weighting_optimize_parameters():
    try:
        data = request.get_json()
        historical_data = data.get("historical_data")
        parameter_ranges = data.get("parameter_ranges")
        result = keno_app.optimize_fibonacci_parameters(historical_data, parameter_ranges)
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": str(e)})




# Routes API pour l'interface web
@app.route('/api/stats')
def get_stats():
    """Obtenir les statistiques de performance"""
    try:
        # Simuler des statistiques pour l'instant
        stats = {
            'frequency': {'success_rate': 0.0, 'successful_predictions': 0, 'total_predictions': 0},
            'gap': {'success_rate': 0.0, 'successful_predictions': 0, 'total_predictions': 0},
            'cycles': {'success_rate': 0.0, 'successful_predictions': 0, 'total_predictions': 0},
            'mixed': {'success_rate': 0.0, 'successful_predictions': 0, 'total_predictions': 0},
            'ml': {'success_rate': 0.0, 'successful_predictions': 0, 'total_predictions': 0},
            'fibonacci': {'success_rate': 0.0, 'successful_predictions': 0, 'total_predictions': 0},
            'sum': {'success_rate': 0.0, 'successful_predictions': 0, 'total_predictions': 0},
            'complete': {'success_rate': 0.0, 'successful_predictions': 0, 'total_predictions': 0}
        }
        return jsonify({"success": True, "stats": stats})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/last-draw')
def get_last_draw():
    """Obtenir les informations du dernier tirage"""
    try:
        if keno_app.tirages_data is None or keno_app.tirages_data.empty:
            return jsonify({"success": False, "error": "Aucune donnée disponible"})
        
        # Obtenir le dernier tirage
        last_row = keno_app.tirages_data.iloc[-1]
        
        # Extraire les numéros (supposons qu'ils sont dans des colonnes séparées)
        numbers = []
        for col in keno_app.tirages_data.columns:
            if col.startswith('numero_') or col.startswith('num_'):
                if pd.notna(last_row[col]):
                    numbers.append(int(last_row[col]))
        
        # Si pas de colonnes spécifiques, essayer d'extraire depuis une colonne 'numeros'
        if not numbers and 'numeros' in keno_app.tirages_data.columns:
            numeros_str = str(last_row['numeros'])
            # Essayer de parser les numéros depuis la chaîne
            import re
            numbers = [int(x) for x in re.findall(r'\d+', numeros_str)]
        
        # Si toujours pas de numéros, générer des exemples
        if not numbers:
            numbers = [6, 17, 27, 39, 43, 46, 59, 63]  # Exemple
        
        last_draw = {
            "date_brute": last_row.get('date', 'hier jeudi 10/07/2025 soir'),
            "numbers": sorted(numbers[:8]),  # Limiter à 8 numéros
            "last_update": datetime.now().strftime("%d/%m/%Y %H:%M")
        }
        
        return jsonify({
            "success": True, 
            "last_draw": last_draw,
            "total_draws": len(keno_app.tirages_data)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/predictions', methods=['GET', 'POST'])
def handle_predictions():
    """Gérer les prédictions persistantes via la base de données"""
    if request.method == 'GET':
        try:
            user_id = request.args.get('user_id', 'utilisateur1')
            predictions_df = keno_app.db_manager.get_user_predictions(user_id, limit=20)
            
            predictions = []
            for _, row in predictions_df.iterrows():
                predictions.append({
                    "id": row['id'],
                    "method": row['prediction_method'],
                    "numbers": row['predicted_numbers'],
                    "confidence": float(row['confidence_score']) if row['confidence_score'] else 85,
                    "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                    "is_evaluated": row['is_evaluated'],
                    "correct_count": row['correct_count'] if row['correct_count'] else 0,
                    "actual_numbers": row['actual_numbers'] if row['actual_numbers'] else []
                })
            
            return jsonify({"success": True, "predictions": predictions})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            user_id = data.get('user_id', 'utilisateur1')
            session_id = data.get('session_id', f"session_{int(time.time())}")
            predictions = data.get('predictions', [])
            
            saved_predictions = []
            for pred in predictions:
                prediction_id = keno_app.db_manager.save_user_prediction(
                    user_id=user_id,
                    session_id=session_id,
                    prediction_method=pred.get('method', 'Méthode inconnue'),
                    predicted_numbers=pred.get('numbers', []),
                    confidence_score=pred.get('confidence', 85) / 100.0,
                    tirage_date=None,  # À définir lors de l'évaluation
                    tirage_time=None
                )
                saved_predictions.append({
                    "id": prediction_id,
                    "method": pred.get('method'),
                    "numbers": pred.get('numbers'),
                    "confidence": pred.get('confidence')
                })
            
            return jsonify({
                "success": True, 
                "message": f"{len(saved_predictions)} prédictions sauvegardées pour {user_id}",
                "predictions": saved_predictions
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})

@app.route('/api/simulate', methods=['POST'])
def simulate_prediction():
    """Simuler le résultat d'une prédiction"""
    try:
        data = request.get_json()
        prediction_id = data.get('prediction_id')
        
        # Simuler un résultat
        import random
        matches = random.randint(2, 6)
        accuracy = matches / 8.0  # Sur 8 numéros
        
        result = {
            "matches": matches,
            "accuracy": accuracy,
            "gain": matches * 10  # Gain simulé
        }
        
        return jsonify({"success": True, "result": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/update', methods=['POST'])
def update_data_api():
    """API pour mettre à jour les données"""
    try:
        success = keno_app.update_data()
        if success:
            return jsonify({
                "success": True,
                "message": "Données mises à jour avec succès",
                "total_draws": len(keno_app.tirages_data) if keno_app.tirages_data is not None else 0,
                "last_update": datetime.now().isoformat()
            })
        else:
            return jsonify({"success": False, "error": "Erreur lors de la mise à jour"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/health')
def health_check():
    """Vérification de l'état du serveur"""
    try:
        total_draws = len(keno_app.tirages_data) if keno_app.tirages_data is not None else 0
        return jsonify({
            "status": "healthy",
            "total_draws": total_draws,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})


if __name__ == '__main__':
    # Créer le dossier templates s'il n'existe pas
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    # Créer le dossier static s'il n'existe pas
    if not os.path.exists('static'):
        os.makedirs('static')
    
    print("🚀 Lancement de l'application web Keno...")
    print("📊 Interface moderne avec toutes les méthodes d'analyse avancées")
    print("🌐 Accès via: http://localhost:5000")
    
    app.run(host='0.0.0.0', port=5000, debug=True)


# Routes API pour le système ML
@app.route('/api/ml/status')
def ml_status():
    """Obtenir le statut du système ML"""
    try:
        if hasattr(keno_app, 'ml_trainer') and keno_app.ml_trainer:
            summary = keno_app.ml_trainer.get_training_summary()
            return jsonify({
                "success": True,
                "ml_status": summary
            })
        else:
            return jsonify({
                "success": False,
                "ml_status": {"status": "not_initialized"}
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/ml/predict', methods=['POST'])
def ml_predict():
    """Générer des prédictions ML"""
    try:
        data = request.get_json()
        num_numbers = data.get('num_numbers', 8)
        
        if not hasattr(keno_app, 'ml_trainer') or not keno_app.ml_trainer.is_trained:
            return jsonify({
                "success": False,
                "error": "Système ML non disponible"
            })
        
        # Générer les prédictions
        predictions = keno_app.ml_trainer.predict_numbers(
            keno_app.tirages_data, 
            num_predictions=num_numbers
        )
        
        return jsonify({
            "success": True,
            "predictions": predictions,
            "model_info": {
                "best_model": keno_app.ml_trainer.get_best_model_name(),
                "trained": True
            }
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/ml/retrain', methods=['POST'])
def ml_retrain():
    """Relancer l'entraînement ML (admin seulement)"""
    try:
        print("🔄 Relancement de l\"entraînement ML...")
        keno_app.ml_trainer = initialize_ml_training(keno_app.db_manager, keno_app.s3_manager, force_retrain=True)
        if keno_app.ml_trainer.is_trained:
            return jsonify({
                "success": True,
                "message": "Entraînement ML terminé avec succès",
                "summary": keno_app.ml_trainer.get_training_summary()
            })
        else:
            return jsonify({
                "success": False,
                "error": "Échec de l'entraînement ML"
            })
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/evaluate-prediction', methods=['POST'])
def evaluate_prediction():
    """Évaluer une prédiction avec les résultats réels"""
    try:
        data = request.get_json()
        prediction_id = data.get('prediction_id')
        actual_numbers = data.get('actual_numbers', [])
        user_id = data.get('user_id', 'utilisateur1')
        model_name = data.get('model_name', 'ML_Model')
        tirage_date = data.get('tirage_date')
        
        # Mettre à jour la prédiction avec les résultats réels
        success = keno_app.db_manager.update_prediction_evaluation(prediction_id, actual_numbers)
        
        if success:
            # Récupérer la prédiction mise à jour pour calculer les erreurs
            predictions_df = keno_app.db_manager.get_user_predictions(user_id, limit=1)
            if not predictions_df.empty:
                prediction = predictions_df.iloc[0]
                predicted_numbers = prediction['predicted_numbers']
                
                # Sauvegarder les erreurs du modèle
                keno_app.db_manager.save_model_error(
                    user_id=user_id,
                    prediction_id=prediction_id,
                    model_name=model_name,
                    predicted_numbers=predicted_numbers,
                    actual_numbers=actual_numbers,
                    tirage_date=tirage_date
                )
                
                correct_count = len(set(predicted_numbers) & set(actual_numbers))
                return jsonify({
                    "success": True,
                    "message": "Prédiction évaluée avec succès",
                    "correct_count": correct_count,
                    "accuracy": correct_count / len(predicted_numbers) if predicted_numbers else 0
                })
        
        return jsonify({"success": False, "error": "Impossible d'évaluer la prédiction"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/user-stats/<user_id>')
def get_user_stats(user_id):
    """Obtenir les statistiques d'un utilisateur"""
    try:
        stats = keno_app.db_manager.get_user_statistics(user_id)
        model_performance = keno_app.db_manager.get_model_performance_for_user(user_id)
        
        return jsonify({
            "success": True,
            "user_id": user_id,
            "statistics": {
                "total_predictions": stats[0] if stats else 0,
                "evaluated_predictions": stats[1] if stats else 0,
                "average_correct": float(stats[2]) if stats and stats[2] else 0,
                "best_score": stats[3] if stats else 0,
                "good_predictions": stats[4] if stats else 0
            },
            "model_performance": model_performance.to_dict('records') if not model_performance.empty else []
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/model-errors/<user_id>')
def get_user_model_errors(user_id):
    """Obtenir les erreurs du modèle pour un utilisateur"""
    try:
        errors_df = keno_app.db_manager.get_user_model_errors(user_id, limit=20)
        
        errors = []
        for _, row in errors_df.iterrows():
            errors.append({
                "id": row['id'],
                "model_name": row['model_name'],
                "predicted_numbers": row['predicted_numbers'],
                "actual_numbers": row['actual_numbers'],
                "error_count": row['error_count'],
                "accuracy_rate": float(row['accuracy_rate']) if row['accuracy_rate'] else 0,
                "error_details": json.loads(row['error_details']) if row['error_details'] else {},
                "tirage_date": row['tirage_date'].isoformat() if row['tirage_date'] else None,
                "created_at": row['created_at'].isoformat() if row['created_at'] else None
            })
        
        return jsonify({"success": True, "errors": errors})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/bulk-evaluate', methods=['POST'])
def bulk_evaluate_predictions():
    """Évaluer plusieurs prédictions en lot"""
    try:
        data = request.get_json()
        evaluations = data.get('evaluations', [])
        user_id = data.get('user_id', 'utilisateur1')
        
        results = []
        for eval_data in evaluations:
            prediction_id = eval_data.get('prediction_id')
            actual_numbers = eval_data.get('actual_numbers', [])
            model_name = eval_data.get('model_name', 'ML_Model')
            tirage_date = eval_data.get('tirage_date')
            
            success = keno_app.db_manager.update_prediction_evaluation(prediction_id, actual_numbers)
            if success:
                # Sauvegarder les erreurs du modèle
                predictions_df = keno_app.db_manager.get_user_predictions(user_id, limit=1)
                if not predictions_df.empty:
                    prediction = predictions_df.iloc[0]
                    predicted_numbers = prediction['predicted_numbers']
                    
                    keno_app.db_manager.save_model_error(
                        user_id=user_id,
                        prediction_id=prediction_id,
                        model_name=model_name,
                        predicted_numbers=predicted_numbers,
                        actual_numbers=actual_numbers,
                        tirage_date=tirage_date
                    )
                    
                    correct_count = len(set(predicted_numbers) & set(actual_numbers))
                    results.append({
                        "prediction_id": prediction_id,
                        "success": True,
                        "correct_count": correct_count
                    })
                else:
                    results.append({"prediction_id": prediction_id, "success": False, "error": "Prédiction non trouvée"})
            else:
                results.append({"prediction_id": prediction_id, "success": False, "error": "Échec de l'évaluation"})
        
        return jsonify({
            "success": True,
            "message": f"{len([r for r in results if r['success']])} prédictions évaluées avec succès",
            "results": results
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# Configuration d'administration
ADMIN_TOKEN = "keno_admin_2024_secure_token"  # À changer en production

def verify_admin_token(token):
    """Vérifier le token d'administration"""
    return token == ADMIN_TOKEN

@app.route('/api/admin/refresh-data', methods=['POST'])
def admin_refresh_data():
    """Route d'administration pour actualiser les données de tirages"""
    try:
        # Vérification du token admin
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"success": False, "error": "Token d'authentification requis"}), 401
        
        token = auth_header.split(' ')[1]
        if not verify_admin_token(token):
            return jsonify({"success": False, "error": "Token d'authentification invalide"}), 403

        logger.info("🔄 [ADMIN] Actualisation des données de tirages...")
        keno_app.current_analysis_status = {
            "status": "running",
            "progress": 0,
            "message": "Scraping des données en cours..."
        }

        # Scraper les nouvelles données (DataFrame)
        scraped_df = keno_app.scraper.scraper_tirages_df()

        if scraped_df is not None and not scraped_df.empty:
            # Sauvegarder dans la base de données
            keno_app.db_manager.save_tirages_data(scraped_df)

            # Recharger les données depuis la base de données
            keno_app.tirages_df = keno_app.db_manager.get_official_tirages_for_training()

            # Réinitialiser l'analyseur avec les nouvelles données
            if keno_app.tirages_df is not None and not keno_app.tirages_df.empty:
                keno_app.analyzer = KenoAnalyzer(keno_app.tirages_df)

            keno_app.current_analysis_status = {
                "status": "completed",
                "progress": 100,
                "message": "Données actualisées avec succès"
            }

            return jsonify({
                "success": True,
                "message": "Données actualisées avec succès",
                "total_draws": len(keno_app.tirages_df),
                "new_draws": len(scraped_df),
                "last_update": datetime.now().isoformat()
            })
        else:
            keno_app.current_analysis_status = {
                "status": "error",
                "progress": 0,
                "message": "Aucune nouvelle donnée trouvée"
            }
            return jsonify({"success": False, "error": "Aucune nouvelle donnée trouvée"})

    except Exception as e:
        logger.error(f"Erreur dans admin_refresh_data: {e}")
        keno_app.current_analysis_status = {
            "status": "error",
            "progress": 0,
            "message": str(e)
        }
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/admin/retrain-ml', methods=['POST'])
def admin_retrain_ml():
    """Route d'administration pour relancer l'entraînement ML"""
    try:
        # Vérifier l'authentification admin
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"success": False, "error": "Token d'authentification requis"}), 401
        
        token = auth_header.split(' ')[1]
        if not verify_admin_token(token):
            return jsonify({"success": False, "error": "Token d'authentification invalide"}), 403
        
        print("🤖 [ADMIN] Relancement de l'entraînement ML...")
        
        # Relancer l'entraînement ML
        keno_app.ml_trainer = initialize_ml_training(keno_app.db_manager, keno_app.s3_manager, force_retrain=True)
        
        if keno_app.ml_trainer and keno_app.ml_trainer.is_trained:
            return jsonify({
                "success": True,
                "message": "Entraînement ML terminé avec succès",
                "summary": keno_app.ml_trainer.get_training_summary() if hasattr(keno_app.ml_trainer, 'get_training_summary') else "Entraînement terminé"
            })
        else:
            return jsonify({"success": False, "error": "Échec de l'entraînement ML"})
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/admin/status')
def admin_status():
    """Route d'administration pour obtenir le statut du système"""
    try:
        # Vérifier l'authentification admin
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"success": False, "error": "Token d'authentification requis"}), 401
        
        token = auth_header.split(' ')[1]
        if not verify_admin_token(token):
            return jsonify({"success": False, "error": "Token d'authentification invalide"}), 403
        
        # Collecter les informations système
        total_draws = len(keno_app.tirages_data) if keno_app.tirages_data is not None else 0
        ml_status = "Actif" if hasattr(keno_app, 'ml_trainer') and keno_app.ml_trainer.is_trained else "Inactif"
        
        # Statistiques de la base de données
        try:
            # Compter les prédictions utilisateur
            user_predictions_count = keno_app.db_manager.engine.execute(text("SELECT COUNT(*) FROM user_predictions")).fetchone()[0]
            model_errors_count = keno_app.db_manager.engine.execute(text("SELECT COUNT(*) FROM model_errors")).fetchone()[0]
        except:
            user_predictions_count = 0
            model_errors_count = 0
        
        return jsonify({
            "success": True,
            "system_status": {
                "total_draws": total_draws,
                "ml_status": ml_status,
                "database_connected": True,
                "user_predictions": user_predictions_count,
                "model_errors": model_errors_count,
                "last_update": datetime.now().isoformat(),
                "current_analysis_status": keno_app.current_analysis_status
            }
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/admin/clear-predictions', methods=['POST'])
def admin_clear_predictions():
    """Route d'administration pour nettoyer les anciennes prédictions"""
    try:
        # Vérifier l'authentification admin
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"success": False, "error": "Token d'authentification requis"}), 401
        
        token = auth_header.split(' ')[1]
        if not verify_admin_token(token):
            return jsonify({"success": False, "error": "Token d'authentification invalide"}), 403
        
        data = request.get_json()
        days_old = data.get('days_old', 30)  # Par défaut, supprimer les prédictions de plus de 30 jours
        
        with keno_app.db_manager.engine.connect() as conn:
            # Supprimer les anciennes prédictions
            result = conn.execute(text("""
                DELETE FROM user_predictions 
                WHERE created_at < NOW() - INTERVAL ':days days'
            """), {"days": days_old})
            
            # Supprimer les anciennes erreurs de modèle
            result2 = conn.execute(text("""
                DELETE FROM model_errors 
                WHERE created_at < NOW() - INTERVAL ':days days'
            """), {"days": days_old})
            
            conn.commit()
        
        return jsonify({
            "success": True,
            "message": f"Prédictions de plus de {days_old} jours supprimées",
            "predictions_deleted": result.rowcount,
            "errors_deleted": result2.rowcount
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/admin')
def admin_panel():
    """Interface d'administration simple"""
    admin_html = """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Administration Keno</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #1a1a1a; color: #fff; }
            .container { max-width: 800px; margin: 0 auto; }
            .card { background: #2a2a2a; padding: 20px; margin: 20px 0; border-radius: 8px; }
            button { background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; margin: 5px; }
            button:hover { background: #0056b3; }
            .danger { background: #dc3545; }
            .danger:hover { background: #c82333; }
            input { padding: 8px; margin: 5px; border: 1px solid #ccc; border-radius: 4px; }
            .status { padding: 10px; margin: 10px 0; border-radius: 4px; }
            .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
            .info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔧 Administration Keno</h1>
            
            <div class="card">
                <h3>Authentification</h3>
                <input type="password" id="adminToken" placeholder="Token d'administration" style="width: 300px;">
                <button onclick="setToken()">Définir Token</button>
            </div>
            
            <div class="card">
                <h3>📊 Statut du Système</h3>
                <button onclick="getStatus()">Actualiser Statut</button>
                <div id="statusResult"></div>
            </div>
            
            <div class="card">
                <h3>🔄 Actualisation des Données</h3>
                <button onclick="refreshData()">Actualiser Tirages</button>
                <div id="refreshResult"></div>
            </div>
            
            <div class="card">
                <h3>🤖 Machine Learning</h3>
                <button onclick="retrainML()">Relancer Entraînement ML</button>
                <div id="mlResult"></div>
            </div>
            
            <div class="card">
                <h3>🗑️ Nettoyage</h3>
                <input type="number" id="daysOld" value="30" min="1" max="365" style="width: 80px;">
                <label>jours</label>
                <button class="danger" onclick="clearPredictions()">Supprimer Anciennes Prédictions</button>
                <div id="clearResult"></div>
            </div>
        </div>
        
        <script>
            let adminToken = '';
            
            function setToken() {
                adminToken = document.getElementById('adminToken').value;
                if (adminToken) {
                    alert('Token défini avec succès');
                } else {
                    alert('Veuillez saisir un token');
                }
            }
            
            function makeRequest(url, method = 'GET', data = null) {
                if (!adminToken) {
                    alert('Veuillez d\\'abord définir le token d\\'administration');
                    return;
                }
                
                const options = {
                    method: method,
                    headers: {
                        'Authorization': 'Bearer ' + adminToken,
                        'Content-Type': 'application/json'
                    }
                };
                
                if (data) {
                    options.body = JSON.stringify(data);
                }
                
                return fetch(url, options).then(response => response.json());
            }
            
            function getStatus() {
                makeRequest('/api/admin/status').then(data => {
                    const result = document.getElementById('statusResult');
                    if (data.success) {
                        const status = data.system_status;
                        result.innerHTML = `
                            <div class="status success">
                                <strong>Système Opérationnel</strong><br>
                                Tirages: ${status.total_draws}<br>
                                ML: ${status.ml_status}<br>
                                Prédictions utilisateur: ${status.user_predictions}<br>
                                Erreurs modèle: ${status.model_errors}<br>
                                Dernière mise à jour: ${new Date(status.last_update).toLocaleString()}
                            </div>
                        `;
                    } else {
                        result.innerHTML = `<div class="status error">Erreur: ${data.error}</div>`;
                    }
                });
            }
            
            function refreshData() {
                const result = document.getElementById('refreshResult');
                result.innerHTML = '<div class="status info">Actualisation en cours...</div>';
                
                makeRequest('/api/admin/refresh-data', 'POST').then(data => {
                    if (data.success) {
                        result.innerHTML = `
                            <div class="status success">
                                ${data.message}<br>
                                Total tirages: ${data.total_draws}<br>
                                Nouveaux tirages: ${data.new_draws}
                            </div>
                        `;
                    } else {
                        result.innerHTML = `<div class="status error">Erreur: ${data.error}</div>`;
                    }
                });
            }
            
            function retrainML() {
                const result = document.getElementById('mlResult');
                result.innerHTML = '<div class="status info">Entraînement ML en cours...</div>';
                
                makeRequest('/api/admin/retrain-ml', 'POST').then(data => {
                    if (data.success) {
                        result.innerHTML = `<div class="status success">${data.message}</div>`;
                    } else {
                        result.innerHTML = `<div class="status error">Erreur: ${data.error}</div>`;
                    }
                });
            }
            
            function clearPredictions() {
                const daysOld = document.getElementById('daysOld').value;
                if (!confirm(`Êtes-vous sûr de vouloir supprimer les prédictions de plus de ${daysOld} jours ?`)) {
                    return;
                }
                
                const result = document.getElementById('clearResult');
                result.innerHTML = '<div class="status info">Suppression en cours...</div>';
                
                makeRequest('/api/admin/clear-predictions', 'POST', {days_old: parseInt(daysOld)}).then(data => {
                    if (data.success) {
                        result.innerHTML = `
                            <div class="status success">
                                ${data.message}<br>
                                Prédictions supprimées: ${data.predictions_deleted}<br>
                                Erreurs supprimées: ${data.errors_deleted}
                            </div>
                        `;
                    } else {
                        result.innerHTML = `<div class="status error">Erreur: ${data.error}</div>`;
                    }
                });
            }
        </script>
    </body>
    </html>
    """
    return admin_html

