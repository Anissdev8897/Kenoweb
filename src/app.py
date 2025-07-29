import os
import logging
import threading
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from database_manager_postgresql import PostgreSQLManager
from routes.user import user_bp
from routes.api_draw import api_draw_bp

# Configuration du logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Initialisation de l'application Flask
app = Flask(__name__, static_folder=".")
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "keno_analyzer_pro_2024_secure_key")
CORS(app, origins="*")

# Initialisation de la base de données
try:
    db_manager = PostgreSQLManager()
    # Initialisation du schéma (uniquement dans le processus principal)
    if __name__ == '__main__' or not os.environ.get('WERKZEUG_RUN_MAIN'):
        db_manager.create_schema_if_needed()
    logger.info("Gestionnaire de base de données initialisé")
except Exception as e:
    logger.error(f"Erreur d'initialisation de la base de données: {e}")
    db_manager = None

# Enregistrement des blueprints
app.register_blueprint(user_bp)
app.register_blueprint(api_draw_bp)

# Routes de l'API
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/analyze', methods=['GET'])
def analyze():
    try:
        # Initialisation de l'analyseur Keno
        from keno_analyzer import KenoAnalyzer
        keno_analyzer = KenoAnalyzer()
        
        # Récupération des données d'analyse
        frequent_numbers = keno_analyzer.get_frequent_numbers()
        least_frequent_numbers = keno_analyzer.get_least_frequent_numbers()
        hot_numbers, cold_numbers = keno_analyzer.get_hot_cold_numbers()
        pair_impair_distribution = keno_analyzer.get_pair_impair_distribution()
        sum_distribution = keno_analyzer.get_sum_distribution()

        response_data = {
            "frequent_numbers": frequent_numbers,
            "least_frequent_numbers": least_frequent_numbers,
            "hot_numbers": hot_numbers,
            "cold_numbers": cold_numbers,
            "pair_impair_distribution": pair_impair_distribution,
            "sum_distribution": sum_distribution
        }

        # Ajout des analyses spécialisées si disponibles
        if hasattr(keno_analyzer, 'get_finales_analysis'):
            response_data["finales_analysis"] = keno_analyzer.get_finales_analysis()
        if hasattr(keno_analyzer, 'get_ecarts_analysis'):
            response_data["ecarts_analysis"] = keno_analyzer.get_ecarts_analysis()
        if hasattr(keno_analyzer, 'get_temporal_analysis'):
            response_data["temporal_analysis"] = keno_analyzer.get_temporal_analysis()
        if hasattr(keno_analyzer, 'get_monte_carlo_simulation'):
            response_data["monte_carlo_simulation"] = keno_analyzer.get_monte_carlo_simulation()

        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/update', methods=['POST'])
def update_data():
    try:
        from keno_web_scraper import KenoWebScraper
        scraper = KenoWebScraper()
        scraper.update_database()
        
        # Recharger les données après mise à jour
        from keno_analyzer import KenoAnalyzer
        KenoAnalyzer().reload_data()
        
        return jsonify({"status": "success", "message": "Données mises à jour avec succès"})
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour des données: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/predictions', methods=['GET'])
def get_predictions():
    try:
        # Implémentation de la récupération des prédictions
        return jsonify({"status": "success", "data": []})
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des prédictions: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # Créer les tables si elles n'existent pas
    if db_manager:
        db_manager.create_tables()
    
    # Démarrer le serveur
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
