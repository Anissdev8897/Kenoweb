#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module d'analyse des écarts pour le Keno
Analyse des écarts entre les tirages pour optimiser les prédictions
"""

import pandas as pd
import numpy as np
from collections import Counter, defaultdict
from typing import Dict, List, Any, Optional, Tuple
import logging
import os
import time
from datetime import datetime

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("keno_ecarts_log.txt"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("KenoEcartsAnalysis")

class KenoEcartsAnalyzer:
    """Analyseur d'écarts pour le Keno"""
    
    def __init__(self, config=None):
        """
        Initialise l'analyseur d'écarts
        
        Args:
            config: Configuration Keno (None = détection automatique format 2025)
        """
        from keno_config import KenoConfig
        self.config = config or KenoConfig.get_current_config()
        self.min_number = self.config['min_number']
        self.max_number = self.config['max_number']
        self.numbers_per_draw = self.config['numbers_per_draw']
        self.version = self.config.get('version', 'new_2025')
        
        # Cache pour les analyses pré-calculées
        self.trained_analysis = None
        self.training_timestamp = None
        self.is_trained = False
        
    def train_model(self, df: pd.DataFrame, window_size: int = 200):
        """
        Entraîne l'analyseur en pré-calculant les analyses d'écarts.
        
        Args:
            df: DataFrame contenant l'historique des tirages
            window_size: Taille de la fenêtre d'analyse pour l'entraînement
        """
        logger.info("🔧 Entraînement de l'analyseur d'écarts...")
        
        try:
            if df.empty:
                logger.warning("DataFrame vide pour l'entraînement")
                self.is_trained = False
                return
            
            # Pré-calculer les analyses principales
            ecarts_analysis = self.calculate_gaps_analysis(df, window_size)
            zero_gaps_analysis = self.analyze_zero_gaps(df, window_size)
            patterns_analysis = self.analyze_gap_patterns(df, window_size)
            
            # Stocker les résultats d'entraînement
            self.trained_analysis = {
                'gaps_analysis': ecarts_analysis,
                'zero_gaps_analysis': zero_gaps_analysis,
                'patterns_analysis': patterns_analysis,
                'training_window_size': window_size,
                'training_data_size': len(df),
                'training_timestamp': datetime.now().isoformat()
            }
            
            self.training_timestamp = datetime.now()
            self.is_trained = True
            
            logger.info(f"✅ Analyseur d'écarts entraîné avec {len(df)} tirages")
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'entraînement de l'analyseur d'écarts: {e}")
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
        
    def calculate_gaps_analysis(self, df: pd.DataFrame, window_size: int = 200) -> Dict[str, Any]:
        """
        Calcule l'analyse des écarts pour chaque numéro.
        
        Args:
            df: DataFrame contenant l'historique des tirages
            window_size: Taille de la fenêtre d'analyse
            
        Returns:
            Dict contenant l'analyse des écarts
        """
        logger.info(f"Analyse des écarts sur les {window_size} derniers tirages...")
        
        try:
            if df.empty or len(df) < window_size:
                logger.warning("Pas assez de données pour l'analyse des écarts")
                return {}
            
            # Prendre les derniers tirages
            df_recent = df.tail(window_size).copy()
            
            # Calculer les écarts pour chaque numéro
            gaps_data = {}
            
            for numero in range(self.min_number, self.max_number + 1):
                appearances = []
                
                # Trouver toutes les positions où le numéro apparaît
                for idx, (_, row) in enumerate(df_recent.iterrows()):
                    numeros_tirage = []
                    for i in range(1, 21):
                        col_name = f'numero_{i}'
                        if col_name in row and pd.notna(row[col_name]):
                            numeros_tirage.append(int(row[col_name]))
                    
                    if numero in numeros_tirage:
                        appearances.append(idx)
                
                # Calculer les écarts entre apparitions
                gaps = []
                if len(appearances) > 1:
                    for i in range(1, len(appearances)):
                        gap = appearances[i] - appearances[i-1]
                        gaps.append(gap)
                
                # Calculer l'écart depuis la dernière apparition
                current_gap = 0
                if appearances:
                    current_gap = len(df_recent) - 1 - appearances[-1]
                else:
                    current_gap = len(df_recent)  # Jamais apparu
                
                # Statistiques des écarts
                if gaps:
                    mean_gap = np.mean(gaps)
                    std_gap = np.std(gaps)
                    min_gap = min(gaps)
                    max_gap = max(gaps)
                    median_gap = np.median(gaps)
                else:
                    mean_gap = std_gap = min_gap = max_gap = median_gap = 0
                
                gaps_data[numero] = {
                    'appearances': len(appearances),
                    'gaps': gaps,
                    'current_gap': current_gap,
                    'mean_gap': mean_gap,
                    'std_gap': std_gap,
                    'min_gap': min_gap,
                    'max_gap': max_gap,
                    'median_gap': median_gap,
                    'gap_score': current_gap / (mean_gap + 1) if mean_gap > 0 else current_gap
                }
            
            # Identifier les numéros avec les plus grands écarts actuels
            high_gap_numbers = sorted(
                gaps_data.items(),
                key=lambda x: x[1]['current_gap'],
                reverse=True
            )
            
            # Identifier les numéros avec un score d'écart élevé
            high_score_numbers = sorted(
                gaps_data.items(),
                key=lambda x: x[1]['gap_score'],
                reverse=True
            )
            
            result = {
                'gaps_data': gaps_data,
                'high_gap_numbers': high_gap_numbers[:20],
                'high_score_numbers': high_score_numbers[:20],
                'window_size': len(df_recent),
                'analysis_timestamp': datetime.now().isoformat()
            }
            
            logger.info("Analyse des écarts terminée.")
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse des écarts: {e}")
            return {}
    
    def analyze_zero_gaps(self, df: pd.DataFrame, window_size: int = 100) -> Dict[str, Any]:
        """
        Analyse les numéros avec écart zéro (sortis au tirage précédent).
        
        Args:
            df: DataFrame contenant l'historique des tirages
            window_size: Taille de la fenêtre d'analyse
            
        Returns:
            Dict contenant l'analyse des écarts zéro
        """
        logger.info("Analyse des écarts zéro...")
        
        try:
            if df.empty or len(df) < 2:
                return {}
            
            df_recent = df.tail(window_size).copy()
            
            # Analyser les répétitions consécutives
            consecutive_repeats = Counter()
            zero_gap_frequencies = Counter()
            
            for i in range(1, len(df_recent)):
                # Numéros du tirage précédent
                prev_numbers = []
                for j in range(1, 21):
                    col_name = f'numero_{j}'
                    if col_name in df_recent.iloc[i-1] and pd.notna(df_recent.iloc[i-1][col_name]):
                        prev_numbers.append(int(df_recent.iloc[i-1][col_name]))
                
                # Numéros du tirage actuel
                curr_numbers = []
                for j in range(1, 21):
                    col_name = f'numero_{j}'
                    if col_name in df_recent.iloc[i] and pd.notna(df_recent.iloc[i][col_name]):
                        curr_numbers.append(int(df_recent.iloc[i][col_name]))
                
                # Trouver les répétitions (écart zéro)
                repeats = set(prev_numbers) & set(curr_numbers)
                
                for numero in repeats:
                    consecutive_repeats[numero] += 1
                    zero_gap_frequencies[numero] += 1
            
            # Calculer les probabilités de répétition
            total_opportunities = len(df_recent) - 1
            repeat_probabilities = {
                numero: count / total_opportunities 
                for numero, count in zero_gap_frequencies.items()
            }
            
            # Identifier les numéros qui se répètent le plus souvent
            most_repeating = consecutive_repeats.most_common(20)
            
            result = {
                'consecutive_repeats': dict(consecutive_repeats),
                'zero_gap_frequencies': dict(zero_gap_frequencies),
                'repeat_probabilities': repeat_probabilities,
                'most_repeating': most_repeating,
                'total_opportunities': total_opportunities,
                'analysis_timestamp': datetime.now().isoformat()
            }
            
            logger.info("Analyse des écarts zéro terminée.")
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse des écarts zéro: {e}")
            return {}
    
    def analyze_gap_patterns(self, df: pd.DataFrame, window_size: int = 150) -> Dict[str, Any]:
        """
        Analyse les patterns dans les écarts.
        
        Args:
            df: DataFrame contenant l'historique des tirages
            window_size: Taille de la fenêtre d'analyse
            
        Returns:
            Dict contenant l'analyse des patterns d'écarts
        """
        logger.info("Analyse des patterns d'écarts...")
        
        try:
            if df.empty:
                return {}
            
            df_recent = df.tail(window_size).copy()
            
            # Analyser les cycles d'apparition
            cycles_data = {}
            
            for numero in range(self.min_number, self.max_number + 1):
                appearances = []
                
                # Trouver les positions d'apparition
                for idx, (_, row) in enumerate(df_recent.iterrows()):
                    numeros_tirage = []
                    for i in range(1, 21):
                        col_name = f'numero_{i}'
                        if col_name in row and pd.notna(row[col_name]):
                            numeros_tirage.append(int(row[col_name]))
                    
                    if numero in numeros_tirage:
                        appearances.append(idx)
                
                # Analyser les cycles
                if len(appearances) >= 3:
                    gaps = [appearances[i] - appearances[i-1] for i in range(1, len(appearances))]
                    
                    # Détecter les patterns cycliques
                    gap_patterns = Counter(gaps)
                    most_common_gap = gap_patterns.most_common(1)[0] if gap_patterns else (0, 0)
                    
                    # Prédire le prochain écart basé sur le pattern
                    if gaps:
                        # Utiliser la moyenne pondérée des derniers écarts
                        recent_gaps = gaps[-3:] if len(gaps) >= 3 else gaps
                        weights = [0.5, 0.3, 0.2][:len(recent_gaps)]
                        predicted_gap = sum(g * w for g, w in zip(recent_gaps, weights))
                    else:
                        predicted_gap = most_common_gap[0]
                    
                    cycles_data[numero] = {
                        'appearances': len(appearances),
                        'gaps': gaps,
                        'gap_patterns': dict(gap_patterns),
                        'most_common_gap': most_common_gap,
                        'predicted_gap': predicted_gap,
                        'last_appearance': appearances[-1] if appearances else -1
                    }
            
            result = {
                'cycles_data': cycles_data,
                'window_size': len(df_recent),
                'analysis_timestamp': datetime.now().isoformat()
            }
            
            logger.info("Analyse des patterns d'écarts terminée.")
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse des patterns: {e}")
            return {}
    
    def predict_numbers_by_gaps(self, df: pd.DataFrame, nb_numbers: int = 8,
                               window_size: int = 200) -> List[int]:
        """
        Prédit des numéros basés sur l'analyse des écarts.
        Utilise l'analyse pré-calculée si disponible.
        
        Args:
            df: DataFrame contenant l'historique des tirages
            nb_numbers: Nombre de numéros à prédire
            window_size: Taille de la fenêtre d'analyse
            
        Returns:
            Liste des numéros prédits
        """
        logger.info(f"Prédiction de {nb_numbers} numéros par analyse des écarts...")
        
        try:
            # Utiliser l'analyse pré-calculée si disponible et récente
            if (self.is_trained and self.trained_analysis and 
                self.trained_analysis.get('gaps_analysis')):
                
                logger.info("Utilisation de l'analyse pré-calculée")
                gaps_analysis = self.trained_analysis['gaps_analysis']
            else:
                # Calculer l'analyse à la volée
                logger.info("Calcul de l'analyse à la volée")
                gaps_analysis = self.calculate_gaps_analysis(df, window_size)
            
            if not gaps_analysis:
                logger.warning("Analyse des écarts échouée, utilisation de numéros aléatoires")
                return sorted(np.random.choice(range(1, 71), nb_numbers, replace=False))
            
            gaps_data = gaps_analysis['gaps_data']
            
            # Stratégie: privilégier les numéros avec les plus grands écarts actuels
            # et un score d'écart élevé
            candidates = []
            
            for numero in range(self.min_number, self.max_number + 1):
                data = gaps_data.get(numero, {})
                
                current_gap = data.get('current_gap', 0)
                gap_score = data.get('gap_score', 0)
                mean_gap = data.get('mean_gap', 0)
                appearances = data.get('appearances', 0)
                
                # Score combiné
                # 1. Favoriser les grands écarts actuels
                gap_factor = current_gap * 2
                
                # 2. Favoriser les numéros avec un score d'écart élevé
                score_factor = gap_score * 3
                
                # 3. Pénaliser les numéros qui n'apparaissent jamais
                appearance_factor = min(appearances, 5) * 0.5
                
                # 4. Bonus pour les numéros qui dépassent leur écart moyen
                mean_bonus = max(0, current_gap - mean_gap) * 1.5
                
                final_score = gap_factor + score_factor + appearance_factor + mean_bonus
                
                candidates.append({
                    'numero': numero,
                    'score': final_score,
                    'current_gap': current_gap,
                    'gap_score': gap_score,
                    'appearances': appearances
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
            logger.info(f"Prédiction par écarts terminée: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de la prédiction par écarts: {e}")
            return sorted(np.random.choice(range(1, 71), nb_numbers, replace=False))

