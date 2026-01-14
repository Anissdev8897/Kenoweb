#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module d'analyse des finales avancées pour le Keno
Analyse des chiffres des unités pour optimiser les prédictions
VERSION CORRIGÉE - Avec méthode train_model
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
        logging.FileHandler("keno_finales_log.txt"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("KenoFinalesAnalysis")

class KenoFinalesAnalyzer:
    """Analyseur de finales avancées pour le Keno"""
    
    def __init__(self):
        self.min_number = 1
        self.max_number = 70
        self.numbers_per_draw = 20
        self.finales = list(range(10))  # 0-9
        
        # Cache pour les analyses pré-calculées
        self.trained_analysis = None
        self.training_timestamp = None
        self.is_trained = False
        
    def train_model(self, df: pd.DataFrame, window_size: int = 100):
        """
        Entraîne l'analyseur en pré-calculant les analyses des finales.
        
        Args:
            df: DataFrame contenant l'historique des tirages
            window_size: Taille de la fenêtre d'analyse pour l'entraînement
        """
        logger.info("🔧 Entraînement de l'analyseur de finales...")
        
        try:
            if df.empty:
                logger.warning("DataFrame vide pour l'entraînement")
                self.is_trained = False
                return
            
            # Pré-calculer les analyses principales
            finales_analysis = self.calculate_finales_frequencies(df, window_size)
            patterns_analysis = self.analyze_finales_patterns(df, window_size)
            
            # Stocker les résultats d'entraînement
            self.trained_analysis = {
                'finales_frequencies': finales_analysis,
                'finales_patterns': patterns_analysis,
                'training_window_size': window_size,
                'training_data_size': len(df),
                'training_timestamp': datetime.now().isoformat()
            }
            
            self.training_timestamp = datetime.now()
            self.is_trained = True
            
            logger.info(f"✅ Analyseur de finales entraîné avec {len(df)} tirages")
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'entraînement de l'analyseur de finales: {e}")
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
        
    def calculate_finales_frequencies(self, df: pd.DataFrame, window_size: int = 50) -> Dict[str, Any]:
        """
        Calcule les fréquences des finales dans une fenêtre récente.
        
        Args:
            df: DataFrame contenant l'historique des tirages
            window_size: Taille de la fenêtre d'analyse
            
        Returns:
            Dict contenant les statistiques des finales
        """
        logger.info(f"Analyse des finales sur les {window_size} derniers tirages...")
        
        try:
            if df.empty:
                logger.warning("DataFrame vide fourni")
                return {}
            
            # Prendre les derniers tirages
            df_recent = df.tail(window_size).copy()
            
            # Compter les finales
            finales_counter = Counter()
            finales_by_position = defaultdict(Counter)
            
            for _, row in df_recent.iterrows():
                numeros = []
                for i in range(1, 21):
                    col_name = f'numero_{i}'
                    if col_name in row and pd.notna(row[col_name]):
                        numeros.append(int(row[col_name]))
                
                # Analyser les finales
                for pos, numero in enumerate(sorted(numeros)):
                    finale = numero % 10
                    finales_counter[finale] += 1
                    finales_by_position[pos][finale] += 1
            
            # Calculer les statistiques
            total_numeros = sum(finales_counter.values())
            finales_stats = {}
            
            for finale in self.finales:
                count = finales_counter[finale]
                frequency = count / total_numeros if total_numeros > 0 else 0
                expected = 0.1  # Fréquence théorique 10%
                deviation = frequency - expected
                
                finales_stats[finale] = {
                    'count': count,
                    'frequency': frequency,
                    'expected': expected,
                    'deviation': deviation,
                    'score': abs(deviation)
                }
            
            # Identifier les finales sous-représentées (candidates pour prédiction)
            finales_candidates = sorted(
                finales_stats.items(),
                key=lambda x: x[1]['deviation']  # Plus négatif = plus sous-représenté
            )
            
            result = {
                'finales_stats': finales_stats,
                'finales_candidates': finales_candidates,
                'total_analyzed': total_numeros,
                'window_size': len(df_recent),
                'analysis_timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Analyse des finales terminée. {total_numeros} numéros analysés.")
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse des finales: {e}")
            return {}
    
    def predict_numbers_by_finales(self, df: pd.DataFrame, nb_numbers: int = 8, 
                                 window_size: int = 50) -> List[int]:
        """
        Prédit des numéros basés sur l'analyse des finales.
        Utilise l'analyse pré-calculée si disponible.
        
        Args:
            df: DataFrame contenant l'historique des tirages
            nb_numbers: Nombre de numéros à prédire
            window_size: Taille de la fenêtre d'analyse
            
        Returns:
            Liste des numéros prédits
        """
        logger.info(f"Prédiction de {nb_numbers} numéros par analyse des finales...")
        
        try:
            # Utiliser l'analyse pré-calculée si disponible et récente
            if (self.is_trained and self.trained_analysis and 
                self.trained_analysis.get('finales_frequencies')):
                
                logger.info("Utilisation de l'analyse pré-calculée")
                finales_analysis = self.trained_analysis['finales_frequencies']
            else:
                # Calculer l'analyse à la volée
                logger.info("Calcul de l'analyse à la volée")
                finales_analysis = self.calculate_finales_frequencies(df, window_size)
            
            if not finales_analysis:
                logger.warning("Analyse des finales échouée, utilisation de numéros aléatoires")
                return sorted(np.random.choice(range(1, 71), nb_numbers, replace=False))
            
            # Sélectionner les finales les plus sous-représentées
            finales_candidates = finales_analysis['finales_candidates']
            selected_finales = []
            
            # Prendre les finales avec la plus grande déviation négative
            for finale, stats in finales_candidates:
                if stats['deviation'] < 0:  # Sous-représentée
                    selected_finales.append(finale)
                if len(selected_finales) >= nb_numbers:
                    break
            
            # Si pas assez de finales sous-représentées, compléter avec les moins fréquentes
            if len(selected_finales) < nb_numbers:
                remaining_finales = [f for f in self.finales if f not in selected_finales]
                remaining_finales.sort(key=lambda f: finales_analysis['finales_stats'][f]['frequency'])
                selected_finales.extend(remaining_finales[:nb_numbers - len(selected_finales)])
            
            # Générer des numéros pour chaque finale sélectionnée
            predicted_numbers = []
            
            for finale in selected_finales[:nb_numbers]:
                # Trouver tous les numéros avec cette finale
                numbers_with_finale = [n for n in range(1, 71) if n % 10 == finale]
                
                # Analyser la fréquence récente de ces numéros
                recent_frequencies = Counter()
                df_recent = df.tail(window_size)
                
                for _, row in df_recent.iterrows():
                    for i in range(1, 21):
                        col_name = f'numero_{i}'
                        if col_name in row and pd.notna(row[col_name]):
                            numero = int(row[col_name])
                            if numero in numbers_with_finale:
                                recent_frequencies[numero] += 1
                
                # Choisir le numéro le moins fréquent avec cette finale
                if recent_frequencies:
                    # Trier par fréquence croissante
                    candidates = sorted(numbers_with_finale, 
                                      key=lambda n: recent_frequencies.get(n, 0))
                else:
                    candidates = numbers_with_finale
                
                # Éviter les doublons
                for candidate in candidates:
                    if candidate not in predicted_numbers:
                        predicted_numbers.append(candidate)
                        break
            
            # Compléter si nécessaire
            while len(predicted_numbers) < nb_numbers:
                remaining = [n for n in range(1, 71) if n not in predicted_numbers]
                if remaining:
                    predicted_numbers.append(np.random.choice(remaining))
                else:
                    break
            
            result = sorted(predicted_numbers[:nb_numbers])
            logger.info(f"Prédiction par finales terminée: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de la prédiction par finales: {e}")
            return sorted(np.random.choice(range(1, 71), nb_numbers, replace=False))
    
    def analyze_finales_patterns(self, df: pd.DataFrame, window_size: int = 100) -> Dict[str, Any]:
        """
        Analyse les patterns avancés des finales.
        
        Args:
            df: DataFrame contenant l'historique des tirages
            window_size: Taille de la fenêtre d'analyse
            
        Returns:
            Dict contenant l'analyse des patterns
        """
        logger.info("Analyse des patterns de finales...")
        
        try:
            if df.empty:
                return {}
            
            df_recent = df.tail(window_size).copy()
            
            # Analyser les séquences de finales
            finales_sequences = []
            finales_pairs = Counter()
            finales_transitions = defaultdict(Counter)
            
            for _, row in df_recent.iterrows():
                numeros = []
                for i in range(1, 21):
                    col_name = f'numero_{i}'
                    if col_name in row and pd.notna(row[col_name]):
                        numeros.append(int(row[col_name]))
                
                # Extraire les finales du tirage
                finales_tirage = sorted([n % 10 for n in numeros])
                finales_sequences.append(finales_tirage)
                
                # Analyser les paires de finales
                for i in range(len(finales_tirage)):
                    for j in range(i + 1, len(finales_tirage)):
                        pair = tuple(sorted([finales_tirage[i], finales_tirage[j]]))
                        finales_pairs[pair] += 1
                
                # Analyser les transitions (si on a un tirage précédent)
                if len(finales_sequences) > 1:
                    prev_finales = set(finales_sequences[-2])
                    curr_finales = set(finales_tirage)
                    
                    for prev_f in prev_finales:
                        for curr_f in curr_finales:
                            finales_transitions[prev_f][curr_f] += 1
            
            # Calculer les statistiques des patterns
            most_common_pairs = finales_pairs.most_common(10)
            
            # Analyser les transitions les plus probables
            transition_probs = {}
            for from_finale, to_counter in finales_transitions.items():
                total = sum(to_counter.values())
                if total > 0:
                    transition_probs[from_finale] = {
                        to_finale: count / total 
                        for to_finale, count in to_counter.items()
                    }
            
            result = {
                'sequences_analyzed': len(finales_sequences),
                'most_common_pairs': most_common_pairs,
                'transition_probabilities': transition_probs,
                'total_pairs': len(finales_pairs),
                'analysis_timestamp': datetime.now().isoformat()
            }
            
            logger.info("Analyse des patterns de finales terminée.")
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse des patterns: {e}")
            return {}

