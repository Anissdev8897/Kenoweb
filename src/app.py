




import os
from database_manager_postgresql import get_postgresql_manager

import json
from routes.user import user_bp
from routes.api_draw import api_draw_bp

app = Flask(__name__, static_folder=".")
app.config["SECRET_KEY"] = "keno_analyzer_pro_2024_secure_key"
CORS(app, origins="*")

app.register_blueprint(user_bp)
app.register_blueprint(api_draw_bp)

# ... (reste du code inchangé)

app.register_blueprint(user_bp)
app.register_blueprint(api_draw_bp)

# ... (reste du code inchangé)
                else:
                    impair_count += 1
        total = pair_count + impair_count
        return {"pair": pair_count / total if total else 0, "impair": impair_count / total if total else 0}

    def get_sum_distribution(self):
        sums = [sum(tirage['numeros']) for tirage in self.tirages]
        sum_counts = Counter(sums)
        return dict(sorted(sum_counts.items()))

    def get_finales_analysis(self):
        if SPECIALIZED_MODULES_AVAILABLE:
            return self.finales_analyzer.analyze_finales()
        return {"error": "Module KenoFinalesAnalyzer non disponible"}

    def get_ecarts_analysis(self):
        if SPECIALIZED_MODULES_AVAILABLE:
            return self.ecarts_analyzer.analyze_ecarts()
        return {"error": "Module KenoEcartsAnalyzer non disponible"}

    def get_temporal_analysis(self):
        if SPECIALIZED_MODULES_AVAILABLE:
            return self.temporal_analyzer.analyze_temporal_patterns()
        return {"error": "Module KenoTemporalAnalyzer non disponible"}

    def get_monte_carlo_simulation(self, num_simulations=1000):
        if SPECIALIZED_MODULES_AVAILABLE:
            return self.monte_carlo_analyzer.run_simulation(num_simulations)
        return {"error": "Module KenoMonteCarloAnalyzer non disponible"}

# Initialisation de l'analyseur Keno
keno_analyzer = KenoAnalyzer()

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/analyze', methods=['GET'])
def analyze():
    try:
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

        if SPECIALIZED_MODULES_AVAILABLE:
            response_data["finales_analysis"] = keno_analyzer.get_finales_analysis()
            response_data["ecarts_analysis"] = keno_analyzer.get_ecarts_analysis()
            response_data["temporal_analysis"] = keno_analyzer.get_temporal_analysis()
            response_data["monte_carlo_simulation"] = keno_analyzer.get_monte_carlo_simulation()

        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/update_data', methods=['POST'])
def update_data():
    try:
        scraper = KenoWebScraper()
        scraper.update_database()
        keno_analyzer.__init__() # Recharger les données après mise à jour
        return jsonify({"status": "success", "message": "Données mises à jour avec succès"})
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour des données: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/predictions.json')
def predictions_json():
    return send_from_directory('.', 'predictions.json')

if __name__ == '__main__':
    # Créer les tables si elles n'existent pas
    db_manager.create_tables()
    # Lancer le scraper dans un thread séparé pour ne pas bloquer l'application Flask
    # scraper_thread = threading.Thread(target=KenoWebScraper().update_database)
    # scraper_thread.start()
    app.run(debug=True, host='0.0.0.0', port=os.getenv("PORT", 5000))


