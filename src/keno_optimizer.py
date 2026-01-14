#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module d'optimisation avancée pour le Keno
Améliore les estimations de gains et optimise les stratégies
"""

import numpy as np
from collections import Counter
import itertools
from math import comb

class KenoOptimizer:
    def __init__(self):
        # Barèmes Keno officiels (approximatifs)
        self.bareme_gains = {
            4: {
                0: 0, 1: 0, 2: 2, 3: 22, 4: 72
            },
            5: {
                0: 0, 1: 0, 2: 0, 3: 2, 4: 12, 5: 320
            },
            6: {
                0: 0, 1: 0, 2: 0, 3: 1, 4: 3, 5: 22, 6: 1000
            },
            7: {
                0: 0, 1: 0, 2: 0, 3: 1, 4: 2, 5: 12, 6: 100, 7: 2500
            }
        }
        
        # Probabilités théoriques Keno
        self.probabilites = self.calculer_probabilites_theoriques()
    
    def calculer_probabilites_theoriques(self):
        """Calcule les probabilités théoriques pour chaque nombre de bons numéros"""
        probabilites = {}
        
        for nb_joues in [4, 5, 6, 7]:
            probabilites[nb_joues] = {}
            
            for nb_bons in range(nb_joues + 1):
                # Probabilité d'avoir exactement nb_bons numéros corrects
                # sur nb_joues numéros joués (20 numéros tirés sur 70)
                
                # Combinaisons favorables
                favorables = comb(20, nb_bons) * comb(50, nb_joues - nb_bons)
                # Combinaisons totales
                totales = comb(70, nb_joues)
                
                probabilites[nb_joues][nb_bons] = favorables / totales
        
        return probabilites
    
    def calculer_esperance_gain(self, nb_numeros):
        """Calcule l'espérance de gain pour un nombre de numéros donné"""
        if nb_numeros not in self.bareme_gains:
            return 0
        
        esperance = 0
        for nb_bons, gain in self.bareme_gains[nb_numeros].items():
            prob = self.probabilites[nb_numeros].get(nb_bons, 0)
            esperance += prob * gain
        
        return esperance
    
    def analyser_rentabilite(self, combinaisons, mise_par_grille=1):
        """Analyse la rentabilité des combinaisons"""
        resultats = []
        
        for combo in combinaisons:
            nb_numeros = len(combo['numeros'])
            esperance = self.calculer_esperance_gain(nb_numeros)
            
            # ROI théorique
            roi = (esperance - mise_par_grille) / mise_par_grille * 100
            
            # Probabilité de gain (au moins 1€)
            prob_gain = 0
            if nb_numeros in self.probabilites:
                for nb_bons, gain in self.bareme_gains[nb_numeros].items():
                    if gain > 0:
                        prob_gain += self.probabilites[nb_numeros].get(nb_bons, 0)
            
            resultats.append({
                'combinaison': combo['numeros'],
                'strategie': combo['strategie'],
                'score_original': combo.get('score_moyen', 0),
                'esperance_gain': esperance,
                'roi_theorique': roi,
                'probabilite_gain': prob_gain,
                'mise': mise_par_grille
            })
        
        return resultats
    
    def optimiser_pour_objectif(self, numeros_predits, objectif_gain=50, budget_max=20):
        """Optimise les combinaisons pour atteindre un objectif de gain"""
        print(f"Optimisation pour objectif: {objectif_gain}€ avec budget max: {budget_max}€")
        
        meilleures_strategies = []
        
        # Tester différentes configurations
        for nb_numeros in [4, 5, 6]:
            for nb_grilles in range(1, budget_max + 1):
                if nb_grilles > budget_max:
                    break
                
                # Générer les meilleures combinaisons pour cette config
                top_numeros = [num for num, score in numeros_predits[:15]]
                
                combinaisons = []
                for i in range(nb_grilles):
                    # Sélectionner les numéros avec un peu de randomisation
                    base_numeros = top_numeros[:nb_numeros + 3]
                    combo = sorted(np.random.choice(base_numeros, nb_numeros, replace=False))
                    
                    if combo not in [c['numeros'] for c in combinaisons]:
                        combinaisons.append({
                            'numeros': combo,
                            'strategie': f'Optimisé {nb_numeros}N',
                            'score_moyen': np.mean([dict(numeros_predits)[n] for n in combo])
                        })
                
                # Calculer les métriques
                esperance_totale = sum(self.calculer_esperance_gain(nb_numeros) for _ in range(nb_grilles))
                cout_total = nb_grilles
                
                # Probabilité d'atteindre l'objectif (approximation)
                prob_objectif = self.estimer_probabilite_objectif(nb_numeros, nb_grilles, objectif_gain)
                
                meilleures_strategies.append({
                    'nb_numeros': nb_numeros,
                    'nb_grilles': nb_grilles,
                    'cout_total': cout_total,
                    'esperance_totale': esperance_totale,
                    'roi_theorique': (esperance_totale - cout_total) / cout_total * 100,
                    'prob_objectif': prob_objectif,
                    'combinaisons': combinaisons[:nb_grilles]
                })
        
        # Trier par probabilité d'atteindre l'objectif
        meilleures_strategies.sort(key=lambda x: x['prob_objectif'], reverse=True)
        
        return meilleures_strategies[:5]
    
    def estimer_probabilite_objectif(self, nb_numeros, nb_grilles, objectif_gain):
        """Estime la probabilité d'atteindre l'objectif de gain"""
        if nb_numeros not in self.bareme_gains:
            return 0
        
        # Probabilité qu'au moins une grille rapporte l'objectif
        gains_possibles = list(self.bareme_gains[nb_numeros].values())
        
        # Trouver les gains qui permettent d'atteindre l'objectif
        prob_objectif = 0
        for gain in gains_possibles:
            if gain >= objectif_gain:
                # Probabilité d'obtenir ce gain sur au moins une grille
                prob_gain = 0
                for nb_bons, g in self.bareme_gains[nb_numeros].items():
                    if g == gain and nb_bons in self.probabilites[nb_numeros]:
                        prob_gain = self.probabilites[nb_numeros][nb_bons]
                        break
                
                if prob_gain > 0:
                    # Probabilité qu'au moins une grille l'obtienne
                    prob_au_moins_une = 1 - (1 - prob_gain) ** nb_grilles
                    prob_objectif = max(prob_objectif, prob_au_moins_une)
        
        return prob_objectif
    
    def generer_rapport_optimisation(self, strategies, objectif_gain):
        """Génère un rapport d'optimisation"""
        rapport = []
        rapport.append("=== RAPPORT D'OPTIMISATION KENO ===\n")
        rapport.append(f"Objectif de gain: {objectif_gain}€\n")
        rapport.append("=" * 50 + "\n")
        
        for i, strategie in enumerate(strategies, 1):
            rapport.append(f"STRATÉGIE {i}:")
            rapport.append(f"  Configuration: {strategie['nb_grilles']} grilles de {strategie['nb_numeros']} numéros")
            rapport.append(f"  Coût total: {strategie['cout_total']}€")
            rapport.append(f"  Espérance de gain: {strategie['esperance_totale']:.2f}€")
            rapport.append(f"  ROI théorique: {strategie['roi_theorique']:.1f}%")
            rapport.append(f"  Probabilité d'atteindre {objectif_gain}€: {strategie['prob_objectif']:.1%}")
            rapport.append("")
            
            rapport.append("  Combinaisons:")
            for j, combo in enumerate(strategie['combinaisons'], 1):
                rapport.append(f"    Grille {j}: {combo['numeros']}")
            rapport.append("")
            rapport.append("-" * 40 + "\n")
        
        return "\n".join(rapport)

def main():
    """Test du module d'optimisation"""
    optimizer = KenoOptimizer()
    
    # Test avec des numéros prédits fictifs
    numeros_predits = [(i, 0.5 - i*0.01) for i in range(1, 71)]
    
    # Optimiser pour 50€
    strategies = optimizer.optimiser_pour_objectif(numeros_predits, 50, 20)
    
    # Générer le rapport
    rapport = optimizer.generer_rapport_optimisation(strategies, 50)
    print(rapport)
    
    # Afficher les probabilités théoriques
    print("=== PROBABILITÉS THÉORIQUES ===")
    for nb_numeros in [4, 5, 6]:
        esperance = optimizer.calculer_esperance_gain(nb_numeros)
        print(f"{nb_numeros} numéros - Espérance: {esperance:.3f}€")

if __name__ == "__main__":
    main()

