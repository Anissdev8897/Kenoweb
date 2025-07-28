#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module de pondération Fibonacci pour le Keno
Adapté des méthodes avancées du Loto
"""

import logging
import numpy as np
import os
import time
from collections import Counter
from typing import Dict, List, Union, Any, Optional, Tuple

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("keno_fibonacci_log.txt"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("KenoFibonacciWeighting")

class KenoFibonacciWeighting:
    """Système de pondération Fibonacci pour le Keno"""
    
    def __init__(self):
        self.fibonacci_cache = {}
        self._precompute_fibonacci(100)  # Précalculer jusqu'à F(100)
        
    def _precompute_fibonacci(self, n: int):
        """Précalcule les nombres de Fibonacci pour optimiser les performances"""
        self.fibonacci_cache[0] = 0
        self.fibonacci_cache[1] = 1
        
        for i in range(2, n + 1):
            self.fibonacci_cache[i] = (self.fibonacci_cache[i-1] + 
                                     self.fibonacci_cache[i-2])
    
    def fibonacci(self, n: int) -> int:
        """
        Calcule le n-ième nombre de Fibonacci de manière optimisée.
        
        Args:
            n: Position dans la séquence de Fibonacci (commence à 0)
            
        Returns:
            Le n-ième nombre de Fibonacci
        """
        try:
            if not isinstance(n, int):
                logger.warning(f"Valeur non entière fournie à fibonacci(): {n}")
                n = int(n)
            
            if n < 0:
                logger.warning(f"Valeur négative fournie à fibonacci(): {n}")
                return 0
            
            # Utiliser le cache si disponible
            if n in self.fibonacci_cache:
                return self.fibonacci_cache[n]
            
            # Calculer et mettre en cache si nécessaire
            if n <= 1:
                result = n
            else:
                # Étendre le cache si nécessaire
                start = max(self.fibonacci_cache.keys()) + 1
                for i in range(start, n + 1):
                    self.fibonacci_cache[i] = (self.fibonacci_cache[i-1] + 
                                             self.fibonacci_cache[i-2])
                result = self.fibonacci_cache[n]
            
            return result
        
        except Exception as e:
            logger.error(f"Erreur lors du calcul de fibonacci({n}): {e}")
            return 0
    
    def apply_inverse_fibonacci_weights(self, counts: Counter, 
                                      reverse_order: bool = True) -> Dict[int, float]:
        """
        Applique une pondération inverse de Fibonacci aux compteurs.
        
        Args:
            counts: Dictionnaire de compteurs (numéro -> fréquence)
            reverse_order: Si True, les éléments les plus fréquents reçoivent
                         les poids les plus faibles (pondération inverse)
                         
        Returns:
            Dict des poids (numéro -> poids)
        """
        logger.info("Application de la pondération inverse de Fibonacci...")
        
        try:
            if not counts:
                logger.warning("Counter vide fourni à apply_inverse_fibonacci_weights")
                return {}
            
            # Trier les éléments par fréquence
            sorted_items = sorted(counts.items(), key=lambda x: x[1], 
                                reverse=not reverse_order)
            
            # Calculer les poids de Fibonacci
            weights = {}
            for i, (item, _) in enumerate(sorted_items):
                try:
                    # Utiliser i+2 pour éviter les premiers nombres de Fibonacci qui sont petits
                    fib_value = self.fibonacci(i + 2)
                    # Inverser pour que les éléments moins fréquents aient des poids plus élevés
                    weights[item] = 1.0 / fib_value if fib_value > 0 else 0.0
                except Exception as e:
                    logger.warning(f"Erreur lors du calcul du poids pour l'élément {item}: {e}")
                    weights[item] = 0.0
            
            # Normaliser les poids pour qu'ils soient entre 0 et 1
            max_weight = max(weights.values()) if weights.values() else 1.0
            if max_weight > 0:
                weights = {item: weight / max_weight for item, weight in weights.items()}
            
            logger.info(f"Pondération Fibonacci appliquée à {len(weights)} éléments")
            return weights
            
        except Exception as e:
            logger.error(f"Erreur lors de l'application de la pondération Fibonacci: {e}")
            return {}
    
    def apply_progressive_fibonacci_weights(self, counts: Counter, 
                                         progression_factor: float = 1.5) -> Dict[int, float]:
        """
        Applique une pondération Fibonacci progressive.
        
        Args:
            counts: Compteurs des fréquences
            progression_factor: Facteur de progression pour amplifier les différences
            
        Returns:
            Dict des poids progressifs
        """
        logger.info("Application de la pondération Fibonacci progressive...")
        
        try:
            if not counts:
                return {}
            
            # Trier par fréquence croissante
            sorted_items = sorted(counts.items(), key=lambda x: x[1])
            
            weights = {}
            for i, (item, freq) in enumerate(sorted_items):
                # Poids basé sur la position et la fréquence
                fib_weight = self.fibonacci(i + 1)
                freq_factor = (freq + 1) ** progression_factor
                
                # Combiner les deux facteurs
                combined_weight = fib_weight / freq_factor
                weights[item] = combined_weight
            
            # Normalisation
            max_weight = max(weights.values()) if weights.values() else 1.0
            if max_weight > 0:
                weights = {item: weight / max_weight for item, weight in weights.items()}
            
            logger.info(f"Pondération Fibonacci progressive appliquée à {len(weights)} éléments")
            return weights
            
        except Exception as e:
            logger.error(f"Erreur lors de la pondération progressive: {e}")
            return {}
    
    def apply_adaptive_fibonacci_weights(self, frequency_data: Dict[str, Counter],
                                       window_weights: Dict[str, float] = None) -> Dict[int, float]:
        """
        Applique une pondération Fibonacci adaptative basée sur plusieurs fenêtres temporelles.
        
        Args:
            frequency_data: Dict contenant les fréquences pour différentes fenêtres
            window_weights: Poids à appliquer à chaque fenêtre
            
        Returns:
            Dict des poids adaptatifs finaux
        """
        logger.info("Application de la pondération Fibonacci adaptative...")
        
        try:
            if not frequency_data:
                return {}
            
            # Poids par défaut pour les fenêtres
            if window_weights is None:
                window_weights = {
                    'recent': 0.4,    # 40% pour les données récentes
                    'medium': 0.35,   # 35% pour les données moyennes
                    'long': 0.25      # 25% pour les données anciennes
                }
            
            # Calculer les poids pour chaque fenêtre
            window_fibonacci_weights = {}
            for window_name, counts in frequency_data.items():
                if counts:
                    fib_weights = self.apply_inverse_fibonacci_weights(counts)
                    window_fibonacci_weights[window_name] = fib_weights
            
            # Combiner les poids de toutes les fenêtres
            combined_weights = {}
            all_numbers = set()
            
            # Collecter tous les numéros
            for weights in window_fibonacci_weights.values():
                all_numbers.update(weights.keys())
            
            # Calculer le poids combiné pour chaque numéro
            for number in all_numbers:
                combined_weight = 0.0
                total_window_weight = 0.0
                
                for window_name, weights in window_fibonacci_weights.items():
                    if number in weights:
                        window_weight = window_weights.get(window_name, 0.0)
                        combined_weight += weights[number] * window_weight
                        total_window_weight += window_weight
                
                # Normaliser par le poids total des fenêtres
                if total_window_weight > 0:
                    combined_weights[number] = combined_weight / total_window_weight
                else:
                    combined_weights[number] = 0.0
            
            logger.info(f"Pondération adaptative calculée pour {len(combined_weights)} numéros")
            return combined_weights
            
        except Exception as e:
            logger.error(f"Erreur lors de la pondération adaptative: {e}")
            return {}
    
    def calculate_fibonacci_scores(self, numbers: List[int], 
                                 frequency_weights: Dict[int, float],
                                 gap_weights: Dict[int, float] = None,
                                 combination_factor: float = 0.7) -> Dict[Tuple[int, ...], float]:
        """
        Calcule les scores Fibonacci pour des combinaisons de numéros.
        
        Args:
            numbers: Liste des numéros à combiner
            frequency_weights: Poids basés sur les fréquences
            gap_weights: Poids basés sur les écarts (optionnel)
            combination_factor: Facteur de combinaison des poids
            
        Returns:
            Dict des scores par combinaison
        """
        logger.info("Calcul des scores Fibonacci pour les combinaisons...")
        
        try:
            from itertools import combinations
            
            scores = {}
            
            # Générer toutes les combinaisons possibles (exemple: combinaisons de 5)
            for combo in combinations(numbers, 5):
                # Score basé sur les fréquences
                freq_score = sum(frequency_weights.get(num, 0) for num in combo)
                
                # Score basé sur les écarts si disponible
                gap_score = 0
                if gap_weights:
                    gap_score = sum(gap_weights.get(num, 0) for num in combo)
                
                # Score combiné
                if gap_weights:
                    combined_score = (freq_score * combination_factor + 
                                    gap_score * (1 - combination_factor))
                else:
                    combined_score = freq_score
                
                # Bonus Fibonacci pour la combinaison elle-même
                combo_length = len(combo)
                fibonacci_bonus = self.fibonacci(combo_length + 1) / 100.0
                
                final_score = combined_score + fibonacci_bonus
                scores[combo] = final_score
            
            logger.info(f"Scores calculés pour {len(scores)} combinaisons")
            return scores
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul des scores Fibonacci: {e}")
            return {}
    
    def optimize_fibonacci_parameters(self, historical_data: Dict[str, Any],
                                    parameter_ranges: Dict[str, Tuple[float, float]] = None) -> Dict[str, float]:
        """
        Optimise les paramètres de la pondération Fibonacci.
        
        Args:
            historical_data: Données historiques pour l'optimisation
            parameter_ranges: Plages de valeurs pour les paramètres
            
        Returns:
            Dict des paramètres optimaux
        """
        logger.info("Optimisation des paramètres Fibonacci...")
        
        try:
            if parameter_ranges is None:
                parameter_ranges = {
                    'progression_factor': (1.0, 3.0),
                    'combination_factor': (0.3, 0.9),
                    'recent_weight': (0.2, 0.6),
                    'medium_weight': (0.2, 0.5),
                    'long_weight': (0.1, 0.4)
                }
            
            # Simulation d'optimisation (version simplifiée)
            best_params = {}
            best_score = 0.0
            
            # Test de différentes combinaisons de paramètres
            for _ in range(50):  # 50 itérations d'optimisation
                test_params = {}
                for param, (min_val, max_val) in parameter_ranges.items():
                    test_params[param] = np.random.uniform(min_val, max_val)
                
                # Normaliser les poids pour qu'ils somment à 1
                weight_sum = (test_params['recent_weight'] + 
                            test_params['medium_weight'] + 
                            test_params['long_weight'])
                if weight_sum > 0:
                    test_params['recent_weight'] /= weight_sum
                    test_params['medium_weight'] /= weight_sum
                    test_params['long_weight'] /= weight_sum
                
                # Évaluer ces paramètres (simulation)
                score = self._evaluate_parameters(test_params, historical_data)
                
                if score > best_score:
                    best_score = score
                    best_params = test_params.copy()
            
            logger.info(f"Paramètres optimaux trouvés avec score: {best_score:.4f}")
            return best_params
            
        except Exception as e:
            logger.error(f"Erreur lors de l'optimisation des paramètres: {e}")
            return {}
    
    def _evaluate_parameters(self, params: Dict[str, float], 
                           historical_data: Dict[str, Any]) -> float:
        """
        Évalue un ensemble de paramètres (fonction d'évaluation simulée).
        
        Args:
            params: Paramètres à évaluer
            historical_data: Données historiques
            
        Returns:
            Score d'évaluation
        """
        try:
            # Simulation d'évaluation basée sur la cohérence des paramètres
            score = 0.0
            
            # Bonus pour des paramètres équilibrés
            weight_balance = abs(params.get('recent_weight', 0.33) - 0.4)
            score += max(0, 1.0 - weight_balance * 2)
            
            # Bonus pour un facteur de progression raisonnable
            prog_factor = params.get('progression_factor', 1.5)
            if 1.2 <= prog_factor <= 2.0:
                score += 0.5
            
            # Bonus pour un facteur de combinaison équilibré
            combo_factor = params.get('combination_factor', 0.7)
            if 0.5 <= combo_factor <= 0.8:
                score += 0.3
            
            # Ajouter un peu de randomness pour simuler la variabilité réelle
            score += np.random.uniform(0, 0.2)
            
            return score
            
        except Exception as e:
            logger.error(f"Erreur lors de l'évaluation des paramètres: {e}")
            return 0.0
    
    def generate_fibonacci_report(self, weights: Dict[int, float],
                                scores: Dict[Tuple[int, ...], float] = None) -> str:
        """
        Génère un rapport de pondération Fibonacci.
        
        Args:
            weights: Poids calculés
            scores: Scores des combinaisons (optionnel)
            
        Returns:
            Rapport formaté
        """
        report = []
        report.append("=" * 60)
        report.append("RAPPORT DE PONDÉRATION FIBONACCI KENO")
        report.append("=" * 60)
        report.append("")
        
        # Top numéros par poids
        if weights:
            sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)
            
            report.append("🏆 TOP 20 NUMÉROS PAR POIDS FIBONACCI")
            report.append("-" * 40)
            for i, (number, weight) in enumerate(sorted_weights[:20], 1):
                report.append(f"{i:2d}. Numéro {number:2d} - Poids: {weight:.4f}")
            report.append("")
            
            # Statistiques des poids
            weights_values = list(weights.values())
            report.append("📊 STATISTIQUES DES POIDS")
            report.append("-" * 40)
            report.append(f"Poids moyen: {np.mean(weights_values):.4f}")
            report.append(f"Écart-type: {np.std(weights_values):.4f}")
            report.append(f"Poids minimum: {min(weights_values):.4f}")
            report.append(f"Poids maximum: {max(weights_values):.4f}")
            report.append("")
        
        # Top combinaisons si disponibles
        if scores:
            sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            
            report.append("🎯 TOP 10 COMBINAISONS PAR SCORE FIBONACCI")
            report.append("-" * 40)
            for i, (combo, score) in enumerate(sorted_scores[:10], 1):
                combo_str = " - ".join(map(str, sorted(combo)))
                report.append(f"{i:2d}. [{combo_str}] - Score: {score:.4f}")
            report.append("")
        
        # Recommandations
        report.append("💡 RECOMMANDATIONS FIBONACCI")
        report.append("-" * 40)
        report.append("• Privilégier les numéros avec les poids les plus élevés")
        report.append("• Combiner avec d'autres méthodes d'analyse")
        report.append("• Ajuster les paramètres selon les performances observées")
        report.append("• Surveiller l'évolution des poids dans le temps")
        report.append("")
        
        report.append(f"Rapport généré le: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        report.append("=" * 60)
        
        return "\n".join(report)

def main():
    """Test du module de pondération Fibonacci"""
    fibonacci_weighting = KenoFibonacciWeighting()
    
    print("Test du module de pondération Fibonacci Keno...")
    
    # Test des nombres de Fibonacci
    print("Premiers nombres de Fibonacci:")
    for i in range(10):
        fib = fibonacci_weighting.fibonacci(i)
        print(f"F({i}) = {fib}")
    
    # Test avec des données simulées
    test_counts = Counter({
        1: 45, 2: 38, 3: 42, 4: 35, 5: 48,
        6: 33, 7: 51, 8: 29, 9: 44, 10: 37,
        11: 40, 12: 32, 13: 46, 14: 31, 15: 49
    })
    
    # Pondération inverse
    inverse_weights = fibonacci_weighting.apply_inverse_fibonacci_weights(test_counts)
    print(f"\nPondération inverse (top 5):")
    sorted_weights = sorted(inverse_weights.items(), key=lambda x: x[1], reverse=True)
    for num, weight in sorted_weights[:5]:
        print(f"  Numéro {num}: {weight:.4f}")
    
    # Pondération progressive
    progressive_weights = fibonacci_weighting.apply_progressive_fibonacci_weights(test_counts)
    print(f"\nPondération progressive (top 5):")
    sorted_prog = sorted(progressive_weights.items(), key=lambda x: x[1], reverse=True)
    for num, weight in sorted_prog[:5]:
        print(f"  Numéro {num}: {weight:.4f}")
    
    # Test de la pondération adaptative
    frequency_data = {
        'recent': Counter({1: 15, 2: 12, 3: 18, 4: 10, 5: 16}),
        'medium': Counter({1: 25, 2: 22, 3: 28, 4: 20, 5: 26}),
        'long': Counter({1: 35, 2: 32, 3: 38, 4: 30, 5: 36})
    }
    
    adaptive_weights = fibonacci_weighting.apply_adaptive_fibonacci_weights(frequency_data)
    print(f"\nPondération adaptative:")
    for num, weight in sorted(adaptive_weights.items()):
        print(f"  Numéro {num}: {weight:.4f}")
    
    # Génération du rapport
    report = fibonacci_weighting.generate_fibonacci_report(inverse_weights)
    print(f"\n{report}")
    
    print("Test terminé avec succès!")

if __name__ == "__main__":
    from datetime import datetime
    main()

