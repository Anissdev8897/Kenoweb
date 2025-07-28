#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module de backtesting pour le Keno
Permet de tester les stratégies sur des données historiques
"""

import pandas as pd
import numpy as np
from collections import Counter, defaultdict
from typing import Dict, List, Any, Optional, Tuple, Callable
import logging
from datetime import datetime, timedelta
import json
import matplotlib.pyplot as plt
import seaborn as sns

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("keno_backtest_log.txt"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("KenoBacktesting")

class KenoBacktester:
    """Système de backtesting pour les stratégies Keno"""
    
    def __init__(self):
        self.min_number = 1
        self.max_number = 70
        self.numbers_per_draw = 20
        
        # Barèmes de gains Keno (approximatifs)
        self.gain_tables = {
            4: {0: 0, 1: 0, 2: 2, 3: 22, 4: 72},
            5: {0: 0, 1: 0, 2: 0, 3: 2, 4: 12, 5: 320},
            6: {0: 0, 1: 0, 2: 0, 3: 1, 4: 3, 5: 22, 6: 1000},
            7: {0: 0, 1: 0, 2: 0, 3: 1, 4: 2, 5: 12, 6: 100, 7: 2500},
            8: {0: 0, 1: 0, 2: 0, 3: 0, 4: 1, 5: 5, 6: 25, 7: 200, 8: 5000},
            9: {0: 0, 1: 0, 2: 0, 3: 0, 4: 1, 5: 3, 6: 15, 7: 75, 8: 500, 9: 10000},
            10: {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 2, 6: 8, 7: 40, 8: 200, 9: 1000, 10: 25000}
        }
        
    def calculate_winnings(self, predicted_numbers: List[int], 
                         drawn_numbers: List[int], bet_amount: float = 1.0) -> Dict[str, Any]:
        """
        Calcule les gains pour une prédiction donnée.
        
        Args:
            predicted_numbers: Numéros prédits
            drawn_numbers: Numéros tirés
            bet_amount: Montant de la mise
            
        Returns:
            Dict contenant les détails des gains
        """
        try:
            num_predicted = len(predicted_numbers)
            if num_predicted not in self.gain_tables:
                logger.warning(f"Nombre de numéros non supporté: {num_predicted}")
                return {
                    'matches': 0,
                    'gross_winnings': 0.0,
                    'net_winnings': -bet_amount,
                    'roi': -100.0,
                    'bet_amount': bet_amount
                }
            
            # Calculer les correspondances
            matches = len(set(predicted_numbers) & set(drawn_numbers))
            
            # Calculer les gains bruts
            gain_table = self.gain_tables[num_predicted]
            gross_winnings = gain_table.get(matches, 0) * bet_amount
            
            # Calculer les gains nets
            net_winnings = gross_winnings - bet_amount
            
            # Calculer le ROI
            roi = (net_winnings / bet_amount * 100) if bet_amount > 0 else 0
            
            return {
                'matches': matches,
                'gross_winnings': gross_winnings,
                'net_winnings': net_winnings,
                'roi': roi,
                'bet_amount': bet_amount,
                'predicted_numbers': predicted_numbers,
                'drawn_numbers': drawn_numbers
            }
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul des gains: {e}")
            return {
                'matches': 0,
                'gross_winnings': 0.0,
                'net_winnings': -bet_amount,
                'roi': -100.0,
                'bet_amount': bet_amount
            }
    
    def backtest_strategy(self, df: pd.DataFrame, 
                         strategy_function: Callable,
                         strategy_params: Dict[str, Any] = None,
                         lookback_window: int = 50,
                         bet_amount: float = 1.0,
                         start_index: int = None,
                         end_index: int = None) -> Dict[str, Any]:
        """
        Effectue le backtesting d'une stratégie.
        
        Args:
            df: DataFrame des tirages historiques
            strategy_function: Fonction de stratégie à tester
            strategy_params: Paramètres de la stratégie
            lookback_window: Fenêtre d'analyse pour la stratégie
            bet_amount: Montant de la mise par tirage
            start_index: Index de début du test
            end_index: Index de fin du test
            
        Returns:
            Dict contenant les résultats du backtesting
        """
        logger.info("Début du backtesting de stratégie...")
        
        try:
            if strategy_params is None:
                strategy_params = {}
            
            # Définir les indices de test
            if start_index is None:
                start_index = lookback_window
            if end_index is None:
                end_index = len(df)
            
            if start_index >= end_index or start_index < lookback_window:
                raise ValueError("Indices de test invalides")
            
            results = []
            cumulative_winnings = 0.0
            total_bets = 0.0
            win_count = 0
            
            # Statistiques détaillées
            match_distribution = Counter()
            roi_history = []
            winning_streaks = []
            losing_streaks = []
            current_streak = 0
            last_result = None
            
            # Boucle de backtesting
            for i in range(start_index, end_index):
                try:
                    # Données d'entraînement (fenêtre glissante)
                    training_data = df.iloc[i-lookback_window:i]
                    
                    # Tirage actuel à prédire
                    current_draw = df.iloc[i]
                    actual_numbers = current_draw['numeros']
                    
                    if isinstance(actual_numbers, str):
                        actual_numbers = [int(x.strip()) for x in actual_numbers.split(',')]
                    elif isinstance(actual_numbers, list):
                        actual_numbers = [int(x) for x in actual_numbers]
                    
                    # Appliquer la stratégie
                    predicted_numbers = strategy_function(training_data, **strategy_params)
                    
                    if not predicted_numbers or not isinstance(predicted_numbers, list):
                        logger.warning(f"Prédiction invalide à l'index {i}")
                        continue
                    
                    # Calculer les gains
                    game_result = self.calculate_winnings(predicted_numbers, actual_numbers, bet_amount)
                    
                    # Mettre à jour les statistiques
                    cumulative_winnings += game_result['net_winnings']
                    total_bets += bet_amount
                    
                    if game_result['net_winnings'] > 0:
                        win_count += 1
                    
                    match_distribution[game_result['matches']] += 1
                    roi_history.append(game_result['roi'])
                    
                    # Gestion des séries
                    current_result = 'win' if game_result['net_winnings'] > 0 else 'loss'
                    if current_result == last_result:
                        current_streak += 1
                    else:
                        if last_result == 'win' and current_streak > 0:
                            winning_streaks.append(current_streak)
                        elif last_result == 'loss' and current_streak > 0:
                            losing_streaks.append(current_streak)
                        current_streak = 1
                        last_result = current_result
                    
                    # Ajouter aux résultats
                    game_result.update({
                        'draw_index': i,
                        'cumulative_winnings': cumulative_winnings,
                        'cumulative_roi': (cumulative_winnings / total_bets * 100) if total_bets > 0 else 0
                    })
                    results.append(game_result)
                    
                except Exception as e:
                    logger.warning(f"Erreur lors du test à l'index {i}: {e}")
                    continue
            
            # Finaliser les séries
            if last_result == 'win' and current_streak > 0:
                winning_streaks.append(current_streak)
            elif last_result == 'loss' and current_streak > 0:
                losing_streaks.append(current_streak)
            
            # Calculer les métriques finales
            total_games = len(results)
            win_rate = (win_count / total_games * 100) if total_games > 0 else 0
            average_roi = np.mean(roi_history) if roi_history else 0
            roi_std = np.std(roi_history) if roi_history else 0
            
            # Métriques de risque
            sharpe_ratio = (average_roi / roi_std) if roi_std > 0 else 0
            max_drawdown = self._calculate_max_drawdown([r['cumulative_winnings'] for r in results])
            
            backtest_summary = {
                'strategy_name': strategy_function.__name__,
                'strategy_params': strategy_params,
                'test_period': {
                    'start_index': start_index,
                    'end_index': end_index,
                    'total_games': total_games
                },
                'financial_metrics': {
                    'total_winnings': cumulative_winnings,
                    'total_bets': total_bets,
                    'final_roi': (cumulative_winnings / total_bets * 100) if total_bets > 0 else 0,
                    'average_roi_per_game': average_roi,
                    'roi_volatility': roi_std,
                    'sharpe_ratio': sharpe_ratio,
                    'max_drawdown': max_drawdown
                },
                'performance_metrics': {
                    'win_rate': win_rate,
                    'win_count': win_count,
                    'loss_count': total_games - win_count,
                    'match_distribution': dict(match_distribution),
                    'average_matches': np.mean([r['matches'] for r in results]) if results else 0
                },
                'streak_analysis': {
                    'max_winning_streak': max(winning_streaks) if winning_streaks else 0,
                    'max_losing_streak': max(losing_streaks) if losing_streaks else 0,
                    'average_winning_streak': np.mean(winning_streaks) if winning_streaks else 0,
                    'average_losing_streak': np.mean(losing_streaks) if losing_streaks else 0
                },
                'detailed_results': results,
                'backtest_date': datetime.now().isoformat()
            }
            
            logger.info(f"Backtesting terminé: {total_games} jeux, ROI final: {backtest_summary['financial_metrics']['final_roi']:.2f}%")
            return backtest_summary
            
        except Exception as e:
            logger.error(f"Erreur lors du backtesting: {e}")
            return {}
    
    def _calculate_max_drawdown(self, cumulative_returns: List[float]) -> float:
        """Calcule le drawdown maximum"""
        try:
            if not cumulative_returns:
                return 0.0
            
            peak = cumulative_returns[0]
            max_dd = 0.0
            
            for value in cumulative_returns:
                if value > peak:
                    peak = value
                
                drawdown = peak - value
                if drawdown > max_dd:
                    max_dd = drawdown
            
            return max_dd
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul du drawdown: {e}")
            return 0.0
    
    def compare_strategies(self, df: pd.DataFrame, 
                          strategies: Dict[str, Dict[str, Any]],
                          common_params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Compare plusieurs stratégies.
        
        Args:
            df: DataFrame des tirages
            strategies: Dict des stratégies à comparer
            common_params: Paramètres communs à toutes les stratégies
            
        Returns:
            Dict contenant la comparaison des stratégies
        """
        logger.info(f"Comparaison de {len(strategies)} stratégies...")
        
        try:
            if common_params is None:
                common_params = {}
            
            strategy_results = {}
            
            # Tester chaque stratégie
            for strategy_name, strategy_config in strategies.items():
                logger.info(f"Test de la stratégie: {strategy_name}")
                
                strategy_function = strategy_config['function']
                strategy_params = strategy_config.get('params', {})
                strategy_params.update(common_params)
                
                result = self.backtest_strategy(
                    df=df,
                    strategy_function=strategy_function,
                    strategy_params=strategy_params,
                    **common_params
                )
                
                strategy_results[strategy_name] = result
            
            # Créer le rapport de comparaison
            comparison = self._create_strategy_comparison(strategy_results)
            
            logger.info("Comparaison des stratégies terminée")
            return {
                'individual_results': strategy_results,
                'comparison': comparison,
                'comparison_date': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la comparaison des stratégies: {e}")
            return {}
    
    def _create_strategy_comparison(self, strategy_results: Dict[str, Any]) -> Dict[str, Any]:
        """Crée un rapport de comparaison des stratégies"""
        try:
            comparison = {
                'ranking': {},
                'metrics_comparison': {},
                'best_performers': {}
            }
            
            # Extraire les métriques clés
            metrics = ['final_roi', 'win_rate', 'sharpe_ratio', 'max_drawdown']
            
            for metric in metrics:
                metric_values = {}
                
                for strategy_name, result in strategy_results.items():
                    if result and 'financial_metrics' in result:
                        if metric in result['financial_metrics']:
                            value = result['financial_metrics'][metric]
                        elif metric in result['performance_metrics']:
                            value = result['performance_metrics'][metric]
                        else:
                            value = 0
                        
                        metric_values[strategy_name] = value
                
                # Classer les stratégies pour cette métrique
                if metric == 'max_drawdown':
                    # Pour le drawdown, plus petit est meilleur
                    ranked = sorted(metric_values.items(), key=lambda x: x[1])
                else:
                    # Pour les autres métriques, plus grand est meilleur
                    ranked = sorted(metric_values.items(), key=lambda x: x[1], reverse=True)
                
                comparison['metrics_comparison'][metric] = {
                    'ranking': ranked,
                    'best': ranked[0] if ranked else None,
                    'worst': ranked[-1] if ranked else None,
                    'average': np.mean(list(metric_values.values())) if metric_values else 0
                }
            
            # Classement global (basé sur le ROI final)
            if 'final_roi' in comparison['metrics_comparison']:
                roi_ranking = comparison['metrics_comparison']['final_roi']['ranking']
                comparison['ranking']['overall'] = roi_ranking
                comparison['best_performers']['highest_roi'] = roi_ranking[0] if roi_ranking else None
            
            # Meilleur taux de réussite
            if 'win_rate' in comparison['metrics_comparison']:
                win_rate_ranking = comparison['metrics_comparison']['win_rate']['ranking']
                comparison['best_performers']['highest_win_rate'] = win_rate_ranking[0] if win_rate_ranking else None
            
            # Meilleur ratio de Sharpe
            if 'sharpe_ratio' in comparison['metrics_comparison']:
                sharpe_ranking = comparison['metrics_comparison']['sharpe_ratio']['ranking']
                comparison['best_performers']['best_risk_adjusted'] = sharpe_ranking[0] if sharpe_ranking else None
            
            return comparison
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de la comparaison: {e}")
            return {}
    
    def monte_carlo_simulation(self, df: pd.DataFrame,
                             strategy_function: Callable,
                             strategy_params: Dict[str, Any] = None,
                             num_simulations: int = 1000,
                             simulation_length: int = 100) -> Dict[str, Any]:
        """
        Effectue une simulation Monte Carlo d'une stratégie.
        
        Args:
            df: DataFrame des tirages
            strategy_function: Fonction de stratégie
            strategy_params: Paramètres de la stratégie
            num_simulations: Nombre de simulations
            simulation_length: Longueur de chaque simulation
            
        Returns:
            Dict contenant les résultats de la simulation
        """
        logger.info(f"Simulation Monte Carlo: {num_simulations} simulations de {simulation_length} tirages...")
        
        try:
            if strategy_params is None:
                strategy_params = {}
            
            simulation_results = []
            
            for sim in range(num_simulations):
                # Sélectionner aléatoirement une période de test
                max_start = len(df) - simulation_length - 50  # 50 pour la fenêtre d'analyse
                if max_start <= 50:
                    logger.warning("Pas assez de données pour la simulation Monte Carlo")
                    break
                
                start_idx = np.random.randint(50, max_start)
                end_idx = start_idx + simulation_length
                
                # Effectuer le backtesting sur cette période
                sim_result = self.backtest_strategy(
                    df=df,
                    strategy_function=strategy_function,
                    strategy_params=strategy_params,
                    start_index=start_idx,
                    end_index=end_idx
                )
                
                if sim_result and 'financial_metrics' in sim_result:
                    simulation_results.append({
                        'simulation_id': sim,
                        'start_index': start_idx,
                        'end_index': end_idx,
                        'final_roi': sim_result['financial_metrics']['final_roi'],
                        'win_rate': sim_result['performance_metrics']['win_rate'],
                        'max_drawdown': sim_result['financial_metrics']['max_drawdown'],
                        'sharpe_ratio': sim_result['financial_metrics']['sharpe_ratio']
                    })
                
                if (sim + 1) % 100 == 0:
                    logger.info(f"Simulation {sim + 1}/{num_simulations} terminée")
            
            # Analyser les résultats
            if simulation_results:
                analysis = self._analyze_monte_carlo_results(simulation_results)
                
                return {
                    'simulation_params': {
                        'num_simulations': len(simulation_results),
                        'simulation_length': simulation_length,
                        'strategy_name': strategy_function.__name__,
                        'strategy_params': strategy_params
                    },
                    'results': simulation_results,
                    'analysis': analysis,
                    'simulation_date': datetime.now().isoformat()
                }
            else:
                logger.warning("Aucun résultat de simulation valide")
                return {}
            
        except Exception as e:
            logger.error(f"Erreur lors de la simulation Monte Carlo: {e}")
            return {}
    
    def _analyze_monte_carlo_results(self, simulation_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyse les résultats de simulation Monte Carlo"""
        try:
            metrics = ['final_roi', 'win_rate', 'max_drawdown', 'sharpe_ratio']
            analysis = {}
            
            for metric in metrics:
                values = [sim[metric] for sim in simulation_results if metric in sim and sim[metric] is not None]
                
                if values:
                    analysis[metric] = {
                        'mean': np.mean(values),
                        'std': np.std(values),
                        'min': np.min(values),
                        'max': np.max(values),
                        'percentiles': {
                            '5th': np.percentile(values, 5),
                            '25th': np.percentile(values, 25),
                            '50th': np.percentile(values, 50),
                            '75th': np.percentile(values, 75),
                            '95th': np.percentile(values, 95)
                        }
                    }
            
            # Probabilité de profit
            roi_values = [sim['final_roi'] for sim in simulation_results if 'final_roi' in sim]
            if roi_values:
                profit_probability = sum(1 for roi in roi_values if roi > 0) / len(roi_values) * 100
                analysis['profit_probability'] = profit_probability
            
            # Analyse de la stabilité
            roi_std = analysis.get('final_roi', {}).get('std', 0)
            roi_mean = analysis.get('final_roi', {}).get('mean', 0)
            
            if roi_mean != 0:
                stability_ratio = abs(roi_mean) / roi_std if roi_std > 0 else float('inf')
                analysis['stability_ratio'] = stability_ratio
            
            return analysis
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse Monte Carlo: {e}")
            return {}
    
    def generate_backtest_report(self, backtest_results: Dict[str, Any]) -> str:
        """
        Génère un rapport de backtesting.
        
        Args:
            backtest_results: Résultats du backtesting
            
        Returns:
            Rapport formaté en texte
        """
        report = []
        report.append("=" * 70)
        report.append("RAPPORT DE BACKTESTING KENO")
        report.append("=" * 70)
        report.append("")
        
        # Informations générales
        if 'strategy_name' in backtest_results:
            report.append(f"📊 STRATÉGIE TESTÉE: {backtest_results['strategy_name']}")
            report.append("-" * 50)
            
            test_period = backtest_results.get('test_period', {})
            report.append(f"Période de test: Index {test_period.get('start_index', 'N/A')} à {test_period.get('end_index', 'N/A')}")
            report.append(f"Nombre total de jeux: {test_period.get('total_games', 'N/A')}")
            report.append("")
        
        # Métriques financières
        financial = backtest_results.get('financial_metrics', {})
        if financial:
            report.append("💰 MÉTRIQUES FINANCIÈRES")
            report.append("-" * 30)
            report.append(f"ROI final: {financial.get('final_roi', 0):.2f}%")
            report.append(f"ROI moyen par jeu: {financial.get('average_roi_per_game', 0):.2f}%")
            report.append(f"Gains totaux: {financial.get('total_winnings', 0):.2f}€")
            report.append(f"Mises totales: {financial.get('total_bets', 0):.2f}€")
            report.append(f"Volatilité ROI: {financial.get('roi_volatility', 0):.2f}%")
            report.append(f"Ratio de Sharpe: {financial.get('sharpe_ratio', 0):.3f}")
            report.append(f"Drawdown maximum: {financial.get('max_drawdown', 0):.2f}€")
            report.append("")
        
        # Métriques de performance
        performance = backtest_results.get('performance_metrics', {})
        if performance:
            report.append("🎯 MÉTRIQUES DE PERFORMANCE")
            report.append("-" * 30)
            report.append(f"Taux de réussite: {performance.get('win_rate', 0):.2f}%")
            report.append(f"Jeux gagnants: {performance.get('win_count', 0)}")
            report.append(f"Jeux perdants: {performance.get('loss_count', 0)}")
            report.append(f"Correspondances moyennes: {performance.get('average_matches', 0):.2f}")
            
            # Distribution des correspondances
            match_dist = performance.get('match_distribution', {})
            if match_dist:
                report.append("Distribution des correspondances:")
                for matches, count in sorted(match_dist.items()):
                    percentage = (count / sum(match_dist.values()) * 100) if match_dist.values() else 0
                    report.append(f"  {matches} correspondances: {count} fois ({percentage:.1f}%)")
            report.append("")
        
        # Analyse des séries
        streaks = backtest_results.get('streak_analysis', {})
        if streaks:
            report.append("📈 ANALYSE DES SÉRIES")
            report.append("-" * 30)
            report.append(f"Plus longue série gagnante: {streaks.get('max_winning_streak', 0)}")
            report.append(f"Plus longue série perdante: {streaks.get('max_losing_streak', 0)}")
            report.append(f"Série gagnante moyenne: {streaks.get('average_winning_streak', 0):.1f}")
            report.append(f"Série perdante moyenne: {streaks.get('average_losing_streak', 0):.1f}")
            report.append("")
        
        # Recommandations
        report.append("💡 RECOMMANDATIONS")
        report.append("-" * 30)
        
        if financial.get('final_roi', 0) > 0:
            report.append("✅ Stratégie rentable sur la période testée")
        else:
            report.append("❌ Stratégie non rentable sur la période testée")
        
        if performance.get('win_rate', 0) > 30:
            report.append("✅ Taux de réussite acceptable")
        else:
            report.append("⚠️  Taux de réussite faible")
        
        if financial.get('sharpe_ratio', 0) > 1:
            report.append("✅ Bon ratio risque/rendement")
        elif financial.get('sharpe_ratio', 0) > 0.5:
            report.append("⚠️  Ratio risque/rendement modéré")
        else:
            report.append("❌ Ratio risque/rendement faible")
        
        report.append("")
        report.append("📝 NOTES:")
        report.append("• Les résultats passés ne garantissent pas les performances futures")
        report.append("• Tester sur différentes périodes pour valider la robustesse")
        report.append("• Considérer les coûts de transaction dans l'analyse")
        report.append("")
        
        report.append(f"Rapport généré le: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        report.append("=" * 70)
        
        return "\n".join(report)
    
    def save_backtest_results(self, results: Dict[str, Any], filename: str):
        """Sauvegarde les résultats de backtesting"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)
            logger.info(f"Résultats sauvegardés dans {filename}")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde: {e}")

# Stratégies d'exemple pour le backtesting
def random_strategy(training_data: pd.DataFrame, num_numbers: int = 5) -> List[int]:
    """Stratégie aléatoire simple"""
    import random
    return sorted(random.sample(range(1, 71), num_numbers))

def frequency_strategy(training_data: pd.DataFrame, num_numbers: int = 5) -> List[int]:
    """Stratégie basée sur les fréquences"""
    try:
        all_numbers = []
        for _, row in training_data.iterrows():
            if 'numeros' in row and row['numeros']:
                numbers = row['numeros']
                if isinstance(numbers, str):
                    numbers = [int(x.strip()) for x in numbers.split(',')]
                elif isinstance(numbers, list):
                    numbers = [int(x) for x in numbers]
                all_numbers.extend(numbers)
        
        if not all_numbers:
            return random_strategy(training_data, num_numbers)
        
        # Prendre les numéros les plus fréquents
        freq_counter = Counter(all_numbers)
        most_common = freq_counter.most_common(num_numbers)
        return sorted([num for num, _ in most_common])
        
    except Exception:
        return random_strategy(training_data, num_numbers)

def gap_strategy(training_data: pd.DataFrame, num_numbers: int = 5) -> List[int]:
    """Stratégie basée sur les écarts"""
    try:
        # Calculer les écarts pour chaque numéro
        gaps = {}
        for num in range(1, 71):
            gaps[num] = len(training_data)
        
        # Parcourir les tirages du plus récent au plus ancien
        for idx, (_, row) in enumerate(training_data.iloc[::-1].iterrows()):
            if 'numeros' in row and row['numeros']:
                numbers = row['numeros']
                if isinstance(numbers, str):
                    numbers = [int(x.strip()) for x in numbers.split(',')]
                elif isinstance(numbers, list):
                    numbers = [int(x) for x in numbers]
                
                for num in numbers:
                    if num in gaps and gaps[num] == len(training_data):
                        gaps[num] = idx
        
        # Prendre les numéros avec les plus gros écarts
        sorted_gaps = sorted(gaps.items(), key=lambda x: x[1], reverse=True)
        return sorted([num for num, _ in sorted_gaps[:num_numbers]])
        
    except Exception:
        return random_strategy(training_data, num_numbers)

def main():
    """Test du module de backtesting"""
    backtester = KenoBacktester()
    
    print("Test du module de backtesting Keno...")
    
    # Créer des données de test
    test_data = []
    for i in range(300):
        import random
        numbers = sorted(random.sample(range(1, 71), 20))
        test_data.append({
            'date': f"2024-{(i//30)+1:02d}-{(i%30)+1:02d}",
            'numeros': numbers
        })
    
    df = pd.DataFrame(test_data)
    
    # Test d'une stratégie simple
    print("Test de la stratégie de fréquence...")
    result = backtester.backtest_strategy(
        df=df,
        strategy_function=frequency_strategy,
        strategy_params={'num_numbers': 5},
        lookback_window=50,
        bet_amount=1.0
    )
    
    if result:
        print(f"ROI final: {result['financial_metrics']['final_roi']:.2f}%")
        print(f"Taux de réussite: {result['performance_metrics']['win_rate']:.2f}%")
        print(f"Nombre de jeux: {result['test_period']['total_games']}")
    
    # Test de comparaison de stratégies
    print("\nComparaison de stratégies...")
    strategies = {
        'Random': {'function': random_strategy, 'params': {'num_numbers': 5}},
        'Frequency': {'function': frequency_strategy, 'params': {'num_numbers': 5}},
        'Gap': {'function': gap_strategy, 'params': {'num_numbers': 5}}
    }
    
    comparison = backtester.compare_strategies(
        df=df,
        strategies=strategies,
        common_params={'lookback_window': 50, 'bet_amount': 1.0}
    )
    
    if comparison and 'comparison' in comparison:
        roi_ranking = comparison['comparison']['metrics_comparison'].get('final_roi', {}).get('ranking', [])
        if roi_ranking:
            print("Classement par ROI:")
            for i, (strategy, roi) in enumerate(roi_ranking, 1):
                print(f"  {i}. {strategy}: {roi:.2f}%")
    
    # Génération du rapport
    if result:
        report = backtester.generate_backtest_report(result)
        print(f"\n{report}")
    
    print("Test terminé avec succès!")

if __name__ == "__main__":
    main()

