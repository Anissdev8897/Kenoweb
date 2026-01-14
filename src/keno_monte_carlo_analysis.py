#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module d'analyse Monte Carlo adaptative pour le Keno
Simulation probabiliste avancée avec adaptation dynamique
VERSION CORRIGÉE - Avec méthode train_model
"""

import pandas as pd
import numpy as np
from collections import Counter, defaultdict
from typing import Dict, List, Any, Optional, Tuple
import logging
import os
import time
import random
from datetime import datetime, timedelta
# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("keno_monte_carlo_log.txt"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("KenoMonteCarloAnalysis")

class KenoMonteCarloAnalyzer:
    """Analyseur Monte Carlo adaptatif pour le Keno"""
    
    def __init__(self):
        self.min_number = 1
        self.max_number = 70
        self.numbers_per_draw = 20
        self.simulation_cache = {}
        
        # Cache pour les analyses pré-calculées
        self.trained_analysis = None
        self.training_timestamp = None
        self.is_trained = False
        
    def train_model(self, df: pd.DataFrame, window_size: int = 200, num_simulations: int = 10000):
        """
        Entraîne l'analyseur en pré-calculant les simulations Monte Carlo.
        
        Args:
            df: DataFrame contenant l'historique des tirages
            window_size: Taille de la fenêtre d'analyse pour l'entraînement
            num_simulations: Nombre de simulations Monte Carlo
        """
        logger.info("🔧 Entraînement de l'analyseur Monte Carlo...")
        
        try:
            if df.empty:
                logger.warning("DataFrame vide pour l'entraînement")
                self.is_trained = False
                return
            
            # Calculer les probabilités empiriques
            probabilities = self.calculate_number_probabilities(df, window_size)
            
            # Exécuter la simulation Monte Carlo
            simulation_results = self.run_monte_carlo_simulation(probabilities, num_simulations)
            
            # Analyser la convergence
            convergence_analysis = self.analyze_convergence(df, max_simulations=5000, step_size=500)
            
            # Stocker les résultats d'entraînement
            self.trained_analysis = {
                'probabilities': probabilities,
                'simulation_results': simulation_results,
                'convergence_analysis': convergence_analysis,
                'training_window_size': window_size,
                'training_simulations': num_simulations,
                'training_data_size': len(df),
                'training_timestamp': datetime.now().isoformat()
            }
            
            self.training_timestamp = datetime.now()
            self.is_trained = True
            
            logger.info(f"✅ Analyseur Monte Carlo entraîné avec {len(df)} tirages et {num_simulations} simulations")
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'entraînement de l'analyseur Monte Carlo: {e}")
            self.is_trained = False
    
    def get_training_status(self) -> Dict[str, Any]:
        """
        Retourne le statut d'entraînement de l'analyseur.
        
        Returns:
            Dict contenant les informations d'entraînement
        """
        return {
            'is_trained': self.is_trained,
            'training_timestamp': self.training_timestamp.isoformat() if self.training_timestamp else None,
            'trained_analysis_available': self.trained_analysis is not None
        }
        
    def calculate_number_probabilities(self, df: pd.DataFrame, window_size: int = 200) -> Dict[int, float]:
        """
        Calcule les probabilités empiriques de chaque numéro.
        
        Args:
            df: DataFrame contenant l'historique des tirages
            window_size: Taille de la fenêtre d'analyse
            
        Returns:
            Dict des probabilités pour chaque numéro
        """
        logger.info(f"Calcul des probabilités empiriques sur {window_size} tirages...")
        
        try:
            if df.empty or len(df) < window_size:
                logger.warning("Pas assez de données pour l'analyse Monte Carlo")
                # Probabilités uniformes par défaut
                return {n: 1/70 for n in range(self.min_number, self.max_number + 1)}
            
            # Prendre les derniers tirages
            df_recent = df.tail(window_size).copy()
            
            # Compter les occurrences de chaque numéro
            number_counts = Counter()
            total_numbers = 0
            
            for _, row in df_recent.iterrows():
                for i in range(1, 21):
                    col_name = f'numero_{i}'
                    if col_name in row and pd.notna(row[col_name]):
                        numero = int(row[col_name])
                        number_counts[numero] += 1
                        total_numbers += 1
            
            # Calculer les probabilités empiriques
            probabilities = {}
            for numero in range(self.min_number, self.max_number + 1):
                count = number_counts.get(numero, 0)
                # Lissage de Laplace pour éviter les probabilités nulles
                probabilities[numero] = (count + 1) / (total_numbers + 70)
            
            # Normaliser pour que la somme soit 1
            total_prob = sum(probabilities.values())
            probabilities = {n: p / total_prob for n, p in probabilities.items()}
            
            logger.info("Calcul des probabilités empiriques terminé.")
            return probabilities
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul des probabilités: {e}")
            return {n: 1/70 for n in range(self.min_number, self.max_number + 1)}
    
    def simulate_draw(self, probabilities: Dict[int, float]) -> List[int]:
        """
        Simule un tirage Keno basé sur les probabilités données.
        
        Args:
            probabilities: Probabilités de chaque numéro
            
        Returns:
            Liste de 20 numéros simulés
        """
        try:
            numbers = list(probabilities.keys())
            probs = list(probabilities.values())
            
            # Simulation d'un tirage de 20 numéros sans remise
            selected = np.random.choice(
                numbers, 
                size=self.numbers_per_draw, 
                replace=False, 
                p=probs
            )
            
            return sorted(selected.tolist())
            
        except Exception as e:
            logger.error(f"Erreur lors de la simulation: {e}")
            return sorted(random.sample(range(1, 71), 20))
    
    def run_monte_carlo_simulation(self, probabilities: Dict[int, float], 
                                 num_simulations: int = 10000) -> Dict[str, Any]:
        """
        Exécute une simulation Monte Carlo complète.
        
        Args:
            probabilities: Probabilités de base pour la simulation
            num_simulations: Nombre de simulations à effectuer
            
        Returns:
            Dict contenant les résultats de la simulation
        """
        logger.info(f"Démarrage simulation Monte Carlo avec {num_simulations} itérations...")
        
        try:
            # Compteurs pour les résultats
            simulation_counts = Counter()
            position_counts = defaultdict(lambda: defaultdict(int))
            frequency_distribution = defaultdict(int)
            
            start_time = time.time()
            
            for i in range(num_simulations):
                # Simuler un tirage
                simulated_draw = self.simulate_draw(probabilities)
                
                # Compter les occurrences
                for numero in simulated_draw:
                    simulation_counts[numero] += 1
                
                # Analyser les positions
                for pos, numero in enumerate(simulated_draw):
                    position_counts[pos][numero] += 1
                
                # Analyser la distribution des fréquences
                draw_freq = len(set(simulated_draw))  # Nombre de numéros uniques (toujours 20 pour Keno)
                frequency_distribution[draw_freq] += 1
                
                # Log de progression
                if (i + 1) % 1000 == 0:
                    logger.info(f"Simulation {i + 1}/{num_simulations} terminée")
            
            execution_time = time.time() - start_time
            
            # Calculer les statistiques finales
            total_numbers = sum(simulation_counts.values())
            simulated_probabilities = {
                numero: count / total_numbers 
                for numero, count in simulation_counts.items()
            }
            
            # Calculer les écarts par rapport aux probabilités théoriques
            probability_deviations = {}
            for numero in range(self.min_number, self.max_number + 1):
                theoretical = probabilities.get(numero, 0)
                simulated = simulated_probabilities.get(numero, 0)
                probability_deviations[numero] = simulated - theoretical
            
            # Identifier les numéros sur-représentés et sous-représentés
            over_represented = sorted(
                [n for n, dev in probability_deviations.items() if dev > 0],
                key=lambda n: probability_deviations[n],
                reverse=True
            )
            
            under_represented = sorted(
                [n for n, dev in probability_deviations.items() if dev < 0],
                key=lambda n: probability_deviations[n]
            )
            
            result = {
                'simulation_counts': dict(simulation_counts),
                'simulated_probabilities': simulated_probabilities,
                'probability_deviations': probability_deviations,
                'over_represented': over_represented,
                'under_represented': under_represented,
                'position_analysis': dict(position_counts),
                'frequency_distribution': dict(frequency_distribution),
                'num_simulations': num_simulations,
                'execution_time': execution_time,
                'analysis_timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Simulation Monte Carlo terminée en {execution_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de la simulation Monte Carlo: {e}")
            return {}
    
    def adaptive_monte_carlo_prediction(self, df: pd.DataFrame, nb_numbers: int = 8,
                                      window_size: int = 200, num_simulations: int = 5000) -> List[int]:
        """
        Prédit des numéros en utilisant Monte Carlo adaptatif.
        Utilise l'analyse pré-calculée si disponible.
        
        Args:
            df: DataFrame contenant l'historique des tirages
            nb_numbers: Nombre de numéros à prédire
            window_size: Taille de la fenêtre d'analyse
            num_simulations: Nombre de simulations Monte Carlo
            
        Returns:
            Liste des numéros prédits
        """
        logger.info(f"Prédiction Monte Carlo adaptative de {nb_numbers} numéros...")
        
        try:
            # Utiliser l'analyse pré-calculée si disponible et récente
            if (self.is_trained and self.trained_analysis and 
                self.trained_analysis.get('simulation_results')):
                
                logger.info("Utilisation de l'analyse pré-calculée")
                simulation_results = self.trained_analysis['simulation_results']
                probabilities = self.trained_analysis['probabilities']
            else:
                # Calculer l'analyse à la volée
                logger.info("Calcul de l'analyse à la volée")
                probabilities = self.calculate_number_probabilities(df, window_size)
                simulation_results = self.run_monte_carlo_simulation(probabilities, num_simulations)
            
            if not simulation_results:
                logger.warning("Simulation Monte Carlo échouée, utilisation de numéros aléatoires")
                return sorted(np.random.choice(range(1, 71), nb_numbers, replace=False))
            
            # Stratégie adaptative : combiner plusieurs critères
            candidates = []
            
            simulated_probs = simulation_results['simulated_probabilities']
            deviations = simulation_results['probability_deviations']
            
            for numero in range(self.min_number, self.max_number + 1):
                # Critères de sélection
                simulated_prob = simulated_probs.get(numero, 0)
                deviation = deviations.get(numero, 0)
                original_prob = probabilities.get(numero, 0)
                
                # Score adaptatif
                # 1. Favoriser les numéros avec une probabilité simulée élevée
                prob_score = simulated_prob * 100
                
                # 2. Favoriser les numéros sous-représentés dans la simulation (compensation)
                compensation_score = max(0, -deviation * 50)
                
                # 3. Équilibrer avec la probabilité empirique originale
                balance_score = original_prob * 30
                
                # 4. Ajouter un facteur de diversité
                diversity_score = random.random() * 5
                
                # Score final combiné
                final_score = prob_score + compensation_score + balance_score + diversity_score
                
                candidates.append({
                    'numero': numero,
                    'score': final_score,
                    'simulated_prob': simulated_prob,
                    'deviation': deviation,
                    'original_prob': original_prob
                })
            
            # Trier par score décroissant
            candidates.sort(key=lambda x: x['score'], reverse=True)
            
            # Sélectionner les meilleurs candidats
            predicted_numbers = []
            for candidate in candidates:
                if len(predicted_numbers) >= nb_numbers:
                    break
                predicted_numbers.append(candidate['numero'])
            
            result = sorted(predicted_numbers)
            logger.info(f"Prédiction Monte Carlo adaptative terminée: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de la prédiction Monte Carlo: {e}")
            return sorted(np.random.choice(range(1, 71), nb_numbers, replace=False))
    
    def analyze_convergence(self, df: pd.DataFrame, max_simulations: int = 20000, 
                          step_size: int = 1000) -> Dict[str, Any]:
        """
        Analyse la convergence de la simulation Monte Carlo.
        
        Args:
            df: DataFrame contenant l'historique des tirages
            max_simulations: Nombre maximum de simulations
            step_size: Pas d'analyse de convergence
            
        Returns:
            Dict contenant l'analyse de convergence
        """
        logger.info("Analyse de convergence Monte Carlo...")
        
        try:
            probabilities = self.calculate_number_probabilities(df)
            convergence_data = []
            
            for num_sims in range(step_size, max_simulations + 1, step_size):
                simulation_results = self.run_monte_carlo_simulation(probabilities, num_sims)
                
                if simulation_results:
                    # Calculer l'erreur moyenne par rapport aux probabilités théoriques
                    deviations = simulation_results['probability_deviations']
                    mean_absolute_error = np.mean([abs(dev) for dev in deviations.values()])
                    
                    convergence_data.append({
                        'num_simulations': num_sims,
                        'mean_absolute_error': mean_absolute_error,
                        'execution_time': simulation_results['execution_time']
                    })
                    
                    logger.info(f"Convergence {num_sims}: MAE = {mean_absolute_error:.6f}")
            
            result = {
                'convergence_data': convergence_data,
                'analysis_timestamp': datetime.now().isoformat()
            }
            
            logger.info("Analyse de convergence terminée.")
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse de convergence: {e}")
            return {}
    
    def predict_numbers_by_monte_carlo(self, df: pd.DataFrame, nb_numbers: int = 8,
                                     window_size: int = 200) -> List[int]:
        """
        Interface principale pour la prédiction Monte Carlo.
        
        Args:
            df: DataFrame contenant l'historique des tirages
            nb_numbers: Nombre de numéros à prédire
            window_size: Taille de la fenêtre d'analyse
            
        Returns:
            Liste des numéros prédits
        """
        return self.adaptive_monte_carlo_prediction(
            df, nb_numbers=nb_numbers, window_size=window_size, num_simulations=5000
        )

