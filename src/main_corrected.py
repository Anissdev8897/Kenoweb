#!/usr/bin/env python3
"""
Keno Analyzer Pro - Application Flask corrigée
Version sans erreurs d'indentation ou de syntaxe
"""

import os
import sys
import json
import random
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KenoAnalyzer:
    """Analyseur principal pour les tirages Keno"""
    
    def __init__(self, csv_file='keno_data.csv'):
        self.csv_file = csv_file
        self.historical_data = []
        self.last_update = None
        
    def load_data(self):
        """Charger les données historiques"""
        try:
            if os.path.exists(self.csv_file):
                with open(self.csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    self.historical_data = list(reader)
                logger.info(f"{len(self.historical_data)} tirages chargés")
            return True
        except Exception as e:
            logger.error(f"Erreur chargement données: {e}")
            return False
    
    def get_last_draw_info(self):
        """Obtenir les informations du dernier tirage"""
        if not self.historical_data:
            return None
        
        last_draw = self.historical_data[0]
        return {
            'date': last_draw.get('date', 'Inconnue'),
            'numbers': last_draw.get('numbers', []),
            'last_update': self.last_update.strftime('%d/%m/%Y à %H:%M') if self.last_update else 'Inconnue'
        }
    
    def save_predictions(self, predictions):
        """Sauvegarder les prédictions"""
        predictions_file = os.path.join(os.path.dirname(self.csv_file), 'predictions.json')
        try:
            predictions_data = {
                'timestamp': datetime.now().isoformat(),
                'predictions': predictions,
                'last_draw': self.get_last_draw_info()
            }
            
            with open(predictions_file, 'w', encoding='utf-8') as f:
                json.dump(predictions_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Prédictions sauvegardées: {len(predictions)} prédictions")
            return True
        except Exception as e:
            logger.error(f"Erreur sauvegarde: {e}")
            return False
    
    def load_predictions(self):
        """Charger les prédictions sauvegardées"""
        predictions_file = os.path.join(os.path.dirname(self.csv_file), 'predictions.json')
        try:
            if os.path.exists(predictions_file):
                with open(predictions_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return None
        except Exception as e:
            logger.error(f"Erreur chargement prédictions: {e}")
            return None

# Configuration Flask
app = Flask(__name__)
CORS(app)

# Initialisation de l'analyseur
analyzer = KenoAnalyzer()

# Routes API
@app.route('/')
def index():
    """Page d'accueil"""
    return render_template('index.html')

@app.route('/api/save_prediction', methods=['POST'])
def save_prediction():
    """Sauvegarder une prédiction"""
    try:
        data = request.json
        predictions = data.get('predictions', [])
        
        if analyzer.save_predictions(predictions):
            return jsonify({'success': True, 'message': 'Prédictions sauvegardées'})
        else:
            return jsonify({'success': False, 'error': 'Erreur lors de la sauvegarde'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/load_predictions', methods=['GET'])
def load_saved_predictions():
    """Charger les prédictions sauvegardées"""
    try:
        predictions = analyzer.load_predictions()
        return jsonify({'success': True, 'predictions': predictions})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/last_draw')
def get_last_draw():
    """Obtenir le dernier tirage"""
    try:
        last_draw = analyzer.get_last_draw_info()
        return jsonify({'success': True, 'last_draw': last_draw})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
