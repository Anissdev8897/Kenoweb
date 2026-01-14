#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module d'analyse de fréquence pour le Keno
Adapté des méthodes avancées du Loto
"""

import pandas as pd
import numpy as np
from collections import Counter
from typing import Dict, List, Tuple, Any, Optional
import logging
import os
import time
from datetime import datetime

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("keno_frequency_log.txt"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("KenoFrequencyAnalysis")

class KenoFrequencyAnalyzer:
    """Analyseur de fréquences pour le Keno"""
    
    def __init__(self, config=None):
        """
        Initialise l'analyseur de fréquences
        
        Args:
            config: Configuration Keno (None = détection automatique format 2025)
        """
        from keno_config import KenoConfig
        self.config = config or KenoConfig.get_current_config()
        self.min_number = self.config['min_number']
        self.max_number = self.config['max_number']
        self.numbers_per_draw = self.config['numbers_per_draw']
        self.version = self.config.get('version', 'new_2025')
        
    def calculate_number_frequencies(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calcule les fréquences absolues et relatives de chaque numéro Keno.
        
        Args:
            df: DataFrame contenant l'historique des tirages Keno
            
        Returns:
            Dict contenant les fréquences absolues et relatives
        """
        logger.info("Calcul des fréquences des numéros Keno...")
        
        try:
            if df.empty:
                logger.warning("DataFrame vide fourni")
                return self._empty_frequency_result()
            
            # Extraction de tous les numéros tirés
            all_numbers = []
            
            # Parcourir chaque tirage
            for _, row in df.iterrows():
                try:
                    # Les numéros sont dans la colonne 'numeros' sous forme de liste
                    if 'numeros' in row and row['numeros']:
                        numbers = row['numeros']
                        if isinstance(numbers, str):
                            # Si c'est une chaîne, la convertir en liste
                            numbers = [int(x.strip()) for x in numbers.split(',')]
                        elif isinstance(numbers, list):
                            numbers = [int(x) for x in numbers]
                        
                        all_numbers.extend(numbers)
                except Exception as e:
                    logger.warning(f"Erreur lors du traitement d'un tirage: {e}")
                    continue
            
            if not all_numbers:
                logger.warning("Aucun numéro valide trouvé")
                return self._empty_frequency_result()
            
            # Calcul des fréquences absolues
            freq_abs = Counter(all_numbers)
            total_numbers = len(all_numbers)
            
            # Calcul des fréquences relatives
            freq_rel = {num: count / total_numbers for num, count in freq_abs.items()}
            
            # Fréquences théoriques (chaque numéro devrait apparaître 20/70 = 28.57% du temps)
            theoretical_freq = self.numbers_per_draw / self.max_number
            
            # Écarts par rapport à la théorie
            freq_deviations = {}
            for num in range(self.min_number, self.max_number + 1):
                actual_freq = freq_rel.get(num, 0)
                freq_deviations[num] = actual_freq - theoretical_freq
            
            # Classification chaud/froid
            hot_numbers = sorted(freq_rel.items(), key=lambda x: x[1], reverse=True)[:15]
            cold_numbers = sorted(freq_rel.items(), key=lambda x: x[1])[:15]
            
            results = {
                "frequency_absolute": freq_abs,
                "frequency_relative": freq_rel,
                "theoretical_frequency": theoretical_freq,
                "frequency_deviations": freq_deviations,
                "hot_numbers": [num for num, _ in hot_numbers],
                "cold_numbers": [num for num, _ in cold_numbers],
                "total_draws": len(df),
                "total_numbers_drawn": total_numbers,
                "analysis_date": datetime.now().isoformat()
            }
            
            logger.info(f"Analyse de fréquence terminée: {len(df)} tirages analysés")
            return results
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul des fréquences: {e}")
            return self._empty_frequency_result()
    
    def _empty_frequency_result(self) -> Dict[str, Any]:
        """Retourne un résultat vide en cas d'erreur"""
        return {
            "frequency_absolute": Counter(),
            "frequency_relative": {},
            "theoretical_frequency": 0,
            "frequency_deviations": {},
            "hot_numbers": [],
            "cold_numbers": [],
            "total_draws": 0,
            "total_numbers_drawn": 0,
            "analysis_date": datetime.now().isoformat()
        }
    
    def analyze_frequency_windows(self, df: pd.DataFrame, window_sizes: List[int] = [10, 20, 50, 100]) -> Dict[str, Any]:
        """
        Analyse les fréquences sur différentes fenêtres temporelles.
        
        Args:
            df: DataFrame des tirages
            window_sizes: Tailles des fenêtres à analyser
            
        Returns:
            Dict contenant les analyses par fenêtre
        """
        logger.info("Analyse des fréquences par fenêtres temporelles...")
        
        results = {}
        
        for window_size in window_sizes:
            if len(df) < window_size:
                logger.warning(f"Pas assez de données pour la fenêtre {window_size}")
                continue
            
            # Prendre les derniers tirages
            recent_df = df.tail(window_size)
            
            # Analyser cette fenêtre
            window_analysis = self.calculate_number_frequencies(recent_df)
            results[f"window_{window_size}"] = window_analysis
            
            logger.info(f"Fenêtre {window_size}: {len(recent_df)} tirages analysés")
        
        return results
    
    def calculate_gaps(self, df: pd.DataFrame) -> Dict[int, int]:
        """
        Calcule les écarts (gaps) pour chaque numéro.
        
        Args:
            df: DataFrame des tirages
            
        Returns:
            Dict des écarts par numéro
        """
        logger.info("Calcul des écarts (gaps)...")
        
        gaps = {}
        
        # Initialiser tous les numéros avec l'écart maximum
        for num in range(self.min_number, self.max_number + 1):
            gaps[num] = len(df)
        
        # Parcourir les tirages du plus récent au plus ancien
        for idx, (_, row) in enumerate(df.iloc[::-1].iterrows()):
            try:
                if 'numeros' in row and row['numeros']:
                    numbers = row['numeros']
                    if isinstance(numbers, str):
                        numbers = [int(x.strip()) for x in numbers.split(',')]
                    elif isinstance(numbers, list):
                        numbers = [int(x) for x in numbers]
                    
                    # Mettre à jour l'écart pour les numéros de ce tirage
                    for num in numbers:
                        if num in gaps and gaps[num] == len(df):
                            gaps[num] = idx
                            
            except Exception as e:
                logger.warning(f"Erreur lors du calcul d'écart: {e}")
                continue
        
        logger.info("Calcul des écarts terminé")
        return gaps
    
    def analyze_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyse les patterns dans les tirages Keno.
        
        Args:
            df: DataFrame des tirages
            
        Returns:
            Dict contenant l'analyse des patterns
        """
        logger.info("Analyse des patterns...")
        
        patterns = {
            "sums": [],
            "even_odd_distribution": [],
            "consecutive_numbers": [],
            "decade_distribution": [],
            "number_spreads": []
        }
        
        for _, row in df.iterrows():
            try:
                if 'numeros' in row and row['numeros']:
                    numbers = row['numeros']
                    if isinstance(numbers, str):
                        numbers = [int(x.strip()) for x in numbers.split(',')]
                    elif isinstance(numbers, list):
                        numbers = [int(x) for x in numbers]
                    
                    numbers = sorted(numbers)
                    
                    # Somme des numéros
                    patterns["sums"].append(sum(numbers))
                    
                    # Distribution pair/impair
                    even_count = sum(1 for n in numbers if n % 2 == 0)
                    odd_count = len(numbers) - even_count
                    patterns["even_odd_distribution"].append((even_count, odd_count))
                    
                    # Numéros consécutifs
                    consecutive = 0
                    for i in range(len(numbers) - 1):
                        if numbers[i+1] == numbers[i] + 1:
                            consecutive += 1
                    patterns["consecutive_numbers"].append(consecutive)
                    
                    # Distribution par dizaines
                    decades = [0] * 7  # 1-10, 11-20, ..., 61-70
                    for num in numbers:
                        decade_idx = min((num - 1) // 10, 6)
                        decades[decade_idx] += 1
                    patterns["decade_distribution"].append(decades)
                    
                    # Écart entre min et max
                    if numbers:
                        spread = max(numbers) - min(numbers)
                        patterns["number_spreads"].append(spread)
                        
            except Exception as e:
                logger.warning(f"Erreur lors de l'analyse de pattern: {e}")
                continue
        
        # Calcul des statistiques
        pattern_stats = {}
        
        if patterns["sums"]:
            pattern_stats["average_sum"] = np.mean(patterns["sums"])
            pattern_stats["sum_std"] = np.std(patterns["sums"])
            pattern_stats["sum_range"] = (min(patterns["sums"]), max(patterns["sums"]))
        
        if patterns["even_odd_distribution"]:
            avg_even = np.mean([x[0] for x in patterns["even_odd_distribution"]])
            avg_odd = np.mean([x[1] for x in patterns["even_odd_distribution"]])
            pattern_stats["average_even_odd"] = (avg_even, avg_odd)
        
        if patterns["consecutive_numbers"]:
            pattern_stats["average_consecutive"] = np.mean(patterns["consecutive_numbers"])
        
        if patterns["number_spreads"]:
            pattern_stats["average_spread"] = np.mean(patterns["number_spreads"])
            pattern_stats["spread_std"] = np.std(patterns["number_spreads"])
        
        # Distribution par dizaines
        if patterns["decade_distribution"]:
            decade_totals = [0] * 7
            for distribution in patterns["decade_distribution"]:
                for i, count in enumerate(distribution):
                    decade_totals[i] += count
            
            total_numbers = sum(decade_totals)
            decade_percentages = [count / total_numbers * 100 if total_numbers > 0 else 0 
                                for count in decade_totals]
            pattern_stats["decade_distribution"] = decade_percentages
        
        results = {
            "raw_patterns": patterns,
            "pattern_statistics": pattern_stats,
            "analysis_date": datetime.now().isoformat()
        }
        
        logger.info("Analyse des patterns terminée")
        return results
    
    def generate_frequency_report(self, frequency_analysis: Dict[str, Any], 
                                 gap_analysis: Dict[int, int],
                                 pattern_analysis: Dict[str, Any]) -> str:
        """
        Génère un rapport complet d'analyse de fréquence.
        
        Args:
            frequency_analysis: Résultats de l'analyse de fréquence
            gap_analysis: Résultats de l'analyse des écarts
            pattern_analysis: Résultats de l'analyse des patterns
            
        Returns:
            Rapport formaté en texte
        """
        report = []
        report.append("=" * 60)
        report.append("RAPPORT D'ANALYSE DE FRÉQUENCE KENO")
        report.append("=" * 60)
        report.append("")
        
        # Informations générales
        report.append("📊 INFORMATIONS GÉNÉRALES")
        report.append("-" * 30)
        report.append(f"Nombre de tirages analysés: {frequency_analysis.get('total_draws', 0)}")
        report.append(f"Nombre total de numéros tirés: {frequency_analysis.get('total_numbers_drawn', 0)}")
        report.append(f"Fréquence théorique par numéro: {frequency_analysis.get('theoretical_frequency', 0):.4f}")
        report.append(f"Date d'analyse: {frequency_analysis.get('analysis_date', 'N/A')}")
        report.append("")
        
        # Numéros chauds
        hot_numbers = frequency_analysis.get('hot_numbers', [])
        if hot_numbers:
            report.append("🔥 TOP 15 NUMÉROS CHAUDS")
            report.append("-" * 30)
            freq_rel = frequency_analysis.get('frequency_relative', {})
            for i, num in enumerate(hot_numbers[:15], 1):
                freq = freq_rel.get(num, 0)
                report.append(f"{i:2d}. Numéro {num:2d} - Fréquence: {freq:.4f} ({freq*100:.2f}%)")
            report.append("")
        
        # Numéros froids
        cold_numbers = frequency_analysis.get('cold_numbers', [])
        if cold_numbers:
            report.append("❄️  TOP 15 NUMÉROS FROIDS")
            report.append("-" * 30)
            freq_rel = frequency_analysis.get('frequency_relative', {})
            for i, num in enumerate(cold_numbers[:15], 1):
                freq = freq_rel.get(num, 0)
                report.append(f"{i:2d}. Numéro {num:2d} - Fréquence: {freq:.4f} ({freq*100:.2f}%)")
            report.append("")
        
        # Écarts les plus importants
        if gap_analysis:
            sorted_gaps = sorted(gap_analysis.items(), key=lambda x: x[1], reverse=True)
            report.append("⏰ TOP 15 ÉCARTS LES PLUS IMPORTANTS")
            report.append("-" * 30)
            for i, (num, gap) in enumerate(sorted_gaps[:15], 1):
                report.append(f"{i:2d}. Numéro {num:2d} - Écart: {gap} tirages")
            report.append("")
        
        # Statistiques des patterns
        pattern_stats = pattern_analysis.get('pattern_statistics', {})
        if pattern_stats:
            report.append("📈 STATISTIQUES DES PATTERNS")
            report.append("-" * 30)
            
            if 'average_sum' in pattern_stats:
                report.append(f"Somme moyenne des tirages: {pattern_stats['average_sum']:.2f}")
                report.append(f"Écart-type des sommes: {pattern_stats.get('sum_std', 0):.2f}")
                sum_range = pattern_stats.get('sum_range', (0, 0))
                report.append(f"Plage des sommes: {sum_range[0]} - {sum_range[1]}")
            
            if 'average_even_odd' in pattern_stats:
                even_odd = pattern_stats['average_even_odd']
                report.append(f"Moyenne pair/impair: {even_odd[0]:.1f} pairs, {even_odd[1]:.1f} impairs")
            
            if 'average_consecutive' in pattern_stats:
                report.append(f"Numéros consécutifs moyens: {pattern_stats['average_consecutive']:.2f}")
            
            if 'average_spread' in pattern_stats:
                report.append(f"Écart moyen min-max: {pattern_stats['average_spread']:.2f}")
            
            report.append("")
        
        # Distribution par dizaines
        decade_dist = pattern_stats.get('decade_distribution', [])
        if decade_dist:
            report.append("📊 DISTRIBUTION PAR DIZAINES")
            report.append("-" * 30)
            decades = ["1-10", "11-20", "21-30", "31-40", "41-50", "51-60", "61-70"]
            for i, (decade, percentage) in enumerate(zip(decades, decade_dist)):
                report.append(f"{decade}: {percentage:.2f}%")
            report.append("")
        
        # Recommandations
        report.append("💡 RECOMMANDATIONS")
        report.append("-" * 30)
        
        if hot_numbers and cold_numbers:
            report.append("• Stratégie équilibrée: Mélanger numéros chauds et froids")
            report.append(f"• Numéros chauds recommandés: {hot_numbers[:5]}")
            report.append(f"• Numéros froids à surveiller: {cold_numbers[:5]}")
        
        if gap_analysis:
            big_gaps = [num for num, gap in gap_analysis.items() if gap > 10]
            if big_gaps:
                report.append(f"• Numéros avec gros écarts (>10): {big_gaps[:10]}")
        
        report.append("• Diversifier les stratégies selon les patterns observés")
        report.append("• Surveiller l'évolution des tendances sur plusieurs tirages")
        
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)

def main():
    """Test du module d'analyse de fréquence"""
    analyzer = KenoFrequencyAnalyzer()
    
    # Test avec des données simulées
    print("Test du module d'analyse de fréquence Keno...")
    
    # Créer des données de test
    test_data = []
    for i in range(100):
        # Simuler un tirage de 20 numéros parmi 70
        import random
        numbers = sorted(random.sample(range(1, 71), 20))
        test_data.append({
            'date': f"2024-01-{i+1:02d}",
            'numeros': numbers
        })
    
    df = pd.DataFrame(test_data)
    
    # Analyse de fréquence
    freq_analysis = analyzer.calculate_number_frequencies(df)
    print(f"Numéros chauds: {freq_analysis['hot_numbers'][:10]}")
    print(f"Numéros froids: {freq_analysis['cold_numbers'][:10]}")
    
    # Analyse des écarts
    gaps = analyzer.calculate_gaps(df)
    big_gaps = sorted(gaps.items(), key=lambda x: x[1], reverse=True)[:10]
    print(f"Plus gros écarts: {big_gaps}")
    
    # Analyse des patterns
    patterns = analyzer.analyze_patterns(df)
    pattern_stats = patterns['pattern_statistics']
    print(f"Somme moyenne: {pattern_stats.get('average_sum', 0):.2f}")
    
    # Génération du rapport
    report = analyzer.generate_frequency_report(freq_analysis, gaps, patterns)
    print("\n" + report)
    
    print("Test terminé avec succès!")

if __name__ == "__main__":
    main()

