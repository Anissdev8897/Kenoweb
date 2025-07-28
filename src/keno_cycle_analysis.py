#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module d'analyse de cycles pour le Keno
Adapté des méthodes avancées du Loto
"""

import pandas as pd
import numpy as np
from collections import Counter
from typing import Dict, List, Any, Optional, Tuple
import logging
import os
import time
from datetime import datetime, timedelta
import math

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("keno_cycle_log.txt"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("KenoCycleAnalysis")

class KenoCycleAnalyzer:
    """Analyseur de cycles pour le Keno"""
    
    def __init__(self):
        self.min_number = 1
        self.max_number = 70
        self.numbers_per_draw = 20
        self.theoretical_frequency = self.numbers_per_draw / self.max_number
        
    def calculate_frequencies_in_window(self, df_window: pd.DataFrame) -> Dict[str, Counter]:
        """
        Calcule les fréquences des numéros dans une fenêtre de tirages donnée.
        
        Args:
            df_window: DataFrame contenant les tirages dans la fenêtre d'analyse
            
        Returns:
            Dict contenant les compteurs de fréquence
        """
        try:
            if df_window.empty:
                logger.warning("DataFrame vide fourni pour le calcul des fréquences")
                return {"main_numbers": Counter()}
            
            main_numbers_in_window = []
            for _, row in df_window.iterrows():
                try:
                    if 'numeros' in row and row['numeros']:
                        numbers = row['numeros']
                        if isinstance(numbers, str):
                            numbers = [int(x.strip()) for x in numbers.split(',')]
                        elif isinstance(numbers, list):
                            numbers = [int(x) for x in numbers]
                        
                        main_numbers_in_window.extend(numbers)
                except Exception as e:
                    logger.warning(f"Erreur lors de l'extraction des numéros: {e}")
            
            main_freq = Counter(main_numbers_in_window)
            return {"main_numbers": main_freq}
        
        except Exception as e:
            logger.error(f"Erreur lors du calcul des fréquences dans la fenêtre: {e}")
            return {"main_numbers": Counter()}
    
    def analyze_cycles(self, df: pd.DataFrame, window_size: int, 
                      min_main_num: int = 1, max_main_num: int = 70) -> Dict[str, Any]:
        """
        Analyse les cycles de tirage en examinant les fréquences des numéros
        dans une fenêtre glissante.
        
        Args:
            df: DataFrame des tirages
            window_size: Taille de la fenêtre d'analyse
            min_main_num: Numéro minimum
            max_main_num: Numéro maximum
            
        Returns:
            Dict contenant l'analyse des cycles
        """
        logger.info(f"Analyse des cycles avec fenêtre de {window_size} tirages...")
        
        if len(df) < window_size:
            logger.warning(f"Pas assez de données pour la fenêtre {window_size}")
            return self._empty_cycle_result()
        
        try:
            # Prendre la fenêtre la plus récente
            df_window = df.tail(window_size)
            
            # Calculer les fréquences dans cette fenêtre
            frequencies = self.calculate_frequencies_in_window(df_window)
            main_freq = frequencies["main_numbers"]
            
            # Fréquence théorique dans cette fenêtre
            expected_frequency_in_window = window_size * self.theoretical_frequency
            
            # Analyser les déviations
            over_represented = {}
            under_represented = {}
            balanced = {}
            
            for num in range(min_main_num, max_main_num + 1):
                actual_freq = main_freq.get(num, 0)
                deviation = actual_freq - expected_frequency_in_window
                deviation_percentage = (deviation / expected_frequency_in_window * 100 
                                      if expected_frequency_in_window > 0 else 0)
                
                if deviation > expected_frequency_in_window * 0.2:  # +20% de la théorie
                    over_represented[num] = {
                        'frequency': actual_freq,
                        'expected': expected_frequency_in_window,
                        'deviation': deviation,
                        'deviation_percentage': deviation_percentage
                    }
                elif deviation < -expected_frequency_in_window * 0.2:  # -20% de la théorie
                    under_represented[num] = {
                        'frequency': actual_freq,
                        'expected': expected_frequency_in_window,
                        'deviation': deviation,
                        'deviation_percentage': deviation_percentage
                    }
                else:
                    balanced[num] = {
                        'frequency': actual_freq,
                        'expected': expected_frequency_in_window,
                        'deviation': deviation,
                        'deviation_percentage': deviation_percentage
                    }
            
            # Calcul des métriques de cycle
            cycle_metrics = self._calculate_cycle_metrics(df_window, main_freq)
            
            # Détection de patterns cycliques
            cyclical_patterns = self._detect_cyclical_patterns(df, window_size)
            
            results = {
                'window_size': window_size,
                'total_draws_in_window': len(df_window),
                'expected_frequency_per_number': expected_frequency_in_window,
                'over_represented': over_represented,
                'under_represented': under_represented,
                'balanced': balanced,
                'cycle_metrics': cycle_metrics,
                'cyclical_patterns': cyclical_patterns,
                'analysis_date': datetime.now().isoformat()
            }
            
            logger.info(f"Analyse des cycles terminée: {len(over_represented)} sur-représentés, "
                       f"{len(under_represented)} sous-représentés")
            
            return results
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse des cycles: {e}")
            return self._empty_cycle_result()
    
    def _calculate_cycle_metrics(self, df_window: pd.DataFrame, main_freq: Counter) -> Dict[str, Any]:
        """Calcule les métriques de cycle"""
        try:
            metrics = {}
            
            # Variance des fréquences
            frequencies = list(main_freq.values())
            if frequencies:
                metrics['frequency_variance'] = np.var(frequencies)
                metrics['frequency_std'] = np.std(frequencies)
                metrics['frequency_mean'] = np.mean(frequencies)
                metrics['frequency_range'] = max(frequencies) - min(frequencies)
            
            # Coefficient de variation
            if metrics.get('frequency_mean', 0) > 0:
                metrics['coefficient_of_variation'] = (metrics['frequency_std'] / 
                                                     metrics['frequency_mean'])
            
            # Entropie de Shannon (mesure de l'uniformité)
            total_numbers = sum(main_freq.values())
            if total_numbers > 0:
                entropy = 0
                for freq in main_freq.values():
                    if freq > 0:
                        p = freq / total_numbers
                        entropy -= p * math.log2(p)
                metrics['shannon_entropy'] = entropy
                
                # Entropie maximale théorique
                max_entropy = math.log2(self.max_number)
                metrics['entropy_ratio'] = entropy / max_entropy if max_entropy > 0 else 0
            
            # Indice de concentration (Herfindahl)
            if total_numbers > 0:
                herfindahl = sum((freq / total_numbers) ** 2 for freq in main_freq.values())
                metrics['herfindahl_index'] = herfindahl
                
                # Indice normalisé (0 = parfaitement uniforme, 1 = parfaitement concentré)
                n = self.max_number
                metrics['normalized_herfindahl'] = ((herfindahl - 1/n) / (1 - 1/n) 
                                                  if n > 1 else 0)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul des métriques de cycle: {e}")
            return {}
    
    def _detect_cyclical_patterns(self, df: pd.DataFrame, window_size: int) -> Dict[str, Any]:
        """Détecte les patterns cycliques"""
        try:
            patterns = {}
            
            if len(df) < window_size * 2:
                return patterns
            
            # Analyser les cycles de différentes longueurs
            cycle_lengths = [7, 14, 30]  # Cycles hebdomadaires, bi-hebdomadaires, mensuels
            
            for cycle_length in cycle_lengths:
                if len(df) >= cycle_length * 3:  # Au moins 3 cycles complets
                    cycle_analysis = self._analyze_cycle_length(df, cycle_length)
                    patterns[f'cycle_{cycle_length}'] = cycle_analysis
            
            # Analyse des tendances saisonnières
            seasonal_analysis = self._analyze_seasonal_patterns(df)
            patterns['seasonal'] = seasonal_analysis
            
            return patterns
            
        except Exception as e:
            logger.error(f"Erreur lors de la détection de patterns cycliques: {e}")
            return {}
    
    def _analyze_cycle_length(self, df: pd.DataFrame, cycle_length: int) -> Dict[str, Any]:
        """Analyse un cycle de longueur spécifique"""
        try:
            # Diviser les données en cycles
            cycles = []
            for i in range(0, len(df), cycle_length):
                cycle_data = df.iloc[i:i+cycle_length]
                if len(cycle_data) == cycle_length:
                    cycles.append(cycle_data)
            
            if len(cycles) < 2:
                return {}
            
            # Analyser chaque position dans le cycle
            position_analysis = {}
            for pos in range(cycle_length):
                position_frequencies = Counter()
                
                for cycle in cycles:
                    if pos < len(cycle):
                        row = cycle.iloc[pos]
                        if 'numeros' in row and row['numeros']:
                            numbers = row['numeros']
                            if isinstance(numbers, str):
                                numbers = [int(x.strip()) for x in numbers.split(',')]
                            elif isinstance(numbers, list):
                                numbers = [int(x) for x in numbers]
                            
                            position_frequencies.update(numbers)
                
                # Top numéros pour cette position
                top_numbers = position_frequencies.most_common(10)
                position_analysis[pos] = {
                    'top_numbers': top_numbers,
                    'total_occurrences': sum(position_frequencies.values()),
                    'unique_numbers': len(position_frequencies)
                }
            
            # Calculer la consistance du cycle
            consistency_score = self._calculate_cycle_consistency(position_analysis)
            
            return {
                'cycle_length': cycle_length,
                'number_of_cycles': len(cycles),
                'position_analysis': position_analysis,
                'consistency_score': consistency_score
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du cycle {cycle_length}: {e}")
            return {}
    
    def _calculate_cycle_consistency(self, position_analysis: Dict[str, Any]) -> float:
        """Calcule la consistance d'un cycle"""
        try:
            if not position_analysis:
                return 0.0
            
            # Calculer la variance des fréquences entre positions
            position_totals = [pos_data['total_occurrences'] 
                             for pos_data in position_analysis.values()]
            
            if not position_totals:
                return 0.0
            
            mean_total = np.mean(position_totals)
            if mean_total == 0:
                return 0.0
            
            variance = np.var(position_totals)
            consistency = 1.0 / (1.0 + variance / mean_total)
            
            return consistency
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul de consistance: {e}")
            return 0.0
    
    def _analyze_seasonal_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyse les patterns saisonniers"""
        try:
            seasonal = {}
            
            # Analyser par jour de la semaine (si les dates sont disponibles)
            if 'date' in df.columns:
                try:
                    df_copy = df.copy()
                    df_copy['date'] = pd.to_datetime(df_copy['date'], errors='coerce')
                    df_copy = df_copy.dropna(subset=['date'])
                    
                    if not df_copy.empty:
                        df_copy['day_of_week'] = df_copy['date'].dt.day_name()
                        
                        # Analyser les fréquences par jour de la semaine
                        day_analysis = {}
                        for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 
                                   'Friday', 'Saturday', 'Sunday']:
                            day_data = df_copy[df_copy['day_of_week'] == day]
                            if not day_data.empty:
                                day_freq = self.calculate_frequencies_in_window(day_data)
                                day_analysis[day] = {
                                    'count': len(day_data),
                                    'top_numbers': day_freq['main_numbers'].most_common(10)
                                }
                        
                        seasonal['day_of_week'] = day_analysis
                        
                        # Analyser par mois
                        df_copy['month'] = df_copy['date'].dt.month_name()
                        month_analysis = {}
                        for month in ['January', 'February', 'March', 'April', 'May', 'June',
                                     'July', 'August', 'September', 'October', 'November', 'December']:
                            month_data = df_copy[df_copy['month'] == month]
                            if not month_data.empty:
                                month_freq = self.calculate_frequencies_in_window(month_data)
                                month_analysis[month] = {
                                    'count': len(month_data),
                                    'top_numbers': month_freq['main_numbers'].most_common(10)
                                }
                        
                        seasonal['month'] = month_analysis
                        
                except Exception as e:
                    logger.warning(f"Erreur lors de l'analyse saisonnière: {e}")
            
            return seasonal
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse des patterns saisonniers: {e}")
            return {}
    
    def _empty_cycle_result(self) -> Dict[str, Any]:
        """Retourne un résultat vide en cas d'erreur"""
        return {
            'window_size': 0,
            'total_draws_in_window': 0,
            'expected_frequency_per_number': 0,
            'over_represented': {},
            'under_represented': {},
            'balanced': {},
            'cycle_metrics': {},
            'cyclical_patterns': {},
            'analysis_date': datetime.now().isoformat()
        }
    
    def analyze_multiple_windows(self, df: pd.DataFrame, 
                               window_sizes: List[int] = [10, 20, 50, 100]) -> Dict[str, Any]:
        """
        Analyse les cycles sur plusieurs tailles de fenêtres.
        
        Args:
            df: DataFrame des tirages
            window_sizes: Liste des tailles de fenêtres à analyser
            
        Returns:
            Dict contenant les analyses pour chaque fenêtre
        """
        logger.info("Analyse des cycles sur plusieurs fenêtres...")
        
        results = {}
        
        for window_size in window_sizes:
            if len(df) >= window_size:
                analysis = self.analyze_cycles(df, window_size)
                results[f'window_{window_size}'] = analysis
                logger.info(f"Fenêtre {window_size}: analyse terminée")
            else:
                logger.warning(f"Pas assez de données pour la fenêtre {window_size}")
        
        # Synthèse comparative
        if results:
            comparative_analysis = self._compare_window_analyses(results)
            results['comparative_analysis'] = comparative_analysis
        
        return results
    
    def _compare_window_analyses(self, window_results: Dict[str, Any]) -> Dict[str, Any]:
        """Compare les analyses de différentes fenêtres"""
        try:
            comparison = {}
            
            # Numéros consistamment sur-représentés
            over_represented_sets = []
            under_represented_sets = []
            
            for window_key, analysis in window_results.items():
                if isinstance(analysis, dict) and 'over_represented' in analysis:
                    over_represented_sets.append(set(analysis['over_represented'].keys()))
                    under_represented_sets.append(set(analysis['under_represented'].keys()))
            
            if over_represented_sets:
                # Intersection de tous les ensembles
                consistent_over = set.intersection(*over_represented_sets) if over_represented_sets else set()
                consistent_under = set.intersection(*under_represented_sets) if under_represented_sets else set()
                
                comparison['consistently_over_represented'] = list(consistent_over)
                comparison['consistently_under_represented'] = list(consistent_under)
                
                # Union de tous les ensembles
                all_over = set.union(*over_represented_sets) if over_represented_sets else set()
                all_under = set.union(*under_represented_sets) if under_represented_sets else set()
                
                comparison['sometimes_over_represented'] = list(all_over - consistent_over)
                comparison['sometimes_under_represented'] = list(all_under - consistent_under)
            
            # Métriques moyennes
            metrics_summary = {}
            metric_names = ['frequency_variance', 'shannon_entropy', 'herfindahl_index']
            
            for metric in metric_names:
                values = []
                for analysis in window_results.values():
                    if (isinstance(analysis, dict) and 'cycle_metrics' in analysis 
                        and metric in analysis['cycle_metrics']):
                        values.append(analysis['cycle_metrics'][metric])
                
                if values:
                    metrics_summary[metric] = {
                        'mean': np.mean(values),
                        'std': np.std(values),
                        'min': min(values),
                        'max': max(values)
                    }
            
            comparison['metrics_summary'] = metrics_summary
            
            return comparison
            
        except Exception as e:
            logger.error(f"Erreur lors de la comparaison des fenêtres: {e}")
            return {}
    
    def generate_cycle_report(self, cycle_analysis: Dict[str, Any]) -> str:
        """
        Génère un rapport complet d'analyse de cycles.
        
        Args:
            cycle_analysis: Résultats de l'analyse des cycles
            
        Returns:
            Rapport formaté en texte
        """
        report = []
        report.append("=" * 60)
        report.append("RAPPORT D'ANALYSE DE CYCLES KENO")
        report.append("=" * 60)
        report.append("")
        
        # Analyse par fenêtre
        for window_key, analysis in cycle_analysis.items():
            if window_key.startswith('window_') and isinstance(analysis, dict):
                window_size = analysis.get('window_size', 0)
                report.append(f"🔍 ANALYSE FENÊTRE {window_size} TIRAGES")
                report.append("-" * 40)
                
                # Numéros sur-représentés
                over_rep = analysis.get('over_represented', {})
                if over_rep:
                    report.append("📈 Numéros sur-représentés:")
                    for num, data in sorted(over_rep.items(), 
                                          key=lambda x: x[1]['deviation'], reverse=True)[:10]:
                        deviation_pct = data['deviation_percentage']
                        report.append(f"   {num:2d}: +{deviation_pct:+.1f}% (fréq: {data['frequency']:.1f})")
                
                # Numéros sous-représentés
                under_rep = analysis.get('under_represented', {})
                if under_rep:
                    report.append("📉 Numéros sous-représentés:")
                    for num, data in sorted(under_rep.items(), 
                                          key=lambda x: x[1]['deviation'])[:10]:
                        deviation_pct = data['deviation_percentage']
                        report.append(f"   {num:2d}: {deviation_pct:+.1f}% (fréq: {data['frequency']:.1f})")
                
                # Métriques de cycle
                metrics = analysis.get('cycle_metrics', {})
                if metrics:
                    report.append("📊 Métriques de cycle:")
                    if 'shannon_entropy' in metrics:
                        report.append(f"   Entropie Shannon: {metrics['shannon_entropy']:.3f}")
                        report.append(f"   Ratio d'entropie: {metrics.get('entropy_ratio', 0):.3f}")
                    if 'herfindahl_index' in metrics:
                        report.append(f"   Indice Herfindahl: {metrics['herfindahl_index']:.3f}")
                    if 'coefficient_of_variation' in metrics:
                        report.append(f"   Coefficient de variation: {metrics['coefficient_of_variation']:.3f}")
                
                report.append("")
        
        # Analyse comparative
        if 'comparative_analysis' in cycle_analysis:
            comp = cycle_analysis['comparative_analysis']
            report.append("🔄 ANALYSE COMPARATIVE")
            report.append("-" * 40)
            
            consistent_over = comp.get('consistently_over_represented', [])
            if consistent_over:
                report.append(f"Toujours sur-représentés: {consistent_over}")
            
            consistent_under = comp.get('consistently_under_represented', [])
            if consistent_under:
                report.append(f"Toujours sous-représentés: {consistent_under}")
            
            sometimes_over = comp.get('sometimes_over_represented', [])
            if sometimes_over:
                report.append(f"Parfois sur-représentés: {sometimes_over[:10]}")
            
            sometimes_under = comp.get('sometimes_under_represented', [])
            if sometimes_under:
                report.append(f"Parfois sous-représentés: {sometimes_under[:10]}")
            
            report.append("")
        
        # Recommandations
        report.append("💡 RECOMMANDATIONS STRATÉGIQUES")
        report.append("-" * 40)
        
        if 'comparative_analysis' in cycle_analysis:
            comp = cycle_analysis['comparative_analysis']
            consistent_over = comp.get('consistently_over_represented', [])
            consistent_under = comp.get('consistently_under_represented', [])
            
            if consistent_over:
                report.append(f"• Éviter temporairement: {consistent_over[:5]} (sur-représentés)")
            if consistent_under:
                report.append(f"• Privilégier: {consistent_under[:5]} (sous-représentés)")
            
            report.append("• Surveiller les numéros à comportement variable")
            report.append("• Adapter la stratégie selon la taille de fenêtre")
        
        report.append("• Combiner avec d'autres analyses pour optimiser")
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)

def main():
    """Test du module d'analyse de cycles"""
    analyzer = KenoCycleAnalyzer()
    
    print("Test du module d'analyse de cycles Keno...")
    
    # Créer des données de test avec patterns
    test_data = []
    for i in range(200):
        import random
        
        # Introduire des patterns cycliques
        if i % 10 < 5:  # Première moitié du cycle
            # Favoriser les numéros 1-35
            pool = list(range(1, 36)) * 2 + list(range(36, 71))
        else:  # Deuxième moitié du cycle
            # Favoriser les numéros 36-70
            pool = list(range(1, 36)) + list(range(36, 71)) * 2
        
        numbers = sorted(random.sample(pool, 20))
        test_data.append({
            'date': f"2024-{(i//30)+1:02d}-{(i%30)+1:02d}",
            'numeros': numbers
        })
    
    df = pd.DataFrame(test_data)
    
    # Analyse des cycles
    cycle_analysis = analyzer.analyze_multiple_windows(df, [20, 50, 100])
    
    # Affichage des résultats
    for window_key, analysis in cycle_analysis.items():
        if window_key.startswith('window_'):
            window_size = analysis.get('window_size', 0)
            over_rep = analysis.get('over_represented', {})
            under_rep = analysis.get('under_represented', {})
            
            print(f"\nFenêtre {window_size}:")
            print(f"  Sur-représentés: {len(over_rep)}")
            print(f"  Sous-représentés: {len(under_rep)}")
            
            if over_rep:
                top_over = sorted(over_rep.items(), 
                                key=lambda x: x[1]['deviation'], reverse=True)[:5]
                print(f"  Top sur-représentés: {[num for num, _ in top_over]}")
    
    # Génération du rapport
    report = analyzer.generate_cycle_report(cycle_analysis)
    print("\n" + report)
    
    print("Test terminé avec succès!")

if __name__ == "__main__":
    main()

