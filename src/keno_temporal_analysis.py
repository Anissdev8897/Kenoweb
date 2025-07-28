#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module d'analyse temporelle avancée pour le Keno
Pondération temporelle adaptative des tirages récents
VERSION CORRIGÉE - Avec méthode train_model
"""

import pandas as pd
import numpy as np
from collections import Counter, defaultdict
from typing import Dict, List, Any, Optional, Tuple
import logging
import os
import time
from datetime import datetime, timedelta

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("keno_temporal_log.txt"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("KenoTemporalAnalysis")

class KenoTemporalAnalyzer:
    """Analyseur temporel avancé pour le Keno"""
    
    def __init__(self):
        self.min_number = 1
        self.max_number = 70
        self.numbers_per_draw = 20
        
        # Cache pour les analyses pré-calculées
        self.trained_analysis = None
        self.training_timestamp = None
        self.is_trained = False
        
    def train_model(self, df: pd.DataFrame, window_size: int = 150, decay_factor: float = 0.95):
        """
        Entraîne l'analyseur en pré-calculant les analyses temporelles.
        
        Args:
            df: DataFrame contenant l'historique des tirages
            window_size: Taille de la fenêtre d'analyse pour l'entraînement
            decay_factor: Facteur de décroissance temporelle
        """
        logger.info("🔧 Entraînement de l'analyseur temporel...")
        
        try:
            if df.empty:
                logger.warning("DataFrame vide pour l'entraînement")
                self.is_trained = False
                return
            
            # Pré-calculer les analyses principales
            weighted_analysis = self.calculate_weighted_frequencies(df, window_size, decay_factor)
            trends_analysis = self.analyze_temporal_trends(df, window_size)
            
            # Stocker les résultats d'entraînement
            self.trained_analysis = {
                'weighted_frequencies': weighted_analysis,
                'temporal_trends': trends_analysis,
                'training_window_size': window_size,
                'training_decay_factor': decay_factor,
                'training_data_size': len(df),
                'training_timestamp': datetime.now().isoformat()
            }
            
            self.training_timestamp = datetime.now()
            self.is_trained = True
            
            logger.info(f"✅ Analyseur temporel entraîné avec {len(df)} tirages")
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'entraînement de l'analyseur temporel: {e}")
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
        
    def calculate_temporal_weights(self, window_size: int, decay_factor: float = 0.95) -> List[float]:
        """
        Calcule les poids temporels avec décroissance exponentielle.
        
        Args:
            window_size: Taille de la fenêtre d'analyse
            decay_factor: Facteur de décroissance (0 < decay_factor < 1)
            
        Returns:
            Liste des poids temporels (plus récent = poids plus élevé)
        """
        weights = []
        for i in range(window_size):
            # Le tirage le plus récent (i=0) a le poids le plus élevé
            weight = decay_factor ** i
            weights.append(weight)
        
        # Normaliser les poids
        total_weight = sum(weights)
        if total_weight > 0:
            weights = [w / total_weight for w in weights]
        
        return weights
    
    def calculate_weighted_frequencies(self, df: pd.DataFrame, window_size: int = 100, 
                                     decay_factor: float = 0.95) -> Dict[str, Any]:
        """
        Calcule les fréquences pondérées temporellement.
        
        Args:
            df: DataFrame contenant l'historique des tirages
            window_size: Taille de la fenêtre d'analyse
            decay_factor: Facteur de décroissance temporelle
            
        Returns:
            Dict contenant les fréquences pondérées
        """
        logger.info(f"Calcul des fréquences pondérées sur {window_size} tirages...")
        
        try:
            if df.empty or len(df) < window_size:
                logger.warning("Pas assez de données pour l'analyse temporelle")
                return {}
            
            # Prendre les derniers tirages
            df_recent = df.tail(window_size).copy()
            
            # Calculer les poids temporels
            weights = self.calculate_temporal_weights(len(df_recent), decay_factor)
            
            # Calculer les fréquences pondérées
            weighted_frequencies = defaultdict(float)
            total_weight = 0
            
            for idx, (_, row) in enumerate(df_recent.iterrows()):
                weight = weights[len(df_recent) - 1 - idx]  # Inverser pour que le plus récent ait le poids max
                total_weight += weight
                
                # Extraire les numéros du tirage
                numeros_tirage = []
                for i in range(1, 21):
                    col_name = f'numero_{i}'
                    if col_name in row and pd.notna(row[col_name]):
                        numeros_tirage.append(int(row[col_name]))
                
                # Ajouter le poids pour chaque numéro
                for numero in numeros_tirage:
                    weighted_frequencies[numero] += weight
            
            # Normaliser par le poids total
            for numero in weighted_frequencies:
                weighted_frequencies[numero] /= total_weight
            
            # Calculer les fréquences simples pour comparaison
            simple_frequencies = Counter()
            for _, row in df_recent.iterrows():
                for i in range(1, 21):
                    col_name = f'numero_{i}'
                    if col_name in row and pd.notna(row[col_name]):
                        simple_frequencies[int(row[col_name])] += 1
            
            # Normaliser les fréquences simples
            total_numbers = sum(simple_frequencies.values())
            simple_freq_normalized = {n: count / total_numbers for n, count in simple_frequencies.items()}
            
            # Calculer les différences (impact de la pondération temporelle)
            frequency_differences = {}
            for numero in range(self.min_number, self.max_number + 1):
                weighted_freq = weighted_frequencies.get(numero, 0)
                simple_freq = simple_freq_normalized.get(numero, 0)
                frequency_differences[numero] = weighted_freq - simple_freq
            
            result = {
                'weighted_frequencies': dict(weighted_frequencies),
                'simple_frequencies': simple_freq_normalized,
                'frequency_differences': frequency_differences,
                'weights_used': weights,
                'window_size': len(df_recent),
                'decay_factor': decay_factor,
                'analysis_timestamp': datetime.now().isoformat()
            }
            
            logger.info("Calcul des fréquences pondérées terminé.")
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul des fréquences pondérées: {e}")
            return {}
    
    def predict_numbers_by_temporal_weighting(self, df: pd.DataFrame, nb_numbers: int = 8,
                                            window_size: int = 100, decay_factor: float = 0.95) -> List[int]:
        """
        Prédit des numéros basés sur la pondération temporelle.
        Utilise l'analyse pré-calculée si disponible.
        
        Args:
            df: DataFrame contenant l'historique des tirages
            nb_numbers: Nombre de numéros à prédire
            window_size: Taille de la fenêtre d'analyse
            decay_factor: Facteur de décroissance temporelle
            
        Returns:
            Liste des numéros prédits
        """
        logger.info(f"Prédiction de {nb_numbers} numéros par pondération temporelle...")
        
        try:
            # Utiliser l'analyse pré-calculée si disponible et récente
            if (self.is_trained and self.trained_analysis and 
                self.trained_analysis.get('weighted_frequencies')):
                
                logger.info("Utilisation de l'analyse pré-calculée")
                temporal_analysis = self.trained_analysis['weighted_frequencies']
            else:
                # Calculer l'analyse à la volée
                logger.info("Calcul de l'analyse à la volée")
                temporal_analysis = self.calculate_weighted_frequencies(df, window_size, decay_factor)
            
            if not temporal_analysis:
                logger.warning("Analyse temporelle échouée, utilisation de numéros aléatoires")
                return sorted(np.random.choice(range(1, 71), nb_numbers, replace=False))
            
            weighted_frequencies = temporal_analysis['weighted_frequencies']
            frequency_differences = temporal_analysis['frequency_differences']
            
            # Stratégie: privilégier les numéros avec une tendance positive récente
            # (fréquence pondérée > fréquence simple)
            candidates = []
            
            for numero in range(self.min_number, self.max_number + 1):
                weighted_freq = weighted_frequencies.get(numero, 0)
                freq_diff = frequency_differences.get(numero, 0)
                
                # Score combinant fréquence pondérée et tendance
                # Favoriser les numéros en hausse récente mais pas trop fréquents
                if freq_diff > 0:  # Tendance positive
                    score = freq_diff * (1 - weighted_freq)  # Pondérer par rareté
                else:
                    # Pour les numéros en baisse, favoriser ceux qui étaient fréquents
                    score = weighted_freq * 0.5
                
                candidates.append({
                    'numero': numero,
                    'weighted_freq': weighted_freq,
                    'freq_diff': freq_diff,
                    'score': score
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
            logger.info(f"Prédiction temporelle terminée: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de la prédiction temporelle: {e}")
            return sorted(np.random.choice(range(1, 71), nb_numbers, replace=False))
    
    def analyze_temporal_trends(self, df: pd.DataFrame, window_size: int = 150) -> Dict[str, Any]:
        """
        Analyse les tendances temporelles des numéros.
        
        Args:
            df: DataFrame contenant l'historique des tirages
            window_size: Taille de la fenêtre d'analyse
            
        Returns:
            Dict contenant l'analyse des tendances
        """
        logger.info("Analyse des tendances temporelles...")
        
        try:
            if df.empty or len(df) < window_size:
                return {}
            
            df_recent = df.tail(window_size).copy()
            
            # Diviser la fenêtre en segments pour analyser l'évolution
            segment_size = window_size // 3
            segments = [
                df_recent.iloc[:segment_size],      # Ancien
                df_recent.iloc[segment_size:2*segment_size],  # Moyen
                df_recent.iloc[2*segment_size:]     # Récent
            ]
            
            # Calculer les fréquences pour chaque segment
            segment_frequencies = []
            for segment in segments:
                freq_counter = Counter()
                for _, row in segment.iterrows():
                    for i in range(1, 21):
                        col_name = f'numero_{i}'
                        if col_name in row and pd.notna(row[col_name]):
                            freq_counter[int(row[col_name])] += 1
                
                # Normaliser
                total = sum(freq_counter.values())
                freq_normalized = {n: count / total for n, count in freq_counter.items()}
                segment_frequencies.append(freq_normalized)
            
            # Analyser les tendances (évolution entre segments)
            trends = {}
            for numero in range(self.min_number, self.max_number + 1):
                freqs = [seg.get(numero, 0) for seg in segment_frequencies]
                
                # Calculer la tendance (régression linéaire simple)
                x = np.array([0, 1, 2])  # Segments
                y = np.array(freqs)
                
                if len(y) > 1 and np.std(y) > 0:
                    # Coefficient de corrélation comme indicateur de tendance
                    correlation = np.corrcoef(x, y)[0, 1]
                    slope = np.polyfit(x, y, 1)[0]
                else:
                    correlation = 0
                    slope = 0
                
                trends[numero] = {
                    'frequencies': freqs,
                    'correlation': correlation,
                    'slope': slope,
                    'trend_direction': 'up' if slope > 0 else 'down' if slope < 0 else 'stable',
                    'trend_strength': abs(correlation)
                }
            
            # Identifier les numéros avec les tendances les plus marquées
            trending_up = []
            trending_down = []
            
            for numero, trend_data in trends.items():
                if trend_data['trend_strength'] > 0.5:  # Seuil de significativité
                    if trend_data['slope'] > 0:
                        trending_up.append({
                            'numero': numero,
                            'slope': trend_data['slope'],
                            'strength': trend_data['trend_strength']
                        })
                    else:
                        trending_down.append({
                            'numero': numero,
                            'slope': trend_data['slope'],
                            'strength': trend_data['trend_strength']
                        })
            
            # Trier par force de tendance
            trending_up.sort(key=lambda x: x['strength'], reverse=True)
            trending_down.sort(key=lambda x: x['strength'], reverse=True)
            
            result = {
                'trends': trends,
                'trending_up': trending_up,
                'trending_down': trending_down,
                'segment_size': segment_size,
                'window_size': len(df_recent),
                'analysis_timestamp': datetime.now().isoformat()
            }
            
            logger.info("Analyse des tendances temporelles terminée.")
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse des tendances: {e}")
            return {}

